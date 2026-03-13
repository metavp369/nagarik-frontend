# NISCHINT Safety Brain — Unified multi-sensor risk scoring engine
#
# Signal fusion: fall*0.35 + voice*0.30 + route*0.15 + wander*0.10 + pickup*0.10
# Risk levels: Normal (0-0.3), Suspicious (0.3-0.6), Dangerous (0.6-0.85), Critical (>=0.85)
# Signal decay: scores decay over time to prevent stale high-risk states
# Auto-SOS at critical level

import logging
import math
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.safety_event import SafetyEvent
from app.services.event_broadcaster import broadcaster
from app.services.redis_service import set_json as _redis_set, get_json as _redis_get, delete_key as _redis_del

logger = logging.getLogger(__name__)

_mem: dict = {}

# Signal weights
WEIGHTS = {
    "fall": 0.35,
    "voice": 0.30,
    "route": 0.15,
    "wander": 0.10,
    "pickup": 0.10,
}

# Decay constants (seconds) — signal decays exponentially with this time constant
DECAY_CONSTANTS = {
    "fall": 60,      # 60s — fast decay for transient impact events
    "voice": 45,     # 45s — voice distress fades quickly
    "route": 120,    # 120s — route deviation needs longer window
    "wander": 180,   # 180s — wandering builds slowly
    "pickup": 90,    # 90s — pickup anomalies are time-sensitive
}

# Risk thresholds
NORMAL_MAX = 0.3
SUSPICIOUS_MAX = 0.6
DANGEROUS_MAX = 0.85
# >= 0.85 is critical


def _set(key, data):
    ok = _redis_set("safety_brain", key, data)
    if not ok:
        _mem[f"safety_brain:{key}"] = data


def _get(key):
    v = _redis_get("safety_brain", key)
    return v if v is not None else _mem.get(f"safety_brain:{key}")


def _del(key):
    _redis_del("safety_brain", key)
    _mem.pop(f"safety_brain:{key}", None)


def _decay_factor(signal_type: str, age_seconds: float) -> float:
    """Exponential decay: score * exp(-elapsed / decay_constant)."""
    decay_constant = DECAY_CONSTANTS.get(signal_type, 120)
    if age_seconds <= 0:
        return 1.0
    return math.exp(-age_seconds / decay_constant)


def classify_risk(score: float) -> str:
    if score >= DANGEROUS_MAX:
        return "critical"
    if score >= SUSPICIOUS_MAX:
        return "dangerous"
    if score >= NORMAL_MAX:
        return "suspicious"
    return "normal"


def compute_risk_score(signals: dict[str, float]) -> tuple[float, str, str]:
    """
    Compute unified risk score from weighted signals.
    Returns (score, risk_level, primary_event).
    """
    score = 0.0
    max_signal = ("none", 0.0)

    for signal_type, value in signals.items():
        weight = WEIGHTS.get(signal_type, 0)
        contribution = value * weight
        score += contribution
        if value > max_signal[1]:
            max_signal = (signal_type, value)

    score = round(min(1.0, score), 3)
    level = classify_risk(score)
    primary = max_signal[0]

    return score, level, primary


def apply_decay(signals_with_timestamps: dict) -> dict[str, float]:
    """Apply time-based decay to signals. Input: {type: {score, timestamp}}."""
    now = datetime.now(timezone.utc)
    decayed = {}
    for sig_type, data in signals_with_timestamps.items():
        raw_score = data.get("score", 0)
        ts = data.get("timestamp")
        if ts:
            age = (now - datetime.fromisoformat(ts)).total_seconds()
            factor = _decay_factor(sig_type, age)
            decayed[sig_type] = round(raw_score * factor, 3)
        else:
            decayed[sig_type] = raw_score
    return decayed


async def evaluate_risk(
    session: AsyncSession,
    user_id: str,
    signals: dict[str, float],
    lat: float,
    lng: float,
    source_event_id: str | None = None,
) -> dict:
    """
    Evaluate unified risk from all active signals.
    Creates safety event if risk is suspicious+.
    """
    score, level, primary = compute_risk_score(signals)

    # Store current signal state
    now = datetime.now(timezone.utc)
    signal_state = _get(f"signals:{user_id}") or {}
    for sig_type, value in signals.items():
        if value > 0:
            signal_state[sig_type] = {"score": value, "timestamp": now.isoformat()}
    _set(f"signals:{user_id}", signal_state)

    result = {
        "risk_score": score,
        "risk_level": level,
        "primary_event": primary,
        "signals": signals,
    }

    # Only create event for suspicious+
    if level == "normal":
        result["status"] = "normal"
        return result

    event = SafetyEvent(
        user_id=uuid.UUID(user_id),
        risk_score=score,
        risk_level=level,
        signals=signals,
        primary_event=primary,
        location_lat=lat,
        location_lng=lng,
        status="active",
    )
    session.add(event)
    await session.flush()
    event_id = str(event.id)

    # Auto-SOS for critical
    emergency_id = None
    if level == "critical":
        try:
            from app.services.emergency_engine import trigger_silent_sos
            sos_result = await trigger_silent_sos(
                session=session, user_id=user_id, lat=lat, lng=lng,
                trigger_source="safety_brain",
                device_metadata={"safety_event_id": event_id, "risk_score": score, "signals": signals},
            )
            emergency_id = sos_result.get("event_id")
        except Exception as e:
            logger.error(f"Safety Brain auto-SOS failed: {e}")

    # SSE broadcast
    sse_data = {
        "event_id": event_id,
        "user_id": user_id,
        "risk_score": score,
        "risk_level": level,
        "primary_event": primary,
        "signals": signals,
        "lat": lat, "lng": lng,
        "auto_sos": level == "critical",
        "emergency_event_id": emergency_id,
        "timestamp": now.isoformat(),
    }
    await broadcaster.broadcast_to_user(user_id, "safety_risk_alert", sse_data)
    await broadcaster.broadcast_to_operators("safety_risk_alert", sse_data)

    # Record metrics for monitoring
    from app.services.monitoring_service import record_risk_spike, record_guardian_alert
    if score >= 0.6:
        record_risk_spike(score)
    if level in ("dangerous", "critical"):
        record_guardian_alert(level)

    # Enqueue AI signal for async batch processing
    from app.services.queue_service import enqueue_ai_signal
    enqueue_ai_signal({
        "signal_type": "risk_assessment",
        "user_id": user_id,
        "score": score,
        "level": level,
        "primary_event": primary,
        "lat": lat,
        "lng": lng,
    })

    logger.warning(f"Safety Brain: user={user_id}, score={score:.2f}, level={level}, primary={primary}")

    # Auto-trigger predictive reroute for dangerous+ events
    if level in ("dangerous", "critical"):
        try:
            from app.services.predictive_reroute_service import on_risk_level_change
            await on_risk_level_change(session, user_id, score, level, signals, lat, lng)
        except Exception as e:
            logger.error(f"Safety Brain auto-reroute hook failed: {e}")

    await session.commit()

    result.update({
        "event_id": event_id,
        "auto_sos": level == "critical",
        "emergency_event_id": emergency_id,
    })
    return result


async def get_user_risk_status(session: AsyncSession, user_id: str) -> dict:
    """Get current risk level for a user, with decayed signals."""
    signal_state = _get(f"signals:{user_id}")
    if not signal_state:
        return {"risk_score": 0, "risk_level": "normal", "signals": {}, "status": "no_data"}

    decayed = apply_decay(signal_state)
    score, level, primary = compute_risk_score(decayed)

    # Latest event
    result = await session.execute(
        select(SafetyEvent)
        .where(SafetyEvent.user_id == uuid.UUID(user_id))
        .order_by(desc(SafetyEvent.created_at))
        .limit(1)
    )
    latest = result.scalar_one_or_none()

    return {
        "risk_score": score,
        "risk_level": level,
        "primary_event": primary,
        "signals": decayed,
        "raw_signals": {k: v.get("score", 0) for k, v in signal_state.items()},
        "latest_event_id": str(latest.id) if latest else None,
        "latest_event_status": latest.status if latest else None,
    }


async def resolve_safety_event(session: AsyncSession, event_id: str, user_id: str) -> dict:
    result = await session.execute(
        select(SafetyEvent).where(SafetyEvent.id == uuid.UUID(event_id))
    )
    event = result.scalar_one_or_none()
    if not event:
        return {"error": "Safety event not found"}
    if str(event.user_id) != user_id:
        return {"error": "Not authorized"}
    if event.status == "resolved":
        return {"status": "already_resolved"}

    event.status = "resolved"
    event.resolved_at = datetime.now(timezone.utc)
    event.updated_at = datetime.now(timezone.utc)

    # Clear signal state
    _del(f"signals:{user_id}")

    await session.commit()
    return {"status": "resolved", "event_id": event_id}


async def get_safety_events(session: AsyncSession, user_id: str | None = None, limit: int = 20) -> list[dict]:
    query = select(SafetyEvent).order_by(desc(SafetyEvent.created_at)).limit(limit)
    if user_id:
        query = query.where(SafetyEvent.user_id == uuid.UUID(user_id))
    result = await session.execute(query)
    return [
        {
            "event_id": str(e.id), "user_id": str(e.user_id),
            "risk_score": e.risk_score, "risk_level": e.risk_level,
            "signals": e.signals, "primary_event": e.primary_event,
            "lat": e.location_lat, "lng": e.location_lng,
            "status": e.status,
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "resolved_at": e.resolved_at.isoformat() if e.resolved_at else None,
        }
        for e in result.scalars().all()
    ]


# ── Detector Integration Hooks ──
# Called by existing detectors to feed signals into the brain

async def on_fall_detected(session: AsyncSession, user_id: str, confidence: float, lat: float, lng: float):
    """Hook called when fall detection fires."""
    current = _get(f"signals:{user_id}") or {}
    signals = {k: v.get("score", 0) if isinstance(v, dict) else v for k, v in current.items()}
    signals["fall"] = confidence
    return await evaluate_risk(session, user_id, signals, lat, lng)


async def on_voice_distress(session: AsyncSession, user_id: str, distress_score: float, lat: float, lng: float):
    """Hook called when voice distress fires."""
    current = _get(f"signals:{user_id}") or {}
    signals = {k: v.get("score", 0) if isinstance(v, dict) else v for k, v in current.items()}
    signals["voice"] = distress_score
    return await evaluate_risk(session, user_id, signals, lat, lng)


async def on_route_deviation(session: AsyncSession, user_id: str, deviation_score: float, lat: float, lng: float):
    """Hook called when route deviation escalates."""
    current = _get(f"signals:{user_id}") or {}
    signals = {k: v.get("score", 0) if isinstance(v, dict) else v for k, v in current.items()}
    signals["route"] = deviation_score
    return await evaluate_risk(session, user_id, signals, lat, lng)


async def on_wandering_detected(session: AsyncSession, user_id: str, wander_score: float, lat: float, lng: float):
    """Hook called when wandering detection fires."""
    current = _get(f"signals:{user_id}") or {}
    signals = {k: v.get("score", 0) if isinstance(v, dict) else v for k, v in current.items()}
    signals["wander"] = wander_score
    return await evaluate_risk(session, user_id, signals, lat, lng)


async def on_pickup_anomaly(session: AsyncSession, user_id: str, anomaly_score: float, lat: float, lng: float):
    """Hook called when a pickup verification fails (invalid code, proximity, expired)."""
    current = _get(f"signals:{user_id}") or {}
    signals = {k: v.get("score", 0) if isinstance(v, dict) else v for k, v in current.items()}
    signals["pickup"] = anomaly_score
    return await evaluate_risk(session, user_id, signals, lat, lng)
