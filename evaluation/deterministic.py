"""
Layer 1: Deterministic, rule-based documentation quality checks.
No LLM involved — results are identical on every run for the same input.

Checks:
  schema    — all 6 required top-level keys are present and non-empty
  coverage  — % of input Java modules that have a module_doc entry
  depth     — average word count of business_logic entries
  rules     — number of business rules captured
"""

from typing import Dict, List


_REQUIRED_KEYS = {
    "overview",
    "business_rules",
    "data_models",
    "service_interfaces",
    "module_docs",
    "technical_specs",
}


def check_schema(documentation: dict) -> Dict:
    """Score = (non-empty required keys / 6) * 100."""
    present = [k for k in _REQUIRED_KEYS if documentation.get(k)]
    missing = [k for k in _REQUIRED_KEYS if not documentation.get(k)]
    score = (len(present) / len(_REQUIRED_KEYS)) * 100
    return {
        "score":        round(score, 1),
        "present":      len(present),
        "total":        len(_REQUIRED_KEYS),
        "missing_keys": missing,
    }


def check_coverage(modules: list, documentation: dict) -> Dict:
    """Score = (modules with a module_doc entry / total modules) * 100."""
    if not modules:
        return {"score": 0.0, "covered": 0, "total": 0, "uncovered_modules": []}

    module_names = {m["name"] for m in modules}
    documented   = {d.get("module", "") for d in documentation.get("module_docs", [])}
    covered      = module_names & documented
    uncovered    = sorted(module_names - documented)

    score = (len(covered) / len(module_names)) * 100
    return {
        "score":             round(score, 1),
        "covered":           len(covered),
        "total":             len(module_names),
        "uncovered_modules": uncovered,
    }


def check_depth(documentation: dict) -> Dict:
    """Score based on average word count across all module_doc.business_logic entries.
    Scoring curve: <10 words→10pts, 30 words→50pts, 80+ words→100pts.
    """
    module_docs = documentation.get("module_docs", [])
    if not module_docs:
        return {"score": 0.0, "avg_words": 0, "min_words": 0, "shallow_modules": []}

    word_counts = {
        d.get("module", f"module_{i}"): len(d.get("business_logic", "").split())
        for i, d in enumerate(module_docs)
    }
    avg_words  = sum(word_counts.values()) / len(word_counts)
    min_words  = min(word_counts.values())
    shallow    = [name for name, wc in word_counts.items() if wc < 20]

    # Linear scale: 0→0, 80→100 (capped)
    score = min(avg_words / 80 * 100, 100.0)
    return {
        "score":           round(score, 1),
        "avg_words":       round(avg_words, 1),
        "min_words":       min_words,
        "shallow_modules": shallow,
    }


def check_business_rules(documentation: dict) -> Dict:
    """Score = min(rule_count / 10 * 100, 100). At least 10 rules expected."""
    rules = documentation.get("business_rules", [])
    count = len(rules) if isinstance(rules, list) else 0
    score = min(count / 10 * 100, 100.0)
    return {"score": round(score, 1), "count": count}


def run_all(modules: list, documentation: dict) -> Dict:
    """Run all deterministic checks and return individual scores (no aggregation)."""
    return {
        "schema":           check_schema(documentation),
        "coverage":         check_coverage(modules, documentation),
        "depth":            check_depth(documentation),
        "business_rules":   check_business_rules(documentation),
    }
