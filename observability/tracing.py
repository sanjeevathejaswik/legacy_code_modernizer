"""
Lightweight pipeline tracer — one span per agent execution.

• instrument_node(name, fn) wraps a LangGraph node with automatic span bookkeeping.
• Singleton access via get_tracer() / reset_tracer().
• to_dict() produces a Gantt-ready payload consumed by the dashboard.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from observability.metrics import get_metrics

_TRACER: Optional["PipelineTracer"] = None


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class TraceSpan:
    span_id:        str
    agent_name:     str
    operation:      str
    start_wall:     str                   # ISO-8601
    end_wall:       Optional[str]  = None
    start_mono:     float          = field(default_factory=time.monotonic)
    duration_ms:    Optional[float]= None
    status:         str            = "running"
    input_summary:  str            = ""
    output_summary: str            = ""
    metadata:       Dict[str, Any] = field(default_factory=dict)


# ── Tracer ────────────────────────────────────────────────────────────────────

class PipelineTracer:
    def __init__(self) -> None:
        self._spans:  List[TraceSpan]       = []
        self._active: Dict[str, TraceSpan]  = {}
        self._seq:    int                   = 0

    def start_span(
        self,
        agent_name:    str,
        operation:     str      = "node_execution",
        input_summary: str      = "",
        **metadata: Any,
    ) -> str:
        self._seq += 1
        span_id = f"{agent_name}-{self._seq:04d}"
        span = TraceSpan(
            span_id=span_id,
            agent_name=agent_name,
            operation=operation,
            start_wall=datetime.now(tz=timezone.utc).isoformat(),
            input_summary=input_summary[:300],
            metadata=metadata,
        )
        self._active[span_id] = span
        self._spans.append(span)
        return span_id

    def end_span(
        self,
        span_id:        str,
        status:         str  = "success",
        output_summary: str  = "",
        **metadata: Any,
    ) -> None:
        span = self._active.pop(span_id, None)
        if span is None:
            return
        now_mono = time.monotonic()
        span.end_wall      = datetime.now(tz=timezone.utc).isoformat()
        span.duration_ms   = round((now_mono - span.start_mono) * 1_000, 1)
        span.status        = status
        span.output_summary = output_summary[:300]
        span.metadata.update(metadata)

    def to_dict(self) -> Dict:
        return {
            "trace_id":    f"pipeline-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "total_spans": len(self._spans),
            "spans": [
                {
                    "span_id":        s.span_id,
                    "agent":          s.agent_name,
                    "operation":      s.operation,
                    "start":          s.start_wall,
                    "end":            s.end_wall,
                    "duration_ms":    s.duration_ms,
                    "status":         s.status,
                    "input_summary":  s.input_summary,
                    "output_summary": s.output_summary,
                    "meta":           s.metadata,
                }
                for s in self._spans
            ],
        }


# ── Singleton accessors ───────────────────────────────────────────────────────

def get_tracer() -> PipelineTracer:
    global _TRACER
    if _TRACER is None:
        _TRACER = PipelineTracer()
    return _TRACER


def reset_tracer() -> PipelineTracer:
    global _TRACER
    _TRACER = PipelineTracer()
    return _TRACER


# ── Node wrapper ──────────────────────────────────────────────────────────────

def instrument_node(agent_name: str, node_fn: Callable) -> Callable:
    """
    Wrap a LangGraph node function with automatic span + metrics bookkeeping.
    The wrapped function is transparent to LangGraph — same signature.
    """
    def wrapper(state: Dict) -> Dict:
        tracer  = get_tracer()
        metrics = get_metrics()

        # Summarise input for the trace
        n_modules = len(state.get("modules", []))
        n_conv    = len(state.get("converted_modules", []))
        in_summary = (
            f"modules={n_modules} converted={n_conv} "
            f"retries={state.get('audit_retries', 0)}"
        )

        span_id = tracer.start_span(agent_name, input_summary=in_summary)
        metrics.start_agent(agent_name)

        try:
            result: Dict = node_fn(state)
        except Exception as exc:
            metrics.end_agent(agent_name, status="failed", errors=1)
            tracer.end_span(span_id, status="failed", error=str(exc)[:200])
            raise

        # Determine outcome
        new_errors = result.get("errors", [])
        status = "partial" if new_errors else "success"

        # Count items produced by this agent
        items = max(
            len(result.get("modules",           [])),
            len(result.get("converted_modules", [])),
            len(result.get("test_suites",       [])),
        )

        metrics.end_agent(agent_name, status=status,
                          items_processed=items, errors=len(new_errors))

        out_summary = (
            f"step={result.get('current_step', '?')} "
            f"items={items} errors={len(new_errors)}"
        )
        tracer.end_span(span_id, status=status, output_summary=out_summary)
        return result

    wrapper.__name__ = node_fn.__name__
    return wrapper
