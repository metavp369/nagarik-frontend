# Guardian Mode Engine
# Manages guardian networks, live sharing sessions, and alert dispatching.
# Persists to PostgreSQL via SQLAlchemy models.

import logging
import math
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guardian import Guardian, GuardianSession, GuardianAlert
from app.services.safe_zone_engine import check_zone, _haversine

logger = logging.getLogger(__name__)

IDLE_SPEED_THRESHOLD = 0.5
IDLE_DURATION_THRESHOLD_S = 120
ROUTE_DEVIATION_THRESHOLD_M = 120

ESC_ORDER = {"none": 0, "user": 1, "guardian": 2, "emergency": 3}
RISK_ESC_MAP = {"SAFE": "none", "LOW": "none", "HIGH": "user", "CRITICAL": "guardian"}
RISK_ORDER = {"SAFE": 0, "LOW": 1, "HIGH": 2, "CRITICAL": 3}

# ── In-memory state for real-time tracking (supplements DB) ──
_live_state: dict[str, dict] = {}


# ── Guardian CRUD ──

async def add_guardian(session: AsyncSession, user_id: str, name: str, phone: str | None, email: str | None, relationship: str) -> dict:
    g = Guardian(
        user_id=uuid.UUID(user_id), name=name, phone=phone, email=email,
        relationship=relationship,
    )
    session.add(g)
    await session.flush()
    return _guardian_to_dict(g)


async def list_guardians(session: AsyncSession, user_id: str) -> list[dict]:
    result = await session.execute(
        select(Guardian).where(Guardian.user_id == uuid.UUID(user_id), Guardian.is_active == True)  # noqa: E712
    )
    return [_guardian_to_dict(g) for g in result.scalars().all()]


async def remove_guardian(session: AsyncSession, guardian_id: str) -> dict:
    result = await session.execute(select(Guardian).where(Guardian.id == uuid.UUID(guardian_id)))
    g = result.scalar_one_or_none()
    if not g:
        return {"error": "Guardian not found"}
    g.is_active = False
    await session.flush()
    return {"removed": True, "guardian_id": guardian_id}


def _guardian_to_dict(g: Guardian) -> dict:
    return {
        "id": str(g.id), "user_id": str(g.user_id), "name": g.name,
        "phone": g.phone, "email": g.email, "relationship": g.relationship,
        "notification_pref": g.notification_pref, "is_active": g.is_active,
        "created_at": g.created_at.isoformat() if g.created_at else None,
    }


# ── Session Management ──

async def start_session(
    session: AsyncSession, user_id: str, lat: float, lng: float,
    dest_lat: float | None = None, dest_lng: float | None = None,
) -> dict:
    now = datetime.now(timezone.utc)
    zone = await check_zone(session, user_id, lat, lng, now)

    gs = GuardianSession(
        user_id=uuid.UUID(user_id), status="active",
        destination={"lat": dest_lat, "lng": dest_lng} if dest_lat else None,
        current_location={"lat": lat, "lng": lng},
        risk_level=zone["risk_level"], risk_score=zone["risk_score"],
        zone_name=zone["zone_name"],
        is_night=(now.hour >= 22 or now.hour < 5),
    )
    session.add(gs)
    await session.flush()

    # Init live state
    _live_state[str(gs.id)] = {
        "prev_location": {"lat": lat, "lng": lng},
        "prev_update_at": now, "idle_since": None, "safety_check_pending": False,
        "safety_check_sent_at": None, "route_points": [],
    }

    # Count guardians notified
    guardians = await list_guardians(session, user_id)

    # Invalidate active sessions cache
    from app.services.redis_service import delete_key
    delete_key("sessions", "active")

    return {
        "session_id": str(gs.id), "status": "active", "user_id": user_id,
        "started_at": now.isoformat(), "initial_zone": {
            "risk_level": zone["risk_level"], "risk_score": zone["risk_score"],
            "zone_name": zone["zone_name"],
        },
        "destination": gs.destination, "guardians_notified": len(guardians),
        "is_night": gs.is_night,
    }


async def stop_session(session: AsyncSession, session_id: str) -> dict:
    result = await session.execute(select(GuardianSession).where(GuardianSession.id == uuid.UUID(session_id)))
    gs = result.scalar_one_or_none()
    if not gs:
        return {"error": "Session not found"}

    now = datetime.now(timezone.utc)
    gs.status = "ended"
    gs.ended_at = now
    await session.flush()
    _live_state.pop(session_id, None)

    # Invalidate active sessions cache
    from app.services.redis_service import delete_key
    delete_key("sessions", "active")

    duration = round((now - gs.started_at).total_seconds() / 60, 1)
    alert_count = await _count_alerts(session, session_id)

    return {
        "session_id": session_id, "status": "ended",
        "duration_minutes": duration, "total_distance_m": round(gs.total_distance_m, 1),
        "location_updates": gs.location_updates, "alerts_triggered": alert_count,
        "final_zone": {"risk_level": gs.risk_level, "risk_score": gs.risk_score, "zone_name": gs.zone_name},
    }


async def get_session(session: AsyncSession, session_id: str) -> dict | None:
    result = await session.execute(select(GuardianSession).where(GuardianSession.id == uuid.UUID(session_id)))
    gs = result.scalar_one_or_none()
    if not gs:
        return None

    now = datetime.now(timezone.utc)
    duration = round((now - gs.started_at).total_seconds() / 60, 1)
    alerts = await _get_session_alerts(session, session_id, limit=10)
    live = _live_state.get(session_id, {})

    return {
        "session_id": str(gs.id), "user_id": str(gs.user_id), "status": gs.status,
        "started_at": gs.started_at.isoformat(), "duration_minutes": duration,
        "current_location": gs.current_location, "destination": gs.destination,
        "risk_level": gs.risk_level, "risk_score": gs.risk_score,
        "zone_name": gs.zone_name, "eta_minutes": gs.eta_minutes,
        "speed_mps": round(gs.speed_mps, 2), "total_distance_m": round(gs.total_distance_m, 1),
        "location_updates": gs.location_updates, "escalation_level": gs.escalation_level,
        "is_night": gs.is_night, "route_deviated": gs.route_deviated,
        "is_idle": gs.is_idle, "alert_count": len(alerts),
        "alerts": alerts,
        "safety_check_pending": live.get("safety_check_pending", False),
    }


async def get_active_sessions(session: AsyncSession) -> list[dict]:
    # Try Redis cache first (short TTL for freshness)
    from app.services.redis_service import get_active_sessions as redis_get, cache_active_sessions

    cached = redis_get()
    if cached is not None:
        return cached

    result = await session.execute(
        select(GuardianSession).where(GuardianSession.status == "active")
    )
    now = datetime.now(timezone.utc)
    sessions = []
    for gs in result.scalars().all():
        sessions.append({
            "session_id": str(gs.id), "user_id": str(gs.user_id),
            "duration_minutes": round((now - gs.started_at).total_seconds() / 60, 1),
            "risk_level": gs.risk_level, "risk_score": gs.risk_score,
            "zone_name": gs.zone_name, "is_idle": gs.is_idle,
            "route_deviated": gs.route_deviated, "escalation_level": gs.escalation_level,
            "location": gs.current_location, "eta_minutes": gs.eta_minutes,
            "location_updates": gs.location_updates,
        })
    sessions.sort(key=lambda x: x["risk_score"], reverse=True)

    # Cache in Redis with short TTL (120s)
    cache_active_sessions(sessions)

    return sessions


async def get_user_sessions(session: AsyncSession, user_id: str, limit: int = 10) -> list[dict]:
    result = await session.execute(
        select(GuardianSession).where(GuardianSession.user_id == uuid.UUID(user_id))
        .order_by(GuardianSession.started_at.desc()).limit(limit)
    )
    now = datetime.now(timezone.utc)
    return [{
        "session_id": str(gs.id), "status": gs.status,
        "started_at": gs.started_at.isoformat(),
        "ended_at": gs.ended_at.isoformat() if gs.ended_at else None,
        "duration_minutes": round(((gs.ended_at or now) - gs.started_at).total_seconds() / 60, 1),
        "risk_level": gs.risk_level, "total_distance_m": round(gs.total_distance_m, 1),
        "location_updates": gs.location_updates, "escalation_level": gs.escalation_level,
    } for gs in result.scalars().all()]


# ── Location Updates ──

async def update_location(
    session: AsyncSession, session_id: str, lat: float, lng: float,
    timestamp: datetime | None = None,
) -> dict:
    result = await session.execute(select(GuardianSession).where(GuardianSession.id == uuid.UUID(session_id)))
    gs = result.scalar_one_or_none()
    if not gs or gs.status != "active":
        return {"error": "No active session"}

    now = timestamp or datetime.now(timezone.utc)
    live = _live_state.get(session_id, {})
    prev_loc = live.get("prev_location", gs.current_location or {"lat": lat, "lng": lng})
    prev_ts = live.get("prev_update_at", gs.started_at)

    # Compute speed & distance
    dt = (now - prev_ts).total_seconds()
    dist = _haversine(prev_loc["lat"], prev_loc["lng"], lat, lng)
    speed = dist / dt if dt > 0 else 0.0

    # Zone check
    zone = await check_zone(session, str(gs.user_id), lat, lng, now)
    prev_risk = gs.risk_level
    new_risk = zone["risk_level"]

    alerts_generated = []

    # Zone escalation
    if RISK_ORDER.get(new_risk, 0) > RISK_ORDER.get(prev_risk, 0):
        esc = RISK_ESC_MAP.get(new_risk, "none")
        alert = await _create_alert(session, session_id, "zone_risk", new_risk.lower(),
            f"Risk escalation: {prev_risk} -> {new_risk}",
            f"Entered {zone['zone_name']} ({new_risk} risk, score {zone['risk_score']})",
            zone.get("recommendation_message", ""),
            {"lat": lat, "lng": lng}, user_id=str(gs.user_id),
        )
        alerts_generated.append(alert)
        if ESC_ORDER.get(esc, 0) > ESC_ORDER.get(gs.escalation_level, 0):
            gs.escalation_level = esc

    # Idle detection
    if speed < IDLE_SPEED_THRESHOLD:
        if not gs.is_idle:
            gs.is_idle = True
            live["idle_since"] = now
        else:
            idle_start = live.get("idle_since", now)
            idle_dur = (now - idle_start).total_seconds()
            if idle_dur >= IDLE_DURATION_THRESHOLD_S and not live.get("safety_check_pending"):
                live["safety_check_pending"] = True
                live["safety_check_sent_at"] = now
                alert = await _create_alert(session, session_id, "idle", "medium",
                    f"Stopped for {round(idle_dur)}s — are you safe?",
                    "Unexpected stop detected", "Tap to confirm you are safe",
                    {"lat": lat, "lng": lng}, user_id=str(gs.user_id),
                )
                alerts_generated.append(alert)
    else:
        gs.is_idle = False
        live["idle_since"] = None
        live["safety_check_pending"] = False

    # ETA
    eta = None
    if gs.destination and speed > 0.3:
        dest_dist = _haversine(lat, lng, gs.destination["lat"], gs.destination["lng"])
        eta = round(dest_dist / speed / 60, 1)
        if dest_dist < 200:
            alert = await _create_alert(session, session_id, "arrived", "low",
                "Arrived at destination safely",
                f"Within {round(dest_dist)}m of destination",
                "Journey complete.", {"lat": lat, "lng": lng}, user_id=str(gs.user_id),
            )
            alerts_generated.append(alert)

    # No-response escalation
    if live.get("safety_check_pending") and live.get("safety_check_sent_at"):
        elapsed = (now - live["safety_check_sent_at"]).total_seconds()
        if elapsed > 300 and gs.escalation_level != "emergency":
            gs.escalation_level = "emergency"
            alert = await _create_alert(session, session_id, "emergency", "critical",
                "No response — escalating to emergency",
                f"Unresponsive for {round(elapsed)}s",
                "Emergency services may be contacted",
                {"lat": lat, "lng": lng}, user_id=str(gs.user_id),
            )
            alerts_generated.append(alert)

    # Update DB
    gs.current_location = {"lat": lat, "lng": lng}
    gs.risk_level = new_risk
    gs.risk_score = zone["risk_score"]
    gs.zone_name = zone["zone_name"]
    gs.speed_mps = speed
    gs.eta_minutes = eta
    gs.total_distance_m += dist
    gs.location_updates += 1
    gs.is_night = (now.hour >= 22 or now.hour < 5)
    await session.flush()

    live["prev_location"] = {"lat": lat, "lng": lng}
    live["prev_update_at"] = now
    _live_state[session_id] = live

    return {
        "session_id": session_id, "location": {"lat": lat, "lng": lng},
        "zone": {"risk_level": new_risk, "risk_score": zone["risk_score"], "zone_name": zone["zone_name"]},
        "speed_mps": round(speed, 2), "eta_minutes": eta,
        "is_idle": gs.is_idle, "escalation_level": gs.escalation_level,
        "alerts": [_alert_to_dict(a) for a in alerts_generated],
        "alert_count": len(alerts_generated),
        "safety_check_pending": live.get("safety_check_pending", False),
        "timestamp": now.isoformat(),
    }


async def acknowledge_safety(session: AsyncSession, session_id: str) -> dict:
    live = _live_state.get(session_id, {})
    live["safety_check_pending"] = False
    live["safety_check_sent_at"] = None
    _live_state[session_id] = live

    result = await session.execute(select(GuardianSession).where(GuardianSession.id == uuid.UUID(session_id)))
    gs = result.scalar_one_or_none()
    if gs and gs.escalation_level == "emergency":
        gs.escalation_level = RISK_ESC_MAP.get(gs.risk_level, "none")
        await session.flush()

    await _create_alert(session, session_id, "safety_confirmed", "low",
        "User confirmed safe", "Safety check acknowledged", "Continue monitoring", None)

    return {"acknowledged": True, "session_id": session_id}


# ── Helpers ──

async def _create_alert(session: AsyncSession, session_id: str, alert_type: str,
                         severity: str, message: str, details: str, recommendation: str,
                         location: dict | None, user_id: str | None = None) -> GuardianAlert:
    alert = GuardianAlert(
        session_id=uuid.UUID(session_id), alert_type=alert_type,
        severity=severity, message=message, details=details,
        recommendation=recommendation, location=location,
    )
    session.add(alert)
    await session.flush()

    # Dispatch real notifications to guardians
    if user_id:
        try:
            from app.services.guardian_notification_dispatcher import dispatch_guardian_alert
            dispatch_result = await dispatch_guardian_alert(session, alert, user_id, session_id)
            logger.info(f"Alert dispatch: {alert_type} -> push={dispatch_result.get('push_sent',0)}, sms={dispatch_result.get('sms_sent',0)}")
        except Exception as e:
            logger.error(f"Notification dispatch failed: {e}")

    return alert


def _alert_to_dict(a: GuardianAlert) -> dict:
    return {
        "id": str(a.id), "alert_type": a.alert_type, "severity": a.severity,
        "message": a.message, "details": a.details,
        "recommendation": a.recommendation, "location": a.location,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "notifications_dispatched": True,
    }


async def _get_session_alerts(session: AsyncSession, session_id: str, limit: int = 10) -> list[dict]:
    result = await session.execute(
        select(GuardianAlert).where(GuardianAlert.session_id == uuid.UUID(session_id))
        .order_by(GuardianAlert.created_at.desc()).limit(limit)
    )
    return [_alert_to_dict(a) for a in result.scalars().all()]


async def _count_alerts(session: AsyncSession, session_id: str) -> int:
    from sqlalchemy import func
    result = await session.execute(
        select(func.count()).where(GuardianAlert.session_id == uuid.UUID(session_id))
    )
    return result.scalar() or 0
