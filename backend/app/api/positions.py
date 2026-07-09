from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.core.database import db_manager
from app.models.entities import Position
from app.observability.metrics import DB_QUERIES

router = APIRouter(prefix="/positions", tags=["positions"])


@router.get("/latest/{imei}")
async def get_latest_position(imei: str) -> dict:
    if db_manager._session_factory is None:
        raise HTTPException(status_code=503, detail="Database not initialized")

    DB_QUERIES.labels(operation="select_latest_position").inc()

    async with db_manager._session_factory() as session:
        result = await session.execute(
            select(Position)
            .where(Position.tracker_imei == imei)
            .order_by(Position.received_at.desc())
            .limit(1)
        )
        position = result.scalar_one_or_none()

    if position is None:
        raise HTTPException(status_code=404, detail=f"No position found for IMEI {imei}")

    return {
        "tracker_imei": position.tracker_imei,
        "trace_id": position.trace_id,
        "latitude": position.latitude,
        "longitude": position.longitude,
        "speed_kmh": position.speed_kmh,
        "course_degrees": position.course_degrees,
        "gps_time": position.gps_time.isoformat() if position.gps_time else None,
        "received_at": position.received_at.isoformat(),
        "remote_ip": position.remote_ip,
    }
