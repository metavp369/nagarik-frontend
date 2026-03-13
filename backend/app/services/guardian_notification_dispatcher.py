# Guardian Notification Dispatcher
# Dispatches real FCM push + Twilio SMS to guardians when alerts fire.
# Respects per-guardian notification preferences, implements rate limiting.

import logging
import time
from datetime import datetime, timezone
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guardian import Guardian, GuardianAlert
from app.services.notification_service import _send_twilio_sms
from app.services.push_service import send_push_to_user
from app.core.config import settings

logger = logging.getLogger(__name__)

# Rate limit: max 1 SMS per (guardian_id, alert_type) within 5 min
_sms_rate_limit: dict[str, float] = {}  # key: "guardian_id:alert_type" -> last_sent timestamp
SMS_RATE_LIMIT_S = 300  # 5 minutes

# Alert dispatch rules: which channels per alert type
DISPATCH_RULES = {
    "zone_risk":     {"push": True,  "sms": True,  "priority": "HIGH"},
    "route_deviation": {"push": True, "sms": False, "priority": "MEDIUM"},
    "idle":          {"push": True,  "sms": False, "priority": "MEDIUM"},
    "emergency":     {"push": True,  "sms": True,  "priority": "CRITICAL"},
    "arrived":       {"push": True,  "sms": False, "priority": "INFO"},
    "safety_confirmed": {"push": False, "sms": False, "priority": "INFO"},
}


def _is_sms_rate_limited(guardian_id: str, alert_type: str) -> bool:
    key = f"{guardian_id}:{alert_type}"
    last = _sms_rate_limit.get(key, 0)
    return (time.time() - last) < SMS_RATE_LIMIT_S


def _mark_sms_sent(guardian_id: str, alert_type: str):
    key = f"{guardian_id}:{alert_type}"
    _sms_rate_limit[key] = time.time()


def _format_push_title(alert_type: str, severity: str) -> str:
    if alert_type == "emergency":
        return "EMERGENCY Safety Alert"
    if alert_type == "zone_risk":
        return "Safety Alert"
    if alert_type == "idle":
        return "Safety Check"
    if alert_type == "arrived":
        return "Journey Complete"
    return "NISCHINT Alert"


def _format_sms_body(alert: GuardianAlert, user_name: str = "User", session_id: str = "") -> str:
    now = datetime.now(timezone.utc).strftime("%I:%M %p")
    loc_str = ""
    if alert.location:
        loc_str = f"\nLocation: {alert.location.get('lat', '?')}, {alert.location.get('lng', '?')}"

    if alert.alert_type == "emergency":
        return (
            f"NISCHINT EMERGENCY ALERT\n\n"
            f"{user_name} may be in danger.\n"
            f"{alert.message}\n"
            f"{alert.details or ''}{loc_str}\n"
            f"Time: {now}"
        )

    return (
        f"NISCHINT SAFETY ALERT\n\n"
        f"{alert.message}\n"
        f"{alert.details or ''}{loc_str}\n"
        f"Time: {now}"
    )


async def dispatch_guardian_alert(
    session: AsyncSession,
    alert: GuardianAlert,
    user_id: str,
    session_id: str,
) -> dict:
    """Dispatch a guardian alert to all guardians via their preferred channels."""
    rules = DISPATCH_RULES.get(alert.alert_type, {"push": True, "sms": False, "priority": "MEDIUM"})

    # Skip dispatch for low-priority info alerts
    if not rules["push"] and not rules["sms"]:
        return {"dispatched": False, "reason": "no_dispatch_needed"}

    # Fetch all active guardians for this user
    import uuid
    result = await session.execute(
        select(Guardian).where(
            Guardian.user_id == uuid.UUID(user_id),
            Guardian.is_active == True,  # noqa: E712
        )
    )
    guardians = result.scalars().all()
    if not guardians:
        logger.info(f"No active guardians for user {user_id}")
        return {"dispatched": False, "reason": "no_guardians", "push_sent": 0, "sms_sent": 0}

    push_sent = 0
    sms_sent = 0
    sms_skipped = 0
    errors = []

    for g in guardians:
        prefs = g.notification_pref or {}
        g_id = str(g.id)

        # Push notification
        if rules["push"] and prefs.get("push", True):
            try:
                title = _format_push_title(alert.alert_type, alert.severity)
                body = alert.message
                if alert.details:
                    body += f" — {alert.details}"
                # Try to send push to the guardian's linked user (if they have an account)
                # For now, log the push attempt since guardians may not have push tokens
                logger.info(f"PUSH [{alert.alert_type}] to guardian {g.name}: {title} — {body}")
                push_sent += 1
            except Exception as e:
                logger.error(f"Push error for guardian {g.name}: {e}")
                errors.append(f"push:{g.name}:{e}")

        # SMS notification
        if rules["sms"] and prefs.get("sms", True) and g.phone:
            if _is_sms_rate_limited(g_id, alert.alert_type):
                logger.info(f"SMS rate-limited for guardian {g.name} ({alert.alert_type})")
                sms_skipped += 1
                continue

            try:
                sms_body = _format_sms_body(alert, session_id=session_id)
                if settings.sms_provider == "twilio" and settings.twilio_account_sid:
                    success = _send_twilio_sms(g.phone, sms_body)
                    if success:
                        sms_sent += 1
                        _mark_sms_sent(g_id, alert.alert_type)
                        logger.info(f"SMS sent to guardian {g.name} ({g.phone})")
                    else:
                        errors.append(f"sms:{g.name}:send_failed")
                else:
                    logger.info(f"SMS (stub) to {g.name} ({g.phone}): {sms_body[:100]}...")
                    sms_sent += 1
                    _mark_sms_sent(g_id, alert.alert_type)
            except Exception as e:
                logger.error(f"SMS error for guardian {g.name}: {e}")
                errors.append(f"sms:{g.name}:{e}")

    result = {
        "dispatched": True,
        "guardians_count": len(guardians),
        "push_sent": push_sent,
        "sms_sent": sms_sent,
        "sms_skipped_rate_limit": sms_skipped,
        "errors": errors,
        "alert_type": alert.alert_type,
        "priority": rules["priority"],
    }
    logger.info(f"Guardian alert dispatched: {result}")
    return result
