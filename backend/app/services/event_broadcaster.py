# Event Broadcaster for SSE — Redis Pub/Sub backed with in-memory fallback
#
# Architecture:
#   publish() → Redis channel → _redis_listener → local asyncio queues → SSE clients
#   If Redis unavailable: publish() → local asyncio queues directly (single-process)
import asyncio
import json
import logging
import threading
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, Set
from uuid import UUID

logger = logging.getLogger(__name__)

_USER_PREFIX = "user:"
_ROLE_PREFIX = "role:"


class EventBroadcaster:
    """
    SSE event broadcaster with Redis Pub/Sub backing.
    Supports scoped channels:
      - user:{user_id}  — guardian sees their own events
      - role:operator    — operators see all events
    """

    def __init__(self):
        self._subscribers: Dict[str, Set[asyncio.Queue]] = defaultdict(set)
        self._lock = asyncio.Lock()
        self._redis_listener_started = False

    # ── Subscribe / Unsubscribe ──

    async def subscribe(self, channel: str) -> asyncio.Queue:
        queue = asyncio.Queue()
        async with self._lock:
            self._subscribers[channel].add(queue)
            logger.info(f"Subscribed to {channel}. Active: {len(self._subscribers[channel])}")
        return queue

    async def unsubscribe(self, channel: str, queue: asyncio.Queue):
        async with self._lock:
            self._subscribers[channel].discard(queue)
            if not self._subscribers[channel]:
                del self._subscribers[channel]
            logger.info(f"Unsubscribed from {channel}")

    # ── Internal: deliver to local asyncio queues ──

    async def _deliver(self, channel: str, event: dict):
        async with self._lock:
            subscribers = self._subscribers.get(channel, set()).copy()
        for queue in subscribers:
            try:
                await queue.put(event)
            except Exception as e:
                logger.error(f"Error delivering to {channel}: {e}")
        if subscribers:
            logger.info(f"Delivered {event.get('type','?')} to {len(subscribers)} on {channel}")

    # ── Publish (Redis-backed with in-memory fallback) ──

    async def _publish(self, channel: str, event_type: str, data: dict):
        event = {
            "type": event_type,
            "channel": channel,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Try Redis first (cross-process delivery)
        from app.services.redis_service import publish_event, EMERGENCY_CHANNEL
        redis_sent = publish_event(EMERGENCY_CHANNEL, event)

        if not redis_sent:
            # Fallback: deliver directly to local queues
            await self._deliver(channel, event)

    # ── Redis Listener (background thread → asyncio loop bridge) ──

    def start_redis_listener(self, loop: asyncio.AbstractEventLoop):
        """Start background thread that listens to Redis Pub/Sub and bridges to asyncio."""
        if self._redis_listener_started:
            return

        from app.services.redis_service import get_pubsub, EMERGENCY_CHANNEL
        pubsub = get_pubsub()
        if not pubsub:
            logger.info("Redis unavailable — using in-memory broadcast only")
            return

        def _listener():
            try:
                pubsub.subscribe(EMERGENCY_CHANNEL)
                logger.info(f"Redis Pub/Sub listener started on {EMERGENCY_CHANNEL}")
                for message in pubsub.listen():
                    if message["type"] != "message":
                        continue
                    try:
                        event = json.loads(message["data"])
                        channel = event.get("channel", "")
                        # Schedule delivery on the asyncio event loop
                        asyncio.run_coroutine_threadsafe(
                            self._deliver(channel, event), loop
                        )
                    except Exception as e:
                        logger.error(f"Redis listener parse error: {e}")
            except Exception as e:
                logger.error(f"Redis listener stopped: {e}")

        thread = threading.Thread(target=_listener, daemon=True, name="redis-pubsub")
        thread.start()
        self._redis_listener_started = True

    # ── Public broadcast helpers ──

    async def broadcast_to_user(self, user_id: str, event_type: str, data: dict):
        await self._publish(f"{_USER_PREFIX}{user_id}", event_type, data)

    async def broadcast_to_operators(self, event_type: str, data: dict):
        await self._publish(f"{_ROLE_PREFIX}operator", event_type, data)

    # ── Emergency-specific broadcasts ──

    async def broadcast_emergency_triggered(self, user_id: str, guardian_ids: list[str], event_data: dict):
        """SOS triggered — notify all guardians + operators."""
        for gid in guardian_ids:
            await self.broadcast_to_user(gid, "emergency_triggered", event_data)
        await self.broadcast_to_operators("emergency_triggered", event_data)

    async def broadcast_emergency_location(self, guardian_ids: list[str], event_data: dict):
        """Location update during active emergency."""
        for gid in guardian_ids:
            await self.broadcast_to_user(gid, "emergency_location_update", event_data)
        await self.broadcast_to_operators("emergency_location_update", event_data)

    async def broadcast_emergency_cancelled(self, guardian_ids: list[str], event_data: dict):
        """Emergency cancelled — notify guardians + operators."""
        for gid in guardian_ids:
            await self.broadcast_to_user(gid, "emergency_cancelled", event_data)
        await self.broadcast_to_operators("emergency_cancelled", event_data)

    async def broadcast_emergency_resolved(self, guardian_ids: list[str], event_data: dict):
        """Emergency resolved — notify guardians + operators."""
        for gid in guardian_ids:
            await self.broadcast_to_user(gid, "emergency_resolved", event_data)
        await self.broadcast_to_operators("emergency_resolved", event_data)

    # ── Incident broadcasts (existing) ──

    async def broadcast_incident_created(self, guardian_id: str, incident_data: dict):
        await self.broadcast_to_user(guardian_id, "incident_created", incident_data)
        await self.broadcast_to_operators("incident_created", incident_data)

    async def broadcast_incident_updated(self, guardian_id: str, incident_data: dict):
        await self.broadcast_to_user(guardian_id, "incident_updated", incident_data)
        await self.broadcast_to_operators("incident_updated", incident_data)

    async def broadcast_incident_escalated(self, guardian_id: str, incident_data: dict):
        await self.broadcast_to_user(guardian_id, "incident_escalated", incident_data)
        await self.broadcast_to_operators("incident_escalated", incident_data)

    # ── Channel key builders ──

    @staticmethod
    def user_channel(user_id: str) -> str:
        return f"{_USER_PREFIX}{user_id}"

    @staticmethod
    def operator_channel() -> str:
        return f"{_ROLE_PREFIX}operator"


# Global broadcaster instance
broadcaster = EventBroadcaster()


def serialize_for_sse(data: Any) -> dict:
    """Convert data to JSON-serializable format."""
    if isinstance(data, dict):
        return {k: serialize_for_sse(v) for k, v in data.items()}
    elif isinstance(data, (list, tuple)):
        return [serialize_for_sse(item) for item in data]
    elif isinstance(data, UUID):
        return str(data)
    elif isinstance(data, datetime):
        return data.isoformat()
    else:
        return data
