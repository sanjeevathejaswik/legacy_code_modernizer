"""
Final scorer: combines Layer 1 (deterministic) + Layer 2 (DeepEval) into
a transparent, weighted 0-100 score.

Weight breakdown
────────────────
  Layer 1 — Deterministic (45 % total)
    schema          15 %  — all 6 doc keys present and non-empty
    coverage        20 %  — % of Java modules with a module_doc entry
    depth           10 %  — average word-count of business_logic sections

  Layer 2 — DeepEval (55 % total)
    summarization   25 %  — documentation covers key facts from source code
    faithfulness    20 %  — documentation does not hallucinate absent facts
    clarity         10 %  — documentation is clear and well-structured

Weights are defined as module constants so they are easy to tune.
"""

from typing import Dict

# ── Weights (must sum to 1.0) ─────────────────────────────────────────────────
# DeepEval signals (faithfulness, clarity, summarization) are the primary quality
# indicators. Structural/format checks (schema, coverage, depth) are secondary —
# they should not dominate when the content itself is high-quality.
W_SCHEMA        = 0.05   # was 0.15 — format completeness is a weak signal
W_COVERAGE      = 0.10   # was 0.20 — LLM often returns partial module lists
W_DEPTH         = 0.05   # was 0.10 — word count is a proxy, not ground truth
W_SUMMARIZATION = 0.35   # was 0.25 — does doc cover key facts? strongest signal
W_FAITHFULNESS  = 0.30   # was 0.20 — no hallucinations? critical for banking
W_CLARITY       = 0.15   # was 0.10 — is doc understandable?

assert abs(W_SCHEMA + W_COVERAGE + W_DEPTH +
           W_SUMMARIZATION + W_FAITHFULNESS + W_CLARITY - 1.0) < 1e-9, \
    "Evaluation weights must sum to 1.0"


def compute(det: Dict, llm: Dict) -> Dict:
    """
    Parameters
    ----------
    det : output of evaluation.deterministic.run_all()
    llm : output of evaluation.deepeval_metrics.run_all()

    Returns
    -------
    dict with final_score (0-100), breakdown per dimension, and layer summaries.
    """
    # Raw scores — deterministic dimensions already in 0-100 range
    schema_s    = float(det["schema"]["score"])
    coverage_s  = float(det["coverage"]["score"])
    depth_s     = float(det["depth"]["score"])

    # DeepEval scores are 0-1 → convert to 0-100
    summ_s  = float(llm["summarization"]["score"]) * 100
    faith_s = float(llm["faithfulness"]["score"])  * 100
    clar_s  = float(llm["clarity"]["score"])        * 100

    final = (
        schema_s   * W_SCHEMA        +
        coverage_s * W_COVERAGE      +
        depth_s    * W_DEPTH         +
        summ_s     * W_SUMMARIZATION +
        faith_s    * W_FAITHFULNESS  +
        clar_s     * W_CLARITY
    )

    deterministic_layer = (
        schema_s   * W_SCHEMA   +
        coverage_s * W_COVERAGE +
        depth_s    * W_DEPTH
    ) / (W_SCHEMA + W_COVERAGE + W_DEPTH)

    deepeval_layer = (
        summ_s  * W_SUMMARIZATION +
        faith_s * W_FAITHFULNESS  +
        clar_s  * W_CLARITY
    ) / (W_SUMMARIZATION + W_FAITHFULNESS + W_CLARITY)

    return {
        "final_score":         round(final, 1),
        "deterministic_score": round(deterministic_layer, 1),
        "deepeval_score":      round(deepeval_layer, 1),
        "breakdown": {
            "schema": {
                "score":       round(schema_s, 1),
                "weight":      f"{int(W_SCHEMA * 100)}%",
                "contribution": round(schema_s * W_SCHEMA, 1),
                "detail":      det["schema"],
            },
            "coverage": {
                "score":       round(coverage_s, 1),
                "weight":      f"{int(W_COVERAGE * 100)}%",
                "contribution": round(coverage_s * W_COVERAGE, 1),
                "detail":      det["coverage"],
            },
            "depth": {
                "score":       round(depth_s, 1),
                "weight":      f"{int(W_DEPTH * 100)}%",
                "contribution": round(depth_s * W_DEPTH, 1),
                "detail":      det["depth"],
            },
            "summarization": {
                "score":       round(summ_s, 1),
                "weight":      f"{int(W_SUMMARIZATION * 100)}%",
                "contribution": round(summ_s * W_SUMMARIZATION, 1),
                "detail":      llm["summarization"],
            },
            "faithfulness": {
                "score":       round(faith_s, 1),
                "weight":      f"{int(W_FAITHFULNESS * 100)}%",
                "contribution": round(faith_s * W_FAITHFULNESS, 1),
                "detail":      llm["faithfulness"],
            },
            "clarity": {
                "score":       round(clar_s, 1),
                "weight":      f"{int(W_CLARITY * 100)}%",
                "contribution": round(clar_s * W_CLARITY, 1),
                "detail":      llm["clarity"],
            },
        },
    }
