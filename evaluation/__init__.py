"""
Evaluation framework for the Legacy Code Conversion pipeline.

Three layers:
  Layer 1  deterministic.py  — rule-based schema, coverage, depth checks (no LLM)
  Layer 2  deepeval_metrics.py — DeepEval SummarizationMetric, HallucinationMetric, GEval
  Layer 3  scorer.py          — combines layers 1+2 into a weighted 0-100 final score
"""
