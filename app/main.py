"""
FastAPI application entry point.

Run:
  uvicorn app.main:app --reload --port 8000

Swagger UI:  http://localhost:8000/docs
ReDoc:       http://localhost:8000/redoc
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routes_conversion import router as conversion_router
from app.api.v1.routes_health     import router as health_router
from app.api.v1.routes_review     import router as review_router


@asynccontextmanager
async def lifespan(application: FastAPI):
    # Startup: ensure base output directory exists
    from utils.file_handler import ensure_output_dirs
    ensure_output_dirs()
    yield
    # Shutdown: nothing to clean up


app = FastAPI(
    title="Legacy Code Conversion API",
    description="""
Multi-agent pipeline that converts monolithic legacy Java code into modern
Spring Boot 3 microservices, orchestrated by **LangGraph** + **Azure OpenAI**.

---

### Quickstart

1. `POST /api/v1/convert` — upload your `.java` file
2. Copy the `job_id` from the response
3. `GET /api/v1/jobs/{job_id}` — poll until `status == "complete"`
4. `GET /api/v1/jobs/{job_id}/results/audit` — view the audit report
5. `GET /api/v1/jobs/{job_id}/download` — download the assembled Maven project as ZIP

---

### Available artifacts

| Name | Content |
|------|---------|
| `modules` | Identified legacy modules |
| `documentation` | Business rules & technical specs |
| `audit` | Documentation quality report (0–100) |
| `conversion` | Converted Spring Boot modules |
| `tests` | Generated JUnit 5 test suites |
| `assembly` | Full Maven project manifest |
| `build` | Compilation verification report |
| `metrics` | Per-agent timing & token usage |
| `traces` | Execution spans (Gantt-ready) |
    """,
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health_router)                         # GET /health
app.include_router(conversion_router, prefix="/api/v1")  # POST /api/v1/convert, GET /api/v1/jobs
app.include_router(review_router,    prefix="/api/v1")   # GET /api/v1/jobs/{id}/...
