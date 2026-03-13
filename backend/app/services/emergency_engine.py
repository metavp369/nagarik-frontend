# Emergency Engine — Silent SOS backend logic
#
# Flow: Trigger → Create Event → Notify Guardians (instant) → Track Location
# User gets cancel window AFTER guardians are notified.

import hashlib
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.emergency import EmergencyEvent
from app.models.guardian import Guardian
from app.services.redis_service import set_json, get_json, delete_key
from app.services.event_broadcaster import broadcaster

logger = logging.getLogger(__name__)


# ── SOS Trigger (immediate) ──

async def trigger_silent_sos(
    session: AsyncSession,
    user_id: str,
    lat: float,
    lng: float,
    trigger_source: str,
    cancel_pin: str | None = None,
    device_metadata: dict | None = None,
) -> dict:
    """
    Create emergency event and notify guardians IMMEDIATELY.
    Cancel window is client-side — guardians are alerted instantly.
    """
    now = datetime.now(timezone.utc)

    # Hash the cancel PIN if provided
    pin_hash = None
    if cancel_pin:
        pin_hash = hashlib.sha256(cancel_pin.encode()).hexdigest()

    # Create emergency event
    event = EmergencyEvent(
        user_id=uuid.UUID(user_id),
        lat=lat,
        lng=lng,
        trigger_source=trigger_source,
        severity_level=2,  # distress
        status="active",
        cancel_pin_hash=pin_hash,
        location_trail=[{"lat": lat, "lng": lng, "ts": now.isoformat()}],
        guardians_notified=0,
        metadata_json=device_metadata,
    )
    session.add(event)
    await session.flush()

    event_id = str(event.id)

    # Notify guardians immediately (push + SMS)
    notified = await _notify_guardians(session, user_id, event_id, lat, lng, trigger_source, now)

    # Update notification count
    event.guardians_notified = notified
    await session.flush()

    # Store in Redis for fast access
    event_data = {
        "event_id": event_id,
        "user_id": user_id,
        "lat": lat,
        "lng": lng,
        "trigger_source": trigger_source,
        "severity_level": 2,
        "status": "active",
        "guardians_notified": notified,
        "created_at": now.isoformat(),
        "location_trail": [{"lat": lat, "lng": lng, "ts": now.isoformat()}],
    }
    set_json("emergency", event_id, event_data)  # No TTL — stays until resolved
    _update_active_list(user_id, event_id, "add")

    logger.info(f"SILENT SOS triggered: event={event_id}, user={user_id}, trigger={trigger_source}, notified={notified}")

    # Live risk assessment — ALWAYS bypass cache during active emergency (safety rule)
    from app.services.redis_service import invalidate_forecast_grid
    invalidate_forecast_grid(lat, lng)  # Clear stale forecast for this cell

    # Broadcast to operators + user via SSE (Redis Pub/Sub backed)
    # Guardians are notified via SMS/push (already handled above)
    await broadcaster.broadcast_to_operators("emergency_triggered", {
        "event": "SOS_TRIGGERED",
        "event_id": event_id,
        "user_id": user_id,
        "lat": lat,
        "lng": lng,
        "trigger_source": trigger_source,
        "severity_level": 2,
        "guardians_notified": notified,
    })
    await broadcaster.broadcast_to_user(user_id, "emergency_triggered", {
        "event": "SOS_TRIGGERED",
        "event_id": event_id,
    })

    return {
        "event_id": event_id,
        "status": "active",
        "severity_level": 2,
        "guardians_notified": notified,
        "created_at": now.isoformat(),
        "message": "Emergency alert sent to guardians immediately.",
    }


# ── Location Update (every 5s during emergency) ──

async def update_emergency_location(
    session: AsyncSession,
    event_id: str,
    lat: float,
    lng: float,
) -> dict:
    """Append location to emergency trail. Updates both DB and Redis."""
    now = datetime.now(timezone.utc)

    result = await session.execute(
        select(EmergencyEvent).where(EmergencyEvent.id == uuid.UUID(event_id))
    )
    event = result.scalar_one_or_none()
    if not event:
        return {"error": "Emergency event not found"}
    if event.status != "active":
        return {"error": f"Event is {event.status}, not active"}

    # Append to trail
    trail = list(event.location_trail or [])
    trail.append({"lat": lat, "lng": lng, "ts": now.isoformat()})
    event.location_trail = trail
    event.lat = lat
    event.lng = lng
    await session.flush()

    # Update Redis
    cached = get_json("emergency", event_id)
    if cached:
        cached["lat"] = lat
        cached["lng"] = lng
        cached["location_trail"] = trail
        set_json("emergency", event_id, cached)

    # Broadcast location update to operators
    user_id = str(event.user_id)
    await broadcaster.broadcast_to_operators("emergency_location_update", {
        "event": "LOCATION_UPDATE",
        "event_id": event_id,
        "user_id": user_id,
        "lat": lat,
        "lng": lng,
        "location_updates": len(trail),
    })

    return {
        "event_id": event_id,
        "status": "active",
        "location_updates": len(trail),
        "latest": {"lat": lat, "lng": lng, "ts": now.isoformat()},
    }


# ── Cancel SOS (requires PIN) ──

async def cancel_emergency(
    session: AsyncSession,
    event_id: str,
    cancel_pin: str,
) -> dict:
    """Cancel SOS. Requires correct PIN to prevent attacker cancellation."""
    result = await session.execute(
        select(EmergencyEvent).where(EmergencyEvent.id == uuid.UUID(event_id))
    )
    event = result.scalar_one_or_none()
    if not event:
        return {"error": "Emergency event not found"}
    if event.status != "active":
        return {"error": f"Event is already {event.status}"}

    # Verify PIN
    if event.cancel_pin_hash:
        pin_hash = hashlib.sha256(cancel_pin.encode()).hexdigest()
        if pin_hash != event.cancel_pin_hash:
            return {"error": "Invalid cancellation PIN"}

    now = datetime.now(timezone.utc)
    event.status = "cancelled"
    event.resolved_at = now
    await session.flush()

    # Clean up Redis
    delete_key("emergency", event_id)
    _update_active_list(str(event.user_id), event_id, "remove")

    # Notify guardians of cancellation
    await _notify_guardians_cancel(session, str(event.user_id), event_id)

    logger.info(f"Emergency CANCELLED: event={event_id}")

    # Broadcast cancellation via SSE
    user_id = str(event.user_id)
    await broadcaster.broadcast_to_operators("emergency_cancelled", {
        "event": "SOS_CANCELLED",
        "event_id": event_id,
        "user_id": user_id,
        "resolved_at": now.isoformat(),
    })

    return {
        "event_id": event_id,
        "status": "cancelled",
        "resolved_at": now.isoformat(),
        "message": "Emergency cancelled. Guardians have been notified.",
    }


# ── Resolve SOS (by guardian or system) ──

async def resolve_emergency(
    session: AsyncSession,
    event_id: str,
) -> dict:
    """Mark emergency as resolved."""
    result = await session.execute(
        select(EmergencyEvent).where(EmergencyEvent.id == uuid.UUID(event_id))
    )
    event = result.scalar_one_or_none()
    if not event:
        return {"error": "Emergency event not found"}

    now = datetime.now(timezone.utc)
    event.status = "resolved"
    event.resolved_at = now
    await session.flush()

    delete_key("emergency", event_id)
    _update_active_list(str(event.user_id), event_id, "remove")

    logger.info(f"Emergency RESOLVED: event={event_id}")

    # Broadcast resolution via SSE
    user_id = str(event.user_id)
    await broadcaster.broadcast_to_operators("emergency_resolved", {
        "event": "SOS_RESOLVED",
        "event_id": event_id,
        "user_id": user_id,
        "resolved_at": now.isoformat(),
    })

    return {
        "event_id": event_id,
        "status": "resolved",
        "resolved_at": now.isoformat(),
        "duration_seconds": round((now - event.created_at).total_seconds()),
        "location_updates": len(event.location_trail or []),
    }


# ── Get Active Emergencies ──

async def get_active_emergencies(
    session: AsyncSession,
    user_id: str | None = None,
) -> list[dict]:
    """Get all active emergencies, optionally filtered by user."""
    query = select(EmergencyEvent).where(EmergencyEvent.status == "active")
    if user_id:
        query = query.where(EmergencyEvent.user_id == uuid.UUID(user_id))
    query = query.order_by(EmergencyEvent.created_at.desc())

    result = await session.execute(query)
    events = []
    for e in result.scalars().all():
        events.append({
            "event_id": str(e.id),
            "user_id": str(e.user_id),
            "lat": e.lat,
            "lng": e.lng,
            "trigger_source": e.trigger_source,
            "severity_level": e.severity_level,
            "status": e.status,
            "guardians_notified": e.guardians_notified,
            "location_updates": len(e.location_trail or []),
            "created_at": e.created_at.isoformat(),
        })
    return events


# ── Get Emergency Details ──

async def get_emergency_details(
    session: AsyncSession,
    event_id: str,
) -> dict:
    """Get full emergency details including location trail."""
    # Try Redis first for active events
    cached = get_json("emergency", event_id)
    if cached and cached.get("status") == "active":
        return cached

    # Fall back to DB
    result = await session.execute(
        select(EmergencyEvent).where(EmergencyEvent.id == uuid.UUID(event_id))
    )
    event = result.scalar_one_or_none()
    if not event:
        return {"error": "Emergency event not found"}

    return {
        "event_id": str(event.id),
        "user_id": str(event.user_id),
        "lat": event.lat,
        "lng": event.lng,
        "trigger_source": event.trigger_source,
        "severity_level": event.severity_level,
        "status": event.status,
        "guardians_notified": event.guardians_notified,
        "location_trail": event.location_trail or [],
        "created_at": event.created_at.isoformat(),
        "resolved_at": event.resolved_at.isoformat() if event.resolved_at else None,
        "metadata": event.metadata_json,
    }


# ── Internal: Guardian Notification ──

async def _notify_guardians(
    session: AsyncSession,
    user_id: str,
    event_id: str,
    lat: float,
    lng: float,
    trigger_source: str,
    timestamp: datetime,
) -> int:
    """Send push + SMS to all linked guardians. Returns count notified."""
    result = await session.execute(
        select(Guardian).where(
            Guardian.user_id == uuid.UUID(user_id),
            Guardian.is_active.is_(True),
        )
    )
    guardians = result.scalars().all()

    if not guardians:
        logger.warning(f"No guardians found for user {user_id}")
        return 0

    notified = 0
    for g in guardians:
        try:
            # Push notification
            prefs = g.notification_pref or {}
            if prefs.get("push", True):
                try:
                    from app.services.notification_service import send_push_notification
                    await send_push_notification(
                        user_id=str(g.user_id),
                        title="SILENT SOS ALERT",
                        body=f"{g.name or 'Your loved one'} triggered Silent SOS. Location tracking active.",
                        data={
                            "type": "emergency_sos",
                            "event_id": event_id,
                            "lat": str(lat),
                            "lng": str(lng),
                        },
                    )
                except Exception as push_err:
                    logger.warning(f"Push failed for guardian {g.id}: {push_err}")

            # SMS fallback
            if prefs.get("sms", True) and g.phone:
                try:
                    from app.services.notification_service import send_sms
                    time_str = timestamp.strftime("%I:%M %p")
                    await send_sms(
                        to=g.phone,
                        body=(
                            f"NISCHINT EMERGENCY: Silent SOS triggered at {time_str}. "
                            f"Location: {lat:.4f},{lng:.4f}. "
                            f"Live tracking active. Check app immediately."
                        ),
                    )
                except Exception as sms_err:
                    logger.warning(f"SMS failed for guardian {g.id}: {sms_err}")

            notified += 1
        except Exception as e:
            logger.error(f"Failed to notify guardian {g.id}: {e}")

    logger.info(f"Emergency {event_id}: notified {notified}/{len(guardians)} guardians")
    return notified


async def _notify_guardians_cancel(session: AsyncSession, user_id: str, event_id: str):
    """Notify guardians that the emergency was cancelled."""
    result = await session.execute(
        select(Guardian).where(
            Guardian.user_id == uuid.UUID(user_id),
            Guardian.is_active.is_(True),
        )
    )
    for g in result.scalars().all():
        try:
            from app.services.notification_service import send_push_notification
            await send_push_notification(
                user_id=str(g.user_id),
                title="Emergency Cancelled",
                body="The Silent SOS alert has been cancelled. User is safe.",
                data={"type": "emergency_cancelled", "event_id": event_id},
            )
        except Exception:
            pass


# ── Redis Active List Management ──

def _update_active_list(user_id: str, event_id: str, action: str):
    """Maintain a Redis list of active emergency event IDs per user."""
    key_data = get_json("emergency", "active") or {}
    user_events = key_data.get(user_id, [])

    if action == "add" and event_id not in user_events:
        user_events.append(event_id)
    elif action == "remove" and event_id in user_events:
        user_events.remove(event_id)

    key_data[user_id] = user_events
    set_json("emergency", "active", key_data)  # No TTL
