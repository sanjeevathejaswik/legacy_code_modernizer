"""
Deterministic quality checks for the assembled Maven project.
Zero LLM cost.

Checks:
  pom_xml       — Spring Boot parent, groupId, artifactId present
  dockerfile    — multi-stage build (builder + runtime)
  app_yml       — server port and spring block present
  manifest      — source_files count matches converted modules
"""

from typing import Dict


def check_pom_xml(project_config: dict) -> Dict:
    """Validate pom.xml content via project_config fields."""
    issues = []
    if not project_config:
        return {"score": 0.0, "issues": ["project_config missing"]}

    sb_ver = project_config.get("spring_boot_version", "")
    if not sb_ver:
        issues.append("spring_boot_version not set — pom.xml will lack a parent version")

    if not project_config.get("group_id"):
        issues.append("group_id missing")

    if not project_config.get("artifact_id"):
        issues.append("artifact_id missing")

    deps = project_config.get("dependencies", [])
    if not deps:
        issues.append("No Maven dependencies declared")

    score = round((1 - len(issues) / 4) * 100, 1)
    return {"score": max(score, 0.0), "spring_boot_version": sb_ver,
            "group_id": project_config.get("group_id", ""),
            "artifact_id": project_config.get("artifact_id", ""),
            "dependency_count": len(deps), "issues": issues}


def check_dockerfile(project_config: dict) -> Dict:
    """Validate the generated Dockerfile."""
    df = project_config.get("dockerfile", "")
    issues = []
    if not df:
        return {"score": 0.0, "stages": 0, "issues": ["Dockerfile missing"]}

    stages = df.count("FROM")
    if stages == 0:
        issues.append("No FROM instruction in Dockerfile")
    elif stages < 2:
        issues.append("Single-stage Dockerfile — should use multi-stage (builder + runtime)")

    if "ENTRYPOINT" not in df and "CMD" not in df:
        issues.append("No ENTRYPOINT or CMD instruction")

    score = round((1 - len(issues) / 2) * 100, 1)
    return {"score": max(score, 0.0), "stages": stages, "issues": issues}


def check_app_yml(project_config: dict) -> Dict:
    """Validate the generated application.yml."""
    yml = project_config.get("application_yml", "")
    issues = []
    if not yml:
        return {"score": 0.0, "issues": ["application.yml missing"]}

    if "server" not in yml and "port" not in yml:
        issues.append("Missing server port configuration")

    if "spring" not in yml:
        issues.append("Missing spring configuration block")

    if "datasource" not in yml and "jpa" not in yml:
        issues.append("No datasource or JPA configuration")

    score = round((1 - len(issues) / 3) * 100, 1)
    return {"score": max(score, 0.0), "issues": issues}


def check_manifest(assembly_result: dict, converted_modules: list) -> Dict:
    """All converted modules should appear as source files in the assembly."""
    source_files  = assembly_result.get("source_files", [])
    module_names  = {m.get("name", "") for m in converted_modules}
    # Match by checking if the module name appears anywhere in the file path
    found = {
        name for name in module_names
        if any(name in f for f in source_files)
    }
    missing  = sorted(module_names - found)
    total    = max(len(module_names), 1)
    score    = round(len(found) / total * 100, 1)
    return {
        "score":           score,
        "total_files":     len(source_files),
        "modules_found":   len(found),
        "modules_missing": missing,
    }


def run_all(assembly_result: dict, converted_modules: list) -> Dict:
    project_config = assembly_result.get("project_config", {})
    checks = {
        "pom_xml":    check_pom_xml(project_config),
        "dockerfile": check_dockerfile(project_config),
        "app_yml":    check_app_yml(project_config),
        "manifest":   check_manifest(assembly_result, converted_modules),
    }
    overall = round(
        sum(c["score"] for c in checks.values()) / len(checks), 1
    )
    return {"overall_score": overall, **checks}
