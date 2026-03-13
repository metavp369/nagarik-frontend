# Monitoring API — Real-time platform metrics and alerts for admin dashboard
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.rbac import require_role
from app.models.guardian import GuardianSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/monitoring", tags=["monitoring"])
_admin_role = require_role(["admin"])


@router.get("/metrics", dependencies=[Depends(_admin_role)])
async def get_monitoring_metrics(session: AsyncSession = Depends(get_db_session)):
    """Get comprehensive platform monitoring metrics."""
    from app.services.monitoring_service import get_metrics

    metrics = get_metrics()

    # Add live DB query: active guardian sessions
    result = await session.execute(
        select(func.count()).select_from(GuardianSession).where(
            GuardianSession.status == "active"
        )
    )
    active_sessions = result.scalar() or 0
    metrics["guardian_sessions"] = {"active": active_sessions}

    return metrics


@router.get("/alerts", dependencies=[Depends(_admin_role)])
async def get_monitoring_alerts(limit: int = Query(50, ge=1, le=200)):
    """Get recent monitoring alerts."""
    from app.services.monitoring_service import get_alerts
    return {"alerts": get_alerts(limit)}


@router.get("/queue-health", dependencies=[Depends(_admin_role)])
async def get_queue_health():
    """Get Redis queue health metrics."""
    try:
        from app.services.queue_service import get_queue_stats
        return get_queue_stats()
    except ImportError:
        return {"status": "queue_service_not_loaded", "queues": {}}
