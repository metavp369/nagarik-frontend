"""
Notification Service — Centralized push notification dispatch.
Handles FCM push, in-app alerts, and notification history.
"""
import os
import json
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Singleton Firebase init flag
_firebase_initialized = False


class NotificationService:
    """Centralized notification dispatcher for Nischint Safety Platform."""

    def __init__(self, db_session_factory):
        self.db = db_session_factory
        self.fcm_available = False
        self._init_fcm()

    def _init_fcm(self):
        """Initialize Firebase Admin SDK if credentials are available."""
        global _firebase_initialized
        try:
            import firebase_admin
            from firebase_admin import credentials

            # Ensure .env is loaded
            try:
                from dotenv import load_dotenv
                from pathlib import Path
                load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
            except Exception:
                pass

            # Check both env var names for backwards compat
            cred_path = os.environ.get("FIREBASE_SA_KEY_PATH") or os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH")
            cred_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")

            if cred_path and os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
            elif cred_json:
                cred = credentials.Certificate(json.loads(cred_json))
            else:
                logger.info("FCM credentials not configured — push notifications disabled")
                return

            if not firebase_admin._apps and not _firebase_initialized:
                firebase_admin.initialize_app(cred)
                _firebase_initialized = True

            self.fcm_available = True
            logger.info("FCM initialized successfully — push notifications ACTIVE")
        except ImportError:
            logger.info("firebase-admin not installed — push notifications disabled")
        except Exception as e:
            logger.warning(f"FCM init failed: {e}")

    async def get_device_tokens(self, user_id: str) -> list:
        """Get all registered device tokens for a user."""
        from sqlalchemy import text
        async with self.db() as session:
            result = await session.execute(
                text("SELECT device_token, device_type FROM device_tokens WHERE user_id = :uid AND is_active = true"),
                {"uid": user_id}
            )
            return [{"token": r[0], "type": r[1]} for r in result.fetchall()]

    async def send_push(self, user_id: str, title: str, body: str,
                        data: Optional[dict] = None, tag: str = "nischint-alert",
                        url: str = "/m/home"):
        """Send push notification to all user devices via FCM."""
        tokens = await self.get_device_tokens(user_id)
        if not tokens:
            logger.debug(f"No device tokens for user {user_id}")
            return {"sent": 0, "reason": "no_tokens"}

        # Store notification in DB
        await self._store_notification(user_id, title, body, data, tag)

        if not self.fcm_available:
            logger.info(f"FCM unavailable — notification stored but not pushed: {title}")
            return {"sent": 0, "stored": True, "reason": "fcm_unavailable"}

        # Ensure all data values are strings (FCM requirement)
        fcm_data = {"tag": tag, "url": url}
        for k, v in (data or {}).items():
            fcm_data[k] = str(v)

        # Build absolute URL for webpush link
        base_url = os.environ.get("CORS_ORIGINS", os.environ.get("APP_BASE_URL", "")).split(",")[0].strip()

        sent = 0
        failed_tokens = []
        try:
            from firebase_admin import messaging

            for device in tokens:
                try:
                    webpush_config = messaging.WebpushConfig(
                        notification=messaging.WebpushNotification(
                            title=title,
                            body=body,
                            icon="/icons/icon-192.png",
                            badge="/icons/icon-192.png",
                            tag=tag,
                            require_interaction=tag == "nischint-sos",
                        ),
                    )
                    # Only set fcm_options.link if we have a valid HTTPS base URL
                    if base_url and base_url.startswith("https://"):
                        webpush_config = messaging.WebpushConfig(
                            notification=messaging.WebpushNotification(
                                title=title,
                                body=body,
                                icon="/icons/icon-192.png",
                                badge="/icons/icon-192.png",
                                tag=tag,
                                require_interaction=tag == "nischint-sos",
                            ),
                            fcm_options=messaging.WebpushFCMOptions(
                                link=f"{base_url}{url}",
                            ),
                        )

                    message = messaging.Message(
                        notification=messaging.Notification(title=title, body=body),
                        data=fcm_data,
                        token=device["token"],
                        webpush=webpush_config,
                        android=messaging.AndroidConfig(
                            priority="high",
                            notification=messaging.AndroidNotification(
                                sound="default",
                                click_action="OPEN_NISCHINT",
                            ),
                        ),
                        apns=messaging.APNSConfig(
                            payload=messaging.APNSPayload(
                                aps=messaging.Aps(sound="default", badge=1),
                            ),
                        ),
                    )
                    messaging.send(message)
                    sent += 1
                    logger.info(f"FCM push sent to {user_id}: {title}")
                except Exception as e:
                    err_str = str(e)
                    if "not found" in err_str.lower() or "not a valid" in err_str.lower() or "invalid-registration" in err_str.lower():
                        failed_tokens.append(device["token"])
                        logger.debug(f"Invalid FCM token for {user_id}, deactivating")
                    else:
                        logger.warning(f"FCM send error for {user_id}: {e}")

        except Exception as e:
            logger.error(f"FCM messaging error: {e}")

        # Deactivate invalid tokens
        if failed_tokens:
            await self._deactivate_tokens(failed_tokens)

        return {"sent": sent, "failed": len(failed_tokens)}

    async def send_sos_notification(self, user_id: str, user_name: str,
                                     location: Optional[dict] = None,
                                     guardian_ids: list = None):
        """Send SOS alert to all guardians."""
        loc_str = ""
        if location and location.get("lat"):
            loc_str = f"\nLocation: {location['lat']:.4f}, {location['lng']:.4f}"

        for gid in (guardian_ids or []):
            await self.send_push(
                user_id=gid,
                title="SOS EMERGENCY ALERT",
                body=f"{user_name} triggered SOS{loc_str}\nTap to view live tracking",
                data={"type": "sos", "source_user": user_id},
                tag="nischint-sos",
                url="/m/home",
            )

    async def send_risk_alert(self, user_id: str, user_name: str,
                               risk_level: str, guardian_ids: list = None):
        """Send risk level spike alert to guardians."""
        for gid in (guardian_ids or []):
            await self.send_push(
                user_id=gid,
                title=f"Risk Level {risk_level.upper()} — {user_name}",
                body=f"Risk level elevated to {risk_level.upper()} for {user_name}.\nTap to view details.",
                data={"type": "risk_alert", "risk_level": risk_level},
                tag="nischint-risk",
                url="/m/home",
            )

    async def send_guardian_alert(self, guardian_id: str, alert_type: str,
                                   message: str):
        """Send generic guardian notification."""
        await self.send_push(
            user_id=guardian_id,
            title=f"Nischint: {alert_type.replace('_', ' ').title()}",
            body=message,
            data={"type": "guardian_alert", "alert_type": alert_type},
            tag="nischint-guardian",
        )

    async def send_session_alert(self, user_id: str, session_event: str,
                                  details: str = "", guardian_ids: list = None):
        """Send session-related notification (start, end, deviation)."""
        titles = {
            "started": "Safety Session Started",
            "ended": "Safety Session Ended",
            "deviation": "Route Deviation Detected",
            "alert": "Session Safety Alert",
        }
        for gid in (guardian_ids or []):
            await self.send_push(
                user_id=gid,
                title=titles.get(session_event, "Session Update"),
                body=details or f"Session event: {session_event}",
                data={"type": "session", "event": session_event},
                tag="nischint-session",
                url="/m/live",
            )

    async def send_incident_alert(self, incident_type: str, user_name: str,
                                   location: Optional[dict] = None,
                                   guardian_ids: list = None):
        """Send incident notification (push + stored) to guardians."""
        loc_str = ""
        if location and location.get("lat"):
            loc_str = f" near ({location['lat']:.4f}, {location['lng']:.4f})"

        for gid in (guardian_ids or []):
            await self.send_push(
                user_id=gid,
                title=f"Incident: {incident_type.replace('_', ' ').title()}",
                body=f"{user_name} — {incident_type} detected{loc_str}. Tap to view.",
                data={"type": "incident", "incident_type": incident_type},
                tag="nischint-incident",
                url="/m/alerts",
            )

    async def send_invite_notification(self, guardian_id: str, inviter_name: str):
        """Push notification when someone invites you as guardian."""
        await self.send_push(
            user_id=guardian_id,
            title="Guardian Invite Received",
            body=f"{inviter_name} added you as a guardian on Nischint. Tap to accept.",
            data={"type": "guardian_invite"},
            tag="nischint-invite",
            url="/m/guardians",
        )

    async def _store_notification(self, user_id: str, title: str, body: str,
                                   data: Optional[dict], tag: str):
        """Store notification in database for history."""
        from sqlalchemy import text
        try:
            async with self.db() as session:
                await session.execute(
                    text("""
                        INSERT INTO push_notifications (user_id, title, body, data, tag, created_at, is_read)
                        VALUES (:uid, :title, :body, :data, :tag, :created_at, false)
                    """),
                    {
                        "uid": user_id,
                        "title": title,
                        "body": body,
                        "data": json.dumps(data or {}),
                        "tag": tag,
                        "created_at": datetime.now(timezone.utc),
                    }
                )
                await session.commit()
        except Exception as e:
            logger.debug(f"Notification storage skipped (table may not exist): {e}")

    async def _deactivate_tokens(self, tokens: list):
        """Mark invalid device tokens as inactive."""
        from sqlalchemy import text
        try:
            async with self.db() as session:
                for token in tokens:
                    await session.execute(
                        text("UPDATE device_tokens SET is_active = false WHERE device_token = :t"),
                        {"t": token}
                    )
                await session.commit()
        except Exception:
            pass
