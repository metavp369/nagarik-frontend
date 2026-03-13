# User Service
from uuid import UUID

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserCreate

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plain password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


async def create_user(session: AsyncSession, user_create: UserCreate) -> User:
    """
    Create a new user with hashed password.
    Raises ValueError if email already exists.
    """
    # Check if email already exists
    existing = await get_user_by_email(session, user_create.email)
    if existing:
        raise ValueError(f"User with email {user_create.email} already exists")

    # Create user with hashed password
    user = User(
        email=user_create.email,
        password_hash=hash_password(user_create.password),
    )

    session.add(user)
    try:
        await session.commit()
        await session.refresh(user)
    except IntegrityError:
        await session.rollback()
        raise ValueError(f"User with email {user_create.email} already exists")

    return user


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    """Get a user by email address."""
    stmt = select(User).where(User.email == email)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: UUID) -> User | None:
    """Get a user by ID."""
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_cognito_sub(session: AsyncSession, cognito_sub: str) -> User | None:
    """Get a user by Cognito sub (external ID)."""
    stmt = select(User).where(User.cognito_sub == cognito_sub)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def auto_provision_cognito_user(
    session: AsyncSession,
    cognito_sub: str,
    email: str,
    full_name: str = None,
    phone: str = None,
    role: str = "guardian",
) -> User:
    """
    Auto-provision a local DB user for a Cognito-authenticated user.
    If user with this email exists, link the cognito_sub.
    If not, create a new user.
    """
    # Check if already linked
    existing = await get_user_by_cognito_sub(session, cognito_sub)
    if existing:
        return existing

    # Check if email already exists (link cognito_sub)
    by_email = await get_user_by_email(session, email)
    if by_email:
        by_email.cognito_sub = cognito_sub
        if full_name and not by_email.full_name:
            by_email.full_name = full_name
        await session.flush()
        return by_email

    # Create new user
    user = User(
        email=email,
        password_hash="cognito-managed",
        cognito_sub=cognito_sub,
        role=role,
        full_name=full_name,
        phone=phone,
    )
    session.add(user)
    await session.flush()
    return user
