"""
Converter Agent
Rewrites each legacy Java module into a modern Spring Boot 3 / Java 17 microservice component.
Uses PromptHelper to separate prompt templates from agent logic.

Build-fix mode: when build_feedback is set (from BuildVerifier), only the failing
classes are re-converted using the SYSTEM_BUILDFIX prompt variant, then merged
back into the existing converted_modules list.
"""

import json
from typing import Dict, List, Set

from graph.state import WorkflowState
from utils.prompt_helper import PromptHelper
from utils.file_handler import save_json, save_text, load_json
from utils.output_formatter import print_step, print_conversion_summary, print_error


def _load_documentation(state: WorkflowState) -> dict:
    """Return documentation from state; fall back to the persisted JSON on disk."""
    docs = state.get("documentation")
    if docs and isinstance(docs, dict):
        return docs
    disk = load_json("docs/documentation.json")
    if disk and isinstance(disk, dict):
        print_step("Converter", "Loaded documentation from docs/documentation.json", "info")
        return disk
    return {}

# Conversion priority — lower number = converted first
_LAYER_ORDER = {
    "model": 0, "exception": 1, "repository": 2, "service": 3,
    "controller": 4, "dto": 5, "config": 6, "utility": 7, "infrastructure": 8,
}
_MAX_MODULES    = 15
_MAX_CODE_CHARS = 5_000


# ── Helpers for build-fix mode ────────────────────────────────────────────────

def _parse_failing_classes(build_feedback: str) -> Set[str]:
    """Extract class names from the feedback block produced by BuildVerifier."""
    classes: Set[str] = set()
    for line in build_feedback.splitlines():
        if line.startswith("Class:"):
            cls = line.removeprefix("Class:").strip()
            if cls:
                classes.add(cls)
    return classes


def _errors_for_class(build_feedback: str, class_name: str) -> str:
    """Pull the error lines that belong to one class out of the feedback block."""
    lines: List[str] = []
    capturing = False
    for line in build_feedback.splitlines():
        if line.startswith("Class:"):
            capturing = line.removeprefix("Class:").strip() == class_name
            continue
        if capturing:
            if line.startswith("Class:"):
                break
            lines.append(line)
    return "\n".join(lines).strip()


# ── Node ──────────────────────────────────────────────────────────────────────

def converter_node(state: WorkflowState) -> dict:
    modules        = state["modules"]
    documentation  = _load_documentation(state)
    build_feedback = state.get("build_feedback", "")
    build_retries  = state.get("build_retries", 0)
    existing_converted: List[Dict] = list(state.get("converted_modules") or [])

    module_docs = {d.get("module"): d for d in documentation.get("module_docs", [])}
    ph = PromptHelper("converter")

    # ── Build-fix mode ────────────────────────────────────────────────────────
    if build_feedback and build_retries > 0:
        failing = _parse_failing_classes(build_feedback)
        if not failing:
            # feedback present but unparseable — skip re-conversion
            print_step("Converter", "Build feedback present but no class names found; skipping re-conversion.", "warning")
            return {"converted_modules": existing_converted, "current_step": "converter_complete"}

        print_step(
            "Converter",
            f"Build-fix mode — re-converting {len(failing)} failing class(es): {', '.join(sorted(failing))}",
            "warning",
        )

        modules_to_fix = [m for m in modules if m.get("name") in failing]
        fixed: List[Dict] = []
        errors: List[str] = []

        for idx, mod in enumerate(modules_to_fix, 1):
            name = mod["name"]
            class_errors = _errors_for_class(build_feedback, name)
            print_step("Converter", f"  ({idx}/{len(modules_to_fix)}) Fixing {name}…")

            code_snippet = mod.get("code", "")
            if len(code_snippet) > _MAX_CODE_CHARS:
                code_snippet = code_snippet[:_MAX_CODE_CHARS] + "\n// … (truncated)"

            try:
                result = ph.invoke_and_parse(
                    system_variant="buildfix",
                    system_kwargs={"build_errors": class_errors or build_feedback[:1_000]},
                    temperature=0.1,
                    max_tokens=4_096,
                    name=name,
                    layer=mod.get("layer", "service"),
                    description=mod.get("description", ""),
                    dependencies_json=json.dumps(mod.get("dependencies", [])),
                    purpose=module_docs.get(name, {}).get("purpose", ""),
                    business_logic=module_docs.get(name, {}).get("business_logic", ""),
                    error_handling=module_docs.get(name, {}).get("error_handling", ""),
                    code_snippet=code_snippet,
                )
                if not isinstance(result, dict):
                    raise ValueError(f"Expected dict, got {type(result)}")

                java_code = result.get("java_code", "")
                if java_code:
                    file_name = f"converted/{result.get('name', name)}.java"
                    save_text(java_code, file_name)
                    result["file_path"] = file_name

                fixed.append(result)
                print_step("Converter", f"    ✓ {name} fixed", "success")

            except Exception as exc:
                msg = f"Fix failed for {name}: {exc}"
                errors.append(msg)
                print_step("Converter", f"    ✗ {name}: {str(exc)[:120]}", "error")

        # Merge: replace old entries for fixed classes, keep everything else
        fixed_names = {m.get("name") for m in fixed}
        merged = [m for m in existing_converted if m.get("name") not in fixed_names] + fixed
        save_json({"converted_modules": merged}, "converted/conversion_summary.json")

        from evaluation import converter_checks
        conv_eval = converter_checks.run_all(merged)
        save_json(conv_eval, "converted/converter_eval.json")
        _log_converter_eval(conv_eval)

        out: dict = {"converted_modules": merged, "converter_eval": conv_eval,
                     "current_step": "converter_complete"}
        if errors:
            out["errors"] = errors
        return out

    # ── Normal conversion mode ────────────────────────────────────────────────
    print_step("Converter", "Converting legacy modules to modern Java microservices…")

    ordered = sorted(
        modules,
        key=lambda m: (_LAYER_ORDER.get(m.get("layer", "utility"), 99), m.get("name", "")),
    )
    to_convert = ordered[:_MAX_MODULES]

    if len(ordered) > _MAX_MODULES:
        print_step("Converter", f"Limiting to {_MAX_MODULES} of {len(ordered)} modules.", "warning")

    converted_modules: List[Dict] = []
    errors_normal: List[str] = []

    for idx, mod in enumerate(to_convert, 1):
        name = mod["name"]
        print_step("Converter", f"({idx}/{len(to_convert)}) Converting {name}…")

        doc = module_docs.get(name, {})
        code_snippet = mod.get("code", "")
        if len(code_snippet) > _MAX_CODE_CHARS:
            code_snippet = code_snippet[:_MAX_CODE_CHARS] + "\n// … (truncated)"

        try:
            result = ph.invoke_and_parse(
                temperature=0.1,
                max_tokens=4_096,
                name=name,
                layer=mod.get("layer", "service"),
                description=mod.get("description", ""),
                dependencies_json=json.dumps(mod.get("dependencies", [])),
                purpose=doc.get("purpose", mod.get("description", "")),
                business_logic=doc.get("business_logic", ""),
                error_handling=doc.get("error_handling", ""),
                code_snippet=code_snippet,
            )
            if not isinstance(result, dict):
                raise ValueError(f"Expected dict, got {type(result)}")

            java_code = result.get("java_code", "")
            if java_code:
                file_name = f"converted/{result.get('name', name)}.java"
                save_text(java_code, file_name)
                result["file_path"] = file_name

            converted_modules.append(result)
            print_step("Converter", f"  ✓ {name} → {result.get('name', name)}", "success")

        except Exception as exc:
            msg = f"Failed to convert {name}: {exc}"
            errors_normal.append(msg)
            print_step("Converter", f"  ✗ {name}: {str(exc)[:120]}", "error")

    save_json({"converted_modules": converted_modules}, "converted/conversion_summary.json")
    print_conversion_summary(converted_modules)
    print_step(
        "Converter",
        f"Done — {len(converted_modules)} converted, {len(errors_normal)} failed.",
        "success" if not errors_normal else "warning",
    )

    from evaluation import converter_checks
    conv_eval = converter_checks.run_all(converted_modules)
    save_json(conv_eval, "converted/converter_eval.json")
    _log_converter_eval(conv_eval)

    out_normal: dict = {"converted_modules": converted_modules, "converter_eval": conv_eval,
                        "current_step": "converter_complete"}
    if errors_normal:
        out_normal["errors"] = errors_normal
    return out_normal


def _log_converter_eval(ev: dict):
    score = ev.get("overall_score", 0)
    level = "success" if score >= 80 else "warning" if score >= 60 else "error"
    print_step("Converter", f"Eval — overall {score}/100  |  "
               f"annotations {ev['spring_annotations']['score']}  |  "
               f"packages {ev['package_declarations']['score']}  |  "
               f"imports {ev['spring_imports']['score']}  |  "
               f"stubs {ev['no_stubs']['score']}", level)
