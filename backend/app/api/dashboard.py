# Dashboard Router
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session, get_current_user
from app.models.user import User
from app.schemas.dashboard import GuardianSummary
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=GuardianSummary)
async def get_guardian_summary(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get aggregated dashboard summary for the logged-in guardian.
    
    Returns counts for:
    - total_seniors
    - total_devices
    - active_incidents (open status)
    - critical_incidents (critical severity + open)
    - devices_online
    - devices_offline
    """
    summary = await dashboard_service.get_guardian_summary(session, current_user.id)
    return summary


@router.get("/sla")
async def get_sla_metrics(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Get SLA metrics (avg acknowledgment time, avg resolution time) for the guardian."""
    return await dashboard_service.get_sla_metrics(session, current_user.id)
