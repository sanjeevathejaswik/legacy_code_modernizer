from datetime import datetime, timezone
from fastapi import APIRouter
from app.schemas.job_models import HealthResponse

router = APIRouter()

_AGENTS = [
    "code_splitter", "documenter", "auditor", "review_gate",
    "converter", "tester", "joiner", "build_verifier",
]


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version="1.0.0",
        timestamp=datetime.now(tz=timezone.utc).isoformat(),
        agents=_AGENTS,
    )
