"""
Conversion routes
-----------------
POST /api/v1/convert   — upload a .java file, receive a job_id immediately
GET  /api/v1/jobs      — list all jobs with status
"""

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from app.schemas.job_models import JobList, JobResponse
from app.services.pipeline import JobRecord, PipelineService

router = APIRouter()


def _to_response(job: JobRecord) -> JobResponse:
    msg = (
        f"Job queued. Poll /api/v1/jobs/{job.job_id} for status."
        if job.status == "queued"
        else ""
    )
    return JobResponse(
        job_id=job.job_id,
        status=job.status,
        source_filename=job.source_filename,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        message=msg,
    )


@router.post(
    "/convert",
    status_code=202,
    response_model=JobResponse,
    tags=["Conversion"],
    summary="Start a conversion job",
    description="Upload a .java legacy source file. Returns a job_id immediately; the pipeline runs in the background.",
)
async def start_conversion(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Legacy Java source file (.java)"),
) -> JobResponse:
    if not (file.filename or "").endswith(".java"):
        raise HTTPException(status_code=400, detail="Only .java files are accepted.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    service = PipelineService.get_service()
    job     = service.create_job(file.filename, content)
    background_tasks.add_task(service.submit_job, job.job_id)

    return _to_response(job)


@router.get(
    "/jobs",
    response_model=JobList,
    tags=["Conversion"],
    summary="List all conversion jobs",
)
async def list_jobs() -> JobList:
    service = PipelineService.get_service()
    jobs    = service.list_jobs()
    return JobList(total=len(jobs), jobs=[_to_response(j) for j in jobs])
