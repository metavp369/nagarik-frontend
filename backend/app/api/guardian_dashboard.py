# Guardian Family Dashboard API
# Consumer-facing endpoints for guardians to monitor loved ones.

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session, get_current_user
from app.models.user import User

router = APIRouter(prefix="/guardian/dashboard", tags=["guardian-dashboard"])


class SafetyCheckRequest(BaseModel):
    session_id: str


@router.get("/loved-ones")
async def get_loved_ones(
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    """Get all people this guardian monitors with their live status."""
    from app.services.guardian_dashboard_engine import get_loved_ones as _get
    return await _get(session, user.email, str(user.id))


@router.get("/sessions")
async def get_sessions(
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    """Get all active sessions for guardian's loved ones."""
    from app.services.guardian_dashboard_engine import get_active_sessions
    return {"sessions": await get_active_sessions(session, user.email)}


@router.get("/alerts")
async def get_alerts(
    limit: int = 50,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    """Get recent alerts for guardian's loved ones."""
    from app.services.guardian_dashboard_engine import get_alerts as _get
    return {"alerts": await _get(session, user.email, limit)}


@router.get("/history")
async def get_history(
    limit: int = 20,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    """Get completed journey history for guardian's loved ones."""
    from app.services.guardian_dashboard_engine import get_session_history
    return {"history": await get_session_history(session, user.email, limit)}


@router.post("/request-check")
async def request_check(
    req: SafetyCheckRequest,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    """Guardian requests a safety check from a monitored user."""
    from app.services.guardian_dashboard_engine import request_safety_check
    result = await request_safety_check(session, req.session_id, user.email)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
