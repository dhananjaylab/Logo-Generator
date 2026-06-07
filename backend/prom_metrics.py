"""
Prometheus metric definitions shared across worker processes.

The module degrades gracefully if prometheus_client is unavailable so local
development and partial installs do not crash the app.
"""

from __future__ import annotations

try:
    from prometheus_client import Counter, Histogram, Gauge
except Exception:  # pragma: no cover - fallback for environments without the package

    class _NoOpTimer:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class _NoOpMetric:
        def labels(self, *args, **kwargs):
            return self

        def inc(self, *args, **kwargs):
            return None

        def observe(self, *args, **kwargs):
            return None

        def time(self):
            return _NoOpTimer()

        def set(self, value):
            pass

    Counter = Histogram = Gauge = lambda *args, **kwargs: _NoOpMetric()  # type: ignore[assignment]


generation_requests = Counter(
    "logoforge_generation_requests_total",
    "Total logo generation requests",
    ["generator"],
)

generation_latency = Histogram(
    "logoforge_generation_latency_seconds",
    "Logo generation duration",
    ["generator", "status"],
    buckets=[1, 3, 5, 10, 20, 35, 50, 75, 120],
)

job_retries_total = Counter(
    "logoforge_job_retries_total",
    "Total job retry attempts before final failure",
    ["generator", "source"],
)

dlq_jobs_total = Counter(
    "logoforge_dlq_jobs_total",
    "Total jobs written to the dead-letter queue",
    ["queue", "generator"],
)

http_requests_total = Counter(
    "logoforge_http_requests_total",
    "Total HTTP requests handled by the API",
    ["method", "path", "status"],
)

http_request_duration_seconds = Histogram(
    "logoforge_http_request_duration_seconds",
    "HTTP request duration",
    ["method", "path", "status"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1, 3, 5, 10],
)

r2_upload_latency = Histogram(
    "logoforge_r2_upload_latency_seconds",
    "R2 upload duration",
    ["status"],
    buckets=[0.1, 0.5, 1, 2, 5, 10],
)

queue_depth = Gauge(
    "logoforge_queue_depth",
    "Current job queue depth",
    ["queue"],
)

worker_max_jobs = Gauge(
    "logoforge_worker_max_jobs",
    "Configured worker concurrency limit",
    ["queue"],
)

component_ready = Gauge(
    "logoforge_component_ready",
    "Readiness indicator for core platform dependencies",
    ["component"],
)

errors_total = Counter(
    "logoforge_errors_total",
    "Total errors by type and source",
    ["error_type", "source"],
)
