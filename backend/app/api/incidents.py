# Incidents Router
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session, get_current_user
from app.models.user import User
from app.schemas.incident import IncidentResponse
from app.services import incident_service
from app.services.incident_events import get_events

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("", response_model=List[IncidentResponse])
async def get_incidents(
    guardian_id: UUID = Query(..., description="Guardian user ID"),
    status: Optional[str] = Query(None, description="Filter by status (open, acknowledged, resolved, false_alarm)"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get all incidents for seniors under a guardian.
    Requires authentication.
    """
    incidents = await incident_service.get_incidents_by_guardian(
        session, guardian_id, status
    )
    return incidents


@router.patch("/{incident_id}/acknowledge", response_model=IncidentResponse)
async def acknowledge_incident(
    incident_id: UUID,
    channel: str = Query("dashboard", description="Acknowledge via: dashboard, sms, push, email"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Acknowledge an incident.
    Can only acknowledge if status == "open".
    """
    try:
        incident = await incident_service.acknowledge_incident(
            session, incident_id, current_user.id,
            current_user.full_name or current_user.email,
            channel,
        )
        return incident
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/{incident_id}/resolve", response_model=IncidentResponse)
async def resolve_incident(
    incident_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Resolve an incident.
    Can resolve if status in ["open", "acknowledged"].
    Sets resolved_at timestamp.
    """
    try:
        incident = await incident_service.resolve_incident(session, incident_id)
        return incident
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/{incident_id}/false-alarm", response_model=IncidentResponse)
async def mark_false_alarm(
    incident_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Mark an incident as false alarm.
    Can mark if status in ["open", "acknowledged"].
    Sets resolved_at timestamp.
    """
    try:
        incident = await incident_service.mark_false_alarm(session, incident_id)
        return incident
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))



@router.get("/{incident_id}/events")
async def get_incident_events(
    incident_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Get the full audit trail of events for an incident."""
    return await get_events(session, incident_id)


@router.get("/{incident_id}/notification-jobs")
async def get_incident_notification_jobs(
    incident_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Get all notification jobs for an incident. Guardian sees only their own incidents."""
    from sqlalchemy import select, text
    from app.models.notification_job import NotificationJob

    # Verify the incident belongs to this guardian's seniors
    ownership = await session.execute(
        text(
            "SELECT i.id FROM incidents i "
            "JOIN seniors s ON i.senior_id = s.id "
            "WHERE i.id = :iid AND s.guardian_id = :gid"
        ),
        {"iid": incident_id, "gid": current_user.id},
    )
    if not ownership.fetchone():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    result = await session.execute(
        select(NotificationJob)
        .where(NotificationJob.incident_id == incident_id)
        .order_by(NotificationJob.created_at.asc())
    )
    jobs = result.scalars().all()
    return [
        {
            "id": str(j.id),
            "channel": j.channel,
            "recipient": j.recipient,
            "status": j.status,
            "attempts": j.attempts,
            "last_attempt_at": j.last_attempt_at.isoformat() if j.last_attempt_at else None,
            "created_at": j.created_at.isoformat() if j.created_at else None,
            "escalation_level": j.payload.get("escalation_level") if j.payload else None,
        }
        for j in jobs
    ]
