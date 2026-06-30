"""
Redis cache wrapper — lazy reconnect + Prometheus metrics.
"""
import json
import time
import threading
import redis
from typing import Any, Optional
from .config import Config
from .logger import log_info, log_warning, log_error

_lock            = threading.Lock()
_redis_client: Optional[redis.Redis] = None
_redis_available: bool = False
_retry_after:    float = 0.0   # timestamp: don't retry before this


def _try_connect() -> bool:
    """Attempt (re)connection to Redis. Backs off 30 s on failure."""
    global _redis_client, _redis_available, _retry_after
    if time.time() < _retry_after:
        return False
    try:
        client = redis.Redis.from_url(
            Config.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        client.ping()
        with _lock:
            _redis_client    = client
            _redis_available = True
            _retry_after     = 0.0
        log_info("CACHE", f"Redis connected: {Config.REDIS_URL}")
        return True
    except Exception as e:
        with _lock:
            _redis_client    = None
            _redis_available = False
            _retry_after     = time.time() + 30   # retry in 30 s
        log_warning("CACHE", f"Redis unavailable ({e}). Retry in 30 s.")
        return False


def _on_connection_error() -> None:
    """Mark Redis as unavailable so next call triggers reconnect."""
    global _redis_available, _retry_after
    with _lock:
        _redis_available = False
        _retry_after     = time.time() + 30


# Initial connection attempt at import time
_try_connect()


def is_available() -> bool:
    return _redis_available


def cache_get(key: str) -> Optional[Any]:
    if not _redis_available:
        _try_connect()
    if not _redis_available or _redis_client is None:
        return None
    try:
        raw = _redis_client.get(key)
        if raw is None:
            try:
                from .middleware.metrics import CACHE_MISSES
                CACHE_MISSES.labels(cache_key=key.split(":")[0]).inc()
            except Exception:
                pass
            return None
        try:
            from .middleware.metrics import CACHE_HITS
            CACHE_HITS.labels(cache_key=key.split(":")[0]).inc()
        except Exception:
            pass
        return json.loads(raw)
    except redis.ConnectionError:
        _on_connection_error()
        return None
    except Exception as e:
        log_error("CACHE_GET", f"key={key}", error=e)
        return None


def cache_set(key: str, value: Any, ttl: int = 300) -> bool:
    if not _redis_available:
        _try_connect()
    if not _redis_available or _redis_client is None:
        return False
    try:
        serialized = json.dumps(value, ensure_ascii=False, default=str)
        _redis_client.setex(key, ttl, serialized)
        return True
    except redis.ConnectionError:
        _on_connection_error()
        return False
    except Exception as e:
        log_error("CACHE_SET", f"key={key}", error=e)
        return False


def cache_delete(key: str) -> bool:
    if not _redis_available or _redis_client is None:
        return False
    try:
        _redis_client.delete(key)
        return True
    except redis.ConnectionError:
        _on_connection_error()
        return False
    except Exception as e:
        log_error("CACHE_DELETE", f"key={key}", error=e)
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
    except redis.ConnectionError:
        _on_connection_error()
        return 0
    except Exception as e:
        log_error("CACHE_DELETE_PATTERN", f"pattern={pattern}", error=e)
        return 0


def blacklist_token(jti: str, ttl_seconds: int) -> bool:
    return cache_set(f"blacklist:{jti}", "revoked", ttl=ttl_seconds)


def is_token_blacklisted(jti: str) -> bool:
    return cache_get(f"blacklist:{jti}") is not None
