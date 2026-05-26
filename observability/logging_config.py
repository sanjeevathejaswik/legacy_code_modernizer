"""
Structured pipeline logger.

• Console  — human-readable via Rich (INFO+)
• File     — newline-delimited JSON (DEBUG+), written to output/logs/
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import config

_LOGGER: Optional[logging.Logger] = None


# ── JSON formatter ────────────────────────────────────────────────────────────

class _JSONFormatter(logging.Formatter):
    """Emit one JSON object per log line (JSONL)."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts":      datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level":   record.levelname,
            "logger":  record.name,
            "msg":     record.getMessage(),
        }
        # Optional context injected via LoggerAdapter extras
        for key in ("agent", "module_name", "span_id"):
            val = record.__dict__.get(key)
            if val is not None:
                payload[key] = val
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


# ── Setup ─────────────────────────────────────────────────────────────────────

def setup_pipeline_logging(log_dir: str = "") -> logging.Logger:
    global _LOGGER
    log_dir = log_dir or f"{config.OUTPUT_DIR}/logs"
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("pipeline")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    # ── Remove previous file handler (each job gets its own log file) ─────────
    for h in logger.handlers[:]:
        if isinstance(h, logging.FileHandler):
            h.close()
            logger.removeHandler(h)

    # ── File handler — structured JSONL (always fresh per job) ───────────────
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fh = logging.FileHandler(
        f"{log_dir}/pipeline_{stamp}.jsonl", encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(_JSONFormatter())
    logger.addHandler(fh)

    # ── Console handler — added only once per process ─────────────────────────
    if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
               for h in logger.handlers):
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.WARNING)
        ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        logger.addHandler(ch)

    _LOGGER = logger
    return logger


def get_logger() -> logging.Logger:
    global _LOGGER
    if _LOGGER is None:
        _LOGGER = setup_pipeline_logging()
    return _LOGGER
