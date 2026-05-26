"""
Per-agent and pipeline-level metrics collection.

Singleton access via get_metrics() / reset_metrics().
Call reset_metrics() at the start of each pipeline run.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

_COLLECTOR: Optional["MetricsCollector"] = None


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class AgentMetrics:
    agent_name:      str
    start_time:      float          = field(default_factory=time.monotonic)
    end_time:        Optional[float]= None
    llm_calls:       int            = 0
    tokens_in:       int            = 0   # estimated from char count / 4
    tokens_out:      int            = 0
    items_processed: int            = 0
    errors:          int            = 0
    status:          str            = "running"   # running|success|partial|failed

    @property
    def duration_ms(self) -> Optional[float]:
        if self.end_time is not None:
            return (self.end_time - self.start_time) * 1_000
        return None

    @property
    def total_tokens(self) -> int:
        return self.tokens_in + self.tokens_out


# ── Collector ─────────────────────────────────────────────────────────────────

class MetricsCollector:
    def __init__(self) -> None:
        self._agents:         Dict[str, AgentMetrics] = {}
        self._pipeline_start: float = time.monotonic()
        self._start_wall:     str   = datetime.now(tz=timezone.utc).isoformat()

    # ── Agent lifecycle ───────────────────────────────────────────────────────

    def start_agent(self, agent_name: str) -> None:
        self._agents[agent_name] = AgentMetrics(agent_name=agent_name)

    def end_agent(
        self,
        agent_name:      str,
        status:          str = "success",
        items_processed: int = 0,
        errors:          int = 0,
    ) -> None:
        m = self._agents.get(agent_name)
        if m:
            m.end_time        = time.monotonic()
            m.status          = status
            m.items_processed = items_processed
            m.errors          = errors

    # ── LLM call recording ────────────────────────────────────────────────────

    def record_llm_call(
        self,
        agent_name:   str,
        input_chars:  int,
        output_chars: int,
    ) -> None:
        m = self._agents.get(agent_name)
        if m:
            m.llm_calls  += 1
            m.tokens_in  += max(1, input_chars  // 4)
            m.tokens_out += max(1, output_chars // 4)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict:
        pipeline_ms    = (time.monotonic() - self._pipeline_start) * 1_000
        total_tokens   = sum(m.total_tokens for m in self._agents.values())
        total_llm      = sum(m.llm_calls    for m in self._agents.values())
        total_errors   = sum(m.errors       for m in self._agents.values())

        return {
            "pipeline": {
                "started_at":       self._start_wall,
                "total_duration_ms": round(pipeline_ms, 1),
                "total_llm_calls":   total_llm,
                "total_tokens":      total_tokens,
                "total_errors":      total_errors,
                "agents_run":        len(self._agents),
            },
            "agents": {
                name: {
                    "status":          m.status,
                    "duration_ms":     round(m.duration_ms or 0, 1),
                    "llm_calls":       m.llm_calls,
                    "tokens_in":       m.tokens_in,
                    "tokens_out":      m.tokens_out,
                    "total_tokens":    m.total_tokens,
                    "items_processed": m.items_processed,
                    "errors":          m.errors,
                }
                for name, m in self._agents.items()
            },
        }


# ── Singleton accessors ───────────────────────────────────────────────────────

def get_metrics() -> MetricsCollector:
    global _COLLECTOR
    if _COLLECTOR is None:
        _COLLECTOR = MetricsCollector()
    return _COLLECTOR


def reset_metrics() -> MetricsCollector:
    global _COLLECTOR
    _COLLECTOR = MetricsCollector()
    return _COLLECTOR
