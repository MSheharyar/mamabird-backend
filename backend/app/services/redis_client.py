"""
Redis client with in-memory fallback.
If REDIS_URL is not set, demo limits use a local dict (per-process, resets on restart).
"""
import os
import time
import threading
import logging

logger = logging.getLogger(__name__)

_redis = None
_redis_available = False

# --- In-memory fallback ---
_mem_store: dict = {}  # key -> (count, expires_at)
_mem_lock = threading.Lock()


def _get_redis():
    global _redis, _redis_available
    if _redis is not None:
        return _redis if _redis_available else None
    url = os.getenv("REDIS_URL")
    if not url:
        _redis_available = False
        return None
    try:
        import redis as redis_lib
        client = redis_lib.from_url(url, decode_responses=True, socket_connect_timeout=2)
        client.ping()
        _redis = client
        _redis_available = True
        logger.info("Redis connected: %s", url.split("@")[-1])
    except Exception as e:
        logger.warning("Redis unavailable (%s) — using in-memory fallback", e)
        _redis_available = False
        _redis = False  # sentinel: don't retry every request
    return _redis if _redis_available else None


def incr_with_ttl(key: str, ttl_seconds: int) -> int:
    """Atomically increment key, setting TTL on first write. Returns new count."""
    r = _get_redis()
    if r:
        try:
            pipe = r.pipeline()
            pipe.incr(key)
            pipe.expire(key, ttl_seconds, nx=True)
            results = pipe.execute()
            return results[0]
        except Exception as e:
            logger.warning("Redis error on incr (%s) — falling back to memory", e)

    # In-memory fallback
    now = time.monotonic()
    with _mem_lock:
        entry = _mem_store.get(key)
        if entry is None or now >= entry[1]:
            _mem_store[key] = (1, now + ttl_seconds)
            return 1
        count = entry[0] + 1
        _mem_store[key] = (count, entry[1])
        return count


def get_count(key: str) -> int:
    """Return current count for key (0 if expired/missing)."""
    r = _get_redis()
    if r:
        try:
            val = r.get(key)
            return int(val) if val else 0
        except Exception:
            pass

    now = time.monotonic()
    with _mem_lock:
        entry = _mem_store.get(key)
        if entry is None or now >= entry[1]:
            return 0
        return entry[0]
