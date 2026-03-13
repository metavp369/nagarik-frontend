# Dashboard Service
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.senior import Senior
from app.models.device import Device
from app.models.incident import Incident


async def get_guardian_summary(
    session: AsyncSession,
    guardian_id: UUID,
) -> dict:
    """
    Get aggregated dashboard summary for a guardian.
    
    Returns:
        dict with total_seniors, total_devices, active_incidents,
        critical_incidents, devices_online, devices_offline
    """
    # Get senior IDs for this guardian
    senior_stmt = select(Senior.id).where(Senior.guardian_id == guardian_id)
    senior_result = await session.execute(senior_stmt)
    senior_ids = [row[0] for row in senior_result.fetchall()]
    
    total_seniors = len(senior_ids)
    
    if not senior_ids:
        return {
            "total_seniors": 0,
            "total_devices": 0,
            "active_incidents": 0,
            "critical_incidents": 0,
            "devices_online": 0,
            "devices_offline": 0,
        }
    
    # Count devices by status
    device_counts = await session.execute(
        select(
            Device.status,
            func.count(Device.id)
        )
        .where(Device.senior_id.in_(senior_ids))
        .group_by(Device.status)
    )
    device_status_map = {row[0]: row[1] for row in device_counts.fetchall()}
    
    total_devices = sum(device_status_map.values())
    devices_online = device_status_map.get("online", 0)
    devices_offline = device_status_map.get("offline", 0)
    
    # Count active incidents
    active_incidents_result = await session.execute(
        select(func.count(Incident.id))
        .where(Incident.senior_id.in_(senior_ids))
        .where(Incident.status == "open")
    )
    active_incidents = active_incidents_result.scalar() or 0
    
    # Count critical incidents
    critical_incidents_result = await session.execute(
        select(func.count(Incident.id))
        .where(Incident.senior_id.in_(senior_ids))
        .where(Incident.status == "open")
        .where(Incident.severity == "critical")
    )
    critical_incidents = critical_incidents_result.scalar() or 0
    
    return {
        "total_seniors": total_seniors,
        "total_devices": total_devices,
        "active_incidents": active_incidents,
        "critical_incidents": critical_incidents,
        "devices_online": devices_online,
        "devices_offline": devices_offline,
    }


async def get_sla_metrics(
    session: AsyncSession,
    guardian_id: UUID,
) -> dict:
    """Compute SLA metrics for a guardian's incidents."""
    senior_stmt = select(Senior.id).where(Senior.guardian_id == guardian_id)
    senior_result = await session.execute(senior_stmt)
    senior_ids = [row[0] for row in senior_result.fetchall()]

    if not senior_ids:
        return {
            "total_incidents": 0,
            "acknowledged_count": 0,
            "resolved_count": 0,
            "avg_time_to_ack_seconds": None,
            "avg_time_to_resolve_seconds": None,
        }

    result = await session.execute(
        select(Incident).where(Incident.senior_id.in_(senior_ids))
    )
    incidents = result.scalars().all()

    acknowledged = [i for i in incidents if i.acknowledged_at]
    resolved = [i for i in incidents if i.resolved_at]

    avg_ack = None
    avg_resolve = None

    if acknowledged:
        avg_ack = sum(
            (i.acknowledged_at - i.created_at).total_seconds()
            for i in acknowledged
        ) / len(acknowledged)

    if resolved:
        avg_resolve = sum(
            (i.resolved_at - i.created_at).total_seconds()
            for i in resolved
        ) / len(resolved)

    return {
        "total_incidents": len(incidents),
        "acknowledged_count": len(acknowledged),
        "resolved_count": len(resolved),
        "avg_time_to_ack_seconds": round(avg_ack, 2) if avg_ack else None,
        "avg_time_to_resolve_seconds": round(avg_resolve, 2) if avg_resolve else None,
    }
