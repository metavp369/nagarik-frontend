# Push Token Router
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.api.deps import get_db_session, get_current_user
from app.models.user import User

router = APIRouter(prefix="/push", tags=["push"])


class PushTokenRequest(BaseModel):
    token: str


@router.post("/token", status_code=status.HTTP_201_CREATED)
async def register_push_token(
    body: PushTokenRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Register an FCM push token for the current user."""
    await session.execute(
        __import__("sqlalchemy").text(
            "INSERT INTO push_tokens (user_id, token) VALUES (:uid, :tok) "
            "ON CONFLICT (user_id, token) DO NOTHING"
        ),
        {"uid": current_user.id, "tok": body.token},
    )
    await session.commit()
    return {"status": "registered"}
