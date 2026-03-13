# API Dependencies
import logging
from typing import Annotated, AsyncGenerator
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_token, decode_token_claims
from app.db.session import async_session
from app.models.user import User
from app.services import user_service

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database session.
    Handles commit on success, rollback on exception.
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """
    Dependency to get the current authenticated user from JWT token.
    Supports both local JWT (sub = user UUID) and Cognito JWT (sub = cognito_sub).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Verify token and extract sub
    user_id_or_sub = verify_token(token)
    if user_id_or_sub is None:
        raise credentials_exception

    # Try loading by local UUID first
    user = None
    try:
        user = await user_service.get_user_by_id(session, UUID(user_id_or_sub))
    except ValueError:
        # Not a valid UUID — might be a Cognito sub
        pass

    # If not found by UUID, try Cognito sub
    if user is None:
        user = await user_service.get_user_by_cognito_sub(session, user_id_or_sub)

    # If still not found but we have a valid Cognito token, auto-provision
    if user is None:
        from app.core.cognito import is_cognito_enabled
        if is_cognito_enabled():
            claims = decode_token_claims(token)
            if claims:
                email = claims.get("email", "")
                name = claims.get("name", "")
                cognito_sub = claims.get("sub", user_id_or_sub)
                if email:
                    user = await user_service.auto_provision_cognito_user(
                        session, cognito_sub, email, name,
                    )
                    await session.commit()
                    logger.info(f"Auto-provisioned user {email} from Cognito sub {cognito_sub}")

    if user is None:
        raise credentials_exception

    return user



def require_role(role: str):
    """Dependency factory: require the current user to have a specific role."""
    async def _check(user: User = Depends(get_current_user)) -> User:
        user_roles = []
        if hasattr(user, 'roles') and user.roles:
            user_roles = user.roles if isinstance(user.roles, list) else [user.roles]
        if hasattr(user, 'role') and user.role:
            user_roles.append(user.role)
        if role not in user_roles:
            raise HTTPException(status_code=403, detail=f"Role '{role}' required")
        return user
    return _check
