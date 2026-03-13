# Voice Distress Detection Service
#
# Hybrid architecture: on-device detection (primary) + optional Whisper verification (Phase 2)
# Distress score: keyword*0.4 + scream*0.35 + repetition*0.25
# Trigger: score >= 0.7 → voice_alert, score >= 0.9 → auto-SOS
# Cooldown: 30s between events (unless score > 0.9)

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.voice_distress_event import VoiceDistressEvent
from app.services.event_broadcaster import broadcaster
from app.services.redis_service import set_json as _redis_set, get_json as _redis_get

logger = logging.getLogger(__name__)

_mem: dict = {}

COOLDOWN_S = 30
AUTO_SOS_THRESHOLD = 0.9
ALERT_THRESHOLD = 0.7

# Scoring weights
W_KEYWORD = 0.40
W_SCREAM = 0.35
W_REPETITION = 0.25

DISTRESS_KEYWORDS = {"help", "stop", "leave me", "call police", "emergency", "don't touch", "save me", "please help"}


def _set(key, data):
    ok = _redis_set("voice_distress", key, data)
    if not ok:
        _mem[f"voice_distress:{key}"] = data


def _get(key):
    v = _redis_get("voice_distress", key)
    return v if v is not None else _mem.get(f"voice_distress:{key}")


def compute_distress_score(keywords: list[str] | None, scream_detected: bool,
                           repeated: bool, audio_features: dict | None) -> float:
    """Compute distress score from detection signals."""
    # Keyword score: based on number and severity of keywords matched
    keyword_score = 0.0
    if keywords:
        matched = [k.lower() for k in keywords if k.lower() in DISTRESS_KEYWORDS]
        if matched:
            keyword_score = min(1.0, len(matched) / 2.0)  # 2+ keywords = max

    # Scream score: binary + amplitude boost
    scream_score = 0.0
    if scream_detected:
        scream_score = 0.8
        if audio_features:
            amp = audio_features.get("amplitude", 0)
            pitch_var = audio_features.get("pitch_variance", 0)
            if amp > 0.8 and pitch_var > 0.6:
                scream_score = 1.0
            elif amp > 0.5:
                scream_score = 0.9

    # Repetition score
    repetition_score = 1.0 if repeated else 0.0

    score = W_KEYWORD * keyword_score + W_SCREAM * scream_score + W_REPETITION * repetition_score
    return round(score, 3)


def _check_cooldown(user_id: str, score: float) -> bool:
    """Returns True if in cooldown. Bypass if score > 0.9."""
    if score >= AUTO_SOS_THRESHOLD:
        return False  # Never block critical alerts
    last = _get(f"cooldown:{user_id}")
    if last:
        last_time = datetime.fromisoformat(last)
        if (datetime.now(timezone.utc) - last_time).total_seconds() < COOLDOWN_S:
            return True
    return False


async def report_voice_distress(
    session: AsyncSession,
    user_id: str,
    lat: float,
    lng: float,
    keywords: list[str] | None,
    scream_detected: bool,
    repeated: bool,
    audio_features: dict | None,
) -> dict:
    """Report voice distress event. Computes score, stores, broadcasts SSE."""
    score = compute_distress_score(keywords, scream_detected, repeated, audio_features)

    if score < ALERT_THRESHOLD:
        return {"status": "below_threshold", "distress_score": score, "message": "Score below alert threshold"}

    if _check_cooldown(user_id, score):
        return {"status": "cooldown", "message": "Voice event recently reported. Wait 30s."}

    is_auto_sos = score >= AUTO_SOS_THRESHOLD

    event = VoiceDistressEvent(
        user_id=uuid.UUID(user_id),
        lat=lat, lng=lng,
        keywords=keywords,
        scream_detected=scream_detected,
        repeated_detection=repeated,
        audio_features=audio_features,
        distress_score=score,
        status="auto_sos" if is_auto_sos else "active",
    )
    session.add(event)
    await session.flush()
    event_id = str(event.id)

    _set(f"cooldown:{user_id}", datetime.now(timezone.utc).isoformat())

    # Auto-SOS for critical distress
    emergency_id = None
    if is_auto_sos:
        try:
            from app.services.emergency_engine import trigger_silent_sos
            sos_result = await trigger_silent_sos(
                session=session, user_id=user_id, lat=lat, lng=lng,
                trigger_source="voice_distress",
                device_metadata={"voice_event_id": event_id, "distress_score": score, "keywords": keywords},
            )
            emergency_id = sos_result.get("event_id")
            if emergency_id:
                event.emergency_event_id = uuid.UUID(emergency_id)
        except Exception as e:
            logger.error(f"Voice auto-SOS failed: {e}")

    # Matched keywords for display
    matched = [k for k in (keywords or []) if k.lower() in DISTRESS_KEYWORDS]

    sse_data = {
        "event_id": event_id,
        "user_id": user_id,
        "lat": lat, "lng": lng,
        "distress_score": score,
        "keywords": matched,
        "scream_detected": scream_detected,
        "repeated": repeated,
        "auto_sos": is_auto_sos,
        "emergency_event_id": emergency_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    await broadcaster.broadcast_to_user(user_id, "voice_alert", sse_data)
    await broadcaster.broadcast_to_operators("voice_alert", sse_data)

    logger.warning(f"Voice distress: user={user_id}, score={score:.2f}, keywords={matched}, "
                   f"scream={scream_detected}, auto_sos={is_auto_sos}")

    await session.commit()

    # Feed signal to Safety Brain (augment, don't replace existing SSE)
    try:
        from app.services.safety_brain_service import on_voice_distress
        await on_voice_distress(session, user_id, score, lat, lng)
    except Exception as e:
        logger.error(f"Safety Brain voice hook failed: {e}")

    return {
        "status": "auto_sos" if is_auto_sos else "alert",
        "event_id": event_id,
        "distress_score": score,
        "keywords_matched": matched,
        "scream_detected": scream_detected,
        "auto_sos": is_auto_sos,
        "emergency_event_id": emergency_id,
    }


async def resolve_voice_distress(session: AsyncSession, event_id: str, user_id: str, resolved_by: str) -> dict:
    result = await session.execute(
        select(VoiceDistressEvent).where(VoiceDistressEvent.id == uuid.UUID(event_id))
    )
    event = result.scalar_one_or_none()
    if not event:
        return {"error": "Voice distress event not found"}
    if str(event.user_id) != user_id:
        return {"error": "Not authorized"}
    if event.status in ("resolved", "false_positive"):
        return {"status": "already_resolved"}

    now = datetime.now(timezone.utc)
    event.status = "false_positive" if resolved_by == "false_positive" else "resolved"
    event.resolved_by = resolved_by
    event.resolved_at = now
    await session.commit()

    sse_data = {"event_id": event_id, "user_id": user_id, "resolved_by": resolved_by, "timestamp": now.isoformat()}
    await broadcaster.broadcast_to_user(user_id, "voice_distress_resolved", sse_data)
    await broadcaster.broadcast_to_operators("voice_distress_resolved", sse_data)

    return {"status": event.status, "event_id": event_id, "resolved_by": resolved_by}


async def get_voice_distress_events(session: AsyncSession, user_id: str | None = None, limit: int = 20) -> list[dict]:
    query = select(VoiceDistressEvent).order_by(desc(VoiceDistressEvent.created_at)).limit(limit)
    if user_id:
        query = query.where(VoiceDistressEvent.user_id == uuid.UUID(user_id))
    result = await session.execute(query)
    return [
        {
            "event_id": str(e.id), "user_id": str(e.user_id),
            "lat": e.lat, "lng": e.lng,
            "keywords": e.keywords, "scream_detected": e.scream_detected,
            "repeated_detection": e.repeated_detection,
            "audio_features": e.audio_features,
            "distress_score": e.distress_score,
            "status": e.status, "resolved_by": e.resolved_by,
            "emergency_event_id": str(e.emergency_event_id) if e.emergency_event_id else None,
            "whisper_verified": e.whisper_verified,
            "whisper_transcript": e.whisper_transcript,
            "whisper_confidence": e.whisper_confidence,
            "verification_status": e.verification_status,
            "distress_phrases_found": e.distress_phrases_found,
            "trigger_type": e.trigger_type,
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "resolved_at": e.resolved_at.isoformat() if e.resolved_at else None,
        }
        for e in result.scalars().all()
    ]
