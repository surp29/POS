"""
Prometheus metrics middleware.

Các metrics được track:
  - http_requests_total        : tổng số request theo method, path, status
  - http_request_duration_seconds : latency histogram theo endpoint
  - http_requests_in_progress  : số request đang xử lý (gauge)
  - db_query_duration_seconds  : thời gian query DB (dùng trong service layer)
  - cache_hits_total / cache_misses_total : hiệu quả cache Redis

Xem tại: GET /metrics
"""
import time
from prometheus_client import (
    Counter, Histogram, Gauge,
    generate_latest, CONTENT_TYPE_LATEST,
    CollectorRegistry, REGISTRY,
)
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Match

# ── Metric definitions ────────────────────────────────────────────────────────

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Tổng số HTTP requests",
    ["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "Thời gian xử lý HTTP request (giây)",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "Số HTTP request đang được xử lý",
    ["method", "endpoint"],
)

CACHE_HITS = Counter(
    "cache_hits_total",
    "Số lần cache HIT",
    ["cache_key"],
)

CACHE_MISSES = Counter(
    "cache_misses_total",
    "Số lần cache MISS",
    ["cache_key"],
)

DB_QUERY_DURATION = Histogram(
    "db_query_duration_seconds",
    "Thời gian thực thi DB query (giây)",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
)

RATE_LIMIT_BLOCKED = Counter(
    "rate_limit_blocked_total",
    "Số request bị block bởi rate limiter",
    ["endpoint"],
)


# ── Helper: normalize path (gộp dynamic segments) ────────────────────────────

def _normalize_path(path: str) -> str:
    """
    Gộp các dynamic segment để tránh cardinality explosion trong Prometheus.
    Ví dụ: /api/products/123 → /api/products/{id}
             /api/orders/456  → /api/orders/{id}
    """
    import re
    # Thay số nguyên trong path bằng {id}
    normalized = re.sub(r"/\d+", "/{id}", path)
    # Giới hạn độ dài để tránh label quá dài
    return normalized[:100]


# ── Middleware ────────────────────────────────────────────────────────────────

class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Tự động track mọi HTTP request vào Prometheus metrics.
    Bỏ qua endpoint /metrics để không tự đếm chính nó.
    """

    async def dispatch(self, request: Request, call_next):
        # Bỏ qua endpoint /metrics và /health để không gây noise
        if request.url.path in ("/metrics", "/health", "/"):
            return await call_next(request)

        method   = request.method
        endpoint = _normalize_path(request.url.path)

        REQUESTS_IN_PROGRESS.labels(method=method, endpoint=endpoint).inc()
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            status   = str(response.status_code)
        except Exception as exc:
            status = "500"
            REQUESTS_IN_PROGRESS.labels(method=method, endpoint=endpoint).dec()
            raise exc

        duration = time.perf_counter() - start_time

        REQUEST_COUNT.labels(
            method=method,
            endpoint=endpoint,
            status_code=status,
        ).inc()

        REQUEST_LATENCY.labels(
            method=method,
            endpoint=endpoint,
        ).observe(duration)

        REQUESTS_IN_PROGRESS.labels(method=method, endpoint=endpoint).dec()

        # Thêm X-Response-Time header để FE/client đọc được latency
        response.headers["X-Response-Time"] = f"{duration:.4f}s"

        return response