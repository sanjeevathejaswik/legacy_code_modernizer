"""
Streamlit Dashboard — Legacy Code Conversion Pipeline
======================================================
Upload a legacy Java file, run the pipeline, review the audit report,
approve or reject, and view all generated artefacts — all from one UI.

Run:
  streamlit run dashboard/app.py
"""

import json
import os
import sys
import time
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Make project root importable (needed when launching via `streamlit run dashboard/app.py`)
sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Legacy Code Conversion",
    page_icon="🔄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Always resolve output dir relative to the project root, not the script dir
_PROJECT_ROOT    = Path(__file__).parent.parent
_BASE_OUTPUT_DIR = os.getenv("OUTPUT_DIR", str(_PROJECT_ROOT / "output"))


# ── Shared severity config (single source of truth) ──────────────────────────
_SEV = {
    "critical": {"icon": "🔴", "label": "Critical", "color": "#e74c3c", "order": 0},
    "major":    {"icon": "🟡", "label": "Major",    "color": "#f39c12", "order": 1},
    "minor":    {"icon": "⚪", "label": "Minor",    "color": "#bdc3c7", "order": 2},
}

def _sev_counts(issues: list) -> dict:
    return {sev: sum(1 for i in issues if i.get("severity") == sev) for sev in _SEV}


# ── API helper (approve / reject) ─────────────────────────────────────────────

def _api_post(url: str, timeout: int = 10) -> tuple:
    import urllib.request, urllib.error
    try:
        req = urllib.request.Request(
            url, method="POST", data=b"", headers={"Content-Length": "0"}
        )
        with urllib.request.urlopen(req, timeout=timeout):
            return True, ""
    except urllib.error.HTTPError as e:
        return False, f"API error {e.code}: {e.read().decode()}"
    except Exception as exc:
        return False, str(exc)


# ── Discover all previous runs (cached for 30 s to avoid repeated disk scans) ─

@st.cache_data(ttl=30, show_spinner=False)
def _discover_runs() -> list:
    from datetime import datetime as _dt
    base = Path(_BASE_OUTPUT_DIR)
    if not base.exists():
        return []
    runs = []
    for d in base.iterdir():
        if not d.is_dir() or len(d.name) < 8 or d.name == "logs":
            continue
        mod_f = d / "modules" / "modules.json"
        if not mod_f.exists():
            continue
        try:
            mtime   = d.stat().st_mtime
            ts_disp = _dt.fromtimestamp(mtime).strftime("%d %b %Y  %H:%M")

            n_modules = len(json.loads(mod_f.read_text(encoding="utf-8")).get("modules", []))

            conv_f = d / "converted" / "conversion_summary.json"
            n_converted = (
                len(json.loads(conv_f.read_text(encoding="utf-8")).get("converted_modules", []))
                if conv_f.exists() else 0
            )
            audit_f = d / "audit" / "audit_report.json"
            score = (
                json.loads(audit_f.read_text(encoding="utf-8")).get("score")
                if audit_f.exists() else None
            )
            score_str = f"  |  Audit: {score:.0f}/100" if score is not None else ""
            runs.append({
                "path":      str(d),
                "job_id":    d.name,
                "ts_sort":   mtime,
                "ts_disp":   ts_disp,
                "modules":   n_modules,
                "converted": n_converted,
                "score":     score,
                "label":     f"{ts_disp}  —  {n_modules} modules, {n_converted} converted{score_str}",
            })
        except Exception:
            continue
    return sorted(runs, key=lambda r: r["ts_sort"], reverse=True)


def _resolve_output_dir(runs: list) -> str:
    """Single call — takes the already-fetched runs list to avoid a second scan."""
    # 1. Active in-memory job
    job_id = st.session_state.get("job_id")
    if job_id:
        try:
            from app.services.pipeline import PipelineService
            job = PipelineService.get_service().get_job(job_id)
            if job and job.output_dir and Path(job.output_dir).exists():
                return job.output_dir
        except Exception:
            pass

    # 2. User-selected via sidebar selectbox
    chosen_label = st.session_state.get("run_selector_key", "")
    if chosen_label and chosen_label != "── Select a run ──":
        for r in runs:
            if r["label"] == chosen_label and Path(r["path"]).exists():
                return r["path"]

    # 3. Persistent marker written on pipeline completion
    marker = Path(_BASE_OUTPUT_DIR) / "current_run.txt"
    if marker.exists():
        candidate = marker.read_text(encoding="utf-8").strip()
        if Path(candidate).exists():
            return candidate

    # 4. Auto-detect most complete run
    if runs:
        best = max(runs, key=lambda r: (r["converted"], r["score"] or 0))
        if best["modules"] > 0:
            return best["path"]

    return _BASE_OUTPUT_DIR


_ALL_RUNS  = _discover_runs()          # single scan per render, shared everywhere
OUTPUT_DIR = _resolve_output_dir(_ALL_RUNS)


# ── Data loaders ──────────────────────────────────────────────────────────────

def _load_json(relative_path: str):
    for base in [OUTPUT_DIR, _BASE_OUTPUT_DIR]:
        p = Path(base) / relative_path
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    return None


def _safe_list(v) -> list:
    """Return v if it's a list, else []."""
    return v if isinstance(v, list) else []

def _safe_str(v) -> str:
    """Return v if it's a str, else ''."""
    return v if isinstance(v, str) else ""

def _safe_dict(v) -> dict:
    """Return v if it's a dict, else {}."""
    return v if isinstance(v, dict) else {}

def _normalize_docs(docs) -> dict:
    """
    Convert ANY structure the LLM may return into the canonical six-key schema.

    Known LLM output shapes:
      A  {"overview": ..., "business_rules": [...], ...}   — already correct
      B  {"modules": [{name, layer, businessRules, ...}]}  — module-centric dict
      C  [{name, layer, businessRules, ...}]               — bare module list

    Always returns a dict with exactly these keys (never raises, never returns a list):
      overview, business_rules, data_models, service_interfaces, module_docs, technical_specs
    """
    # Nothing to work with
    if not docs:
        return {}

    # Shape A — keys already match the expected schema
    if isinstance(docs, dict) and any(
        k in docs for k in ("overview", "business_rules", "module_docs")
    ):
        # Guarantee every key exists and has the right type
        return {
            "overview":           _safe_str(docs.get("overview")),
            "business_rules":     _safe_list(docs.get("business_rules")),
            "data_models":        _safe_list(docs.get("data_models")),
            "service_interfaces": _safe_list(docs.get("service_interfaces")),
            "module_docs":        _safe_list(docs.get("module_docs")),
            "technical_specs":    _safe_str(docs.get("technical_specs")),
        }

    # Unwrap shapes B and C into a flat module list
    raw_modules = docs if isinstance(docs, list) else (
        docs.get("modules", []) if isinstance(docs, dict) else []
    )
    # Keep only dict items — discard any malformed entries
    modules = [m for m in raw_modules if isinstance(m, dict)]

    all_rules: list = []
    module_docs: list = []
    data_models: list = []
    service_interfaces: list = []

    for m in modules:
        name  = _safe_str(m.get("name",  "?"))
        desc  = _safe_str(m.get("description", ""))
        layer = _safe_str(m.get("layer",  ""))
        rules = _safe_list(m.get("businessRules", m.get("business_rules", [])))
        deps  = _safe_list(m.get("dependencies", []))

        for r in rules:
            all_rules.append(f"[{name}] {_safe_str(r)}")

        module_docs.append({
            "module":         name,
            "purpose":        desc,
            "business_logic": " | ".join(_safe_str(r) for r in rules) or desc,
            "dependencies":   deps,
            "error_handling": _safe_str(m.get("errorHandling", m.get("error_handling", ""))),
        })

        if layer in ("model", "dto", "entity"):
            data_models.append({
                "name":        name,
                "description": desc,
                "fields":      _safe_list(m.get("fields", [])),
            })

        if layer in ("service", "controller", "repository"):
            service_interfaces.append({
                "name":        name,
                "description": desc,
                "methods":     _safe_list(m.get("methods", [])),
            })

    return {
        "overview":           f"System contains {len(modules)} components across multiple layers.",
        "business_rules":     all_rules,
        "data_models":        data_models,
        "service_interfaces": service_interfaces,
        "module_docs":        module_docs,
        "technical_specs":    _safe_str(docs.get("technical_specs", "")) if isinstance(docs, dict) else "",
    }


def _list_java_files(sub: str) -> list[str]:
    for base in [OUTPUT_DIR, _BASE_OUTPUT_DIR]:
        d = Path(base) / sub
        if d.exists():
            return sorted(f.name for f in d.iterdir() if f.suffix == ".java")
    return []


def _read_java(sub: str, filename: str) -> str:
    for base in [OUTPUT_DIR, _BASE_OUTPUT_DIR]:
        p = Path(base) / sub / filename
        if p.exists():
            return p.read_text(encoding="utf-8")
    return "// File not found"


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🔄 Legacy Code\nConversion")
    st.markdown("---")
    page = st.radio(
        "Navigate",
        [
            "🚀 Run Pipeline",
            "📊 Overview",
            "🔧 Code Modules",
            "📝 Documentation",
            "🔍 Audit Report",
            "☕ Converted Code",
            "🧪 Test Suites",
            "🔗 Dependency Graph",
            "🏗️ Build Report",
            "📡 Observability",
        ],
        label_visibility="collapsed",
    )
    st.markdown("---")

    # ── Live job status badge ─────────────────────────────────────────────────
    _job_id = st.session_state.get("job_id")
    if _job_id:
        try:
            from app.services.pipeline import PipelineService as _PS
            _j = _PS.get_service().get_job(_job_id)
            if _j:
                _badge = {
                    "queued":          "🟡 Queued",
                    "running":         "🔵 Running…",
                    "awaiting_review": "🟠 Awaiting review",
                    "complete":        "🟢 Complete",
                    "failed":          "🔴 Failed",
                }.get(_j.status, _j.status)
                st.markdown(f"**Job status:** {_badge}")
        except Exception:
            pass

    # ── Run selector ──────────────────────────────────────────────────────────
    if _ALL_RUNS:
        st.markdown("**Select pipeline run to view:**")
        _placeholder = "── Select a run ──"
        _run_labels  = [_placeholder] + [r["label"] for r in _ALL_RUNS]
        st.selectbox("Run", _run_labels, key="run_selector_key", label_visibility="collapsed")
        _active_run = next((r for r in _ALL_RUNS if r["path"] == OUTPUT_DIR), None)
        if _active_run:
            st.success(
                f"Showing: **{_active_run['ts_disp']}**\n\n"
                f"{_active_run['modules']} modules · "
                f"{_active_run['converted']} converted"
                + (f" · score {_active_run['score']:.0f}" if _active_run["score"] else "")
            )
    else:
        st.caption(f"Output: `{Path(OUTPUT_DIR).name}`")

    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()


# ── Page: Run Pipeline ────────────────────────────────────────────────────────

if page == "🚀 Run Pipeline":

    # ── Session state ──────────────────────────────────────────────────────────
    if "job_id" not in st.session_state: st.session_state.job_id = None

    from app.services.pipeline import PipelineService
    import json as _json
    svc = PipelineService.get_service()

    # ── Pipeline stage stepper ─────────────────────────────────────────────────
    STAGES = ["Upload", "Split Code", "Document", "Audit + Review", "Convert", "Test", "Assemble", "Done"]

    def _stepper(active_idx: int) -> None:
        cols = st.columns(len(STAGES))
        for i, (col, name) in enumerate(zip(cols, STAGES)):
            if i < active_idx:
                col.markdown(f"<div style='text-align:center;color:#27ae60;font-size:12px'>✅<br><b>{name}</b></div>", unsafe_allow_html=True)
            elif i == active_idx:
                col.markdown(f"<div style='text-align:center;color:#e67e22;font-size:12px'>▶<br><b>{name}</b></div>", unsafe_allow_html=True)
            else:
                col.markdown(f"<div style='text-align:center;color:#bdc3c7;font-size:12px'>○<br>{name}</div>", unsafe_allow_html=True)
        st.markdown("<hr style='margin:8px 0'>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # STATE: IDLE — show upload
    # ══════════════════════════════════════════════════════════════════════════
    if st.session_state.job_id is None:
        st.title("🚀 Legacy Code Conversion")
        st.markdown("Upload your Java source file and the AI pipeline will automatically split, document, audit, and convert it to Spring Boot microservices.")
        _stepper(0)

        # ── Azure config check ─────────────────────────────────────────────────
        import config as _cfg
        _missing_vars = []
        if not _cfg.AZURE_OPENAI_ENDPOINT:
            _missing_vars.append(("AZURE_OPENAI_ENDPOINT", "Add to your `.env` file"))
        if not _cfg.AZURE_OPENAI_DEPLOYMENT:
            _missing_vars.append(("AZURE_OPENAI_DEPLOYMENT", "Add to your `.env` file"))
        if not _cfg.AZURE_OPENAI_API_KEY:
            _missing_vars.append((
                "AZURE_OPENAI_KEY_GPT4o",
                "Set in your terminal: `$env:AZURE_OPENAI_KEY_GPT4o = \"<your-key>\"`",
            ))

        if _missing_vars:
            st.error("**Azure OpenAI credentials are not configured** — the pipeline cannot start.")
            for var, hint in _missing_vars:
                st.markdown(f"- **`{var}`** — {hint}")
            st.info(
                "After setting the variables, restart the Streamlit app so the new values are loaded.\n\n"
                "PowerShell: `$env:AZURE_OPENAI_KEY_GPT4o = \"<your-key>\"` then `streamlit run dashboard/app.py`"
            )
            st.stop()
        else:
            st.success(
                f"Azure OpenAI ready — endpoint: `{_cfg.AZURE_OPENAI_ENDPOINT}` · "
                f"deployment: `{_cfg.AZURE_OPENAI_DEPLOYMENT}`"
            )

        st.markdown("### Step 1 — Upload your Java file")
        uploaded = st.file_uploader(
            "Drag & drop or click to browse",
            type=["java"],
            label_visibility="collapsed",
        )

        if uploaded:
            size_kb = len(uploaded.getvalue()) // 1024
            st.markdown(f"""
            <div style='background:#eafaf1;border:1px solid #27ae60;border-radius:8px;padding:16px;margin:8px 0'>
            <b>File ready:</b> {uploaded.name}<br>
            <span style='color:#666'>Size: {size_kb:,} KB &nbsp;|&nbsp; The pipeline will process this file through 7 AI agents</span>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("#### What will happen:")
            st.markdown("""
            1. **Split** — AI identifies all classes and components in your file
            2. **Document** — AI extracts business rules, data models, and logic
            3. **Audit** — AI scores the documentation quality (you review this)
            4. **You decide** — Approve to convert, or Reject to improve docs first
            5. **Convert** — AI rewrites code as Spring Boot 3 microservices
            6. **Test** — AI generates JUnit 5 unit tests
            7. **Assemble** — AI produces a complete Maven project ready to build
            """)

            if st.button("Start Conversion Pipeline", type="primary", use_container_width=True):
                job = svc.create_job(uploaded.name, uploaded.getvalue())
                svc.submit_job(job.job_id)
                st.session_state.job_id = job.job_id
                st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # STATE: JOB ACTIVE
    # ══════════════════════════════════════════════════════════════════════════
    else:
        job = svc.get_job(st.session_state.job_id)
        if not job:
            st.error("Session expired. Please start a new run.")
            st.session_state.job_id = None
            st.rerun()

        # ── RUNNING ───────────────────────────────────────────────────────────
        if job.status in ("queued", "running"):
            st.title("⚙️ Pipeline Running…")
            _stepper(2)   # approximately at document stage

            st.markdown(f"""
            <div style='background:#ebf5fb;border:1px solid #3498db;border-radius:8px;padding:20px;margin:12px 0'>
            <h4 style='margin:0 0 8px 0;color:#2980b9'>The AI agents are working on your file</h4>
            <p style='margin:0;color:#555'>This usually takes <b>10–15 minutes</b> for a large file.<br>
            When the documentation audit is ready, this page will show you the results and ask for your decision.</p>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("**What's happening right now:**")
            st.markdown("""
            - Agent 1 is reading your Java file and splitting it into logical modules
            - Agent 2 will then extract business rules and create documentation
            - Agent 3 will score the documentation quality out of 100
            - **You will be asked to review the score and approve or reject before conversion starts**
            """)

            started = job.started_at[:19].replace("T", " ") + " UTC" if job.started_at else "just now"
            st.caption(f"Started: {started}  |  Job: `{job.job_id[:8]}…`")

            st.button("🔄 Check for updates", use_container_width=True)

        # ── AWAITING HUMAN REVIEW ─────────────────────────────────────────────
        elif job.status == "awaiting_review":
            st.title("📋 Documentation Review Required")
            _stepper(3)

            # Load audit report
            audit_path = Path(job.output_dir) / "audit" / "audit_report.json"
            audit = {}
            if audit_path.exists():
                audit = _json.loads(audit_path.read_text(encoding="utf-8"))

            score     = float(audit.get("score", 0))
            passed    = audit.get("passed", False)
            threshold = float(audit.get("threshold", 70))
            issues    = audit.get("issues", [])
            metrics   = audit.get("metrics", {})
            summary   = audit.get("summary", "")
            recs      = audit.get("recommendations", [])

            no_docs = score == 0 and not audit.get("metrics")

            # ── Top verdict card ──────────────────────────────────────────────
            if no_docs:
                st.error("""
                **The AI could not generate documentation for this file.**

                This usually means the AI service had trouble processing the file.
                Click **Try Again** below — the AI will attempt documentation again.
                """)
            elif passed:
                st.success(f"""
                **Documentation looks good! Score: {score:.0f} / 100**

                The AI reviewed the generated documentation and it meets the quality bar ({threshold:.0f}/100).
                You can safely approve and let the conversion begin, or reject if you spot issues below.
                """)
            else:
                st.warning(f"""
                **Documentation needs improvement. Score: {score:.0f} / 100** (minimum needed: {threshold:.0f})

                The AI found some gaps in the documentation. Review the issues below.
                You can still approve to proceed, or reject to let the AI try again automatically.
                """)

            if not no_docs:
                # ── What the score means ──────────────────────────────────────
                st.markdown("---")
                st.markdown("### How good is the documentation?")
                sc1, sc2, sc3, sc4 = st.columns(4)
                labels = {"completeness": "All modules\ndocumented?",
                          "accuracy":     "Docs match\nactual code?",
                          "clarity":      "Easy to\nunderstand?",
                          "coverage":     "Business rules\ncaptured?"}
                for col, (key, label) in zip([sc1,sc2,sc3,sc4], labels.items()):
                    val = int(metrics.get(key, 0))
                    colour = "#27ae60" if val >= threshold else "#e74c3c"
                    col.markdown(
                        f"<div style='text-align:center;padding:12px;background:#f8f9fa;border-radius:8px;border-top:4px solid {colour}'>"
                        f"<div style='font-size:28px;font-weight:bold;color:{colour}'>{val}</div>"
                        f"<div style='font-size:11px;color:#555;white-space:pre'>{label}</div>"
                        f"</div>", unsafe_allow_html=True
                    )

                if summary:
                    st.markdown("---")
                    st.info(f"**AI assessment:** {summary}")

                # ── Gap summary banner ────────────────────────────────────────
                st.markdown("---")
                critical = [i for i in issues if i.get("severity") == "critical"]
                major    = [i for i in issues if i.get("severity") == "major"]
                minor    = [i for i in issues if i.get("severity") == "minor"]

                if issues:
                    # Counts banner
                    b1, b2, b3 = st.columns(3)
                    b1.markdown(
                        f"<div style='text-align:center;background:#fdf2f2;border:2px solid #e74c3c;border-radius:8px;padding:14px'>"
                        f"<div style='font-size:32px;font-weight:bold;color:#e74c3c'>{len(critical)}</div>"
                        f"<div style='color:#666;font-size:13px'>Critical gaps<br><small>Must review before approving</small></div></div>",
                        unsafe_allow_html=True)
                    b2.markdown(
                        f"<div style='text-align:center;background:#fefdf0;border:2px solid #f39c12;border-radius:8px;padding:14px'>"
                        f"<div style='font-size:32px;font-weight:bold;color:#f39c12'>{len(major)}</div>"
                        f"<div style='color:#666;font-size:13px'>Major gaps<br><small>Should review before approving</small></div></div>",
                        unsafe_allow_html=True)
                    b3.markdown(
                        f"<div style='text-align:center;background:#f8f9fa;border:2px solid #bdc3c7;border-radius:8px;padding:14px'>"
                        f"<div style='font-size:32px;font-weight:bold;color:#7f8c8d'>{len(minor)}</div>"
                        f"<div style='color:#666;font-size:13px'>Minor notes<br><small>Optional — low risk</small></div></div>",
                        unsafe_allow_html=True)

                    st.markdown("<br>", unsafe_allow_html=True)

                    # ── Full gaps table ───────────────────────────────────────
                    st.markdown("### What is missing or incomplete")
                    st.markdown("The table below shows every gap the AI found. These are the areas you should manually verify before approving.")

                    SEV_BADGE = {
                        "critical": "🔴 Critical",
                        "major":    "🟡 Major",
                        "minor":    "⚪ Minor",
                    }
                    for iss in sorted(issues, key=lambda x: {"critical":0,"major":1,"minor":2}.get(x.get("severity","minor"),2)):
                        sev    = iss.get("severity", "minor")
                        module = iss.get("module", "?")
                        issue  = iss.get("issue", "")
                        fix    = iss.get("suggestion", "")
                        badge  = SEV_BADGE.get(sev, "⚪ Minor")
                        border = {"critical":"#e74c3c","major":"#f39c12","minor":"#bdc3c7"}.get(sev,"#bdc3c7")
                        st.markdown(
                            f"""<div style='border-left:4px solid {border};background:#fafafa;
                                border-radius:0 8px 8px 0;padding:14px 18px;margin:8px 0'>
                                <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:6px'>
                                  <span style='font-weight:bold;font-size:15px'>{module}</span>
                                  <span style='font-size:12px;color:#666'>{badge}</span>
                                </div>
                                <div style='color:#333;margin-bottom:6px'><b>What is missing:</b> {issue}</div>
                                <div style='color:#27ae60'><b>What to check / do:</b> {fix}</div>
                            </div>""",
                            unsafe_allow_html=True,
                        )

                else:
                    st.success("No gaps found — documentation looks complete.")

                # ── Recommendations as action cards ───────────────────────────
                if recs:
                    st.markdown("---")
                    st.markdown("### Recommended actions before approving")
                    st.markdown("If you choose to **Reject**, the AI will focus on these improvements automatically. If you **Approve**, handle these manually after conversion.")
                    for i, rec in enumerate(recs, 1):
                        st.markdown(
                            f"""<div style='background:#eaf4fb;border:1px solid #3498db;border-radius:8px;
                                padding:14px 18px;margin:8px 0;display:flex;align-items:flex-start;gap:12px'>
                                <span style='background:#3498db;color:white;border-radius:50%;
                                  width:26px;height:26px;display:inline-flex;align-items:center;
                                  justify-content:center;font-weight:bold;flex-shrink:0'>{i}</span>
                                <span style='color:#1a5276'>{rec}</span>
                            </div>""",
                            unsafe_allow_html=True,
                        )

            # ── Decision buttons ──────────────────────────────────────────────
            st.markdown("---")
            st.markdown("### Your decision")

            if no_docs:
                st.markdown("The AI couldn't generate documentation. Click **Try Again** to retry.")
                if st.button("🔄 Try Again", type="primary", use_container_width=True):
                    if svc.resume_job(job.job_id, "reject"):
                        st.rerun()
            else:
                recommend = "approve" if passed else "reject"
                if recommend == "approve":
                    st.markdown("**Our recommendation: Approve** — the documentation is good enough to proceed.")
                else:
                    st.markdown("**Our recommendation: Let AI try again** — score is below the quality threshold.")

                a_col, r_col = st.columns(2)
                with a_col:
                    approve_label = "✅ Approve — start code conversion" if passed else "✅ Approve anyway — start code conversion"
                    if st.button(approve_label, type="primary" if passed else "secondary", use_container_width=True):
                        if svc.resume_job(job.job_id, "approve"):
                            st.success("Approved! Code conversion starting…")
                            time.sleep(1); st.rerun()

                with r_col:
                    reject_label = "🔄 Let AI improve documentation first" if not passed else "❌ Reject — ask AI to improve docs"
                    if st.button(reject_label, type="primary" if not passed else "secondary", use_container_width=True):
                        if svc.resume_job(job.job_id, "reject"):
                            st.info("Sent back for improvement. The AI will re-document and re-audit.")
                            time.sleep(1); st.rerun()

                st.caption("Approving means: the AI will now convert the code to Spring Boot microservices using this documentation.")
                st.caption("Rejecting means: the AI will re-read the code and try to write better documentation, then ask you again.")

        # ── COMPLETE ──────────────────────────────────────────────────────────
        elif job.status == "complete":
            out_check = Path(job.output_dir) / "converted" / "conversion_summary.json"
            conversion_ran = out_check.exists()

            if conversion_ran:
                st.title("✅ Conversion Complete!")
                _stepper(7)
                st.success("Your legacy Java file has been fully converted to Spring Boot microservices.")
            else:
                st.title("⚠️ Pipeline Stopped at Review Stage")
                _stepper(3)
                st.warning("""
                **The conversion step did not run.**

                This happens when you click **Reject** at the review stage — the pipeline
                re-documents and re-audits, then waits for a new decision.
                Because the page was refreshed or the session ended before the second
                review appeared, the job was marked complete prematurely.

                **What to do:**
                - Start a new run and click **Approve** at the review step, OR
                - Select a previous completed run from the sidebar dropdown to view full results.
                """)

            # Read actual counts from output files (source of truth)
            out = Path(job.output_dir)
            def _count(rel, key):
                p = out / rel
                if not p.exists():          # fallback to global output dir
                    p = Path(OUTPUT_DIR) / rel
                if p.exists():
                    d = _json.loads(p.read_text(encoding="utf-8"))
                    return len(d.get(key, []))
                return 0
            def _score(rel, key):
                p = out / rel
                if not p.exists():
                    p = Path(OUTPUT_DIR) / rel
                if p.exists():
                    d = _json.loads(p.read_text(encoding="utf-8"))
                    return d.get(key)
                return None

            n_modules   = _count("modules/modules.json",             "modules")           or job.modules_count
            n_converted = _count("converted/conversion_summary.json","converted_modules") or job.converted_count
            n_tests     = _count("tests/test_suites_summary.json",   "test_suites")       or job.test_suites_count
            n_assembled = _score("assembled/assembly_manifest.json", "total_files")
            audit_score = _score("audit/audit_report.json", "score")
            audit_pass  = _score("audit/audit_report.json", "passed")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Classes found",    n_modules,   help="Distinct Java classes identified in the original file")
            c2.metric("Classes converted",n_converted, help="Converted to Spring Boot 3 / Java 17 components")
            c3.metric("Test classes",     n_tests,     help="JUnit 5 test files generated")
            c4.metric("Files assembled",  n_assembled or 0, help="Total files in the compiled Maven project")

            if audit_score is not None:
                score_col = "normal" if audit_pass else "inverse"
                st.metric("Documentation quality", f"{audit_score:.1f} / 100",
                          delta="Passed quality check" if audit_pass else "Below threshold — you approved",
                          delta_color=score_col)

            st.markdown("---")
            st.markdown("### What's been generated")
            st.markdown("""
            | What | Where to view |
            |------|--------------|
            | Identified modules | Sidebar → Code Modules |
            | Business documentation | Sidebar → Documentation |
            | Audit quality report | Sidebar → Audit Report |
            | Spring Boot source code | Sidebar → Converted Code |
            | JUnit 5 tests | Sidebar → Test Suites |
            | Dependency graph | Sidebar → Dependency Graph |
            | Build result | Sidebar → Build Report |
            | Timing & token usage | Sidebar → Observability |
            """)

            if st.button("Start a new conversion", use_container_width=True):
                st.session_state.job_id = None; st.rerun()

        # ── FAILED ────────────────────────────────────────────────────────────
        elif job.status == "failed":
            st.title("❌ Pipeline Failed")
            _stepper(1)
            st.error(f"""
            **Something went wrong during the conversion.**

            Error: {job.error or 'Unknown error'}

            **Most common causes:**
            - Azure OpenAI API key or endpoint is incorrect
            - The Java file is too large or has encoding issues
            - Network timeout during a long AI call
            """)
            if st.button("Try again with a new file", type="primary", use_container_width=True):
                st.session_state.job_id = None; st.rerun()

        else:
            st.info(f"Status: {job.status}")
            if st.button("🔄 Refresh"): st.rerun()


# ── Page: Overview ────────────────────────────────────────────────────────────

elif page == "📊 Overview":
    st.title("🔄 Legacy Code Conversion — Pipeline Dashboard")
    st.markdown("---")

    modules_data   = _load_json("modules/modules.json")
    docs_data      = _load_json("docs/documentation.json")
    audit_data     = _load_json("audit/audit_report.json")
    conv_data      = _load_json("converted/conversion_summary.json")
    tests_data     = _load_json("tests/test_suites_summary.json")

    # ── KPI row ────────────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)

    modules_count = len((modules_data or {}).get("modules", []))
    c1.metric("Modules Split", modules_count)

    c2.metric("Documentation", "✅ Done" if docs_data else "⏳ Pending")

    if audit_data:
        score = audit_data.get("score", 0)
        passed = audit_data.get("passed", False)
        c3.metric(
            "Audit Score",
            f"{score:.1f} / 100",
            delta="PASSED ✅" if passed else "FAILED ❌",
            delta_color="normal" if passed else "inverse",
        )
    else:
        c3.metric("Audit Score", "⏳ Pending")

    conv_count = len((conv_data or {}).get("converted_modules", []))
    c4.metric("Converted Modules", conv_count,
              delta="⚠ Conversion failed — select a previous run" if conv_data and conv_count == 0 else None,
              delta_color="inverse" if conv_data and conv_count == 0 else "off")

    if tests_data:
        suites = tests_data.get("test_suites", [])
        total_tests = sum(s.get("test_count", 0) for s in suites)
        c5.metric("Unit Tests", total_tests, delta=f"{len(suites)} suites")
    elif conv_data:           # conversion ran but produced nothing → 0, not Pending
        c5.metric("Unit Tests", 0)
    else:
        c5.metric("Unit Tests", "⏳ Pending")

    st.markdown("---")

    # ── Pipeline stage status ──────────────────────────────────────────────────
    st.subheader("Pipeline Stage Status")
    stages = [
        ("1. Code Splitter", modules_data is not None),
        ("2. Documenter",    docs_data is not None),
        ("3. Auditor",       audit_data is not None),
        ("4. Converter",     conv_data is not None),
        ("5. Tester",        tests_data is not None),
    ]
    cols = st.columns(5)
    for col, (label, done) in zip(cols, stages):
        if done:
            col.success(f"✅ {label}")
        else:
            col.warning(f"⏳ {label}")

    st.markdown("---")

    # ── Charts ────────────────────────────────────────────────────────────────
    if modules_data or audit_data:
        left, right = st.columns(2)

        if modules_data:
            with left:
                st.subheader("Modules by Layer")
                mods = modules_data.get("modules", [])
                layer_counts = {}
                for m in mods:
                    l = m.get("layer", "unknown")
                    layer_counts[l] = layer_counts.get(l, 0) + 1
                fig = px.pie(
                    values=list(layer_counts.values()),
                    names=list(layer_counts.keys()),
                    color_discrete_sequence=px.colors.qualitative.Set2,
                    hole=0.35,
                )
                fig.update_layout(height=340, margin=dict(t=10, b=10))
                st.plotly_chart(fig, use_container_width=True)

        if audit_data:
            with right:
                st.subheader("Audit Metrics")
                metrics = audit_data.get("metrics", {})
                if metrics:
                    threshold = audit_data.get("threshold", 70)
                    fig = go.Figure(
                        go.Bar(
                            x=list(metrics.values()),
                            y=list(metrics.keys()),
                            orientation="h",
                            marker_color=[
                                "#2ecc71" if v >= threshold else "#e74c3c"
                                for v in metrics.values()
                            ],
                            text=[str(v) for v in metrics.values()],
                            textposition="inside",
                        )
                    )
                    fig.add_vline(x=threshold, line_dash="dash", line_color="orange",
                                  annotation_text=f"Threshold ({threshold})")
                    fig.update_layout(
                        xaxis=dict(range=[0, 100]),
                        height=340,
                        margin=dict(t=10, b=10),
                    )
                    st.plotly_chart(fig, use_container_width=True)


# ── Page: Code Modules ────────────────────────────────────────────────────────

elif page == "🔧 Code Modules":
    st.title("🔧 Identified Code Modules")

    data = _load_json("modules/modules.json")
    if not data:
        st.warning("No modules data found. Run the pipeline first.")
        st.stop()

    modules = data.get("modules", [])
    all_layers = sorted(set(m.get("layer", "unknown") for m in modules))

    col_f, col_s = st.columns([1, 2])
    with col_f:
        sel_layer = st.selectbox("Filter by layer", ["All"] + all_layers)
    with col_s:
        search = st.text_input("Search by name", placeholder="ClassName…")

    filtered = modules
    if sel_layer != "All":
        filtered = [m for m in filtered if m.get("layer") == sel_layer]
    if search:
        filtered = [m for m in filtered if search.lower() in m.get("name", "").lower()]

    st.caption(f"Showing {len(filtered)} of {len(modules)} modules")

    for mod in filtered:
        label = f"📦 {mod['name']}  [{mod.get('layer', 'unknown').upper()}]"
        with st.expander(label):
            info_col, code_col = st.columns([1, 3])
            with info_col:
                st.markdown(f"**Layer:** `{mod.get('layer')}`")
                deps = mod.get("dependencies", [])
                st.markdown(f"**Dependencies ({len(deps)}):**")
                for d in deps:
                    st.markdown(f"  `{d}`")
            with code_col:
                st.markdown(f"**Description:** {mod.get('description', '')}")
                st.code(mod.get("code", ""), language="java")


# ── Page: Documentation ───────────────────────────────────────────────────────

elif page == "📝 Documentation":
    st.title("📝 Technical Documentation")

    docs = _normalize_docs(_load_json("docs/documentation.json"))
    if not docs:
        st.warning("No documentation found. Run the pipeline first.")
        st.stop()

    tab_ov, tab_br, tab_dm, tab_si, tab_md, tab_ts = st.tabs(
        ["Overview", "Business Rules", "Data Models", "Service Interfaces", "Module Docs", "Technical Specs"]
    )

    with tab_ov:
        st.subheader("System Overview")
        st.markdown(docs.get("overview") or "_No overview available._")

    with tab_br:
        st.subheader("Business Rules")
        rules = [r for r in _safe_list(docs.get("business_rules")) if r]
        if rules:
            for i, rule in enumerate(rules, 1):
                st.markdown(f"{i}. {_safe_str(rule)}")
        else:
            st.info("No business rules documented.")

    with tab_dm:
        st.subheader("Data Models")
        models = [m for m in _safe_list(docs.get("data_models")) if isinstance(m, dict)]
        if not models:
            st.info("No data models documented.")
        for model in models:
            with st.expander(f"📋 {model.get('name', 'Unknown')}"):
                st.markdown(f"**Description:** {model.get('description', '')}")
                fields = _safe_list(model.get("fields"))
                if fields and all(isinstance(f, dict) for f in fields):
                    st.dataframe(pd.DataFrame(fields), use_container_width=True, hide_index=True)

    with tab_si:
        st.subheader("Service Interfaces")
        services = [s for s in _safe_list(docs.get("service_interfaces")) if isinstance(s, dict)]
        if not services:
            st.info("No service interfaces documented.")
        for svc in services:
            with st.expander(f"⚙️ {svc.get('name', 'Unknown')}"):
                st.markdown(f"**Description:** {svc.get('description', '')}")
                for meth in _safe_list(svc.get("methods")):
                    if not isinstance(meth, dict):
                        continue
                    params = ", ".join(_safe_list(meth.get("parameters")))
                    ret    = meth.get("returns", "void")
                    st.markdown(f"**`{meth.get('name', '?')}({params})`** → `{ret}`")
                    if meth.get("description"):
                        st.caption(meth.get("description"))

    with tab_md:
        st.subheader("Per-Module Documentation")
        mod_docs = [d for d in _safe_list(docs.get("module_docs")) if isinstance(d, dict)]
        if not mod_docs:
            st.info("No module documentation available.")
        for d in mod_docs:
            with st.expander(f"📄 {d.get('module', 'Unknown')}"):
                if d.get("purpose"):        st.markdown(f"**Purpose:** {d['purpose']}")
                if d.get("business_logic"): st.markdown(f"**Business Logic:** {d['business_logic']}")
                if d.get("error_handling"): st.markdown(f"**Error Handling:** {d['error_handling']}")
                deps = _safe_list(d.get("dependencies"))
                if deps:
                    st.markdown("**Dependencies:** " + ", ".join(f"`{dep}`" for dep in deps if dep))

    with tab_ts:
        st.subheader("Technical Specifications")
        specs = docs.get("technical_specs") or ""
        if specs:
            st.markdown(specs)
        else:
            st.info("No technical specifications documented.")


# ── Page: Audit Report ────────────────────────────────────────────────────────

elif page == "🔍 Audit Report":
    st.title("🔍 Documentation Audit Report")

    audit = _load_json("audit/audit_report.json")
    if not audit:
        st.warning("No audit report found. Run the pipeline first.")
        st.stop()

    score     = float(audit.get("score", 0))
    passed    = audit.get("passed", False)
    threshold = float(audit.get("threshold", 70))

    # ── Score gauge + status + issue bar ──────────────────────────────────────
    g_col, s_col, b_col = st.columns(3)

    with g_col:
        fig = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=score,
                title={"text": "Quality Score"},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": "#2ecc71" if passed else "#e74c3c"},
                    "steps": [
                        {"range": [0, threshold], "color": "#fde8e8"},
                        {"range": [threshold, 100], "color": "#e8fde8"},
                    ],
                    "threshold": {
                        "line": {"color": "orange", "width": 4},
                        "thickness": 0.75,
                        "value": threshold,
                    },
                },
            )
        )
        fig.update_layout(height=280, margin=dict(t=20, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with s_col:
        if passed:
            st.success("### ✅ AUDIT PASSED")
        else:
            st.error("### ❌ AUDIT FAILED")
        st.markdown(f"**Score:** `{score:.1f} / 100`")
        st.markdown(f"**Threshold:** `{threshold}`")
        st.markdown(f"**Timestamp:** `{audit.get('timestamp', 'N/A')}`")

    with b_col:
        issues = audit.get("issues", [])
        critical = sum(1 for i in issues if i.get("severity") == "critical")
        major    = sum(1 for i in issues if i.get("severity") == "major")
        minor    = sum(1 for i in issues if i.get("severity") == "minor")
        fig = go.Figure(
            go.Bar(
                x=["Critical", "Major", "Minor"],
                y=[critical, major, minor],
                marker_color=["#e74c3c", "#f39c12", "#95a5a6"],
                text=[critical, major, minor],
                textposition="outside",
            )
        )
        fig.update_layout(title="Issues by Severity", height=280, margin=dict(t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)

    # ── Metrics ────────────────────────────────────────────────────────────────
    metrics = audit.get("metrics", {})
    if metrics:
        st.markdown("---")
        st.subheader("Detailed Metrics")
        mcols = st.columns(len(metrics))
        for col, (k, v) in zip(mcols, metrics.items()):
            ok = int(v) >= threshold
            col.metric(k.capitalize(), f"{v} / 100",
                       delta="✅ OK" if ok else "⚠ Low",
                       delta_color="normal" if ok else "inverse")

    # ── Summary ────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Summary")
    st.info(audit.get("summary", "_No summary._"))

    # ── Issues list ────────────────────────────────────────────────────────────
    if issues:
        st.subheader(f"Issues ({len(issues)})")
        sev_order = {"critical": 0, "major": 1, "minor": 2}
        sorted_issues = sorted(issues, key=lambda x: sev_order.get(x.get("severity", "minor"), 2))
        sev_icon = {"critical": "🔴", "major": "🟡", "minor": "⚪"}
        for iss in sorted_issues:
            sev = iss.get("severity", "minor")
            icon = sev_icon.get(sev, "⚪")
            with st.expander(
                f"{icon} [{sev.upper()}] {iss.get('module', '?')} — {iss.get('issue', '')[:80]}"
            ):
                st.markdown(f"**Module:** `{iss.get('module', '?')}`")
                st.markdown(f"**Issue:** {iss.get('issue', '')}")
                st.markdown(f"**Suggestion:** {iss.get('suggestion', '')}")

    # ── Recommendations ────────────────────────────────────────────────────────
    recs = audit.get("recommendations", [])
    if recs:
        st.subheader("Recommendations")
        for rec in recs:
            st.markdown(f"💡 {rec}")

    # ── Evaluation Breakdown ───────────────────────────────────────────────────
    eb = audit.get("evaluation_breakdown", {})
    if eb:
        st.markdown("---")
        st.subheader("Evaluation Breakdown")

        det_score  = audit.get("deterministic_score", 0)
        deep_score = audit.get("deepeval_score", 0)

        d_col, e_col = st.columns(2)
        d_col.metric("Deterministic Score",
                     f"{det_score:.1f} / 100",
                     help="Schema completeness · Module coverage · Business logic depth")
        e_col.metric("DeepEval Score",
                     f"{deep_score:.1f} / 100",
                     help="Summarization · Faithfulness · Clarity")

        st.markdown("#### Deterministic Checks")
        det_tab1, det_tab2, det_tab3 = st.tabs(["Schema", "Coverage", "Depth"])

        with det_tab1:
            schema = eb.get("schema", {})
            st.metric("Score", f"{schema.get('score', 0):.1f} / 100")
            st.markdown(f"**Present:** {schema.get('present', '?')} / {schema.get('total', 6)} required keys")
            missing = schema.get("missing_keys", [])
            if missing:
                st.error(f"Missing sections: {', '.join(missing)}")
            else:
                st.success("All required sections present")

        with det_tab2:
            cov = eb.get("coverage", {})
            st.metric("Score", f"{cov.get('score', 0):.1f} / 100")
            st.markdown(f"**Covered:** {cov.get('covered', '?')} / {cov.get('total', '?')} modules")
            uncovered = cov.get("uncovered_modules", [])
            if uncovered:
                st.warning(f"Undocumented modules ({len(uncovered)}):")
                for m in uncovered:
                    st.markdown(f"  - `{m}`")
            else:
                st.success("All modules have a module_doc entry")

        with det_tab3:
            depth = eb.get("depth", {})
            st.metric("Score", f"{depth.get('score', 0):.1f} / 100")
            st.markdown(f"**Avg words:** {depth.get('avg_words', 0):.0f} &nbsp;&nbsp; "
                        f"**Min words:** {depth.get('min_words', 0)}")
            shallow = depth.get("shallow_modules", [])
            if shallow:
                st.warning(f"Shallow business_logic (< 20 words) in {len(shallow)} module(s):")
                for m in shallow:
                    st.markdown(f"  - `{m}`")
            else:
                st.success("All modules have sufficient business logic depth")

        st.markdown("#### DeepEval Metrics")
        de_tab1, de_tab2, de_tab3 = st.tabs(["Summarization", "Faithfulness", "Clarity"])

        with de_tab1:
            summ = eb.get("summarization", eb.get("llm_score", {}))
            s = float(summ.get("score", 0)) if "score" in summ else 0.0
            st.metric("Score", f"{s * 100:.1f} / 100" if s <= 1 else f"{s:.1f} / 100")
            st.markdown("**Does the documentation cover the key facts from the source code?**")
            if summ.get("reason"):
                st.caption(summ["reason"])
            st.success("Passed" if summ.get("passed") else "Below threshold",
                       icon="✅" if summ.get("passed") else "⚠️")

        with de_tab2:
            faith = eb.get("faithfulness", {})
            f_score  = float(faith.get("score", 0.5))
            h_rate   = float(faith.get("hallucination_rate", 0.5))
            st.metric("Faithfulness Score", f"{f_score:.2f}",
                      delta=f"Hallucination rate: {h_rate:.0%}",
                      delta_color="inverse" if h_rate > 0.3 else "normal")
            st.markdown("**Does the documentation hallucinate facts absent from the source?**")
            if faith.get("reason"):
                st.caption(faith["reason"])
            if h_rate > 0.4:
                st.error(f"High hallucination rate ({h_rate:.0%}) — documentation may contain invented facts")
            elif h_rate > 0.2:
                st.warning(f"Moderate hallucination rate ({h_rate:.0%})")
            else:
                st.success("Low hallucination rate — documentation is grounded in source code")

        with de_tab3:
            clar = eb.get("clarity_ai", {})
            c_score = float(clar.get("score", 0.5))
            st.metric("Score", f"{c_score * 100:.1f} / 100" if c_score <= 1 else f"{c_score:.1f} / 100")
            st.markdown("**Is the documentation clear, structured, and unambiguous?**")
            if clar.get("reason"):
                st.caption(clar["reason"])
            st.success("Passed" if clar.get("passed") else "Below threshold",
                       icon="✅" if clar.get("passed") else "⚠️")

    # ── HITL: Human Review Gate ───────────────────────────────────────────────
    hitl = _load_json("hitl/review_status.json")
    if hitl and hitl.get("status") == "awaiting_review":
        st.markdown("---")
        st.subheader("🙋 Human Review Required")
        st.warning(
            "The pipeline is **paused** and waiting for your decision before "
            "proceeding to code conversion. Review the audit report above, then:"
        )

        # Pull job_id from the API (stored in hitl file if available, else ask user)
        api_base = st.text_input(
            "FastAPI base URL", value="http://localhost:8000", key="api_base"
        )
        job_id_input = st.text_input("Job ID", key="job_id_input",
                                      placeholder="Paste job_id from the terminal or POST /convert response")

        col_a, col_r = st.columns(2)
        with col_a:
            if st.button("✅ APPROVE — proceed to conversion", type="primary", use_container_width=True):
                if job_id_input:
                    ok, err = _api_post(f"{api_base}/api/v1/jobs/{job_id_input}/approve")
                    if ok:  st.success("Approved! Pipeline resuming — conversion started."); st.rerun()
                    else:   st.error(err)
                else:
                    st.warning("Enter the Job ID first.")

        with col_r:
            if st.button("❌ REJECT — re-document", use_container_width=True):
                if job_id_input:
                    ok, err = _api_post(f"{api_base}/api/v1/jobs/{job_id_input}/reject")
                    if ok:  st.info("Rejected. Pipeline resuming — re-documenting."); st.rerun()
                    else:   st.error(err)
                else:
                    st.warning("Enter the Job ID first.")

        if st.button("🔄 Refresh status"):
            st.rerun()

    elif hitl and hitl.get("status") == "decided":
        st.markdown("---")
        decision = hitl.get("decision", "?").upper()
        if decision == "APPROVE":
            st.success(f"Human decision: {decision} — pipeline is running conversion.")
        else:
            st.info(f"Human decision: {decision} — pipeline is re-documenting.")


# ── Page: Converted Code ──────────────────────────────────────────────────────

elif page == "☕ Converted Code":
    st.title("☕ Converted Java Microservices")

    data = _load_json("converted/conversion_summary.json")
    if not data:
        st.warning("No converted code found. Run the pipeline first.")
        st.stop()

    converted = data.get("converted_modules", [])
    st.caption(f"{len(converted)} modules converted")

    # Type distribution chart
    type_counts: dict = {}
    for m in converted:
        t = m.get("microservice_type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1
    if type_counts:
        fig = px.bar(
            x=list(type_counts.keys()),
            y=list(type_counts.values()),
            labels={"x": "Type", "y": "Count"},
            color=list(type_counts.keys()),
            color_discrete_sequence=px.colors.qualitative.Pastel,
        )
        fig.update_layout(showlegend=False, height=280, margin=dict(t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    for mod in converted:
        label = f"☕ {mod.get('name', '?')}  [{mod.get('microservice_type', 'unknown').upper()}]"
        with st.expander(label):
            meta_col, code_col = st.columns([1, 3])
            with meta_col:
                st.markdown(f"**Package:**\n`{mod.get('package', 'N/A')}`")
                st.markdown(f"**Type:** `{mod.get('microservice_type', 'N/A')}`")
                deps = mod.get("dependencies", [])
                if deps:
                    st.markdown(f"**Dependencies ({len(deps)}):**")
                    for d in deps:
                        st.markdown(f"  `{d}`")
            with code_col:
                st.code(mod.get("java_code", "// No code"), language="java")

    # ── Converter Evaluation ──────────────────────────────────────────────────
    conv_eval = _load_json("converted/converter_eval.json")
    if conv_eval:
        st.markdown("---")
        st.subheader("Converter Evaluation")
        st.metric("Overall Score", f"{conv_eval.get('overall_score', 0)} / 100")
        t1, t2, t3, t4 = st.tabs(
            ["Spring Annotations", "Package Declarations", "Spring Imports", "No Stubs"]
        )
        with t1:
            c = conv_eval.get("spring_annotations", {})
            st.metric("Score", f"{c.get('score', 0)} / 100")
            missing = c.get("missing", [])
            if missing:
                st.warning(f"{len(missing)} module(s) missing expected Spring annotations:")
                for m in missing:
                    st.markdown(f"  - `{m['name']}` ({m['layer']}) — expected one of: "
                                f"`{'`, `'.join(m['expected_one_of'])}`")
            else:
                st.success("All modules have correct Spring annotations")
        with t2:
            c = conv_eval.get("package_declarations", {})
            st.metric("Score", f"{c.get('score', 0)} / 100")
            missing = c.get("missing_package", [])
            if missing:
                st.warning(f"Missing package declaration: {', '.join(f'`{m}`' for m in missing)}")
            else:
                st.success("All modules have package declarations")
        with t3:
            c = conv_eval.get("spring_imports", {})
            st.metric("Score", f"{c.get('score', 0)} / 100")
            missing = c.get("missing_spring_imports", [])
            if missing:
                st.warning(f"Missing Spring imports: {', '.join(f'`{m}`' for m in missing)}")
            else:
                st.success("All Spring modules import org.springframework")
        with t4:
            c = conv_eval.get("no_stubs", {})
            st.metric("Score", f"{c.get('score', 0)} / 100")
            stubs = c.get("stub_modules", [])
            if stubs:
                st.error(f"Stub code detected in: {', '.join(f'`{m}`' for m in stubs)}")
            else:
                st.success("No stub code detected")


# ── Page: Test Suites ─────────────────────────────────────────────────────────

elif page == "🧪 Test Suites":
    st.title("🧪 Generated Unit Tests")

    data = _load_json("tests/test_suites_summary.json")
    if not data:
        st.warning("No test suites found. Run the pipeline first.")
        st.stop()

    suites = data.get("test_suites", [])
    total_tests = sum(s.get("test_count", 0) for s in suites)

    kc1, kc2 = st.columns(2)
    kc1.metric("Test Suites", len(suites))
    kc2.metric("Total Tests", total_tests)

    st.markdown("---")
    for suite in suites:
        count = suite.get("test_count", 0)
        label = f"🧪 {suite.get('test_class_name', '?')}  ({count} tests)"
        with st.expander(label):
            st.caption(f"Module: `{suite.get('module_name', '?')}`  |  "
                       f"File: `{suite.get('file_path', 'N/A')}`")
            st.code(suite.get("test_code", "// No test code"), language="java")

    # ── Tester Evaluation ─────────────────────────────────────────────────────
    test_eval = _load_json("tests/tester_eval.json")
    if test_eval:
        st.markdown("---")
        st.subheader("Tester Evaluation")
        st.metric("Overall Score", f"{test_eval.get('overall_score', 0)} / 100")
        t1, t2, t3, t4 = st.tabs(
            ["@Test Annotations", "Assertions", "Coverage Ratio", "Mockito Usage"]
        )
        with t1:
            c = test_eval.get("test_annotations", {})
            st.metric("Score", f"{c.get('score', 0)} / 100")
            missing = c.get("missing_test_annotation", [])
            if missing:
                st.error(f"No @Test annotation in: {', '.join(f'`{m}`' for m in missing)}")
            else:
                st.success("All test classes have @Test annotations")
        with t2:
            c = test_eval.get("assertions", {})
            st.metric("Score", f"{c.get('score', 0)} / 100")
            missing = c.get("missing_assertions", [])
            if missing:
                st.error(f"No assertions in: {', '.join(f'`{m}`' for m in missing)}")
            else:
                st.success("All test classes have assertions")
        with t3:
            c = test_eval.get("coverage_ratio", {})
            st.metric("Score", f"{c.get('score', 0)} / 100",
                      help=f"{c.get('covered', 0)} / {c.get('total', 0)} modules tested")
            untested = c.get("untested_modules", [])
            if untested:
                st.warning(f"No test suite for: {', '.join(f'`{m}`' for m in untested)}")
            else:
                st.success("All converted modules have a test suite")
        with t4:
            c = test_eval.get("mockito_usage", {})
            st.metric("Score", f"{c.get('score', 0)} / 100")
            missing = c.get("missing_mocks", [])
            if missing:
                st.warning(f"No Mockito usage in: {', '.join(f'`{m}`' for m in missing)}")
            else:
                st.success("All service/controller tests use Mockito")


# ── Page: Dependency Graph ────────────────────────────────────────────────────

elif page == "🔗 Dependency Graph":
    st.title("🔗 Module Dependency Graph")

    data = _load_json("assembled/dependency_graph.json")
    if not data:
        st.warning("No dependency graph found. Run the pipeline first.")
        st.stop()

    # ── KPIs ──────────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Modules",    data.get("total_modules", 0))
    c2.metric("Microservice Groups", len(data.get("microservice_groups", {})))
    cycles = data.get("circular_deps", [])
    c3.metric("Circular Deps", len(cycles),
              delta="⚠ Fix before build" if cycles else "✅ None",
              delta_color="inverse" if cycles else "normal")
    most_dep = data.get("most_depended_on", [{}])
    c4.metric("Most Depended On", most_dep[0].get("name", "—") if most_dep else "—",
              delta=f"{most_dep[0].get('dependent_count', 0)} dependents" if most_dep else "")

    st.markdown("---")

    # ── Microservice groups ───────────────────────────────────────────────────
    st.subheader("Microservice Groups")
    groups = data.get("microservice_groups", {})
    GROUP_COLOURS = {
        "api":     "#3498db",
        "service": "#2ecc71",
        "data":    "#e67e22",
        "domain":  "#9b59b6",
        "shared":  "#95a5a6",
    }
    if groups:
        gcols = st.columns(len(groups))
        for col, (grp, members) in zip(gcols, groups.items()):
            colour = GROUP_COLOURS.get(grp, "#bdc3c7")
            col.markdown(
                f"<div style='background:{colour}22;border-left:4px solid {colour};"
                f"padding:8px;border-radius:4px'>"
                f"<b>{grp.upper()}</b><br/>"
                + "<br/>".join(f"• {m}" for m in members)
                + "</div>",
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # ── Build order ───────────────────────────────────────────────────────────
    st.subheader("Build Order (topological)")
    build_order = data.get("build_order", [])
    if build_order:
        order_df = pd.DataFrame(
            [{"#": i + 1, "Module": name} for i, name in enumerate(build_order)]
        )
        st.dataframe(order_df, use_container_width=True, hide_index=True, height=300)

    # ── Circular dependencies ─────────────────────────────────────────────────
    if cycles:
        st.markdown("---")
        st.subheader("⚠ Circular Dependencies")
        for i, cycle in enumerate(cycles, 1):
            st.error(f"Cycle {i}: " + " → ".join(cycle))

    # ── Most-depended-on ──────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Most Depended-On Modules")
    top = data.get("most_depended_on", [])
    if top:
        fig = px.bar(
            top,
            x="dependent_count",
            y="name",
            orientation="h",
            color="layer",
            text="dependent_count",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=280,
                          margin=dict(t=10, b=10), showlegend=True)
        st.plotly_chart(fig, use_container_width=True)

    # ── Full node table ────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("All Module Dependencies")
    nodes = data.get("nodes", {})
    if nodes:
        rows = [
            {
                "Module":       name,
                "Layer":        n.get("layer"),
                "Package":      n.get("package"),
                "Depends On":   len(n.get("dependencies", [])),
                "Depended By":  len(n.get("dependents", [])),
            }
            for name, n in nodes.items()
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ── Assembly manifest ─────────────────────────────────────────────────────
    manifest = _load_json("assembled/assembly_manifest.json")
    if manifest:
        st.markdown("---")
        st.subheader("Assembly Manifest")
        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric("Project",      manifest.get("project_name", "?"))
        mc2.metric("Total Files",  manifest.get("total_files", 0))
        mc3.metric("Source Files", len(manifest.get("source_files", [])))
        mc4.metric("Test Files",   len(manifest.get("test_files", [])))

        with st.expander("View generated file tree"):
            all_files = (
                manifest.get("config_files", [])
                + manifest.get("source_files", [])
                + manifest.get("test_files",   [])
            )
            st.code("\n".join(sorted(all_files)), language="text")

        if manifest.get("warnings"):
            st.warning("Assembly warnings:\n" + "\n".join(f"• {w}" for w in manifest["warnings"]))

    # ── Joiner Evaluation ─────────────────────────────────────────────────────
    joiner_eval = _load_json("assembled/joiner_eval.json")
    if joiner_eval:
        st.markdown("---")
        st.subheader("Joiner Evaluation")
        st.metric("Overall Score", f"{joiner_eval.get('overall_score', 0)} / 100")
        t1, t2, t3, t4 = st.tabs(["pom.xml", "Dockerfile", "application.yml", "Manifest"])
        with t1:
            c = joiner_eval.get("pom_xml", {})
            st.metric("Score", f"{c.get('score', 0)} / 100")
            st.markdown(f"**Spring Boot version:** `{c.get('spring_boot_version', 'N/A')}`")
            st.markdown(f"**Group ID:** `{c.get('group_id', 'N/A')}`  "
                        f"**Artifact ID:** `{c.get('artifact_id', 'N/A')}`")
            st.markdown(f"**Dependencies declared:** {c.get('dependency_count', 0)}")
            if c.get("issues"):
                for iss in c["issues"]:
                    st.warning(iss)
            else:
                st.success("pom.xml is well-formed")
        with t2:
            c = joiner_eval.get("dockerfile", {})
            st.metric("Score", f"{c.get('score', 0)} / 100")
            st.markdown(f"**Build stages:** {c.get('stages', 0)}")
            if c.get("issues"):
                for iss in c["issues"]:
                    st.warning(iss)
            else:
                st.success("Multi-stage Dockerfile generated correctly")
        with t3:
            c = joiner_eval.get("app_yml", {})
            st.metric("Score", f"{c.get('score', 0)} / 100")
            if c.get("issues"):
                for iss in c["issues"]:
                    st.warning(iss)
            else:
                st.success("application.yml has required configuration")
        with t4:
            c = joiner_eval.get("manifest", {})
            st.metric("Score", f"{c.get('score', 0)} / 100",
                      help=f"{c.get('modules_found', 0)} / {c.get('total_files', 0)} modules in assembly")
            missing = c.get("modules_missing", [])
            if missing:
                st.warning(f"Modules not found in assembly: "
                           f"{', '.join(f'`{m}`' for m in missing)}")
            else:
                st.success("All converted modules present in the assembled project")


# ── Page: Build Report ───────────────────────────────────────────────────────

elif page == "🏗️ Build Report":
    st.title("🏗️ Build Verification Report")

    data = _load_json("build/build_report.json")
    if not data:
        st.warning("No build report found. Run the pipeline first.")
        st.stop()

    status  = data.get("status",  "unknown")
    method  = data.get("method",  "?")
    n_errs  = data.get("error_count", 0)
    retries = data.get("build_retries", 0)
    ts      = data.get("timestamp", "")

    # ── Status banner ─────────────────────────────────────────────────────────
    STATUS_CFG = {
        "success": ("green",  "✅ COMPILATION PASSED"),
        "failed":  ("red",    "❌ COMPILATION FAILED"),
        "skipped": ("orange", "⏭️ SKIPPED (no assembled project)"),
        "unknown": ("blue",   "❓ UNKNOWN (no build tools — LLM analysis used)"),
    }
    colour, label = STATUS_CFG.get(status, ("grey", f"? {status}"))
    if colour == "green":
        st.success(f"### {label}")
    elif colour == "red":
        st.error(f"### {label}")
    else:
        st.warning(f"### {label}")

    # ── KPI row ───────────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Status",         status.upper())
    k2.metric("Tool Used",      method)
    k3.metric("Compile Errors", n_errs,
              delta="✅ Clean" if n_errs == 0 else f"⚠ {n_errs} errors",
              delta_color="normal" if n_errs == 0 else "inverse")
    k4.metric("Fix Retries Used", retries)
    st.caption(f"Timestamp: {ts}  |  Project: `{data.get('project_root', 'N/A')}`")

    st.markdown("---")

    # ── Error list ────────────────────────────────────────────────────────────
    errors = data.get("errors", [])
    failing = data.get("failing_classes", [])

    if errors:
        st.subheader(f"Compilation Errors ({len(errors)})")

        # Summary bar per failing class
        if failing:
            class_counts = {}
            for e in errors:
                c = e.get("class", "unknown")
                class_counts[c] = class_counts.get(c, 0) + 1
            fig = px.bar(
                x=list(class_counts.values()),
                y=list(class_counts.keys()),
                orientation="h",
                labels={"x": "Errors", "y": "Class"},
                color_discrete_sequence=["#e74c3c"],
                text=list(class_counts.values()),
            )
            fig.update_layout(height=max(200, 50 * len(class_counts)),
                              margin=dict(t=10, b=10), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        # Per-class expandable error detail
        from itertools import groupby
        sorted_errors = sorted(errors, key=lambda e: e.get("class", ""))
        for cls, grp in groupby(sorted_errors, key=lambda e: e.get("class", "unknown")):
            cls_errors = list(grp)
            with st.expander(f"🔴 {cls}  ({len(cls_errors)} error(s))", expanded=len(cls_errors) <= 3):
                rows = [{"Line": e.get("line","?"), "Message": e.get("message","")} for e in cls_errors]
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    elif status == "success":
        st.success("No compilation errors — the project compiled cleanly.")

    # ── What was checked ──────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("What was verified")
    tool_info = {
        "maven":              "Full Maven compilation — resolves all dependencies via pom.xml",
        "javac":              "Direct `javac` compilation — catches syntax and symbol errors (no dependency resolution)",
        "llm-static-analysis":"LLM code review — identifies likely compilation issues without executing a build",
        "unknown":            "Build tool not recorded",
    }
    # strip the parenthetical from method name for lookup
    tool_key = method.split("(")[0].strip() if "(" in method else method
    st.info(tool_info.get(tool_key, f"Tool: {method}"))

    # ── Raw build output ──────────────────────────────────────────────────────
    raw = data.get("raw_output", "")
    if raw:
        with st.expander("Raw build output"):
            st.code(raw, language="text")

    # ── Manual review checklist ───────────────────────────────────────────────
    if errors or status != "success":
        st.markdown("---")
        st.subheader("Manual Review Checklist")
        st.markdown("""
Items to inspect before declaring the converted project production-ready:

- [ ] All `import` statements resolved (especially `jakarta.*` vs `javax.*`)
- [ ] `@Entity` classes have an `@Id` field with the correct type
- [ ] Repository interfaces extend the correct Spring Data base interface
- [ ] Controller `@RequestMapping` paths don't clash
- [ ] `application.yml` datasource URL matches your target database
- [ ] No hardcoded credentials or secrets in generated code
        """)


# ── Page: Observability ───────────────────────────────────────────────────────

elif page == "📡 Observability":
    st.title("📡 Pipeline Observability")

    metrics_data = _load_json("observability/metrics.json")
    traces_data  = _load_json("observability/traces.json")

    if not metrics_data and not traces_data:
        st.warning("No observability data found. Run the pipeline first.")
        st.stop()

    if metrics_data:
        pipeline = metrics_data.get("pipeline", {})
        agents   = metrics_data.get("agents", {})

        # ── Pipeline KPIs ─────────────────────────────────────────────────────
        st.subheader("Pipeline Summary")
        p1, p2, p3, p4 = st.columns(4)
        total_ms = pipeline.get("total_duration_ms", 0)
        p1.metric("Total Time",   f"{total_ms / 1000:.1f}s")
        p2.metric("LLM Calls",    pipeline.get("total_llm_calls", 0))
        p3.metric("Total Tokens", f"{pipeline.get('total_tokens', 0):,}")
        p4.metric("Errors",       pipeline.get("total_errors", 0),
                  delta_color="inverse" if pipeline.get("total_errors", 0) > 0 else "off")

        st.markdown("---")

        # ── Per-agent metrics table ───────────────────────────────────────────
        st.subheader("Per-Agent Metrics")
        if agents:
            rows = []
            for name, m in agents.items():
                rows.append({
                    "Agent":        name,
                    "Status":       m.get("status", "?"),
                    "Duration (ms)": m.get("duration_ms", 0),
                    "LLM Calls":    m.get("llm_calls", 0),
                    "Tokens In":    m.get("tokens_in", 0),
                    "Tokens Out":   m.get("tokens_out", 0),
                    "Total Tokens": m.get("total_tokens", 0),
                    "Items":        m.get("items_processed", 0),
                    "Errors":       m.get("errors", 0),
                })
            df = pd.DataFrame(rows)

            def _highlight(row):
                colour = {"success": "#d5f5e3", "partial": "#fef9e7",
                          "failed": "#fadbd8", "running": "#d6eaf8"}.get(row["Status"], "")
                return [f"background-color: {colour}"] * len(row)

            st.dataframe(
                df.style.apply(_highlight, axis=1),
                use_container_width=True,
                hide_index=True,
            )

        st.markdown("---")

        # ── Charts row ────────────────────────────────────────────────────────
        ch1, ch2 = st.columns(2)

        with ch1:
            st.subheader("Token Usage by Agent")
            if agents:
                fig = px.bar(
                    x=list(agents.keys()),
                    y=[m.get("total_tokens", 0) for m in agents.values()],
                    color=list(agents.keys()),
                    labels={"x": "Agent", "y": "Tokens"},
                    color_discrete_sequence=px.colors.qualitative.Pastel,
                )
                fig.update_layout(showlegend=False, height=300, margin=dict(t=10, b=10))
                st.plotly_chart(fig, use_container_width=True)

        with ch2:
            st.subheader("Time Spent by Agent")
            if agents:
                fig = px.pie(
                    values=[m.get("duration_ms", 0) for m in agents.values()],
                    names=list(agents.keys()),
                    color_discrete_sequence=px.colors.qualitative.Set2,
                    hole=0.35,
                )
                fig.update_layout(height=300, margin=dict(t=10, b=10))
                st.plotly_chart(fig, use_container_width=True)

    # ── Execution timeline (Gantt) ────────────────────────────────────────────
    if traces_data:
        st.markdown("---")
        st.subheader("Execution Timeline")
        spans = traces_data.get("spans", [])
        if spans:
            gantt_rows = []
            for s in spans:
                if s.get("start") and s.get("end"):
                    gantt_rows.append({
                        "Agent":  s["agent"],
                        "Start":  s["start"],
                        "Finish": s["end"],
                        "Status": s.get("status", "?"),
                        "ms":     s.get("duration_ms", 0),
                    })
            if gantt_rows:
                df_gantt = pd.DataFrame(gantt_rows)
                fig = px.timeline(
                    df_gantt,
                    x_start="Start",
                    x_end="Finish",
                    y="Agent",
                    color="Status",
                    color_discrete_map={
                        "success": "#2ecc71",
                        "partial": "#f39c12",
                        "failed":  "#e74c3c",
                        "running": "#3498db",
                    },
                    hover_data=["ms"],
                )
                fig.update_yaxes(categoryorder="array",
                                 categoryarray=[r["Agent"] for r in gantt_rows])
                fig.update_layout(height=350, margin=dict(t=20, b=10))
                st.plotly_chart(fig, use_container_width=True)

        # ── Span detail table ─────────────────────────────────────────────────
        with st.expander("Span details"):
            span_rows = [
                {
                    "Span":     s.get("span_id"),
                    "Agent":    s.get("agent"),
                    "Status":   s.get("status"),
                    "ms":       s.get("duration_ms"),
                    "In":       s.get("input_summary",  "")[:80],
                    "Out":      s.get("output_summary", "")[:80],
                }
                for s in spans
            ]
            if span_rows:
                st.dataframe(pd.DataFrame(span_rows), use_container_width=True, hide_index=True)
