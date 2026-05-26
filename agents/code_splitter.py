"""
Code Splitter Agent — fully deterministic, zero LLM cost.

tree-sitter extracts every class / interface / enum declaration with:
  • full source code (complete, no truncation)
  • file-level imports
  • annotations  → layer via annotation map
  • superclass   → layer fallback + relationships
  • implements   → class relationships
  • field types  → internal dependency graph
  • method signatures → API surface

Layer assignment (no LLM):
  1. Spring/JPA annotation map (@Service, @Entity, etc.)
  2. Naming convention patterns (UserService → service, UserRepository → repository)
  3. Structural signals (extends Exception → exception, enum → model)
  4. Final fallback → "utility"

Description generation (no LLM):
  Built from method signatures, field types, and relationships.
  Descriptive enough for the Documenter to produce proper documentation.
"""

import re
from graph.state import WorkflowState
from utils.file_handler import save_json, save_text, ensure_output_dirs
from utils.output_formatter import print_step, print_modules_table, print_error

# ── tree-sitter node type sets ────────────────────────────────────────────────

_DECLARATION_TYPES = frozenset({
    "class_declaration",
    "interface_declaration",
    "enum_declaration",
    "annotation_type_declaration",
})

_TYPE_NODE_TYPES = frozenset({
    "type_identifier",
    "generic_type",
    "array_type",
})

# ── Layer inference — annotation map ─────────────────────────────────────────

_ANNOTATION_LAYER: dict[str, str] = {
    "Service":                  "service",
    "Transactional":            "service",
    "RestController":           "controller",
    "Controller":               "controller",
    "RequestMapping":           "controller",
    "FeignClient":              "controller",
    "Repository":               "repository",
    "Entity":                   "model",
    "Table":                    "model",
    "Embeddable":               "model",
    "MappedSuperclass":         "model",
    "Configuration":            "config",
    "SpringBootApplication":    "config",
    "EnableAutoConfiguration":  "config",
    "EnableWebSecurity":        "config",
    "Component":                "utility",
    "ControllerAdvice":         "utility",
    "RestControllerAdvice":     "utility",
    "Aspect":                   "infrastructure",
    "EnableCaching":            "infrastructure",
    "EnableAsync":              "infrastructure",
    "Scheduled":                "infrastructure",
}

# ── Layer inference — naming convention patterns ───────────────────────────

_NAME_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r".+Service(Impl)?$"),      "service"),
    (re.compile(r".+Manager$"),             "service"),
    (re.compile(r".+Processor$"),           "service"),
    (re.compile(r".+Handler$"),             "service"),
    (re.compile(r".+Facade$"),              "service"),
    (re.compile(r".+Orchestrator$"),        "service"),
    (re.compile(r".+Repository(Impl)?$"),   "repository"),
    (re.compile(r".+Repo$"),               "repository"),
    (re.compile(r".+DAO$"),                "repository"),
    (re.compile(r".+Controller$"),          "controller"),
    (re.compile(r".+Resource$"),            "controller"),
    (re.compile(r".+Endpoint$"),            "controller"),
    (re.compile(r".+Exception$"),           "exception"),
    (re.compile(r".+Error$"),               "exception"),
    (re.compile(r".+Config(uration)?$"),    "config"),
    (re.compile(r".+Application$"),         "config"),
    (re.compile(r".+Properties$"),          "config"),
    (re.compile(r".+DTO$"),                "dto"),
    (re.compile(r".+Request$"),             "dto"),
    (re.compile(r".+Response$"),            "dto"),
    (re.compile(r".+Helper$"),              "utility"),
    (re.compile(r".+Util(s)?$"),            "utility"),
    (re.compile(r".+Converter$"),           "utility"),
    (re.compile(r".+Mapper$"),              "utility"),
    (re.compile(r".+Validator$"),           "utility"),
    (re.compile(r".+Formatter$"),           "utility"),
]

_LAYER_LABELS: dict[str, str] = {
    "service":        "Service",
    "controller":     "REST controller",
    "repository":     "Repository",
    "model":          "Data model",
    "dto":            "DTO",
    "config":         "Configuration",
    "exception":      "Exception",
    "utility":        "Utility",
    "infrastructure": "Infrastructure component",
}

# ── Parser singleton ──────────────────────────────────────────────────────────

_PARSER = None

def _get_parser():
    global _PARSER
    if _PARSER is None:
        import tree_sitter_java as tsjava
        from tree_sitter import Language, Parser
        _PARSER = Parser(Language(tsjava.language()))
    return _PARSER


# ── CST navigation utilities ──────────────────────────────────────────────────

def _text(node, src: bytes) -> str:
    return src[node.start_byte:node.end_byte].decode("utf-8")

def _child(node, *types):
    for c in node.children:
        if c.type in types:
            return c
    return None

def _type_name(node, src: bytes) -> str:
    if node.type == "type_identifier":
        return _text(node, src)
    if node.type == "generic_type":
        base = _child(node, "type_identifier")
        return _text(base, src) if base else ""
    if node.type == "array_type":
        inner = _child(node, "type_identifier", "generic_type")
        return _type_name(inner, src) if inner else ""
    return ""


# ── Extraction helpers ────────────────────────────────────────────────────────

def _extract_imports(root_node, src: bytes) -> list[str]:
    imports = []
    for child in root_node.children:
        if child.type == "import_declaration":
            path_node = _child(child, "scoped_identifier", "identifier")
            if path_node:
                imports.append(_text(path_node, src))
    return imports

def _extract_annotations(decl_node, src: bytes) -> list[str]:
    annotations = []
    modifiers = _child(decl_node, "modifiers")
    if not modifiers:
        return annotations
    for child in modifiers.children:
        if child.type in ("annotation", "marker_annotation"):
            name_node = _child(child, "identifier")
            if name_node:
                annotations.append(_text(name_node, src))
    return annotations

def _extract_superclass(decl_node, src: bytes) -> str:
    sc = _child(decl_node, "superclass")
    if sc:
        type_node = _child(sc, "type_identifier", "generic_type")
        if type_node:
            return _type_name(type_node, src)
    return ""

def _extract_implements(decl_node, src: bytes) -> list[str]:
    names = []
    si = _child(decl_node, "super_interfaces")
    if not si:
        return names
    type_list = _child(si, "interface_type_list", "type_list")
    if type_list:
        for child in type_list.children:
            if child.type in _TYPE_NODE_TYPES:
                n = _type_name(child, src)
                if n:
                    names.append(n)
    return names

def _extract_field_types(body_node, src: bytes) -> list[str]:
    types = []
    for child in body_node.children:
        if child.type == "field_declaration":
            type_node = _child(child, *_TYPE_NODE_TYPES)
            if type_node:
                n = _type_name(type_node, src)
                if n:
                    types.append(n)
    return types

def _extract_methods(body_node, src: bytes) -> list[dict]:
    _PRIMITIVE = frozenset({
        "void_type", "integral_type", "boolean_type", "floating_point_type", "void",
    })
    methods = []
    for child in body_node.children:
        if child.type == "method_declaration":
            name_node = _child(child, "identifier")
            if not name_node:
                continue
            ret = ""
            for c in child.children:
                if c.type in _TYPE_NODE_TYPES:
                    ret = _type_name(c, src)
                    break
                if c.type in _PRIMITIVE:
                    ret = _text(c, src)
                    break
            params = []
            fp = _child(child, "formal_parameters")
            if fp:
                for param in fp.children:
                    if param.type == "formal_parameter":
                        pt = _child(param, *_TYPE_NODE_TYPES)
                        if pt:
                            params.append(_type_name(pt, src))
            methods.append({"name": _text(name_node, src), "return_type": ret, "parameters": params})
    return methods


# ── Layer inference ───────────────────────────────────────────────────────────

def _infer_layer(annotations: list[str], superclass: str,
                 decl_type: str, name: str) -> str:
    """Fully deterministic — no LLM fallback needed."""
    # 1. Annotation map
    for ann in annotations:
        if ann in _ANNOTATION_LAYER:
            return _ANNOTATION_LAYER[ann]
    # 2. Structural signals
    if superclass and "Exception" in superclass:
        return "exception"
    if decl_type == "enum":
        return "model"
    if decl_type == "annotation_type":
        return "config"
    # 3. Naming conventions
    for pattern, layer in _NAME_PATTERNS:
        if pattern.match(name):
            return layer
    # 4. Final fallback
    return "utility"


# ── Description generation (no LLM) ──────────────────────────────────────────

def _generate_description(decl: dict) -> str:
    """
    Build a concise, informative description purely from structural metadata.
    Provides enough signal for the Documenter to produce proper documentation.
    """
    name       = decl["name"]
    layer      = decl.get("inferred_layer", "utility")
    methods    = decl.get("methods", [])
    fields     = decl.get("field_types", [])
    superclass = decl.get("superclass", "")
    implements = decl.get("implements", [])
    label      = _LAYER_LABELS.get(layer, decl["decl_type"].capitalize())

    method_names = [m["name"] for m in methods[:5]]

    if method_names:
        return f"{label} providing: {', '.join(method_names)}"
    if superclass:
        return f"{label} extending {superclass}"
    if implements:
        return f"{label} implementing {', '.join(implements[:2])}"
    if fields:
        return f"{label} with fields: {', '.join(fields[:4])}"
    return f"{label} {name}"


# ── CST walker ────────────────────────────────────────────────────────────────

def _collect_declarations(node, src: bytes, results: list):
    if node.type in _DECLARATION_TYPES:
        decl_type = node.type.replace("_declaration", "")
        name_node = _child(node, "identifier")
        if name_node:
            name        = _text(name_node, src)
            annotations = _extract_annotations(node, src)
            superclass  = _extract_superclass(node, src)
            implements  = _extract_implements(node, src)
            body        = _child(node, "class_body", "interface_body",
                                 "enum_body", "annotation_type_body")
            field_types = _extract_field_types(body, src) if body else []
            methods     = _extract_methods(body, src)     if body else []
            results.append({
                "name":        name,
                "decl_type":   decl_type,
                "code":        _text(node, src),
                "annotations": annotations,
                "superclass":  superclass,
                "implements":  implements,
                "field_types": field_types,
                "methods":     methods,
            })
    for child in node.children:
        _collect_declarations(child, src, results)


def _extract_all_declarations(source: str) -> tuple[list, list]:
    src_bytes = source.encode("utf-8")
    tree      = _get_parser().parse(src_bytes)
    imports   = _extract_imports(tree.root_node, src_bytes)
    results   = []
    _collect_declarations(tree.root_node, src_bytes, results)
    return results, imports


def _compute_dependencies(decl: dict, known_names: set) -> list[str]:
    candidates = set(decl["field_types"])
    for m in decl["methods"]:
        if m["return_type"]:
            candidates.add(m["return_type"])
        candidates.update(m["parameters"])
    return sorted(candidates & known_names - {decl["name"]})


# ── LangGraph node ────────────────────────────────────────────────────────────

def code_splitter_node(state: WorkflowState) -> dict:
    print_step("Code Splitter", "Analysing legacy source — identifying logical modules…")
    ensure_output_dirs()

    source_code = state["source_code"]
    print_step("Code Splitter", f"Source: {len(source_code):,} chars — parsing full file with tree-sitter.")

    try:
        declarations, imports = _extract_all_declarations(source_code)

        if not declarations:
            raise ValueError("tree-sitter found no class/interface/enum declarations.")

        # Deduplicate by name — keep first occurrence (source order)
        seen:   set  = set()
        unique: list = []
        for d in declarations:
            if d["name"] not in seen:
                seen.add(d["name"])
                d["inferred_layer"] = _infer_layer(
                    d["annotations"], d["superclass"], d["decl_type"], d["name"]
                )
                unique.append(d)

        known_names = {d["name"] for d in unique}

        # Build final modules — fully deterministic, zero LLM calls
        modules = []
        for d in unique:
            modules.append({
                "name":         d["name"],
                "description":  _generate_description(d),
                "code":         d["code"],
                "layer":        d["inferred_layer"],
                "dependencies": _compute_dependencies(d, known_names),
                "superclass":   d["superclass"],
                "implements":   d["implements"],
                "annotations":  d["annotations"],
                "methods":      d["methods"],
                "field_types":  d["field_types"],
                "imports":      imports,
            })

        save_json({"modules": modules}, "modules/modules.json")
        for mod in modules:
            save_text(mod["code"], f"modules/{mod['name']}.java")

        layer_counts = {}
        for m in modules:
            layer_counts[m["layer"]] = layer_counts.get(m["layer"], 0) + 1
        layer_summary = "  ".join(f"{l}:{c}" for l, c in sorted(layer_counts.items()))

        print_step("Code Splitter",
                   f"Identified {len(modules)} unique modules — {layer_summary}.", "success")
        print_modules_table(modules)

        return {"modules": modules, "current_step": "code_splitter_complete"}

    except Exception as exc:
        msg = f"Code Splitter failed: {exc}"
        print_error(msg)
        return {"errors": [msg], "modules": [], "current_step": "code_splitter_failed"}
