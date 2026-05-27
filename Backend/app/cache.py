"""
Redis cache wrapper với Prometheus metrics tích hợp.
"""
import json
import redis
from typing import Any, Optional
from .config import Config
from .logger import log_info, log_warning, log_error

try:
    _redis_client = redis.Redis.from_url(
        Config.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )
    _redis_client.ping()
    _redis_available = True
    log_info("CACHE", f"Redis kết nối thành công: {Config.REDIS_URL}")
except Exception as e:
    _redis_client = None
    _redis_available = False
    log_warning("CACHE", f"Redis không khả dụng ({e}). Cache bị bỏ qua.")


def is_available() -> bool:
    return _redis_available


def cache_get(key: str) -> Optional[Any]:
    if not _redis_available or _redis_client is None:
        return None
    try:
        raw = _redis_client.get(key)
        if raw is None:
            # Track cache MISS
            try:
                from .middleware.metrics import CACHE_MISSES
                CACHE_MISSES.labels(cache_key=key.split(":")[0]).inc()
            except Exception:
                pass
            return None
        # Track cache HIT
        try:
            from .middleware.metrics import CACHE_HITS
            CACHE_HITS.labels(cache_key=key.split(":")[0]).inc()
        except Exception:
            pass
        return json.loads(raw)
    except Exception as e:
        log_error("CACHE_GET", f"Lỗi đọc cache key={key}", error=e)
        return None


def cache_set(key: str, value: Any, ttl: int = 300) -> bool:
    if not _redis_available or _redis_client is None:
        return False
    try:
        serialized = json.dumps(value, ensure_ascii=False, default=str)
        _redis_client.setex(key, ttl, serialized)
        return True
    except Exception as e:
        log_error("CACHE_SET", f"Lỗi ghi cache key={key}", error=e)
        return False


def cache_delete(key: str) -> bool:
    if not _redis_available or _redis_client is None:
        return False
    try:
        _redis_client.delete(key)
        return True
    except Exception as e:
        log_error("CACHE_DELETE", f"Lỗi xóa cache key={key}", error=e)
        return False


def cache_delete_pattern(pattern: str) -> int:
    if not _redis_available or _redis_client is None:
        return 0
    try:
        deleted = 0
        cursor  = 0
        while True:
            cursor, keys = _redis_client.scan(cursor, match=pattern, count=100)
            if keys:
                _redis_client.delete(*keys)
                deleted += len(keys)
            if cursor == 0:
                break
        return deleted
    except Exception as e:
        log_error("CACHE_DELETE_PATTERN", f"Lỗi xóa pattern={pattern}", error=e)
        return 0


def blacklist_token(jti: str, ttl_seconds: int) -> bool:
    return cache_set(f"blacklist:{jti}", "revoked", ttl=ttl_seconds)


def is_token_blacklisted(jti: str) -> bool:
    return cache_get(f"blacklist:{jti}") is not None