"""
Deterministic quality checks for generated JUnit 5 test suites.
Zero LLM cost.

Checks:
  test_annotations  — every test class has at least one @Test method
  assertions        — every test method contains at least one assertion
  coverage_ratio    — % of converted modules that have a test suite
  mockito_usage     — service / controller tests use Mockito mocks
"""

import re
from typing import Dict, List

_ASSERTION_PATTERNS = [
    "assert", "assertEquals", "assertTrue", "assertFalse",
    "assertNotNull", "assertNull", "assertThat", "assertThrows",
    "verify(", "verifyNoInteractions",
]

_NEEDS_MOCKS = {"service", "controller"}


def check_test_annotations(test_suites: list) -> Dict:
    """Every generated test class must have at least one @Test method."""
    missing = [
        t.get("test_class_name", "?")
        for t in test_suites
        if "@Test" not in t.get("test_code", "")
    ]
    total = max(len(test_suites), 1)
    score = round((1 - len(missing) / total) * 100, 1)
    return {"score": score, "missing_test_annotation": missing, "checked": len(test_suites)}


def check_assertions(test_suites: list) -> Dict:
    """Every test class must contain at least one assertion or verify call."""
    missing = []
    for t in test_suites:
        code = t.get("test_code", "")
        if not any(p in code for p in _ASSERTION_PATTERNS):
            missing.append(t.get("test_class_name", "?"))
    total = max(len(test_suites), 1)
    score = round((1 - len(missing) / total) * 100, 1)
    return {"score": score, "missing_assertions": missing, "checked": len(test_suites)}


def check_coverage_ratio(test_suites: list, converted_modules: list) -> Dict:
    """What % of converted modules have a corresponding test suite."""
    tested  = {t.get("module_name") for t in test_suites}
    total   = len(converted_modules)
    covered = len([m for m in converted_modules if m.get("name") in tested])
    untested = [
        m.get("name", "?")
        for m in converted_modules
        if m.get("name") not in tested
    ]
    score = round(covered / max(total, 1) * 100, 1)
    return {
        "score":            score,
        "covered":          covered,
        "total":            total,
        "untested_modules": untested,
    }


def check_mockito_usage(test_suites: list, converted_modules: list) -> Dict:
    """Service and controller test suites should use Mockito mocks."""
    layer_map = {m.get("name"): m.get("microservice_type", "") for m in converted_modules}
    missing = []
    for t in test_suites:
        layer = layer_map.get(t.get("module_name"), "")
        code  = t.get("test_code", "")
        if layer in _NEEDS_MOCKS and "mock" not in code.lower():
            missing.append(t.get("test_class_name", "?"))
    candidates = [t for t in test_suites
                  if layer_map.get(t.get("module_name"), "") in _NEEDS_MOCKS]
    total = max(len(candidates), 1)
    score = round((1 - len(missing) / total) * 100, 1)
    return {"score": score, "missing_mocks": missing, "checked": len(candidates)}


def needs_retry(checks: dict) -> List[str]:
    """
    Return module names whose test suites are critical failures
    (no @Test annotation or no assertions) and should be regenerated.
    """
    bad = set(checks["test_annotations"]["missing_test_annotation"])
    bad |= set(checks["assertions"]["missing_assertions"])
    return sorted(bad)


def run_all(test_suites: list, converted_modules: list) -> Dict:
    checks = {
        "test_annotations": check_test_annotations(test_suites),
        "assertions":       check_assertions(test_suites),
        "coverage_ratio":   check_coverage_ratio(test_suites, converted_modules),
        "mockito_usage":    check_mockito_usage(test_suites, converted_modules),
    }
    overall = round(
        sum(c["score"] for c in checks.values()) / len(checks), 1
    )
    return {"overall_score": overall, **checks}
