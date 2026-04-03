"""
Observability and metrics collection for Logo Generator.
Tracks queue depth, generation latency, R2 uploads, and error rates.
"""

import time
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Types of metrics we track"""
    COUNTER = "counter"      # Increment only
    GAUGE = "gauge"          # Point-in-time value
    HISTOGRAM = "histogram"  # Distribution
    TIMER = "timer"          # Duration


@dataclass
class Metric:
    """Single metric data point"""
    name: str
    value: float
    type: MetricType
    timestamp: datetime = field(default_factory=datetime.utcnow)
    labels: Dict[str, str] = field(default_factory=dict)
    
    def __str__(self):
        label_str = ",".join(f"{k}={v}" for k, v in self.labels.items())
        return f"{self.name}{{{label_str}}} = {self.value} @ {self.timestamp.isoformat()}"


class MetricsCollector:
    """Centralized metrics collection"""
    
    def __init__(self):
        self.metrics: Dict[str, list] = defaultdict(list)
        self.timers: Dict[str, float] = {}
        self.retention_seconds = 3600  # Keep 1 hour of metrics
        
    def start_timer(self, name: str) -> str:
        """Start a named timer, return timer_id"""
        timer_id = f"{name}_{id(self)}"
        self.timers[timer_id] = time.time()
        return timer_id
    
    def end_timer(self, timer_id: str) -> Optional[float]:
        """End a timer, return elapsed seconds"""
        if timer_id not in self.timers:
            logger.warning(f"Timer {timer_id} not found")
            return None
        elapsed = time.time() - self.timers.pop(timer_id)
        return elapsed
    
    def record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        labels: Optional[Dict[str, str]] = None
    ):
        """Record a metric"""
        metric = Metric(name, value, metric_type, labels=labels or {})
        self.metrics[name].append(metric)
        self._cleanup_old_metrics(name)
        return metric
    
    def _cleanup_old_metrics(self, name: str):
        """Remove metrics older than retention period"""
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.retention_seconds)
        self.metrics[name] = [
            m for m in self.metrics[name]
            if m.timestamp > cutoff
        ]
    
    def get_metric_summary(self, name: str) -> Dict[str, float]:
        """Get summary statistics for a metric"""
        if name not in self.metrics or not self.metrics[name]:
            return {}
        
        values = [m.value for m in self.metrics[name]]
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "latest": values[-1] if values else 0,
        }
    
    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format"""
        lines = []
        for name, metrics in self.metrics.items():
            if not metrics:
                continue
            
            latest = metrics[-1]
            label_str = ",".join(f'{k}="{v}"' for k, v in latest.labels.items())
            if label_str:
                lines.append(f'{name}{{{label_str}}} {latest.value}')
            else:
                lines.append(f'{name} {latest.value}')
        
        return "\n".join(lines)


# Global metrics collector instance
metrics = MetricsCollector()


# ─────────────────────────────────────────────────────────────────────────────
# Built-in Metrics
# ─────────────────────────────────────────────────────────────────────────────

def record_generation_start(generator: str, user_id: str):
    """Record generation request start"""
    metrics.record_metric(
        "generation_requests_total",
        1,
        MetricType.COUNTER,
        labels={"generator": generator, "user": user_id}
    )


def record_generation_latency(duration_seconds: float, generator: str, status: str):
    """Record generation latency"""
    metrics.record_metric(
        "generation_latency_seconds",
        duration_seconds,
        MetricType.HISTOGRAM,
        labels={"generator": generator, "status": status}
    )


def record_r2_upload(duration_seconds: float, success: bool, size_mb: float):
    """Record R2 upload metrics"""
    metrics.record_metric(
        "r2_upload_latency_seconds",
        duration_seconds,
        MetricType.TIMER,
        labels={"status": "success" if success else "failed"}
    )
    metrics.record_metric(
        "r2_upload_size_mb",
        size_mb,
        MetricType.GAUGE,
        labels={"status": "success" if success else "failed"}
    )


def record_queue_depth(queue_name: str, depth: int):
    """Record current queue depth"""
    metrics.record_metric(
        "queue_depth",
        depth,
        MetricType.GAUGE,
        labels={"queue": queue_name}
    )


def record_error(error_type: str, source: str):
    """Record error occurrence"""
    metrics.record_metric(
        "errors_total",
        1,
        MetricType.COUNTER,
        labels={"type": error_type, "source": source}
    )


def record_cache_hit(cache_name: str, hit: bool):
    """Record cache hit/miss"""
    metrics.record_metric(
        "cache_hits_total" if hit else "cache_misses_total",
        1,
        MetricType.COUNTER,
        labels={"cache": cache_name}
    )


# ─────────────────────────────────────────────────────────────────────────────
# Async Metrics Middleware (for FastAPI)
# ─────────────────────────────────────────────────────────────────────────────

async def metrics_middleware(request, call_next):
    """
    FastAPI middleware to record request metrics.
    Usage: app.middleware("http")(metrics_middleware)
    """
    start_time = time.time()
    
    # Get or create request ID
    request_id = request.headers.get("x-request-id", f"req_{id(request)}")
    request.state.request_id = request_id
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        
        # Record HTTP metrics
        metrics.record_metric(
            "http_requests_total",
            1,
            MetricType.COUNTER,
            labels={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code
            }
        )
        
        metrics.record_metric(
            "http_request_duration_seconds",
            duration,
            MetricType.TIMER,
            labels={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code
            }
        )
        
        return response
    except Exception as e:
        duration = time.time() - start_time
        metrics.record_metric(
            "http_requests_total",
            1,
            MetricType.COUNTER,
            labels={
                "method": request.method,
                "path": request.url.path,
                "status": "error"
            }
        )
        record_error(type(e).__name__, request.url.path)
        raise
