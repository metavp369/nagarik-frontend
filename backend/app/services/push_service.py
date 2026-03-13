# Push Notification Service (FCM via HTTP v1)
import json
import logging
from uuid import UUID

import google.auth.transport.requests
from google.oauth2 import service_account
import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger(__name__)

FCM_SCOPES = ["https://www.googleapis.com/auth/firebase.messaging"]
_credentials = None


def _get_credentials():
    global _credentials
    if _credentials is None:
        sa_path = settings.firebase_sa_key_path
        if sa_path and __import__("os").path.exists(sa_path):
            _credentials = service_account.Credentials.from_service_account_file(
                sa_path, scopes=FCM_SCOPES
            )
        else:
            sa_json = settings.firebase_sa_key_json
            if sa_json:
                info = json.loads(sa_json)
                _credentials = service_account.Credentials.from_service_account_info(
                    info, scopes=FCM_SCOPES
                )
    return _credentials


def _get_access_token() -> str:
    creds = _get_credentials()
    if creds is None:
        raise RuntimeError("Firebase service account not configured")
    request = google.auth.transport.requests.Request()
    creds.refresh(request)
    return creds.token


async def get_user_push_tokens(session: AsyncSession, user_id: UUID) -> list[str]:
    result = await session.execute(
        text("SELECT token FROM push_tokens WHERE user_id = :uid"),
        {"uid": user_id},
    )
    return [row[0] for row in result.fetchall()]


async def send_push_to_user(
    session: AsyncSession,
    user_id: UUID,
    title: str,
    body: str,
) -> int:
    """Send push notification to all devices of a user. Returns count sent."""
    tokens = await get_user_push_tokens(session, user_id)
    if not tokens:
        logger.info(f"No push tokens for user {user_id}, skipping push")
        return 0

    project_id = settings.firebase_project_id
    url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"

    try:
        access_token = _get_access_token()
    except Exception as e:
        logger.error(f"Failed to get FCM access token: {e}")
        return 0

    sent = 0
    async with httpx.AsyncClient() as client:
        for token in tokens:
            payload = {
                "message": {
                    "token": token,
                    "notification": {"title": title, "body": body},
                    "webpush": {
                        "notification": {
                            "icon": "/logo192.png",
                            "requireInteraction": True,
                            "tag": "nischint-escalation",
                        }
                    },
                }
            }
            try:
                resp = await client.post(
                    url,
                    json=payload,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if resp.status_code == 200:
                    logger.info(f"FCM push sent to token ...{token[-8:]}")
                    sent += 1
                else:
                    logger.warning(f"FCM error {resp.status_code}: {resp.text}")
            except Exception as e:
                logger.error(f"FCM send error: {e}")

    return sent
