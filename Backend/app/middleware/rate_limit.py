"""
Rate limiting middleware dùng Redis (sliding window counter).
"""
import time
import uuid
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from ..cache import _redis_client, _redis_available
from ..logger import log_warning

RATE_LIMIT_RULES: dict[str, tuple[int, int]] = {
    "/api/auth/login":  (5, 60),
    "/api/auth/":       (20, 60),
    "/api/products/":   (60, 60),
    "/api/orders/":     (30, 60),
}
DEFAULT_LIMIT  = 100
DEFAULT_WINDOW = 60


def _get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _get_limit_for_path(path: str) -> tuple[int, int]:
    matching = [
        (prefix, limit, window)
        for prefix, (limit, window) in RATE_LIMIT_RULES.items()
        if path.startswith(prefix)
    ]
    if not matching:
        return DEFAULT_LIMIT, DEFAULT_WINDOW
    matching.sort(key=lambda x: len(x[0]), reverse=True)
    _, limit, window = matching[0]
    return limit, window


def _check_rate_limit(ip: str, path: str) -> tuple[bool, int, int]:
    """
    Sliding window counter dùng Redis Sorted Set.
    Member = uuid4 (unique mỗi request, tránh collision khi gọi nhanh).
    Score  = timestamp (giây) để expire đúng window.
    """
    if not _redis_available or _redis_client is None:
        return True, 0, DEFAULT_LIMIT

    limit, window = _get_limit_for_path(path)
    key = f"rl:{ip}:{path}"

    try:
        now          = int(time.time())
        window_start = now - window
        member       = str(uuid.uuid4())   # unique mỗi lần gọi

        pipe = _redis_client.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)  # xóa request cũ
        pipe.zadd(key, {member: now})                # thêm request mới
        pipe.zcard(key)                               # đếm tổng
        pipe.expire(key, window)                      # auto cleanup

        results      = pipe.execute()
        current_count = results[2]

        return current_count <= limit, current_count, limit

    except Exception as e:
        log_warning("RATE_LIMIT", f"Redis error: {e}")
        return True, 0, DEFAULT_LIMIT


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        ip   = _get_client_ip(request)
        path = request.url.path

        if path in ("/health", "/", "/docs", "/redoc", "/openapi.json") \
                or path.startswith("/static"):
            return await call_next(request)

        is_allowed, current, limit = _check_rate_limit(ip, path)

        if not is_allowed:
            _, window = _get_limit_for_path(path)
            log_warning("RATE_LIMIT",
                f"IP {ip} bị block tại {path} ({current}/{limit} trong {window}s)")
            return JSONResponse(
                status_code=429,
                content={
                    "error":       "Too Many Requests",
                    "message":     f"Quá nhiều yêu cầu. Vui lòng thử lại sau {window} giây.",
                    "limit":       limit,
                    "current":     current,
                    "retry_after": window,
                },
                headers={
                    "Retry-After":        str(window),
                    "X-RateLimit-Limit":  str(limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        _, window = _get_limit_for_path(path)
        remaining = max(0, limit - current)
        response.headers["X-RateLimit-Limit"]     = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"]    = f"{window}s"
        return response