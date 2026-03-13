# Guardian Mode Models
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, JSON, ForeignKey, Text, Integer, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Guardian(Base):
    __tablename__ = "guardians"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    relationship: Mapped[str] = mapped_column(String(100), default="family", nullable=False)
    notification_pref: Mapped[dict] = mapped_column(type_=JSON, default=lambda: {"push": True, "sms": True, "email": True}, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class GuardianSession(Base):
    __tablename__ = "guardian_sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    destination: Mapped[dict | None] = mapped_column(type_=JSON, nullable=True)
    route_points: Mapped[dict | None] = mapped_column(type_=JSON, nullable=True)
    current_location: Mapped[dict | None] = mapped_column(type_=JSON, nullable=True)
    previous_location: Mapped[dict | None] = mapped_column(type_=JSON, nullable=True)
    previous_update_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    zone_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    risk_level: Mapped[str] = mapped_column(String(20), default="SAFE", nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    zone_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    eta_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
    speed_mps: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_distance_m: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    location_updates: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    escalation_level: Mapped[str] = mapped_column(String(20), default="none", nullable=False)
    is_night: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    route_deviated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    route_deviation_m: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_idle: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    idle_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    idle_duration_s: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    alert_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_alert_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    safety_check_pending: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    safety_check_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GuardianAlert(Base):
    __tablename__ = "guardian_alerts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("guardian_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[dict | None] = mapped_column(type_=JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
