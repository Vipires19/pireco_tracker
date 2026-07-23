from fastapi import APIRouter

from app.domains.monitoring.api.dashboard import router as dashboard_router
from app.domains.monitoring.api.vehicles import router as vehicles_router

router = APIRouter()
router.include_router(dashboard_router)
router.include_router(vehicles_router)

__all__ = ["router"]
