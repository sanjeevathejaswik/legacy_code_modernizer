"""
Joiner Agent (Reassembly node)
==============================
LangGraph node that:
  1. Builds a DependencyGraph from converted_modules
  2. Calls LLM (via PromptHelper) for project config (pom.xml, Dockerfile, yml)
     — enriched with documentation (technical_specs, data_models, service_interfaces)
  3. Uses CodeStitcher to write the full Maven project tree
  4. Returns assembly_result in the state
"""

import json
from typing import Dict

from graph.state import WorkflowState
from reassembly.dependency_graph import DependencyGraph
from reassembly.code_stitcher import CodeStitcher
from utils.prompt_helper import PromptHelper
from utils.file_handler import save_json, load_json
from utils.output_formatter import print_step, print_error


def _load_documentation(state: WorkflowState) -> dict:
    """Return documentation from state; fall back to the persisted JSON on disk."""
    docs = state.get("documentation")
    if docs and isinstance(docs, dict):
        return docs
    disk = load_json("docs/documentation.json")
    if disk and isinstance(disk, dict):
        print_step("Joiner", "Loaded documentation from docs/documentation.json", "info")
        return disk
    return {}


def joiner_node(state: WorkflowState) -> Dict:
    print_step("Joiner", "Analysing dependencies and assembling project structure…")

    converted_modules = state.get("converted_modules", [])
    test_suites       = state.get("test_suites", [])

    # Load persisted documentation for forward engineering context
    documentation      = _load_documentation(state)
    technical_specs    = documentation.get("technical_specs", "")
    data_models        = documentation.get("data_models", [])
    service_interfaces = documentation.get("service_interfaces", [])

    if not converted_modules:
        msg = "Joiner skipped — no converted modules in state."
        print_step("Joiner", msg, "warning")
        return {
            "assembly_result": None,
            "current_step":    "joiner_skipped",
            "errors":          [msg],
        }

    # ── 1. Build dependency graph ─────────────────────────────────────────────
    print_step("Joiner", "Building dependency graph…")
    graph      = DependencyGraph(converted_modules)
    graph_dict = graph.to_dict()

    cycles = graph_dict.get("circular_deps", [])
    if cycles:
        print_step("Joiner", f"  ⚠ {len(cycles)} circular dependency cycle(s) detected", "warning")

    save_json(graph_dict, "assembled/dependency_graph.json")

    # ── 2. Ask LLM for project config ─────────────────────────────────────────
    print_step("Joiner", "Generating Maven project configuration via LLM…")

    modules_summary = "\n".join(
        f"  [{m.get('microservice_type', m.get('layer', '?')):12s}] "
        f"{m.get('name', '?')}  →  {m.get('package', '?')}"
        for m in converted_modules
    )

    try:
        ph = PromptHelper("joiner")
        project_config = ph.invoke_and_parse(
            max_tokens=4_096,
            module_count=len(converted_modules),
            modules_summary=modules_summary,
            groups_json=json.dumps(graph_dict.get("microservice_groups", {}), indent=2),
            build_order_json=json.dumps(graph_dict.get("build_order", []), indent=2),
            cycles_json=json.dumps(cycles or ["none"], indent=2),
            technical_specs=technical_specs or "Not available.",
            data_models_json=json.dumps(data_models, indent=2) if data_models else "[]",
            service_interfaces_json=json.dumps(service_interfaces, indent=2) if service_interfaces else "[]",
        )

        if not isinstance(project_config, dict):
            raise ValueError(f"Expected dict from LLM, got {type(project_config)}")

    except Exception as exc:
        # Fall back to a minimal default config so stitching still runs
        print_step("Joiner", f"LLM config failed ({exc}); using defaults.", "warning")
        project_config = {
            "project_name":        "modernised-service",
            "group_id":            "com.bank.modernised",
            "artifact_id":         "modernised-service",
            "version":             "1.0.0-SNAPSHOT",
            "spring_boot_version": "3.2.0",
            "dependencies":        [],
        }

    save_json(project_config, "assembled/project_config.json")

    # ── 3. Stitch the full project tree ───────────────────────────────────────
    print_step("Joiner", "Writing Maven project tree to output/assembled/…")
    try:
        stitcher = CodeStitcher()
        manifest = stitcher.stitch(
            project_config=project_config,
            converted_modules=converted_modules,
            test_suites=test_suites,
            dep_graph_dict=graph_dict,
        )

        total = manifest.total_files
        print_step(
            "Joiner",
            f"Assembly complete — {total} files written "
            f"({len(manifest.source_files)} src, "
            f"{len(manifest.test_files)} tests, "
            f"{len(manifest.config_files)} config).",
            "success",
        )

        if manifest.warnings:
            for w in manifest.warnings:
                print_step("Joiner", f"  ⚠ {w}", "warning")

        assembly_result = {
            **manifest.to_dict(),
            "dependency_graph": graph_dict,
            "project_config":   project_config,
        }
        save_json(assembly_result, "assembled/assembly_result.json")

        from evaluation import joiner_checks
        joiner_eval = joiner_checks.run_all(assembly_result, converted_modules)
        save_json(joiner_eval, "assembled/joiner_eval.json")

        score = joiner_eval.get("overall_score", 0)
        level = "success" if score >= 80 else "warning" if score >= 60 else "error"
        print_step("Joiner", f"Eval — overall {score}/100  |  "
                   f"pom {joiner_eval['pom_xml']['score']}  |  "
                   f"dockerfile {joiner_eval['dockerfile']['score']}  |  "
                   f"app_yml {joiner_eval['app_yml']['score']}  |  "
                   f"manifest {joiner_eval['manifest']['score']}", level)

        return {
            "assembly_result": assembly_result,
            "joiner_eval":     joiner_eval,
            "current_step":    "joiner_complete",
        }

    except Exception as exc:
        msg = f"CodeStitcher failed: {exc}"
        print_error(msg)
        return {
            "assembly_result": None,
            "current_step":    "joiner_failed",
            "errors":          [msg],
        }
