"""
LangGraph StateGraph definition — with Human-in-the-Loop (HITL).

Full pipeline flow
──────────────────
START
  └─► code_splitter
        └─► documenter
              └─► auditor
                    ├─► (retries remaining)      documenter  (auto-retry loop)
                    └─► (passed | retries done)  review_gate  ← PAUSE
                                                      │
                                          Human reviews audit report
                                          on Streamlit dashboard
                                                      │
                                         ┌────────────┴────────────┐
                                      Approve                   Reject
                                         │                         │
                                      converter              documenter
                                         │
                                       tester
                                         │
                                       joiner
                                         │
                                   build_verifier ──► END

Every agent node is wrapped by instrument_node() for automatic tracing/metrics.
The graph is compiled with a MemorySaver checkpointer so the Review Gate can
pause and resume across HTTP calls.
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

import config
from agents.build_verifier  import build_verifier_node
from agents.code_splitter   import code_splitter_node
from agents.converter        import converter_node
from agents.documenter       import documenter_node
from agents.auditor          import auditor_node
from agents.review_gate      import review_gate_node
from agents.tester           import tester_node
from graph.state             import WorkflowState
from observability.tracing   import instrument_node
from reassembly.joiner_agent import joiner_node


# ── Routing functions ─────────────────────────────────────────────────────────

def _route_after_audit(state: WorkflowState) -> str:
    """
    Auto-retry loop: route back to Documenter while retries remain.
    Once retries are exhausted OR the audit passes, send to human review.
    """
    audit_report  = state.get("audit_report")
    audit_retries = state.get("audit_retries", 0)

    if audit_report and audit_report.get("passed", False):
        return "review_gate"                   # passed — human approves before converting

    if audit_retries < config.MAX_AUDIT_RETRIES:
        return "documenter"                    # failed but retries remain — auto-retry

    return "review_gate"                       # retries exhausted — human decides


def _route_after_review(state: WorkflowState) -> str:
    """Human approved → Converter.  Rejected → Documenter for another pass."""
    decision = state.get("hitl_decision", "")
    if decision == "approve":
        return "converter"
    if decision == "reject":
        return "documenter"
    return "end"


def _route_after_build(state: WorkflowState) -> str:
    build_report  = state.get("build_report", {})
    build_retries = state.get("build_retries", 0)
    status        = build_report.get("status", "unknown")

    if status in ("success", "skipped", "unknown"):
        return "end"
    if build_retries <= config.MAX_BUILD_RETRIES:
        return "converter"
    return "end"


# ── Graph factory ─────────────────────────────────────────────────────────────

def create_workflow(checkpointer=None):
    """
    Build and compile the LangGraph StateGraph.

    Args:
        checkpointer: LangGraph checkpointer (e.g. MemorySaver).
                      Required for HITL interrupt/resume.
                      If None, a fresh MemorySaver is created.
    """
    if checkpointer is None:
        checkpointer = MemorySaver()

    wf = StateGraph(WorkflowState)

    # ── Register nodes (each wrapped with observability instrumentation) ───────
    wf.add_node("code_splitter",  instrument_node("code_splitter",  code_splitter_node))
    wf.add_node("documenter",     instrument_node("documenter",      documenter_node))
    wf.add_node("auditor",        instrument_node("auditor",         auditor_node))
    wf.add_node("review_gate",    instrument_node("review_gate",     review_gate_node))
    wf.add_node("converter",      instrument_node("converter",       converter_node))
    wf.add_node("tester",         instrument_node("tester",          tester_node))
    wf.add_node("joiner",         instrument_node("joiner",          joiner_node))
    wf.add_node("build_verifier", instrument_node("build_verifier",  build_verifier_node))

    # ── Linear edges ──────────────────────────────────────────────────────────
    wf.add_edge(START,           "code_splitter")
    wf.add_edge("code_splitter", "documenter")
    wf.add_edge("documenter",    "auditor")

    # ── Conditional: auto-retry or human review ───────────────────────────────
    wf.add_conditional_edges(
        "auditor",
        _route_after_audit,
        {"documenter": "documenter", "review_gate": "review_gate"},
    )

    # ── Conditional: human decision drives next step ──────────────────────────
    wf.add_conditional_edges(
        "review_gate",
        _route_after_review,
        {"converter": "converter", "documenter": "documenter", "end": END},
    )

    # ── Linear: conversion pipeline ───────────────────────────────────────────
    wf.add_edge("converter",      "tester")
    wf.add_edge("tester",         "joiner")
    wf.add_edge("joiner",         "build_verifier")

    # ── Conditional: build fix-loop or end ────────────────────────────────────
    wf.add_conditional_edges(
        "build_verifier",
        _route_after_build,
        {"converter": "converter", "end": END},
    )

    return wf.compile(checkpointer=checkpointer)
