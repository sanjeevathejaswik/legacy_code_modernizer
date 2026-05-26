"""
Build Verifier Agent
====================
Verifies the assembled Maven project actually compiles, closing the "runnable" gap.

Tool selection (in priority order):
  1. mvn compile   — if Maven is on PATH
  2. javac         — if only JDK is on PATH (no class-path resolution, catches syntax/symbol errors)
  3. LLM static    — fallback when no build tools are available at all

On failure + retries remaining  → writes structured feedback, routes back to Converter.
On failure + retries exhausted  → saves report and ends (dashboard surfaces the errors).
On success / skipped / unknown  → saves report and ends.
"""

import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import config
from graph.state import WorkflowState
from utils.file_handler import save_json
from utils.output_formatter import print_step, print_error
from utils.prompt_helper import PromptHelper


# ── Build tool detection ──────────────────────────────────────────────────────

def _find_maven() -> Optional[str]:
    for candidate in ("mvn", "mvn.cmd", "mvnw", "./mvnw"):
        if shutil.which(candidate):
            return candidate
    return None


def _find_javac() -> Optional[str]:
    return shutil.which("javac")


# ── Runners ───────────────────────────────────────────────────────────────────

def _run_maven(project_root: str, tool: str) -> Tuple[bool, str]:
    try:
        proc = subprocess.run(
            [tool, "compile", "-q", "--no-transfer-progress", "-B"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=config.BUILD_TIMEOUT_SECS,
        )
        output = f"{proc.stdout}\n{proc.stderr}".strip()
        return proc.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, f"mvn timed out after {config.BUILD_TIMEOUT_SECS}s"
    except Exception as exc:
        return False, f"mvn error: {exc}"


def _run_javac(project_root: str) -> Tuple[bool, str]:
    java_files = sorted(Path(project_root).rglob("src/main/java/**/*.java"))
    if not java_files:
        return True, "No Java source files found."
    try:
        proc = subprocess.run(
            ["javac", "-source", "17", "--release", "17", *[str(f) for f in java_files]],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=config.BUILD_TIMEOUT_SECS,
        )
        output = f"{proc.stdout}\n{proc.stderr}".strip()
        return proc.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, f"javac timed out after {config.BUILD_TIMEOUT_SECS}s"
    except Exception as exc:
        return False, f"javac error: {exc}"


def _validate_llm_static_result(result: dict) -> Tuple[bool, List[Dict], str]:
    """
    Validate the LLM static analysis output before trusting it.
    Repairs:
      - has_critical_issues not a bool  → defaults to True (safe: assume failure)
      - issues not a list               → reset to []
      - each issue missing required keys → filled with placeholders
      - summary not a string            → default message
    Returns (success, issues, summary).
    """
    repairs = []

    # has_critical_issues
    has_critical = result.get("has_critical_issues")
    if not isinstance(has_critical, bool):
        repairs.append(f"has_critical_issues is '{has_critical}' not bool — defaulting to True")
        has_critical = True   # safe default: assume there are issues

    # issues
    issues = result.get("issues")
    if not isinstance(issues, list):
        repairs.append(f"issues is {type(issues).__name__} not list — reset to []")
        issues = []
    else:
        for i, iss in enumerate(issues):
            if not isinstance(iss, dict):
                issues[i] = {"class": "unknown", "severity": "error",
                              "message": str(iss), "line": 0}
                repairs.append(f"issues[{i}] not a dict — wrapped")
                continue
            for key in ("class", "severity", "message"):
                if key not in iss:
                    iss[key] = "" if key != "line" else 0
                    repairs.append(f"issues[{i}] missing '{key}' — filled")

    # summary
    summary = result.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        summary = "LLM static analysis complete."
        repairs.append("summary missing or empty — using default")

    if repairs:
        print_step("Build Verifier",
                   f"LLM output validation: {len(repairs)} repair(s) — "
                   + "; ".join(repairs[:3])
                   + (" …" if len(repairs) > 3 else ""),
                   "warning")

    return (not has_critical), issues, summary


def _llm_static_check(converted_modules: List[Dict]) -> Tuple[Optional[bool], List[Dict], str]:
    """Ask the LLM to spot compilation issues when no build tools are available."""
    samples = []
    for mod in converted_modules[:10]:
        code = mod.get("java_code", "")[:2_000]
        samples.append({
            "class":   mod.get("name"),
            "package": mod.get("package"),
            "code":    code,
        })
    try:
        ph = PromptHelper("build_verifier")
        result = ph.invoke_and_parse(
            max_tokens=4_096,
            code_samples_json=json.dumps(samples, indent=2),
        )
        return _validate_llm_static_result(result)
    except Exception as exc:
        return None, [], f"LLM static check failed: {exc}"


# ── Error parsing ─────────────────────────────────────────────────────────────

def _parse_errors(output: str) -> List[Dict]:
    """Extract structured error records from Maven or javac output."""
    errors: List[Dict] = []
    seen: set = set()

    # Maven: [ERROR] /abs/path/File.java:[10,5] error: cannot find symbol
    for m in re.finditer(r"\[ERROR\]\s+(.+?\.java):\[(\d+),\d+\]\s+(.+)", output):
        fp, line, msg = m.group(1), m.group(2), m.group(3).strip()
        key = (fp, line, msg[:60])
        if key not in seen:
            seen.add(key)
            errors.append({"class": Path(fp).stem, "file": fp, "line": int(line), "message": msg})

    # javac: File.java:10: error: cannot find symbol
    if not errors:
        for m in re.finditer(r"(.+?\.java):(\d+):\s+error:\s+(.+)", output):
            fp, line, msg = m.group(1), m.group(2), m.group(3).strip()
            key = (fp, line, msg[:60])
            if key not in seen:
                seen.add(key)
                errors.append({"class": Path(fp).stem, "file": fp, "line": int(line), "message": msg})

    return errors


# ── Feedback formatter ────────────────────────────────────────────────────────

def _format_feedback(errors: List[Dict]) -> str:
    """Produce human-readable feedback grouped by class for the Converter."""
    by_class: Dict[str, List[str]] = {}
    for e in errors:
        by_class.setdefault(e.get("class", "unknown"), []).append(
            f"  Line {e.get('line', '?')}: {e.get('message', '')}"
        )
    lines = ["Compilation failed. Fix these errors:\n"]
    for cls, msgs in by_class.items():
        lines.append(f"Class: {cls}")
        lines.extend(msgs)
        lines.append("")
    return "\n".join(lines)


# ── Node ──────────────────────────────────────────────────────────────────────

def build_verifier_node(state: WorkflowState) -> dict:
    print_step("Build Verifier", "Verifying assembled project compiles…")

    assembly_result   = state.get("assembly_result")
    build_retries     = state.get("build_retries", 0)
    converted_modules = state.get("converted_modules", [])

    # ── Guard: nothing assembled ──────────────────────────────────────────────
    if not assembly_result:
        print_step("Build Verifier", "No assembled project — skipping.", "warning")
        report = {"status": "skipped", "reason": "no assembly result",
                  "timestamp": datetime.now(tz=timezone.utc).isoformat()}
        save_json(report, "build/build_report.json")
        return {"build_report": report, "build_feedback": "",
                "build_retries": build_retries + 1, "current_step": "build_verifier_skipped"}

    project_root = assembly_result.get("project_root", "")
    if not project_root or not Path(project_root).exists():
        print_step("Build Verifier", f"Project root missing: {project_root}", "warning")
        report = {"status": "skipped", "reason": "project root not found",
                  "timestamp": datetime.now(tz=timezone.utc).isoformat()}
        save_json(report, "build/build_report.json")
        return {"build_report": report, "build_feedback": "",
                "build_retries": build_retries + 1, "current_step": "build_verifier_skipped"}

    # ── Select and run build tool ─────────────────────────────────────────────
    maven  = _find_maven()
    javac  = _find_javac()
    method = "unknown"
    success: Optional[bool] = None
    raw_output = ""
    errors: List[Dict] = []

    if maven:
        method = f"maven ({maven})"
        print_step("Build Verifier", f"Running: {maven} compile …")
        success, raw_output = _run_maven(project_root, maven)
        if not success:
            errors = _parse_errors(raw_output)

    elif javac:
        method = "javac"
        print_step("Build Verifier", "Maven not found — falling back to javac …", "warning")
        success, raw_output = _run_javac(project_root)
        if not success:
            errors = _parse_errors(raw_output)

    else:
        method = "llm-static-analysis"
        print_step("Build Verifier",
                   "No build tools on PATH — using LLM static analysis (fallback) …", "warning")
        success, llm_issues, raw_output = _llm_static_check(converted_modules)
        errors = llm_issues

    # ── Build report ──────────────────────────────────────────────────────────
    failing_classes = sorted({e.get("class", "") for e in errors if e.get("class")})
    status = "success" if success is True else ("unknown" if success is None else "failed")

    report = {
        "status":          status,
        "method":          method,
        "timestamp":       datetime.now(tz=timezone.utc).isoformat(),
        "project_root":    project_root,
        "error_count":     len(errors),
        "failing_classes": failing_classes,
        "errors":          errors,
        "raw_output":      raw_output[:4_000],
        "build_retries":   build_retries,
    }
    save_json(report, "build/build_report.json")

    # ── Success / unknown ─────────────────────────────────────────────────────
    if success is True:
        print_step("Build Verifier", f"Compilation SUCCESS via {method}.", "success")
        return {"build_report": report, "build_feedback": "",
                "build_retries": build_retries + 1, "current_step": "build_verifier_passed"}

    if success is None:
        print_step("Build Verifier", "Build status unknown (no tools). Report saved.", "warning")
        return {"build_report": report, "build_feedback": "",
                "build_retries": build_retries + 1, "current_step": "build_verifier_unknown"}

    # ── Failure ───────────────────────────────────────────────────────────────
    print_step(
        "Build Verifier",
        f"Compilation FAILED — {len(errors)} error(s) in {len(failing_classes)} class(es). "
        f"(attempt {build_retries + 1} / {config.MAX_BUILD_RETRIES})",
        "error",
    )

    feedback = _format_feedback(errors) if errors else raw_output[:2_000]

    return {
        "build_report":   report,
        "build_feedback": feedback,
        "build_retries":  build_retries + 1,
        "current_step":   "build_verifier_failed",
    }
