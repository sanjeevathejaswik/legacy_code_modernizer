"""
Deterministic quality checks for converted Spring Boot modules.
Zero LLM cost.

Checks:
  spring_annotations  — each module has annotations matching its microservice_type
  package_declaration — each module declares a package
  spring_imports      — service/controller/repository import org.springframework
  no_stubs            — no { ... } placeholders, minimum code length
"""

import re
from typing import Dict, List

# Expected annotations per microservice_type
_LAYER_ANNOTATIONS: Dict[str, List[str]] = {
    "service":        ["@Service", "@Transactional"],
    "controller":     ["@RestController", "@Controller"],
    "repository":     ["@Repository"],
    "model":          ["@Entity", "@Table", "@Embeddable", "@MappedSuperclass"],
    "config":         ["@Configuration", "@SpringBootApplication", "@EnableAutoConfiguration"],
    "utility":        ["@Component"],
    "infrastructure": ["@Component", "@Aspect", "@Scheduled"],
    "exception":      [],   # extends Exception — no annotation required
    "dto":            [],   # plain POJO — no annotation required
}

_MIN_CODE_CHARS = 80


def check_spring_annotations(modules: list) -> Dict:
    """Each module should have at least one annotation matching its layer."""
    missing = []
    for m in modules:
        layer    = m.get("microservice_type", "utility")
        code     = m.get("java_code", "")
        expected = _LAYER_ANNOTATIONS.get(layer, [])
        if expected and not any(ann in code for ann in expected):
            missing.append({
                "name":         m.get("name", "?"),
                "layer":        layer,
                "expected_one_of": expected,
            })
    total = max(len(modules), 1)
    score = round((1 - len(missing) / total) * 100, 1)
    return {"score": score, "missing": missing, "checked": len(modules)}


def check_package_declarations(modules: list) -> Dict:
    """Every module must start with a package declaration."""
    missing = [
        m.get("name", "?")
        for m in modules
        if not re.search(r"^\s*package\s+[\w.]+\s*;", m.get("java_code", ""), re.MULTILINE)
    ]
    total = max(len(modules), 1)
    score = round((1 - len(missing) / total) * 100, 1)
    return {"score": score, "missing_package": missing, "checked": len(modules)}


def check_spring_imports(modules: list) -> Dict:
    """Service / controller / repository modules must import Spring classes."""
    _NEEDS_SPRING = {"service", "controller", "repository"}
    missing = [
        m.get("name", "?")
        for m in modules
        if m.get("microservice_type") in _NEEDS_SPRING
        and "import org.springframework" not in m.get("java_code", "")
    ]
    candidates = [m for m in modules if m.get("microservice_type") in _NEEDS_SPRING]
    total = max(len(candidates), 1)
    score = round((1 - len(missing) / total) * 100, 1)
    return {"score": score, "missing_spring_imports": missing, "checked": len(candidates)}


def check_no_stubs(modules: list) -> Dict:
    """Detect modules where the LLM returned placeholder code."""
    stubs = [
        m.get("name", "?")
        for m in modules
        if "{ ... }" in m.get("java_code", "")
        or "{...}" in m.get("java_code", "")
        or len(m.get("java_code", "")) < _MIN_CODE_CHARS
    ]
    total = max(len(modules), 1)
    score = round((1 - len(stubs) / total) * 100, 1)
    return {"score": score, "stub_modules": stubs, "checked": len(modules)}


def run_all(modules: list) -> Dict:
    checks = {
        "spring_annotations":  check_spring_annotations(modules),
        "package_declarations": check_package_declarations(modules),
        "spring_imports":       check_spring_imports(modules),
        "no_stubs":             check_no_stubs(modules),
    }
    overall = round(
        sum(c["score"] for c in checks.values()) / len(checks), 1
    )
    return {"overall_score": overall, **checks}
