"""
Observability support utilities.

P3.5 FIX (MED-01) — Removed duplicate metrics system.
─────────────────────────────────────────────────────
This module previously maintained a parallel in-process `MetricsCollector`
(a dict-of-lists, memory-only, 1-hour retention, never exposed externally,
never aggregated across worker processes) that duplicated every measurement
already tracked by the proper Prometheus counters and histograms defined in
prom_metrics.py. That duplication wasted memory on every request, doubled
the instrumentation call sites that needed updating for any metric change,
and created real ambiguity for contributors about which system was
authoritative — the answer was always prom_metrics.py, since that's the only
one actually scraped by Prometheus via GET /metrics.

The custom MetricsCollector, Metric dataclass, MetricType enum, and all
record_*() helper functions have been deleted entirely. Nothing in the
codebase called them outside of metrics_middleware itself, so removal is a
clean cut with no follow-on changes required elsewhere.

What remains, and why:
  - request_id_ctx: an async ContextVar read by `RequestIDFilter` in
    logging_config.py so every log line can be correlated with the HTTP
    request that produced it. This is genuinely cross-cutting context-var
    plumbing, not a metric, so it stays here.
  - metrics_middleware: FastAPI HTTP middleware that records request count
    and latency directly into the Prometheus counters/histograms — no
    intermediate in-process store, no duplication.
"""

import time
import logging
from contextvars import ContextVar

from prom_metrics import http_requests_total, http_request_duration_seconds

logger = logging.getLogger(__name__)

# Stores the current request ID for the duration of each async request.
# Set by metrics_middleware; read by RequestIDFilter in logging_config.py.
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="N/A")


async def metrics_middleware(request, call_next):
    """
    FastAPI middleware recording request count/latency directly to Prometheus.
    Usage: app.middleware("http")(metrics_middleware)
    """
    start_time = time.time()

    request_id = request.headers.get("x-request-id", f"req_{id(request)}")
    request.state.request_id = request_id
    request_id_ctx.set(request_id)   # ← inject into logging context

    try:
        response = await call_next(request)
        duration = time.time() - start_time

        http_requests_total.labels(
            method=request.method,
            path=request.url.path,
            status=str(response.status_code),
        ).inc()
        http_request_duration_seconds.labels(
            method=request.method,
            path=request.url.path,
            status=str(response.status_code),
        ).observe(duration)

        return response

    except Exception as exc:
        duration = time.time() - start_time
        http_requests_total.labels(
            method=request.method,
            path=request.url.path,
            status="error",
        ).inc()
        http_request_duration_seconds.labels(
            method=request.method,
            path=request.url.path,
            status="error",
        ).observe(duration)
        logger.error(
            f"[Metrics] Unhandled exception in {request.method} {request.url.path}: {exc}"
        )
        raise
