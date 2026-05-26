"""
PipelineService — manages conversion jobs with HITL support.

Two-phase execution
───────────────────
Phase 1  run_phase1()   Runs Code Splitter → Documenter → Auditor → Review Gate.
                        The graph pauses at interrupt() inside review_gate_node.
                        Job status becomes "awaiting_review".

Phase 2  resume_job()   Called by POST /approve or /reject.
                        Resumes the graph with Command(resume=decision).
                        Runs Converter → Tester → Joiner → Build Verifier.
                        Job status becomes "complete" or "failed".

A single MemorySaver checkpointer is shared across all jobs; each job is
isolated by its own thread_id (= job_id).
"""

import concurrent.futures
import os
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

import config
from graph.state import WorkflowState
from utils.file_handler import ensure_output_dirs, save_json
from observability import get_metrics, get_tracer, reset_metrics, reset_tracer
from observability.logging_config import setup_pipeline_logging


# ── Shared checkpointer (one per process, thread-safe) ────────────────────────
_CHECKPOINTER = MemorySaver()
_APP      = None
_APP_LOCK = threading.Lock()


def _get_app():
    """Lazy-initialise the compiled graph (singleton)."""
    global _APP
    if _APP is None:
        with _APP_LOCK:
            if _APP is None:
                from graph.workflow import create_workflow
                _APP = create_workflow(checkpointer=_CHECKPOINTER)
    return _APP


# ── Job data model ────────────────────────────────────────────────────────────

@dataclass
class JobRecord:
    job_id:          str
    source_filename: str
    source_path:     str
    output_dir:      str
    status:          str            = "queued"
    created_at:      str            = field(
        default_factory=lambda: datetime.now(tz=timezone.utc).isoformat()
    )
    started_at:      Optional[str]  = None
    completed_at:    Optional[str]  = None
    error:           Optional[str]  = None
    graph_config:    Optional[dict] = None    # {"configurable": {"thread_id": ...}}
    # Result counters
    modules_count:         int             = 0
    converted_count:       int             = 0
    test_suites_count:     int             = 0
    audit_score:           Optional[float] = None
    audit_passed:          Optional[bool]  = None
    total_files_assembled: int             = 0
    build_status:          Optional[str]   = None


# ── Service ───────────────────────────────────────────────────────────────────

class PipelineService:
    _instance: Optional["PipelineService"] = None

    def __init__(self) -> None:
        self._jobs:    Dict[str, JobRecord] = {}
        self._lock     = threading.Lock()
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

    @classmethod
    def get_service(cls) -> "PipelineService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── Job creation ──────────────────────────────────────────────────────────

    def create_job(self, filename: str, content: bytes) -> JobRecord:
        job_id     = str(uuid.uuid4())
        base       = os.environ.get("PIPELINE_OUTPUT_BASE", "output")
        output_dir = f"{base}/{job_id}"

        input_dir = Path(output_dir) / "input"
        input_dir.mkdir(parents=True, exist_ok=True)
        source_path = str(input_dir / filename)
        with open(source_path, "wb") as fh:
            fh.write(content)

        job = JobRecord(
            job_id=job_id,
            source_filename=filename,
            source_path=source_path,
            output_dir=output_dir,
            graph_config={"configurable": {"thread_id": job_id}},
        )
        with self._lock:
            self._jobs[job_id] = job
        return job

    # ── Phase 1 submission (non-blocking) ─────────────────────────────────────

    def submit_job(self, job_id: str) -> None:
        self._executor.submit(self._run_phase1, job_id)

    # ── Phase 2 — resume after human decision ─────────────────────────────────

    def resume_job(self, job_id: str, decision: str) -> bool:
        """Called by the approve/reject API endpoint."""
        with self._lock:
            job = self._jobs.get(job_id)
        if not job or job.status != "awaiting_review":
            return False
        job.status = "running"
        self._executor.submit(self._run_phase2, job_id, decision)
        # Clear the Streamlit run-discovery cache so the sidebar refreshes
        try:
            from dashboard.app import _discover_runs
            _discover_runs.clear()
        except Exception:
            pass
        return True

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_job(self, job_id: str) -> Optional[JobRecord]:
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(self) -> List[JobRecord]:
        with self._lock:
            return sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)

    # ── Internal: Phase 1 ─────────────────────────────────────────────────────

    def _run_phase1(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
        if not job:
            return

        job.status     = "running"
        job.started_at = datetime.now(tz=timezone.utc).isoformat()

        original_dir      = config.OUTPUT_DIR
        config.OUTPUT_DIR = job.output_dir

        try:
            ensure_output_dirs()
            # Also ensure the hitl subdirectory exists
            Path(job.output_dir, "hitl").mkdir(parents=True, exist_ok=True)

            reset_metrics()
            reset_tracer()
            setup_pipeline_logging(log_dir=f"{job.output_dir}/logs")

            with open(job.source_path, "r", encoding="utf-8") as fh:
                source_code = fh.read()

            initial_state: WorkflowState = {
                "source_code":        source_code,
                "source_file_path":   job.source_path,
                "modules":            [],
                "documentation":      None,
                "audit_report":       None,
                "audit_feedback":     "",
                "audit_retries":      0,
                "converted_modules":  [],
                "test_suites":        [],
                "assembly_result":    None,
                "build_report":       None,
                "build_feedback":     "",
                "build_retries":      0,
                "hitl_decision":      "",
                "awaiting_review":    False,
                "metrics_summary":    None,
                "trace_data":         None,
                "errors":             [],
                "current_step":       "start",
                "processing_complete": False,
            }

            app    = _get_app()
            config_ = job.graph_config

            # Invoke — runs until interrupt() inside review_gate_node
            app.invoke(initial_state, config=config_)

            # Detect whether the graph is paused at the interrupt
            graph_state = app.get_state(config_)
            if graph_state.next:          # pending nodes → interrupted
                job.status = "awaiting_review"
                # Update audit counters from the saved state
                saved = graph_state.values
                if ar := saved.get("audit_report"):
                    job.audit_score  = ar.get("score")
                    job.audit_passed = ar.get("passed")
                job.modules_count = len(saved.get("modules", []))
            else:
                # No interrupt — graph ran to END (unusual but handle gracefully)
                self._populate_job_results(job, graph_state.values)
                self._save_observability(job)
                job.status       = "complete"
                job.completed_at = datetime.now(tz=timezone.utc).isoformat()

        except Exception as exc:
            job.status     = "failed"
            job.error      = str(exc)
            job.completed_at = datetime.now(tz=timezone.utc).isoformat()
        finally:
            config.OUTPUT_DIR = original_dir

    # ── Internal: Phase 2 ─────────────────────────────────────────────────────

    def _run_phase2(self, job_id: str, decision: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
        if not job:
            return

        original_dir      = config.OUTPUT_DIR
        config.OUTPUT_DIR = job.output_dir

        try:
            app     = _get_app()
            config_ = job.graph_config

            # Resume with human decision; may pause AGAIN at review_gate if the
            # user rejected and the loop runs Documenter → Auditor → review_gate.
            app.invoke(Command(resume=decision), config=config_)

            graph_state = app.get_state(config_)

            if graph_state.next:
                # Graph paused again (re-entered review_gate after a reject cycle)
                saved = graph_state.values
                job.status = "awaiting_review"
                # Update audit metrics from the new run
                if ar := saved.get("audit_report"):
                    job.audit_score  = ar.get("score")
                    job.audit_passed = ar.get("passed")
                job.modules_count = len(saved.get("modules", []))
            else:
                # Graph ran all the way to END — full conversion complete
                self._populate_job_results(job, graph_state.values)
                self._save_observability(job)
                job.status       = "complete"
                job.completed_at = datetime.now(tz=timezone.utc).isoformat()

        except Exception as exc:
            job.status     = "failed"
            job.error      = str(exc)
            job.completed_at = datetime.now(tz=timezone.utc).isoformat()
        finally:
            config.OUTPUT_DIR = original_dir

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _populate_job_results(self, job: JobRecord, state: dict) -> None:
        job.modules_count     = len(state.get("modules", []))
        job.converted_count   = len(state.get("converted_modules", []))
        job.test_suites_count = len(state.get("test_suites", []))
        if ar := state.get("audit_report"):
            job.audit_score  = ar.get("score")
            job.audit_passed = ar.get("passed")
        if asm := state.get("assembly_result"):
            job.total_files_assembled = asm.get("total_files", 0)
        if br := state.get("build_report"):
            job.build_status = br.get("status")

    def _save_observability(self, job: JobRecord) -> None:
        save_json(get_metrics().to_dict(), "observability/metrics.json")
        save_json(get_tracer().to_dict(),  "observability/traces.json")
        # Write a persistent marker so the dashboard can find this run after restart
        import config as _cfg
        marker = Path(_cfg.OUTPUT_DIR).parent / "current_run.txt"
        try:
            marker.write_text(job.output_dir, encoding="utf-8")
        except Exception:
            pass
