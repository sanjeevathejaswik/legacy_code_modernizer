"""
Auditor Agent — content-first evaluation.

Scoring approach
────────────────
Primary (80 %):  Single LLM call that reads the documentation CONTENT and scores
                 four dimensions: completeness, accuracy, clarity, coverage.
                 This correctly handles any documentation format the LLM produces
                 (list, {modules:[]}, or the canonical 6-key object).

Supplementary:   Deterministic structural checks (schema completeness, module
                 coverage %, depth) are computed and stored in the breakdown
                 for the dashboard / observability pages, but do NOT override
                 the LLM content score.

DeepEval:        Runs asynchronously after the primary score and enriches the
                 breakdown with faithfulness and clarity signals.  Falls back
                 to neutral values on any failure — never blocks the pipeline.
"""

import json
from datetime import datetime
from graph.state import WorkflowState
from utils.prompt_helper import PromptHelper
from utils.file_handler import save_json, load_json
from utils.output_formatter import print_step, print_audit_report, print_error
import config

_MAX_DOC_CHARS    = 10_000
_MAX_SOURCE_CHARS =  4_000


# ── Helpers ────────────────────────────────────────────────────────────────────

def _needs_normalization(documentation) -> bool:
    """True when documentation is missing or lacks the canonical module_docs key."""
    if not documentation:
        return True
    if not isinstance(documentation, dict):
        return True
    if not documentation.get("module_docs"):
        return True
    return False


_VALID_SEVERITIES   = {"critical", "major", "minor"}
_REQUIRED_METRICS   = {"completeness", "accuracy", "clarity", "coverage"}
_REQUIRED_ISSUE_KEYS = {"severity", "module", "issue", "suggestion"}


def _validate_llm_result(result: dict, det: dict) -> dict:
    """
    Validate and repair the LLM scoring output before it drives the retry decision.
    Repairs:
      - score out of 0–100 range → clamped
      - score not a number       → derived from deterministic average
      - missing / invalid metrics → filled from deterministic or defaulted to 50
      - malformed issues          → missing fields filled with placeholders
      - issues not a list         → reset to []
    Logs a warning for every repair made.
    """
    repairs = []

    # ── Score ────────────────────────────────────────────────────────────────
    raw_score = result.get("score")
    try:
        score = float(raw_score)
        if not (0.0 <= score <= 100.0):
            repairs.append(f"score {score} out of range — clamped to [0, 100]")
            score = max(0.0, min(100.0, score))
    except (TypeError, ValueError):
        det_avg = (det["schema"]["score"] + det["coverage"]["score"] + det["depth"]["score"]) / 3
        score = round(det_avg, 1)
        repairs.append(f"score '{raw_score}' is not a number — derived from deterministic avg {score}")
    result["score"] = score

    # ── Metrics ───────────────────────────────────────────────────────────────
    metrics = result.get("metrics")
    if not isinstance(metrics, dict):
        repairs.append(f"metrics is {type(metrics).__name__} not dict — reset to defaults")
        metrics = {}
    for key in _REQUIRED_METRICS:
        if key not in metrics:
            fallback = det.get(key, {}).get("score", 50)
            metrics[key] = fallback
            repairs.append(f"metrics['{key}'] missing — defaulted to {fallback}")
        else:
            try:
                v = float(metrics[key])
                metrics[key] = max(0.0, min(100.0, v))
            except (TypeError, ValueError):
                metrics[key] = 50
                repairs.append(f"metrics['{key}'] not numeric — set to 50")
    result["metrics"] = metrics

    # ── Issues ────────────────────────────────────────────────────────────────
    issues = result.get("issues")
    if not isinstance(issues, list):
        repairs.append(f"issues is {type(issues).__name__} not list — reset to []")
        result["issues"] = []
    else:
        for i, iss in enumerate(issues):
            if not isinstance(iss, dict):
                issues[i] = {"severity": "minor", "module": "unknown",
                              "issue": str(iss), "suggestion": ""}
                repairs.append(f"issues[{i}] not a dict — wrapped")
                continue
            for key in _REQUIRED_ISSUE_KEYS:
                if key not in iss:
                    iss[key] = "minor" if key == "severity" else ""
                    repairs.append(f"issues[{i}] missing '{key}' — filled with placeholder")
            if iss.get("severity") not in _VALID_SEVERITIES:
                repairs.append(f"issues[{i}] invalid severity '{iss['severity']}' — set to 'minor'")
                iss["severity"] = "minor"

    # ── Recommendations ───────────────────────────────────────────────────────
    if not isinstance(result.get("recommendations"), list):
        result["recommendations"] = []

    if repairs:
        print_step("Auditor",
                   f"LLM output validation: {len(repairs)} repair(s) — "
                   + "; ".join(repairs[:3])
                   + (" …" if len(repairs) > 3 else ""),
                   "warning")

    return result


def _empty_report(reason: str) -> dict:
    return {
        "score": 0.0,
        "passed": False,
        "threshold": config.AUDIT_PASS_THRESHOLD,
        "issues": [{"severity": "critical", "module": "all",
                    "issue": reason, "suggestion": "Re-run the Documenter step first."}],
        "summary": reason,
        "timestamp": datetime.now().isoformat(),
        "recommendations": ["Generate documentation before auditing."],
        "metrics": {"completeness": 0, "accuracy": 0, "clarity": 0, "coverage": 0},
        "evaluation_breakdown": {},
    }


def _build_feedback(audit_report: dict, retry_number: int) -> str:
    score    = audit_report.get("score", 0)
    issues   = audit_report.get("issues", [])
    critical = [i for i in issues if i.get("severity") == "critical"]
    major    = [i for i in issues if i.get("severity") == "major"]
    eb       = audit_report.get("evaluation_breakdown", {})

    lines = [
        f"Audit FAILED — score {score:.1f} / threshold {config.AUDIT_PASS_THRESHOLD} "
        f"(retry {retry_number} of {config.MAX_AUDIT_RETRIES}).",
        f"Summary: {audit_report.get('summary', '')}",
    ]

    # ── LLM-identified issues ─────────────────────────────────────────────────
    if critical:
        lines.append("\nCRITICAL issues to fix:")
        for i in critical:
            lines.append(f"  [{i['module']}] {i['issue']}  →  {i['suggestion']}")
    if major:
        lines.append("\nMAJOR issues to fix:")
        for i in major[:5]:
            lines.append(f"  [{i['module']}] {i['issue']}  →  {i['suggestion']}")

    # ── Deterministic structural gaps ─────────────────────────────────────────
    schema = eb.get("schema", {})
    missing_keys = schema.get("missing_keys", [])
    if missing_keys:
        lines.append(f"\nMISSING documentation sections — add these: {', '.join(missing_keys)}")

    coverage = eb.get("coverage", {})
    uncovered = coverage.get("uncovered_modules", [])
    if uncovered:
        lines.append(f"\nUNDOCUMENTED modules ({len(uncovered)}) — add a module_doc entry for each:")
        lines.append("  " + ", ".join(uncovered[:10]))

    depth = eb.get("depth", {})
    shallow = depth.get("shallow_modules", [])
    if shallow:
        lines.append(f"\nSHALLOW business_logic (< 20 words) — expand these modules:")
        lines.append("  " + ", ".join(shallow[:10]))

    # ── DeepEval semantic signals ─────────────────────────────────────────────
    faith = eb.get("faithfulness", {})
    hallucination_rate = faith.get("hallucination_rate", 0)
    if hallucination_rate > 0.4:
        lines.append(
            f"\nHALLUCINATION DETECTED — faithfulness score {faith.get('score', 0):.2f} "
            f"(hallucination rate {hallucination_rate:.0%}). "
            "Ensure every claim in the documentation is grounded in the actual source code. "
            f"Reason: {faith.get('reason', '')}"
        )

    clarity = eb.get("clarity_ai", {})
    if float(clarity.get("score", 1.0)) < 0.5:
        lines.append(
            f"\nLOW CLARITY — clarity score {clarity.get('score', 0):.2f}. "
            "Rewrite business_logic sections in plain English. "
            "Each section must be concrete, specific, and understandable without reading the code. "
            f"Reason: {clarity.get('reason', '')}"
        )

    for rec in audit_report.get("recommendations", [])[:3]:
        lines.append(f"\nRecommendation: {rec}")

    return "\n".join(lines)


def _run_deterministic(modules: list, documentation: dict) -> dict:
    """Structural checks — informational only, not used in primary score."""
    try:
        from evaluation import deterministic
        return deterministic.run_all(modules, documentation)
    except Exception as exc:
        print_step("Auditor", f"Deterministic checks failed ({exc}); skipping.", "warning")
        return {
            "schema":         {"score": 0.0, "missing_keys": [], "present": 0, "total": 6},
            "coverage":       {"score": 0.0, "covered": 0, "total": len(modules), "uncovered_modules": []},
            "depth":          {"score": 0.0, "avg_words": 0, "min_words": 0, "shallow_modules": []},
            "business_rules": {"score": 0.0, "count": 0},
        }


def _run_deepeval(source_code: str, documentation: dict) -> dict:
    """DeepEval metrics — enriches breakdown, never blocks scoring."""
    try:
        from evaluation import deepeval_metrics
        return deepeval_metrics.run_all(source_code[:_MAX_SOURCE_CHARS], documentation)
    except Exception as exc:
        print_step("Auditor", f"DeepEval metrics failed ({exc}); using neutral values.", "warning")
    return {
        "summarization": {"score": 0.5, "reason": "unavailable"},
        "faithfulness":  {"score": 0.5, "reason": "unavailable", "hallucination_rate": 0.5},
        "clarity":       {"score": 0.5, "reason": "unavailable"},
    }


# ── Node ───────────────────────────────────────────────────────────────────────

def auditor_node(state: WorkflowState) -> dict:
    print_step("Auditor", "Evaluating documentation quality…")

    modules       = state["modules"]
    documentation = state.get("documentation")
    retries       = state.get("audit_retries", 0)
    source_code   = state.get("source_code", "")

    # ── Normalise / load from disk if state has wrong format ──────────────────
    if _needs_normalization(documentation):
        from agents.documenter import _normalize_documentation
        if documentation:
            documentation = _normalize_documentation(documentation)
            print_step("Auditor", "Normalised documentation from state (wrong format).", "warning")
        if _needs_normalization(documentation):
            disk = load_json("docs/documentation.json")
            if disk:
                documentation = _normalize_documentation(disk)
                print_step("Auditor", "Loaded documentation from docs/documentation.json.", "warning")

    # ── Guard ─────────────────────────────────────────────────────────────────
    if not documentation:
        report = _empty_report("No documentation provided to the Auditor.")
        save_json(report, "audit/audit_report.json")
        return {"audit_report": report, "audit_feedback": report["summary"],
                "audit_retries": retries + 1, "current_step": "auditor_complete"}

    # ── Supplementary: deterministic structural checks ────────────────────────
    print_step("Auditor", "Running structural checks…")
    det = _run_deterministic(modules, documentation)

    # ── Primary: LLM content evaluation (produces the actual score) ───────────
    print_step("Auditor", "Running LLM content evaluation…")
    module_names = [m["name"] for m in modules]
    doc_str = json.dumps(documentation, indent=2)
    if len(doc_str) > _MAX_DOC_CHARS:
        doc_str = doc_str[:_MAX_DOC_CHARS] + "\n// … (truncated)"

    try:
        ph = PromptHelper("auditor")
        llm_result = ph.invoke_and_parse(
            system_kwargs={"threshold": config.AUDIT_PASS_THRESHOLD},
            max_tokens=3_000,
            module_count=len(modules),
            module_names_json=json.dumps(module_names, indent=2),
            documentation_json=doc_str,
        )

        # Validate and repair LLM output before it drives the retry decision
        llm_result = _validate_llm_result(llm_result, det)

        llm_result.setdefault("timestamp", datetime.now().isoformat())
        llm_result.setdefault("threshold", config.AUDIT_PASS_THRESHOLD)
        score = float(llm_result["score"])   # already validated / clamped
        llm_result["passed"] = score >= config.AUDIT_PASS_THRESHOLD

    except Exception as exc:
        print_step("Auditor", f"LLM evaluation failed ({exc}); using deterministic fallback.", "warning")
        det_avg = (det["schema"]["score"] + det["coverage"]["score"] + det["depth"]["score"]) / 3
        score = round(det_avg, 1)
        issues, summary, recs = _fallback_issues(det, score)
        llm_result = {
            "score": score, "passed": score >= config.AUDIT_PASS_THRESHOLD,
            "threshold": config.AUDIT_PASS_THRESHOLD,
            "issues": issues, "summary": summary,
            "timestamp": datetime.now().isoformat(),
            "recommendations": recs,
            "metrics": {
                "completeness": round(det["schema"]["score"], 1),
                "accuracy":     50,
                "clarity":      50,
                "coverage":     round(det["coverage"]["score"], 1),
            },
        }

    # ── Supplementary: DeepEval (enriches breakdown only) ────────────────────
    print_step("Auditor", "Running DeepEval supplementary metrics…")
    deepeval_result = _run_deepeval(source_code, documentation)

    # ── Assemble final report ─────────────────────────────────────────────────
    report = {
        **llm_result,
        "evaluation_breakdown": {
            "llm_score":    {"score": llm_result["score"], "weight": "primary"},
            "schema":       {**det["schema"],    "weight": "structural"},
            "coverage":     {**det["coverage"],  "weight": "structural"},
            "depth":        {**det["depth"],     "weight": "structural"},
            "faithfulness": {**deepeval_result["faithfulness"], "weight": "deepeval"},
            "clarity_ai":   {**deepeval_result["clarity"],      "weight": "deepeval"},
        },
        "deterministic_score": round(
            (det["schema"]["score"] + det["coverage"]["score"] + det["depth"]["score"]) / 3, 1
        ),
        "deepeval_score": round(
            (deepeval_result["summarization"]["score"] +
             deepeval_result["faithfulness"]["score"] +
             deepeval_result["clarity"]["score"]) / 3 * 100, 1
        ),
    }

    save_json(report, "audit/audit_report.json")
    print_audit_report(report)

    feedback = ""
    if not report["passed"]:
        feedback = _build_feedback(report, retries + 1)
        print_step("Auditor",
                   f"Audit FAILED (score {report['score']:.1f}). "
                   f"Retry {retries + 1} / {config.MAX_AUDIT_RETRIES}.", "warning")
    else:
        print_step("Auditor", "Audit PASSED — proceeding to HITL review.", "success")

    return {
        "audit_report":   report,
        "audit_feedback": feedback,
        "audit_retries":  retries + 1,
        "current_step":   "auditor_complete",
    }


# ── Deterministic fallback for issues ─────────────────────────────────────────

def _fallback_issues(det: dict, score: float):
    issues = []
    uncovered = det["coverage"].get("uncovered_modules", [])
    if uncovered:
        issues.append({"severity": "critical", "module": ", ".join(uncovered[:5]),
                       "issue": f"{len(uncovered)} modules have no documentation.",
                       "suggestion": "Add a module_doc entry for each missing module."})
    missing = det["schema"].get("missing_keys", [])
    if missing:
        issues.append({"severity": "major", "module": "documentation root",
                       "issue": f"Required sections missing: {', '.join(missing)}",
                       "suggestion": "Ensure the Documenter returns all 6 required sections."})
    shallow = det["depth"].get("shallow_modules", [])
    if shallow:
        issues.append({"severity": "minor", "module": ", ".join(shallow[:5]),
                       "issue": f"{len(shallow)} modules have very short business_logic.",
                       "suggestion": "Expand business logic to at least 50 words per module."})
    summary = (f"Score {score:.1f}/100. Coverage {det['coverage']['score']:.0f}%, "
               f"{len(issues)} issue(s) identified.")
    recs = ["Address all uncovered modules first.", "Expand shallow business_logic sections."]
    return issues, summary, recs
