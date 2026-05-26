"""
Review routes
-------------
GET  /api/v1/jobs/{job_id}                        — full job detail
GET  /api/v1/jobs/{job_id}/results/{artifact}     — return a pipeline artefact as JSON
GET  /api/v1/jobs/{job_id}/download               — stream assembled Maven project as ZIP
POST /api/v1/jobs/{job_id}/approve                — HITL: approve audit, proceed to conversion
POST /api/v1/jobs/{job_id}/reject                 — HITL: reject audit, re-document
"""

import io
import json
import zipfile
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from app.schemas.job_models import JobDetail
from app.services.pipeline import JobRecord, PipelineService

router = APIRouter()

# Maps URL-friendly names to relative paths inside the job's output_dir
_ARTIFACT_MAP = {
    "modules":       "modules/modules.json",
    "documentation": "docs/documentation.json",
    "audit":         "audit/audit_report.json",
    "conversion":    "converted/conversion_summary.json",
    "tests":         "tests/test_suites_summary.json",
    "assembly":      "assembled/assembly_result.json",
    "build":         "build/build_report.json",
    "metrics":       "observability/metrics.json",
    "traces":        "observability/traces.json",
}


def _to_detail(job: JobRecord) -> JobDetail:
    awaiting = job.status == "awaiting_review"
    base_url = f"/api/v1/jobs/{job.job_id}"
    return JobDetail(
        job_id=job.job_id,
        status=job.status,
        source_filename=job.source_filename,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error=job.error,
        modules_count=job.modules_count,
        converted_count=job.converted_count,
        test_suites_count=job.test_suites_count,
        audit_score=job.audit_score,
        audit_passed=job.audit_passed,
        total_files_assembled=job.total_files_assembled,
        build_status=job.build_status,
        output_dir=job.output_dir,
        awaiting_review=awaiting,
        approve_url=f"{base_url}/approve" if awaiting else "",
        reject_url=f"{base_url}/reject"  if awaiting else "",
    )


def _get_or_404(job_id: str) -> JobRecord:
    job = PipelineService.get_service().get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return job


@router.get(
    "/jobs/{job_id}",
    response_model=JobDetail,
    tags=["Review"],
    summary="Get job status and result summary",
)
async def get_job(job_id: str) -> JobDetail:
    return _to_detail(_get_or_404(job_id))


@router.get(
    "/jobs/{job_id}/results/{artifact}",
    tags=["Review"],
    summary="Get a specific pipeline artefact as JSON",
    description=f"Valid artifact names: {', '.join(_ARTIFACT_MAP)}",
)
async def get_artifact(job_id: str, artifact: str):
    if artifact not in _ARTIFACT_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown artifact '{artifact}'. Valid options: {list(_ARTIFACT_MAP)}",
        )

    job = _get_or_404(job_id)

    if job.status not in ("complete", "running"):
        raise HTTPException(
            status_code=409,
            detail=f"Job is '{job.status}' — no results available yet.",
        )

    file_path = Path(job.output_dir) / _ARTIFACT_MAP[artifact]
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Artifact '{artifact}' has not been generated yet.",
        )

    with open(file_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    return JSONResponse(content=data)


@router.get(
    "/jobs/{job_id}/download",
    tags=["Review"],
    summary="Download the assembled Maven project as a ZIP archive",
)
async def download_assembled_project(job_id: str):
    job = _get_or_404(job_id)

    if job.status != "complete":
        raise HTTPException(
            status_code=409,
            detail=f"Job is '{job.status}' — download only available after completion.",
        )

    assembled_dir = Path(job.output_dir) / "assembled"
    if not assembled_dir.exists():
        raise HTTPException(status_code=404, detail="Assembled project directory not found.")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for fp in assembled_dir.rglob("*"):
            if fp.is_file():
                zf.write(fp, fp.relative_to(assembled_dir))
    buf.seek(0)

    short_id = job_id[:8]
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=project-{short_id}.zip"},
    )


# ── HITL: Approve ─────────────────────────────────────────────────────────────

@router.post(
    "/jobs/{job_id}/approve",
    tags=["HITL Review"],
    summary="Approve the audit report — pipeline proceeds to code conversion",
)
async def approve_job(job_id: str):
    job = _get_or_404(job_id)
    if job.status != "awaiting_review":
        raise HTTPException(
            status_code=409,
            detail=f"Job is '{job.status}' — only 'awaiting_review' jobs can be approved.",
        )
    ok = PipelineService.get_service().resume_job(job_id, "approve")
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to resume job.")
    return {"job_id": job_id, "decision": "approve", "message": "Pipeline resumed — converting code."}


# ── HITL: Reject ──────────────────────────────────────────────────────────────

@router.post(
    "/jobs/{job_id}/reject",
    tags=["HITL Review"],
    summary="Reject the audit report — pipeline loops back to re-document",
)
async def reject_job(job_id: str):
    job = _get_or_404(job_id)
    if job.status != "awaiting_review":
        raise HTTPException(
            status_code=409,
            detail=f"Job is '{job.status}' — only 'awaiting_review' jobs can be rejected.",
        )
    ok = PipelineService.get_service().resume_job(job_id, "reject")
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to resume job.")
    return {"job_id": job_id, "decision": "reject", "message": "Pipeline resumed — re-documenting."}
