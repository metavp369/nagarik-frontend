# SOS Silent Mode API — Covert emergency trigger system
import logging
import uuid
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session, get_current_user
from app.core.rbac import require_role
from app.core.rate_limiter import limiter
from app.models.user import User
from app.services import sos_service as svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sos", tags=["sos"])

_escape_role = require_role(["guardian", "operator", "admin"])


# ── Schemas ──

class SOSConfigUpdate(BaseModel):
    enabled: Optional[bool] = None
    voice_keywords: Optional[List[str]] = None
    chain_notification: Optional[bool] = None
    chain_notification_delay: Optional[int] = Field(None, ge=0, le=300)
    chain_call: Optional[bool] = None
    chain_call_delay: Optional[int] = Field(None, ge=0, le=300)
    chain_call_preset_name: Optional[str] = Field(None, max_length=120)
    chain_notification_title: Optional[str] = Field(None, max_length=200)
    chain_notification_message: Optional[str] = Field(None, max_length=500)
    trusted_contacts: Optional[List[dict]] = None
    auto_share_location: Optional[bool] = None
    silent_mode: Optional[bool] = None


class SOSTrigger(BaseModel):
    trigger_type: str = Field("manual", max_length=30)
    lat: Optional[float] = None
    lng: Optional[float] = None


class SOSCancel(BaseModel):
    resolved_by: str = Field("user", max_length=50)


# ── Config ──

@router.get("/config")
async def get_config(
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(_escape_role),
):
    config = await svc.get_or_create_config(session, user.id)
    await session.commit()
    return config


@router.put("/config")
async def update_config(
    body: SOSConfigUpdate,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(_escape_role),
):
    return await svc.update_config(session, user.id, body.model_dump(exclude_unset=True))


# ── Trigger ──

@router.post("/trigger")
@limiter.limit("10/minute")
async def trigger_sos(
    request: Request,
    body: SOSTrigger,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(_escape_role),
):
    return await svc.trigger_sos(
        session, user.id,
        trigger_type=body.trigger_type,
        lat=body.lat, lng=body.lng,
    )


# ── Cancel ──

@router.post("/cancel/{sos_id}")
async def cancel_sos(
    sos_id: str,
    body: SOSCancel,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(_escape_role),
):
    result = await svc.cancel_sos(session, user.id, uuid.UUID(sos_id), resolved_by=body.resolved_by)
    if not result:
        raise HTTPException(status_code=404, detail="SOS event not found")
    return result


# ── History ──

@router.get("/history")
async def sos_history(
    limit: int = 20,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(_escape_role),
):
    logs = await svc.get_history(session, user.id, limit)
    return {"history": logs, "count": len(logs)}
