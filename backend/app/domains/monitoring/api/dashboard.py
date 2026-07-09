from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends

from app.domains.crm.models import Customer
from app.domains.devices.models import Tracker
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


@router.get("/overview", response_model=DashboardOverview)
async def dashboard_overview(
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DashboardOverview:
    clients = int(
        (await session.execute(
            select(func.count()).select_from(Customer).where(Customer.deleted_at.is_(None))
        )).scalar_one()
    )
    vehicles = int(
        (await session.execute(
            select(func.count()).select_from(Vehicle).where(Vehicle.deleted_at.is_(None))
        )).scalar_one()
    )
    trackers = int(
        (await session.execute(
            select(func.count()).select_from(Tracker).where(Tracker.deleted_at.is_(None))
        )).scalar_one()
    )

    online = 0
    offline = trackers

    return DashboardOverview(
        clients=clients,
        vehicles=vehicles,
        online=online,
        offline=offline,
    )
