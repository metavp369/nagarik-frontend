# Guardian Mode API — Live safety sharing with trusted contacts
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.api.deps import get_db_session, get_current_user
from app.models import User

router = APIRouter(prefix="/guardian", tags=["guardian"])


class LocationInput(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)


class AddGuardianRequest(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    relationship: str = "family"


class StartSessionRequest(BaseModel):
    location: LocationInput
    destination: Optional[LocationInput] = None


class UpdateLocationRequest(BaseModel):
    session_id: str
    location: LocationInput
    timestamp: Optional[str] = None


# ── Guardian CRUD ──

@router.post("/add")
async def add_guardian(
    req: AddGuardianRequest,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    from app.services.guardian_mode_engine import add_guardian as add_g
    return await add_g(session, str(user.id), req.name, req.phone, req.email, req.relationship)


@router.get("/list")
async def list_guardians(
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    from app.services.guardian_mode_engine import list_guardians as list_g
    guardians = await list_g(session, str(user.id))
    return {"guardians": guardians}


@router.delete("/remove/{guardian_id}")
async def remove_guardian(
    guardian_id: str,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    from app.services.guardian_mode_engine import remove_guardian as remove_g
    result = await remove_g(session, guardian_id)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


# ── Session Management ──

@router.post("/start")
async def start_session(
    req: StartSessionRequest,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    from app.services.guardian_mode_engine import start_session as start_s
    return await start_s(
        session, str(user.id), req.location.lat, req.location.lng,
        dest_lat=req.destination.lat if req.destination else None,
        dest_lng=req.destination.lng if req.destination else None,
    )


@router.post("/stop")
async def stop_session(
    session_id: str,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    from app.services.guardian_mode_engine import stop_session as stop_s
    result = await stop_s(session, session_id)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


@router.get("/session/{session_id}")
async def get_session(
    session_id: str,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    from app.services.guardian_mode_engine import get_session as get_s
    result = await get_s(session, session_id)
    if not result:
        raise HTTPException(404, "Session not found")
    return result


@router.get("/sessions/active")
async def list_active_sessions(
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    from app.services.guardian_mode_engine import get_active_sessions
    if user.role != "operator":
        raise HTTPException(403, "Operator access required")
    return {"sessions": await get_active_sessions(session)}


@router.get("/sessions/history")
async def get_user_history(
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    from app.services.guardian_mode_engine import get_user_sessions
    return {"sessions": await get_user_sessions(session, str(user.id))}


# ── Location Updates ──

@router.post("/update-location")
async def update_location(
    req: UpdateLocationRequest,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    from app.services.guardian_mode_engine import update_location as update_l
    ts = None
    if req.timestamp:
        try:
            ts = datetime.fromisoformat(req.timestamp.replace("Z", "+00:00"))
        except ValueError:
            pass
    result = await update_l(session, req.session_id, req.location.lat, req.location.lng, ts)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


@router.post("/acknowledge-safety")
async def acknowledge_safety(
    session_id: str,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    from app.services.guardian_mode_engine import acknowledge_safety as ack_s
    return await ack_s(session, session_id)
