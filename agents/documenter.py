"""
Documenter Agent
Extracts business logic from code modules and produces structured technical specs.
On audit-retry runs it incorporates the auditor's feedback to improve quality.
Uses PromptHelper to separate prompt templates from agent logic.
"""

import json
from graph.state import WorkflowState
from utils.prompt_helper import PromptHelper
from utils.file_handler import save_json
from utils.output_formatter import print_step, print_error

_CODE_OPENING_CHARS = 500   # opening snippet per module — just enough for class-level context


def _normalize_documentation(raw) -> dict:
    """
    Coerce whatever the LLM returned into the canonical 6-key dict.

    The LLM frequently returns a module list instead of the 6-key schema.
    Rather than leaving the derived sections empty, this function synthesises
    business_rules, data_models, service_interfaces, overview, and technical_specs
    directly from the module-level data the LLM did provide.
    """
    # Unwrap {"modules": [...]} or {"module_docs": [...]} wrappers
    if isinstance(raw, dict):
        if raw.get("module_docs"):
            # Correct shape — fill any missing keys and return
            raw.setdefault("overview", "")
            raw.setdefault("business_rules", [])
            raw.setdefault("data_models", [])
            raw.setdefault("service_interfaces", [])
            raw.setdefault("technical_specs", "")
            return raw
        if "modules" in raw:
            raw = raw["modules"]
        else:
            # Unknown dict — fill missing keys and return as-is
            raw.setdefault("overview", "")
            raw.setdefault("business_rules", [])
            raw.setdefault("data_models", [])
            raw.setdefault("service_interfaces", [])
            raw.setdefault("module_docs", [])
            raw.setdefault("technical_specs", "")
            return raw

    if not isinstance(raw, list):
        return {
            "overview": "", "business_rules": [], "data_models": [],
            "service_interfaces": [], "module_docs": [], "technical_specs": "",
        }

    # ── Synthesise all 6 sections from the module list ────────────────────────
    module_docs:        list = []
    business_rules:     list = []
    data_models:        list = []
    service_interfaces: list = []

    _MODEL_LAYERS    = {"model", "entity", "dto", "domain"}
    _SERVICE_LAYERS  = {"service", "controller", "api", "repository"}
    _MODEL_KEYWORDS  = {"model", "entity", "dto", "record", "cheque", "transaction",
                        "user", "rate", "status", "request", "response"}
    _SERVICE_KEYWORDS = {"service", "controller", "handler", "manager", "processor",
                         "processor", "gateway", "facade"}

    for item in raw:
        name          = item.get("name",         item.get("module",        ""))
        layer         = item.get("layer",        "").lower()
        description   = item.get("description",  item.get("purpose",       ""))
        biz_logic     = item.get("businessLogic", item.get("business_logic",
                        item.get("businesslogic", "")))
        dependencies  = item.get("dependencies", [])
        error_handling = item.get("errorHandling", item.get("error_handling", ""))
        fields        = item.get("fields",   [])
        methods       = item.get("methods",  [])

        # module_docs — always add every module
        module_docs.append({
            "module":         name,
            "purpose":        description,
            "business_logic": biz_logic or description,
            "dependencies":   dependencies,
            "error_handling": error_handling,
        })

        # business_rules — use businessLogic as a rule entry
        if biz_logic and len(biz_logic) > 30:
            rule = biz_logic if len(biz_logic) <= 200 else biz_logic[:200].rsplit(" ", 1)[0] + "…"
            if rule not in business_rules:
                business_rules.append(rule)

        # data_models — model/entity/dto layer or name suggests a data class
        name_lower = name.lower()
        is_model = layer in _MODEL_LAYERS or any(k in name_lower for k in _MODEL_KEYWORDS)
        if is_model:
            data_models.append({
                "name":        name,
                "description": description,
                "fields":      fields if isinstance(fields, list) and fields else [],
            })

        # service_interfaces — service/controller/repository layer or service name
        is_service = layer in _SERVICE_LAYERS or any(k in name_lower for k in _SERVICE_KEYWORDS)
        if is_service:
            service_interfaces.append({
                "name":        name,
                "description": description,
                "methods":     methods if isinstance(methods, list) and methods else [],
            })

    # overview — join the first few module descriptions
    descriptions = [m.get("description", "") or m.get("businessLogic", "")
                    for m in raw if m.get("description") or m.get("businessLogic")]
    overview = " ".join(descriptions[:3]).strip()
    if not overview:
        overview = f"Banking/fintech system with {len(raw)} processing modules."

    # technical_specs — summarise layers present
    layers = sorted({item.get("layer", "") for item in raw if item.get("layer")})
    technical_specs = (
        f"Application layers: {', '.join(layers)}. "
        f"Spring Boot microservice architecture with {len(raw)} modules."
        if layers else f"Multi-module banking application with {len(raw)} components."
    )

    return {
        "overview":           overview[:600],
        "business_rules":     business_rules[:20],
        "data_models":        data_models,
        "service_interfaces": service_interfaces,
        "module_docs":        module_docs,
        "technical_specs":    technical_specs,
    }


def documenter_node(state: WorkflowState) -> dict:
    modules = state["modules"]
    feedback = state.get("audit_feedback", "")
    retries = state.get("audit_retries", 0)

    if feedback and retries > 0:
        print_step(
            "Documenter",
            f"Revising documentation (retry {retries}) — addressing audit feedback…",
            "warning",
        )
        system_variant = "retry"
        system_kwargs = {"feedback": feedback}
    else:
        print_step("Documenter", "Extracting business logic and creating technical specs…")
        system_variant = ""
        system_kwargs = {}

    # Build structured summaries using tree-sitter metadata — no raw code truncation.
    # Method signatures + field types convey far more signal per token than
    # a raw code snippet cut off mid-method.
    summaries = []
    for m in modules:
        # Format method signatures as readable strings: "ReturnType methodName(ParamType, ...)"
        method_sigs = []
        for meth in m.get("methods", [])[:12]:
            params = ", ".join(meth.get("parameters", [])) or ""
            ret    = meth.get("return_type", "void") or "void"
            method_sigs.append(f"{ret} {meth['name']}({params})")

        summaries.append({
            "name":         m["name"],
            "layer":        m["layer"],
            "description":  m["description"],
            "annotations":  m.get("annotations", []),
            "superclass":   m.get("superclass", ""),
            "implements":   m.get("implements", []),
            "field_types":  m.get("field_types", []),
            "dependencies": m.get("dependencies", []),
            "methods":      method_sigs,
            "code_opening": m.get("code", "")[:_CODE_OPENING_CHARS],
        })

    try:
        ph = PromptHelper("documenter")
        raw = ph.invoke_and_parse(
            system_variant=system_variant,
            system_kwargs=system_kwargs,
            max_tokens=6_144,
            modules_json=json.dumps(summaries, indent=2),
        )

        documentation = _normalize_documentation(raw)

        # Warn if the LLM ignored the schema (normalization had to rescue it)
        if isinstance(raw, list):
            print_step(
                "Documenter",
                "LLM returned a list instead of the required 6-key object — normalized automatically. "
                "business_rules/data_models/service_interfaces will be empty on this pass.",
                "warning",
            )
        elif isinstance(raw, dict) and "modules" in raw and len(raw) <= 2:
            print_step("Documenter", "LLM returned {modules:[...]} wrapper — normalized automatically.", "warning")

        save_json(documentation, "docs/documentation.json")

        rules_count = len(documentation.get("business_rules", []))
        models_count = len(documentation.get("data_models", []))
        print_step(
            "Documenter",
            f"Documentation created — {rules_count} business rules, {models_count} data models.",
            "success" if rules_count > 0 and models_count > 0 else "warning",
        )

        return {"documentation": documentation, "current_step": "documenter_complete"}

    except Exception as exc:
        msg = f"Documenter failed: {exc}"
        print_error(msg)
        return {
            "errors": [msg],
            "documentation": None,
            "current_step": "documenter_failed",
        }
