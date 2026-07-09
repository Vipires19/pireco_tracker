import math
from datetime import UTC, datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.domains.crm.models import Customer
from app.domains.devices.models import (
    InstallationStatus,
    InstallationType,
    Tracker,
    TrackerAssignment,
)
from app.domains.fleet.models import Vehicle
from app.domains.identity.models import User

_ACTIVE_INSTALLATION_STATUSES = (
    InstallationStatus.PENDING.value,
    InstallationStatus.IN_PROGRESS.value,
    InstallationStatus.INSTALLED.value,
)


class InstallationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _active_filter(self):
        return and_(
            TrackerAssignment.removed_at.is_(None),
            TrackerAssignment.status.in_(_ACTIVE_INSTALLATION_STATUSES),
        )

    def _base_query(self):
        technician = aliased(User)
        return (
            select(
                TrackerAssignment,
                Tracker,
                Vehicle,
                Customer,
                technician,
            )
            .join(Tracker, Tracker.id == TrackerAssignment.tracker_id)
            .join(Vehicle, Vehicle.id == TrackerAssignment.vehicle_id)
            .join(Customer, Customer.id == Vehicle.customer_id)
            .outerjoin(technician, technician.id == TrackerAssignment.installed_by)
            .where(Vehicle.deleted_at.is_(None))
        )

    async def get_detail(self, installation_id: int) -> tuple | None:
        query = self._base_query().where(TrackerAssignment.id == installation_id)
        result = await self._session.execute(query)
        row = result.first()
        return tuple(row) if row else None

    async def list_installations(
        self,
        *,
        search: str | None,
        status: InstallationStatus | None,
        installation_type: InstallationType | None,
        vehicle_id: int | None,
        tracker_id: int | None,
        customer_id: int | None,
        active_only: bool,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[tuple], int]:
        query = self._base_query()

        if active_only:
            query = query.where(self._active_filter())
        if status is not None:
            query = query.where(TrackerAssignment.status == status.value)
        if installation_type is not None:
            query = query.where(TrackerAssignment.installation_type == installation_type.value)
        if vehicle_id is not None:
            query = query.where(TrackerAssignment.vehicle_id == vehicle_id)
        if tracker_id is not None:
            query = query.where(TrackerAssignment.tracker_id == tracker_id)
        if customer_id is not None:
            query = query.where(Vehicle.customer_id == customer_id)

        if search:
            term = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Tracker.imei.ilike(term),
                    Tracker.model.ilike(term),
                    Vehicle.plate.ilike(term),
                    Vehicle.nickname.ilike(term),
                    Customer.full_name.ilike(term),
                )
            )

        count_query = select(func.count()).select_from(query.subquery())
        total = int((await self._session.execute(count_query)).scalar_one())

        sort_map = {
            "installed_at": TrackerAssignment.installed_at,
            "created_at": TrackerAssignment.created_at,
            "status": TrackerAssignment.status,
            "installation_type": TrackerAssignment.installation_type,
        }
        sort_column = sort_map.get(sort_by, TrackerAssignment.installed_at)
        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(query)
        return [tuple(row) for row in result.all()], total

    async def create(self, installation: TrackerAssignment) -> TrackerAssignment:
        self._session.add(installation)
        await self._session.flush()
        await self._session.refresh(installation)
        return installation

    async def update(self, installation: TrackerAssignment) -> TrackerAssignment:
        await self._session.flush()
        await self._session.refresh(installation)
        return installation

    @staticmethod
    def total_pages(total: int, page_size: int) -> int:
        return max(1, math.ceil(total / page_size)) if total else 1
