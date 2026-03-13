# Guardian Live Status API — Real-time monitoring for guardians
# Powers the Guardian Live Map mobile screen

import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session, get_current_user
from app.models.user import User
from app.models.guardian import GuardianSession, GuardianAlert
from app.models.guardian_network import GuardianRelationship

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/guardian/live", tags=["Guardian Live Map"])


@router.get("/protected-users")
async def get_protected_users(
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    """Get all users this guardian protects, with basic live status.
    Includes self for personal safety monitoring."""
    users = []

    # 1. Users where current user is listed as guardian (via GuardianRelationship)
    rels = (await session.execute(
        select(GuardianRelationship).where(and_(
            GuardianRelationship.guardian_user_id == user.id,
            GuardianRelationship.is_active == True,  # noqa: E712
        ))
    )).scalars().all()

    seen_ids = set()
    for rel in rels:
        if rel.user_id in seen_ids:
            continue
        seen_ids.add(rel.user_id)
        u = (await session.execute(select(User).where(User.id == rel.user_id))).scalar_one_or_none()
        if not u:
            continue

        active = (await session.execute(
            select(GuardianSession).where(and_(
                GuardianSession.user_id == u.id,
                GuardianSession.status == "active",
            )).limit(1)
        )).scalar_one_or_none()

        users.append({
            "user_id": str(u.id),
            "name": u.full_name or u.email,
            "email": u.email,
            "relationship": rel.relationship_type,
            "has_active_session": active is not None,
            "risk_level": active.risk_level if active else "SAFE",
            "risk_score": round(active.risk_score, 1) if active else 0,
            "is_self": False,
        })

    # 2. Always include self for personal safety monitoring
    if user.id not in seen_ids:
        self_active = (await session.execute(
            select(GuardianSession).where(and_(
                GuardianSession.user_id == user.id,
                GuardianSession.status == "active",
            )).limit(1)
        )).scalar_one_or_none()

        users.insert(0, {
            "user_id": str(user.id),
            "name": f"{user.full_name or user.email} (You)",
            "email": user.email,
            "relationship": "self",
            "has_active_session": self_active is not None,
            "risk_level": self_active.risk_level if self_active else "SAFE",
            "risk_score": round(self_active.risk_score, 1) if self_active else 0,
            "is_self": True,
        })

    return {"protected_users": users, "count": len(users)}


@router.get("/status/{user_id}")
async def get_live_status(
    user_id: str,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    """Get comprehensive live status for a protected user — powers Guardian Live Map."""
    try:
        target_uid = uuid.UUID(user_id)
    except (ValueError, AttributeError):
        raise HTTPException(422, "Invalid user ID format")

    # Allow self-view OR verify guardian relationship
    is_self = target_uid == user.id
    if not is_self:
        rel = (await session.execute(
            select(GuardianRelationship).where(and_(
                GuardianRelationship.guardian_user_id == user.id,
                GuardianRelationship.user_id == target_uid,
                GuardianRelationship.is_active == True,  # noqa: E712
            )).limit(1)
        )).scalar_one_or_none()

        if not rel:
            raise HTTPException(403, "You are not a guardian of this user")
        relationship = rel.relationship_type
    else:
        relationship = "self"

    # Get target user info
    target = (await session.execute(select(User).where(User.id == target_uid))).scalar_one_or_none()
    if not target:
        raise HTTPException(404, "User not found")

    # Get active session
    active = (await session.execute(
        select(GuardianSession).where(and_(
            GuardianSession.user_id == target_uid,
            GuardianSession.status == "active",
        )).order_by(desc(GuardianSession.started_at)).limit(1)
    )).scalar_one_or_none()

    # Compute AI risk score
    risk_data = None
    try:
        from app.services.guardian_ai_refinement import compute_risk_score
        risk_data = await compute_risk_score(session, target_uid)
    except Exception as e:
        logger.debug(f"Risk score computation skipped: {e}")

    # Get recent alerts (last 10)
    recent_alerts = []
    if active:
        alerts_q = await session.execute(
            select(GuardianAlert)
            .where(GuardianAlert.session_id == active.id)
            .order_by(desc(GuardianAlert.created_at))
            .limit(10)
        )
        for a in alerts_q.scalars().all():
            recent_alerts.append({
                "id": str(a.id),
                "type": a.alert_type,
                "severity": a.severity,
                "message": a.message,
                "recommendation": a.recommendation,
                "location": a.location,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            })

    # Build response
    now = datetime.now(timezone.utc)
    session_data = None
    if active:
        duration = int((now - active.started_at).total_seconds()) if active.started_at else 0
        last_update_seconds = 0
        if active.previous_update_at:
            last_update_seconds = int((now - active.previous_update_at).total_seconds())

        session_data = {
            "session_id": str(active.id),
            "started_at": active.started_at.isoformat(),
            "duration_seconds": duration,
            "destination": active.destination,
            "risk_level": active.risk_level,
            "risk_score": round(active.risk_score, 2),
            "current_location": active.current_location,
            "route_points": active.route_points,
            "speed_kmh": round(active.speed_mps * 3.6, 1) if active.speed_mps else 0,
            "total_distance_m": round(active.total_distance_m, 1),
            "is_idle": active.is_idle,
            "is_night": active.is_night,
            "route_deviated": active.route_deviated,
            "escalation_level": active.escalation_level,
            "alert_count": active.alert_count,
            "last_update_seconds": last_update_seconds,
        }

    # Get behavior pattern from risk data
    behavior_pattern = "Normal"
    recommendation = "No action needed"
    if risk_data:
        score = risk_data.get("score", 0)
        if score >= 85:
            behavior_pattern = "Critical Alert"
            recommendation = "Immediate contact required"
        elif score >= 60:
            behavior_pattern = "Deviating"
            recommendation = "Check-in with user"
        elif score >= 30:
            behavior_pattern = "Slight Changes"
            recommendation = "Continue monitoring"

    # Get last 5 completed sessions for history context
    past_sessions = []
    past_q = await session.execute(
        select(GuardianSession).where(and_(
            GuardianSession.user_id == target_uid,
            GuardianSession.status != "active",
        )).order_by(desc(GuardianSession.ended_at)).limit(5)
    )
    for ps in past_q.scalars().all():
        past_sessions.append({
            "session_id": str(ps.id),
            "started_at": ps.started_at.isoformat() if ps.started_at else None,
            "ended_at": ps.ended_at.isoformat() if ps.ended_at else None,
            "risk_level": ps.risk_level,
            "distance_m": round(ps.total_distance_m, 1),
        })

    return {
        "user_id": str(target_uid),
        "user_name": target.full_name or target.email,
        "email": target.email,
        "relationship": relationship,
        "session_active": active is not None,
        "session": session_data,
        "risk": {
            "score": risk_data.get("score", 0) if risk_data else 0,
            "level": risk_data.get("level", "SAFE") if risk_data else "SAFE",
            "factors": risk_data.get("factors", []) if risk_data else [],
        },
        "behavior_pattern": behavior_pattern,
        "recommendation": recommendation,
        "recent_alerts": recent_alerts,
        "past_sessions": past_sessions,
        "last_update": now.isoformat(),
    }
