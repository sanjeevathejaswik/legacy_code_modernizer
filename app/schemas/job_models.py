"""Pydantic request/response models for the conversion API."""

from typing import List, Optional
from pydantic import BaseModel


class JobResponse(BaseModel):
    """Lightweight job summary returned on creation and in list endpoints."""
    job_id:          str
    status:          str          # queued | running | complete | failed
    source_filename: str
    created_at:      str
    started_at:      Optional[str] = None
    completed_at:    Optional[str] = None
    message:         str = ""


class JobDetail(JobResponse):
    """Full job details including pipeline results."""
    error:                 Optional[str]   = None
    modules_count:         int             = 0
    converted_count:       int             = 0
    test_suites_count:     int             = 0
    audit_score:           Optional[float] = None
    audit_passed:          Optional[bool]  = None
    total_files_assembled: int             = 0
    build_status:          Optional[str]   = None
    output_dir:            str             = ""
    # HITL fields
    awaiting_review:       bool            = False
    approve_url:           str             = ""
    reject_url:            str             = ""


class JobList(BaseModel):
    total: int
    jobs:  List[JobResponse]


class HealthResponse(BaseModel):
    status:    str
    version:   str
    timestamp: str
    agents:    List[str]
