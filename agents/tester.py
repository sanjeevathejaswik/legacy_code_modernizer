"""
Tester Agent
Generates JUnit 5 unit-test suites for each converted Spring Boot module.
Uses PromptHelper to separate prompt templates from agent logic.
Documentation produced by the Documenter agent is loaded from disk (docs/documentation.json)
and used to generate business-rule-aware tests.
"""

import json
from graph.state import WorkflowState
from utils.prompt_helper import PromptHelper
from utils.file_handler import save_json, save_text, load_json
from utils.output_formatter import print_step, print_test_summary, print_error


def _load_documentation(state: WorkflowState) -> dict:
    """Return documentation from state; fall back to the persisted JSON on disk."""
    docs = state.get("documentation")
    if docs and isinstance(docs, dict):
        return docs
    disk = load_json("docs/documentation.json")
    if disk and isinstance(disk, dict):
        print_step("Tester", "Loaded documentation from docs/documentation.json", "info")
        return disk
    return {}

_PRIORITY_TYPES = {"service", "controller", "repository"}
_MAX_SUITES = 10
_MAX_CODE_CHARS = 5_000


def tester_node(state: WorkflowState) -> dict:
    print_step("Tester", "Generating unit tests for converted modules…")

    converted = state.get("converted_modules", [])

    if not converted:
        print_error("No converted modules available — skipping test generation.")
        return {
            "test_suites": [],
            "current_step": "tester_complete",
            "processing_complete": True,
        }

    # Load persisted documentation for forward engineering context
    documentation    = _load_documentation(state)
    module_docs_map  = {d.get("module"): d for d in documentation.get("module_docs", [])}
    business_rules   = documentation.get("business_rules", [])[:10]  # cap to stay within token budget

    # Prioritise service / controller / repository modules
    prioritised = sorted(
        converted,
        key=lambda m: (
            0 if m.get("microservice_type", "") in _PRIORITY_TYPES else 1,
            m.get("name", ""),
        ),
    )
    to_test = prioritised[:_MAX_SUITES]

    if len(converted) > _MAX_SUITES:
        print_step(
            "Tester",
            f"Limiting to {_MAX_SUITES} of {len(converted)} modules.",
            "warning",
        )

    ph = PromptHelper("tester")
    test_suites: list = []
    errors: list = []

    for idx, mod in enumerate(to_test, 1):
        name = mod.get("name", f"Module{idx}")
        print_step("Tester", f"({idx}/{len(to_test)}) Generating tests for {name}…")

        java_code = mod.get("java_code", "")
        if len(java_code) > _MAX_CODE_CHARS:
            java_code = java_code[:_MAX_CODE_CHARS] + "\n// … (truncated)"

        # Pull module-specific forward engineering context
        doc            = module_docs_map.get(name, {})
        business_logic = doc.get("business_logic", "")
        error_handling = doc.get("error_handling", "")

        try:
            suite = ph.invoke_and_parse(
                temperature=0.1,
                max_tokens=4_096,
                name=name,
                microservice_type=mod.get("microservice_type", "service"),
                package=mod.get("package", "com.bank.service"),
                dependencies_json=json.dumps(mod.get("dependencies", [])),
                java_code=java_code,
                business_logic=business_logic,
                error_handling=error_handling,
                business_rules_json=json.dumps(business_rules),
            )

            if not isinstance(suite, dict):
                raise ValueError(f"Expected dict response, got {type(suite)}")

            # Persist the test file
            test_code = suite.get("test_code", "")
            if test_code:
                test_class = suite.get("test_class_name", f"{name}Test")
                file_name = f"tests/{test_class}.java"
                save_text(test_code, file_name)
                suite["file_path"] = file_name

            test_suites.append(suite)
            print_step(
                "Tester",
                f"  ✓ {name}: {suite.get('test_count', '?')} tests",
                "success",
            )

        except Exception as exc:
            msg = f"Failed to generate tests for {name}: {exc}"
            errors.append(msg)
            print_step("Tester", f"  ✗ {name}: {str(exc)[:120]}", "error")

    save_json({"test_suites": test_suites}, "tests/test_suites_summary.json")
    print_test_summary(test_suites)
    print_step(
        "Tester",
        f"Done — {len(test_suites)} test suites generated, {len(errors)} failed.",
        "success" if not errors else "warning",
    )

    # ── Evaluation + self-healing ─────────────────────────────────────────────
    from evaluation import tester_checks
    test_eval = tester_checks.run_all(test_suites, converted)
    bad_suites = tester_checks.needs_retry(test_eval)

    if bad_suites:
        print_step(
            "Tester",
            f"Eval found {len(bad_suites)} test suite(s) with no @Test or no assertions — regenerating: "
            f"{', '.join(bad_suites)}",
            "warning",
        )
        # Retry once for each bad suite with an explicit instruction
        for suite in [s for s in test_suites if s.get("test_class_name") in bad_suites]:
            mod_name = suite.get("module_name", "")
            mod = next((m for m in converted if m.get("name") == mod_name), None)
            if not mod:
                continue
            try:
                retry_result = ph.invoke_and_parse(
                    temperature=0.2,
                    max_tokens=3_000,
                    name=mod_name,
                    microservice_type=mod.get("microservice_type", "service"),
                    java_code=mod.get("java_code", "")[:_MAX_CODE_CHARS],
                    package=mod.get("package", ""),
                    dependencies_json=json.dumps(mod.get("dependencies", [])),
                    additional_instruction=(
                        "IMPORTANT: every test method MUST have @Test annotation and at least "
                        "one assertion (assertEquals, assertTrue, assertNotNull, verify, etc.)."
                    ),
                )
                if isinstance(retry_result, dict) and retry_result.get("test_code"):
                    suite.update(retry_result)
                    save_text(retry_result["test_code"], suite["file_path"])
                    print_step("Tester", f"  ✓ Regenerated {suite['test_class_name']}", "success")
            except Exception as exc:
                print_step("Tester", f"  ✗ Retry failed for {mod_name}: {exc}", "error")

        # Re-evaluate after self-healing
        test_eval = tester_checks.run_all(test_suites, converted)

    save_json(test_eval, "tests/tester_eval.json")
    _log_tester_eval(test_eval)
    save_json({"test_suites": test_suites}, "tests/test_suites_summary.json")

    out: dict = {
        "test_suites":  test_suites,
        "tester_eval":  test_eval,
        "current_step": "tester_complete",
        "processing_complete": True,
    }
    if errors:
        out["errors"] = errors
    return out


def _log_tester_eval(ev: dict):
    score = ev.get("overall_score", 0)
    level = "success" if score >= 80 else "warning" if score >= 60 else "error"
    print_step("Tester", f"Eval — overall {score}/100  |  "
               f"@Test {ev['test_annotations']['score']}  |  "
               f"assertions {ev['assertions']['score']}  |  "
               f"coverage {ev['coverage_ratio']['score']}  |  "
               f"mockito {ev['mockito_usage']['score']}", level)
