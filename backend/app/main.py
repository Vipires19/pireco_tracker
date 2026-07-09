from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.positions import router as positions_router
from app.config import get_settings
from app.core.database import db_manager
from app.core.logging import get_logger, setup_logging
from app.domains.crm.api import router as crm_router
from app.domains.devices.api import router as devices_router
from app.domains.fleet.api import router as fleet_router
from app.domains.identity.api import router as auth_router
from app.domains.monitoring.api import router as dashboard_router
from app.domains.operations.api import router as operations_router
from app.kernel.middlewares import SecurityHeadersMiddleware
from app.observability.middleware import MetricsMiddleware
from app.seed.bootstrap import run_bootstrap
from app.services.redis import redis_service

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    settings = get_settings()
    logger.info("Starting backend service env=%s", settings.app_env)

    db_manager.init()
    await redis_service.connect()

    async for session in db_manager.get_session():
        try:
            await run_bootstrap(session)
        except Exception:
            logger.exception("Bootstrap failed — ensure migrations are applied")
        break

    yield

    await redis_service.close()
    await db_manager.close()
    logger.info("Backend service stopped")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Vehicle Tracker API",
        description="Plataforma de rastreamento veicular — API REST",
        version="0.2.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(health_router, prefix=settings.api_prefix)
    app.include_router(positions_router)
    app.include_router(positions_router, prefix=settings.api_prefix)
    app.include_router(auth_router, prefix=settings.api_prefix)
    app.include_router(crm_router, prefix=settings.api_prefix)
    app.include_router(fleet_router, prefix=settings.api_prefix)
    app.include_router(devices_router, prefix=settings.api_prefix)
    app.include_router(operations_router, prefix=settings.api_prefix)
    app.include_router(dashboard_router, prefix=settings.api_prefix)

    @app.get("/")
    async def root() -> dict:
        return {
            "service": "vehicle-tracker-backend",
            "version": "0.2.0",
            "docs": "/docs",
            "health": "/health",
        }

    return app


app = create_app()
