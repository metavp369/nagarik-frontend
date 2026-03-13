# Redis Cache Service for NISCHINT
# Production-grade cache layer with connection pooling, namespaced keys, and fallback.
#
# Key namespace: nischint:<domain>:<key>
#   nischint:heatmap:live          — pre-computed heatmap (TTL 600s)
#   nischint:heatmap:timeline      — last 12 snapshots (TTL 600s)
#   nischint:heatmap:delta         — latest risk changes (TTL 600s)
#   nischint:heatmap:meta          — cache metadata (TTL 600s)
#   nischint:safety_score:grid     — grid scores for percentile ranking (TTL 600s)
#   nischint:sessions:active       — active guardian sessions (TTL 120s)

import json
import logging
from datetime import datetime, timezone

import redis

logger = logging.getLogger(__name__)

_pool = None
_client = None
_available = False

PREFIX = "nischint"


def _get_redis_url() -> str:
    from app.core.config import settings
    return settings.redis_url


def _get_client():
    """Lazy-initialize Redis connection pool and client."""
    global _pool, _client, _available
    if _client is not None:
        return _client
    url = _get_redis_url()
    if not url:
        logger.warning("REDIS_URL not set — Redis cache disabled")
        return None
    try:
        _pool = redis.ConnectionPool.from_url(
            url,
            max_connections=50,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
        _client = redis.Redis(connection_pool=_pool)
        _client.ping()
        _available = True
        logger.info(f"Redis connected: {url}")
        return _client
    except Exception as e:
        logger.warning(f"Redis connection failed: {e} — running without cache")
        _available = False
        _client = None
        return None


def is_available() -> bool:
    """Check if Redis is connected and responsive."""
    c = _get_client()
    if not c:
        return False
    try:
        c.ping()
        return True
    except Exception:
        return False


# ── JSON Helpers ──

def _key(namespace: str, key: str) -> str:
    return f"{PREFIX}:{namespace}:{key}"


def set_json(namespace: str, key: str, data, ttl: int | None = None):
    """Store JSON-serializable data in Redis with optional TTL (seconds)."""
    c = _get_client()
    if not c:
        return False
    try:
        full_key = _key(namespace, key)
        c.set(full_key, json.dumps(data, default=str))
        if ttl:
            c.expire(full_key, ttl)
        return True
    except Exception as e:
        logger.warning(f"Redis SET failed [{namespace}:{key}]: {e}")
        return False


def get_json(namespace: str, key: str):
    """Retrieve and parse JSON data from Redis. Returns None on miss or failure."""
    c = _get_client()
    if not c:
        return None
    try:
        raw = c.get(_key(namespace, key))
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as e:
        logger.warning(f"Redis GET failed [{namespace}:{key}]: {e}")
        return None


def delete_key(namespace: str, key: str) -> bool:
    """Delete a specific key."""
    c = _get_client()
    if not c:
        return False
    try:
        c.delete(_key(namespace, key))
        return True
    except Exception:
        return False


def get_info() -> dict:
    """Return Redis connection info for health checks."""
    c = _get_client()
    if not c:
        return {"cache": "redis", "status": "disconnected", "url": _get_redis_url() or "not configured"}
    try:
        c.ping()
        info = c.info("memory")
        return {
            "cache": "redis",
            "status": "connected",
            "used_memory_human": info.get("used_memory_human", "unknown"),
            "connected_clients": c.info("clients").get("connected_clients", 0),
            "keys": c.dbsize(),
        }
    except Exception as e:
        return {"cache": "redis", "status": "error", "error": str(e)}


# ── Pre-defined Cache Operations ──

# Heatmap TTL: 10 minutes (scheduler runs every 5 min, so always fresh)
HEATMAP_TTL = 600
# Sessions TTL: 2 minutes (frequently updated)
SESSION_TTL = 120
# Safety score grid TTL: 10 minutes (matches heatmap cycle)
SCORE_GRID_TTL = 600


def cache_heatmap_live(data: dict) -> bool:
    return set_json("heatmap", "live", data, ttl=HEATMAP_TTL)


def get_heatmap_live() -> dict | None:
    return get_json("heatmap", "live")


def cache_heatmap_timeline(data: list) -> bool:
    return set_json("heatmap", "timeline", data, ttl=HEATMAP_TTL)


def get_heatmap_timeline() -> list | None:
    return get_json("heatmap", "timeline")


def cache_heatmap_delta(data: dict) -> bool:
    return set_json("heatmap", "delta", data, ttl=HEATMAP_TTL)


def get_heatmap_delta() -> dict | None:
    return get_json("heatmap", "delta")


def cache_heatmap_meta(data: dict) -> bool:
    return set_json("heatmap", "meta", data, ttl=HEATMAP_TTL)


def get_heatmap_meta() -> dict | None:
    return get_json("heatmap", "meta")


def cache_safety_score_grid(data: list) -> bool:
    return set_json("safety_score", "grid", data, ttl=SCORE_GRID_TTL)


def get_safety_score_grid() -> list | None:
    return get_json("safety_score", "grid")


def cache_active_sessions(data: list) -> bool:
    return set_json("sessions", "active", data, ttl=SESSION_TTL)


def get_active_sessions() -> list | None:
    return get_json("sessions", "active")


# ── Risk Forecast 1hr Cache ──
# Grid-based cache: ~250m cells, 30-min TTL

FORECAST_TTL = 1800  # 30 minutes
_forecast_mem_cache: dict[str, tuple[float, dict]] = {}  # grid_id -> (ts, data)


def _to_grid_id(lat: float, lng: float, cell_size_m: int = 250) -> str:
    """Convert lat/lng to a grid cell ID (~250m cells at equator)."""
    # ~0.00225 degrees ≈ 250m at equator
    cell_deg = cell_size_m / 111_000
    grid_lat = round(lat / cell_deg) * cell_deg
    grid_lng = round(lng / cell_deg) * cell_deg
    return f"{grid_lat:.5f}_{grid_lng:.5f}"


def cache_forecast_1hr(lat: float, lng: float, data: dict) -> bool:
    """Cache a 1-hour risk forecast for a grid cell."""
    grid_id = _to_grid_id(lat, lng)
    redis_ok = set_json("risk_forecast_1hr", grid_id, data, ttl=FORECAST_TTL)
    # Always update in-memory fallback
    _forecast_mem_cache[grid_id] = (_time.time(), data)
    return redis_ok


def get_forecast_1hr(lat: float, lng: float) -> dict | None:
    """Retrieve cached 1-hour risk forecast for a grid cell."""
    grid_id = _to_grid_id(lat, lng)

    # Try Redis first
    cached = get_json("risk_forecast_1hr", grid_id)
    if cached:
        return cached

    # In-memory fallback
    entry = _forecast_mem_cache.get(grid_id)
    if entry:
        ts, data = entry
        if (_time.time() - ts) < FORECAST_TTL:
            return data
        del _forecast_mem_cache[grid_id]

    return None


def invalidate_forecast_grid(lat: float, lng: float) -> bool:
    """Invalidate cached forecast for a grid cell (e.g., after new incident)."""
    grid_id = _to_grid_id(lat, lng)
    _forecast_mem_cache.pop(grid_id, None)
    return delete_key("risk_forecast_1hr", grid_id)


def cache_forecast_zone(zone_id: str, data: dict) -> bool:
    """Cache forecast for a named zone."""
    redis_ok = set_json("risk_forecast_zone", zone_id, data, ttl=FORECAST_TTL)
    _forecast_mem_cache[f"zone:{zone_id}"] = (_time.time(), data)
    return redis_ok


def get_forecast_zone(zone_id: str) -> dict | None:
    """Retrieve cached zone forecast."""
    cached = get_json("risk_forecast_zone", zone_id)
    if cached:
        return cached
    entry = _forecast_mem_cache.get(f"zone:{zone_id}")
    if entry:
        ts, data = entry
        if (_time.time() - ts) < FORECAST_TTL:
            return data
    return None


def get_all_forecast_keys() -> list[str]:
    """List all cached forecast grid keys (for monitoring/pre-warm)."""
    c = _get_client()
    if not c:
        return list(_forecast_mem_cache.keys())
    try:
        keys = c.keys(f"{PREFIX}:risk_forecast_1hr:*")
        return [k.decode() if isinstance(k, bytes) else k for k in keys]
    except Exception:
        return list(_forecast_mem_cache.keys())


# ── Pub/Sub ──

EMERGENCY_CHANNEL = "nischint:emergency:events"


def publish_event(channel: str, data: dict) -> bool:
    """Publish a JSON event to a Redis channel. Returns False if Redis unavailable."""
    r = _get_client()
    if not r:
        return False
    try:
        r.publish(channel, json.dumps(data))
        return True
    except Exception as e:
        logger.warning(f"Redis publish failed: {e}")
        return False


def get_pubsub():
    """Get a Redis PubSub object for subscribing. Returns None if unavailable."""
    r = _get_client()
    if not r:
        return None
    try:
        return r.pubsub()
    except Exception:
        return None



# ── Rate Limiting ──

import time as _time
_rate_limit_store: dict[str, list[float]] = {}


class RateLimitResult:
    __slots__ = ("allowed", "limit", "remaining", "reset_at")

    def __init__(self, allowed: bool, limit: int, remaining: int, reset_at: int):
        self.allowed = allowed
        self.limit = limit
        self.remaining = remaining
        self.reset_at = reset_at


def check_rate_limit(domain: str, key: str, max_requests: int, window_seconds: int) -> RateLimitResult:
    """
    Sliding-window rate limiter. Returns RateLimitResult with allowed, remaining, reset_at.
    Uses Redis if available, in-memory fallback otherwise.
    """
    now_ts = int(_time.time())
    reset_at = now_ts + window_seconds

    r = _get_client()
    if r:
        redis_key = f"{PREFIX}:ratelimit:{domain}:{key}"
        try:
            current = r.incr(redis_key)
            if current == 1:
                r.expire(redis_key, window_seconds)
            ttl = r.ttl(redis_key)
            reset_at = now_ts + max(ttl, 0)
            remaining = max(0, max_requests - current)
            return RateLimitResult(current <= max_requests, max_requests, remaining, reset_at)
        except Exception as e:
            logger.warning(f"Redis rate limit failed: {e}, using in-memory fallback")

    # In-memory fallback (single process)
    bucket = f"{domain}:{key}"
    now = _time.time()
    timestamps = _rate_limit_store.get(bucket, [])
    timestamps = [t for t in timestamps if now - t < window_seconds]
    remaining = max(0, max_requests - len(timestamps) - 1)

    if len(timestamps) >= max_requests:
        _rate_limit_store[bucket] = timestamps
        earliest = timestamps[0] if timestamps else now
        return RateLimitResult(False, max_requests, 0, int(earliest + window_seconds))

    timestamps.append(now)
    _rate_limit_store[bucket] = timestamps
    return RateLimitResult(True, max_requests, remaining, reset_at)


def get_info() -> dict:
    """Get Redis server info for monitoring dashboard."""
    c = _get_client()
    if not c:
        return {"status": "disconnected"}
    try:
        info = c.info(section="server")
        mem = c.info(section="memory")
        clients = c.info(section="clients")
        return {
            "status": "connected",
            "redis_version": info.get("redis_version", "unknown"),
            "uptime_seconds": info.get("uptime_in_seconds", 0),
            "used_memory_mb": round(mem.get("used_memory", 0) / 1048576, 2),
            "peak_memory_mb": round(mem.get("used_memory_peak", 0) / 1048576, 2),
            "connected_clients": clients.get("connected_clients", 0),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
