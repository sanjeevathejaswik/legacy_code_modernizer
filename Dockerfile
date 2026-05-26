# ── Stage 1: dependency builder ───────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim

# Install Maven + JDK for build verification (pipeline falls back to javac or
# LLM static analysis when these are absent — they are optional)
RUN apt-get update && apt-get install -y --no-install-recommends \
        default-jdk-headless \
        maven \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY . .

# Pre-create the output directory so bind-mounts work cleanly
RUN mkdir -p output

EXPOSE 8000 8501

# Default: run the FastAPI server
# Override with `command:` in docker-compose to run the dashboard instead
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
