# Guardian Family Dashboard Engine
# Provides data for the consumer-facing guardian dashboard.
# Links guardians to their monitored loved ones via the guardians table.

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guardian import Guardian, GuardianSession, GuardianAlert
from app.models.user import User
from app.models.senior import Senior

logger = logging.getLogger(__name__)


async def _get_linked_user_ids(session: AsyncSession, guardian_email: str) -> list[uuid.UUID]:
    """Find all user_ids that have this guardian as a contact (by email match)."""
    result = await session.execute(
        select(Guardian.user_id).where(
            Guardian.email == guardian_email, Guardian.is_active == True  # noqa: E712
        )
    )
    return list(set(row[0] for row in result.all()))


async def get_loved_ones(session: AsyncSession, guardian_email: str, guardian_user_id: str) -> dict:
    """Get all people this guardian monitors, with their live status."""
    user_ids = await _get_linked_user_ids(session, guardian_email)

    monitored = []
    for uid in user_ids:
        user_result = await session.execute(select(User).where(User.id == uid))
        user = user_result.scalar_one_or_none()
        if not user:
            continue

        # Get guardian entry for relationship info
        entry_result = await session.execute(
            select(Guardian).where(
                Guardian.user_id == uid,
                Guardian.email == guardian_email,
                Guardian.is_active == True,  # noqa: E712
            ).limit(1)
        )
        entry = entry_result.scalar_one_or_none()

        # Active session
        sess_result = await session.execute(
            select(GuardianSession).where(
                GuardianSession.user_id == uid,
                GuardianSession.status == "active",
            ).order_by(GuardianSession.started_at.desc()).limit(1)
        )
        active = sess_result.scalar_one_or_none()

        item = {
            "user_id": str(uid),
            "name": user.full_name or user.email,
            "email": user.email,
            "phone": user.phone,
            "relationship": entry.relationship if entry else "family",
            "has_active_session": active is not None,
            "active_session": None,
        }

        if active:
            now = datetime.now(timezone.utc)
            dur = round((now - active.started_at).total_seconds() / 60, 1)
            ac_result = await session.execute(
                select(func.count()).where(GuardianAlert.session_id == active.id)
            )
            item["active_session"] = {
                "session_id": str(active.id),
                "started_at": active.started_at.isoformat(),
                "duration_minutes": dur,
                "current_location": active.current_location,
                "destination": active.destination,
                "risk_level": active.risk_level,
                "risk_score": round(active.risk_score, 2),
                "zone_name": active.zone_name,
                "eta_minutes": active.eta_minutes,
                "speed_mps": round(active.speed_mps, 2),
                "speed_kmh": round(active.speed_mps * 3.6, 1),
                "total_distance_m": round(active.total_distance_m, 1),
                "escalation_level": active.escalation_level,
                "is_night": active.is_night,
                "is_idle": active.is_idle,
                "route_deviated": active.route_deviated,
                "location_updates": active.location_updates,
                "alert_count": ac_result.scalar() or 0,
            }

        monitored.append(item)

    # Also include seniors directly linked to this guardian user
    seniors_result = await session.execute(
        select(Senior).where(Senior.guardian_id == uuid.UUID(guardian_user_id))
    )
    seniors = []
    for s in seniors_result.scalars().all():
        seniors.append({
            "senior_id": str(s.id),
            "name": s.full_name,
            "age": s.age,
        })

    return {
        "monitored_users": monitored,
        "seniors": seniors,
        "total_loved_ones": len(monitored) + len(seniors),
        "active_journeys": sum(1 for m in monitored if m["has_active_session"]),
    }


async def get_active_sessions(session: AsyncSession, guardian_email: str) -> list[dict]:
    """Get all active sessions for guardian's loved ones."""
    user_ids = await _get_linked_user_ids(session, guardian_email)
    if not user_ids:
        return []

    result = await session.execute(
        select(GuardianSession).where(
            GuardianSession.user_id.in_(user_ids),
            GuardianSession.status == "active",
        )
    )
    now = datetime.now(timezone.utc)
    sessions = []

    for gs in result.scalars().all():
        user_result = await session.execute(select(User).where(User.id == gs.user_id))
        user = user_result.scalar_one_or_none()
        ac = await session.execute(
            select(func.count()).where(GuardianAlert.session_id == gs.id)
        )
        sessions.append({
            "session_id": str(gs.id),
            "user_id": str(gs.user_id),
            "user_name": (user.full_name or user.email) if user else "Unknown",
            "status": gs.status,
            "started_at": gs.started_at.isoformat(),
            "duration_minutes": round((now - gs.started_at).total_seconds() / 60, 1),
            "current_location": gs.current_location,
            "destination": gs.destination,
            "risk_level": gs.risk_level,
            "risk_score": round(gs.risk_score, 2),
            "zone_name": gs.zone_name,
            "eta_minutes": gs.eta_minutes,
            "speed_mps": round(gs.speed_mps, 2),
            "speed_kmh": round(gs.speed_mps * 3.6, 1),
            "total_distance_m": round(gs.total_distance_m, 1),
            "escalation_level": gs.escalation_level,
            "is_night": gs.is_night,
            "is_idle": gs.is_idle,
            "route_deviated": gs.route_deviated,
            "alert_count": ac.scalar() or 0,
        })

    sessions.sort(key=lambda x: x["risk_score"], reverse=True)
    return sessions


async def get_alerts(session: AsyncSession, guardian_email: str, limit: int = 50) -> list[dict]:
    """Get recent alerts for guardian's loved ones."""
    user_ids = await _get_linked_user_ids(session, guardian_email)
    if not user_ids:
        return []

    sess_result = await session.execute(
        select(GuardianSession.id, GuardianSession.user_id).where(
            GuardianSession.user_id.in_(user_ids)
        )
    )
    session_map = {row[0]: row[1] for row in sess_result.all()}
    if not session_map:
        return []

    # Pre-fetch user names
    user_result = await session.execute(select(User).where(User.id.in_(set(session_map.values()))))
    user_names = {u.id: u.full_name or u.email for u in user_result.scalars().all()}

    alerts_result = await session.execute(
        select(GuardianAlert).where(
            GuardianAlert.session_id.in_(list(session_map.keys()))
        ).order_by(GuardianAlert.created_at.desc()).limit(limit)
    )

    return [{
        "id": str(a.id),
        "session_id": str(a.session_id),
        "user_name": user_names.get(session_map.get(a.session_id), "Unknown"),
        "alert_type": a.alert_type,
        "severity": a.severity,
        "message": a.message,
        "details": a.details,
        "recommendation": a.recommendation,
        "location": a.location,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    } for a in alerts_result.scalars().all()]


async def get_session_history(session: AsyncSession, guardian_email: str, limit: int = 20) -> list[dict]:
    """Get completed journey history for guardian's loved ones."""
    user_ids = await _get_linked_user_ids(session, guardian_email)
    if not user_ids:
        return []

    # Pre-fetch user names
    user_result = await session.execute(select(User).where(User.id.in_(user_ids)))
    user_names = {u.id: u.full_name or u.email for u in user_result.scalars().all()}

    result = await session.execute(
        select(GuardianSession).where(
            GuardianSession.user_id.in_(user_ids),
            GuardianSession.status.in_(["ended", "expired"]),
        ).order_by(GuardianSession.ended_at.desc()).limit(limit)
    )

    history = []
    for gs in result.scalars().all():
        ac = await session.execute(
            select(func.count()).where(GuardianAlert.session_id == gs.id)
        )
        duration = round(((gs.ended_at or gs.started_at) - gs.started_at).total_seconds() / 60, 1)
        history.append({
            "session_id": str(gs.id),
            "user_name": user_names.get(gs.user_id, "Unknown"),
            "started_at": gs.started_at.isoformat(),
            "ended_at": gs.ended_at.isoformat() if gs.ended_at else None,
            "duration_minutes": duration,
            "max_risk_level": gs.risk_level,
            "total_distance_m": round(gs.total_distance_m, 1),
            "alert_count": ac.scalar() or 0,
            "escalation_level": gs.escalation_level,
        })

    return history


async def request_safety_check(session: AsyncSession, session_id: str, guardian_email: str) -> dict:
    """Guardian requests a safety check from the monitored user."""
    # Verify guardian has access to this session
    gs_result = await session.execute(
        select(GuardianSession).where(
            GuardianSession.id == uuid.UUID(session_id),
            GuardianSession.status == "active",
        )
    )
    gs = gs_result.scalar_one_or_none()
    if not gs:
        return {"error": "No active session found"}

    # Verify this guardian is linked to the user
    link = await session.execute(
        select(Guardian).where(
            Guardian.user_id == gs.user_id,
            Guardian.email == guardian_email,
            Guardian.is_active == True,  # noqa: E712
        ).limit(1)
    )
    if not link.scalar_one_or_none():
        return {"error": "Not authorized for this session"}

    from app.services.guardian_mode_engine import _create_alert
    alert = await _create_alert(
        session, session_id, "check_in_request", "medium",
        "Guardian requested safety confirmation",
        "A guardian has requested that you confirm you are safe",
        "Please confirm your safety status",
        gs.current_location, user_id=str(gs.user_id),
    )

    return {
        "requested": True,
        "session_id": session_id,
        "alert_id": str(alert.id),
    }
