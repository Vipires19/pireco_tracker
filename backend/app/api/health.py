from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from sqlalchemy import text

from app.config import get_settings
from app.core.database import db_manager
from app.observability.metrics import DB_QUERIES, metrics_payload
from app.services.redis import redis_service

router = APIRouter(tags=["health"])


async def _check_database() -> bool:
    try:
        if db_manager._session_factory is None:
            return False
        async with db_manager._session_factory() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def _check_redis() -> bool:
    try:
        return await redis_service.ping()
    except Exception:
        return False


@router.get("/health")
async def health_check() -> dict:
    settings = get_settings()
    db_ok = await _check_database()
    redis_ok = await _check_redis()
    status = "healthy" if db_ok and redis_ok else "degraded"
    return {
        "status": status,
        "service": settings.service_name,
        "environment": settings.app_env,
        "checks": {"database": "healthy" if db_ok else "unhealthy", "redis": "healthy" if redis_ok else "unhealthy"},
    }


@router.get("/ready")
async def readiness_check() -> dict:
    from fastapi import HTTPException

    db_ok = await _check_database()
    redis_ok = await _check_redis()
    if not (db_ok and redis_ok):
        raise HTTPException(
            status_code=503,
            detail={"status": "not_ready", "database": db_ok, "redis": redis_ok},
        )
    return {"status": "ready", "service": "backend"}


@router.get("/live")
async def liveness_check() -> dict:
    return {"status": "alive", "service": "backend"}


@router.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics() -> PlainTextResponse:
    return PlainTextResponse(metrics_payload().decode(), media_type="text/plain; version=0.0.4; charset=utf-8")
