from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends

from app.domains.crm.models import Customer
from app.domains.devices.health import count_tracker_health
from app.domains.fleet.models import Vehicle
from app.domains.identity.api.dependencies import get_current_user
from app.domains.identity.models import User
from app.kernel.dependencies import get_db

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class DashboardOverview(BaseModel):
    clients: int
    vehicles: int
    online: int
    offline: int
    unstable: int = 0
    unknown: int = 0


@router.get("/overview", response_model=DashboardOverview)
async def dashboard_overview(
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DashboardOverview:
    clients = int(
        (
            await session.execute(
                select(func.count()).select_from(Customer).where(Customer.deleted_at.is_(None))
            )
        ).scalar_one()
    )
    vehicles = int(
        (
            await session.execute(
                select(func.count()).select_from(Vehicle).where(Vehicle.deleted_at.is_(None))
            )
        ).scalar_one()
    )

    health = await count_tracker_health(session)

    return DashboardOverview(
        clients=clients,
        vehicles=vehicles,
        online=health.online,
        offline=health.offline,
        unstable=health.unstable,
        unknown=health.unknown,
    )
