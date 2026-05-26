"""
Review Gate — Human-in-the-Loop Node
======================================
Pauses the pipeline after the Auditor so a human can review the
documentation quality report before expensive code conversion begins.

LangGraph interrupt() serialises the graph state into the checkpointer.
The pipeline resumes when:
  • CLI mode  — the user types their decision at the prompt
  • API mode  — POST /api/v1/jobs/{id}/approve  or  /reject is called
"""

from datetime import datetime, timezone

from langgraph.types import interrupt

from graph.state import WorkflowState
from utils.file_handler import save_json
from utils.output_formatter import print_audit_report, print_step


def review_gate_node(state: WorkflowState) -> dict:
    audit_report  = state.get("audit_report") or {}
    audit_retries = state.get("audit_retries", 0)
    score         = audit_report.get("score", 0)
    passed        = audit_report.get("passed", False)
    issues        = audit_report.get("issues", [])

    print_step("Review Gate", "Pipeline paused — waiting for human approval.")
    print_step(
        "Review Gate",
        f"Audit score: {score:.1f}/100 | "
        f"{'PASSED' if passed else 'FAILED'} | "
        f"{len(issues)} issue(s) | "
        f"{audit_retries} automated retry/retries used",
    )

    # Write status file so the dashboard can show Approve/Reject buttons
    save_json(
        {
            "status":       "awaiting_review",
            "audit_score":  score,
            "audit_passed": passed,
            "issue_count":  len(issues),
            "critical":     sum(1 for i in issues if i.get("severity") == "critical"),
            "major":        sum(1 for i in issues if i.get("severity") == "major"),
            "minor":        sum(1 for i in issues if i.get("severity") == "minor"),
            "summary":      audit_report.get("summary", ""),
            "recommendations": audit_report.get("recommendations", []),
            "timestamp":    datetime.now(tz=timezone.utc).isoformat(),
        },
        "hitl/review_status.json",
    )

    # ── Pause here ────────────────────────────────────────────────────────────
    # LangGraph serialises state into the checkpointer and returns control
    # to the caller.  Execution resumes when Command(resume=decision) is
    # passed back via graph.invoke() / graph.stream().
    decision: str = interrupt(
        {
            "message":     "Review the audit report, then Approve or Reject.",
            "audit_score": score,
            "audit_passed": passed,
            "dashboard":   "http://localhost:8501  →  Audit Report page",
        }
    )
    # ── Resumed ───────────────────────────────────────────────────────────────

    save_json(
        {
            "decision":  decision,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        },
        "hitl/review_decision.json",
    )

    # Clear the awaiting-review status file
    save_json({"status": "decided", "decision": decision}, "hitl/review_status.json")

    print_step(
        "Review Gate",
        f"Decision received: [{decision.upper()}] — pipeline resuming.",
        "success" if decision == "approve" else "warning",
    )

    return {
        "hitl_decision":  decision,
        "awaiting_review": False,
        "current_step":   "review_gate_complete",
    }
