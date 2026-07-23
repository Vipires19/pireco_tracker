from sqlalchemy import and_, case, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.crm.models import Customer
from app.domains.devices.models import (
    InstallationStatus,
    InstallationType,
    Tracker,
    TrackerAssignment,
)
from app.domains.fleet.models import Vehicle

_ACTIVE_INSTALLED = and_(
    TrackerAssignment.removed_at.is_(None),
    TrackerAssignment.status == InstallationStatus.INSTALLED.value,
)


class MonitoringRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _installed_query(self):
        return (
            select(TrackerAssignment, Tracker, Vehicle, Customer)
            .join(Tracker, Tracker.id == TrackerAssignment.tracker_id)
            .join(Vehicle, Vehicle.id == TrackerAssignment.vehicle_id)
            .join(Customer, Customer.id == Vehicle.customer_id)
            .where(
                _ACTIVE_INSTALLED,
                Vehicle.deleted_at.is_(None),
                Tracker.deleted_at.is_(None),
            )
        )

    async def list_installed_vehicles(self) -> list[tuple[TrackerAssignment, Tracker, Vehicle, Customer]]:
        query = (
            self._installed_query()
            .order_by(
                Vehicle.id.asc(),
                case(
                    (TrackerAssignment.installation_type == InstallationType.PRIMARY.value, 0),
                    else_=1,
                ),
                TrackerAssignment.installed_at.desc(),
            )
        )
        result = await self._session.execute(query)
        rows = result.all()

        seen: set[int] = set()
        unique: list[tuple[TrackerAssignment, Tracker, Vehicle, Customer]] = []
        for row in rows:
            assignment, tracker, vehicle, customer = row
            if vehicle.id in seen:
                continue
            seen.add(vehicle.id)
            unique.append((assignment, tracker, vehicle, customer))
        return unique

    async def get_installed_vehicle(
        self, vehicle_id: int
    ) -> tuple[TrackerAssignment, Tracker, Vehicle, Customer] | None:
        query = (
            self._installed_query()
            .where(Vehicle.id == vehicle_id)
            .order_by(
                case(
                    (TrackerAssignment.installation_type == InstallationType.PRIMARY.value, 0),
                    else_=1,
                ),
                TrackerAssignment.installed_at.desc(),
            )
            .limit(1)
        )
        result = await self._session.execute(query)
        row = result.first()
        return tuple(row) if row else None
