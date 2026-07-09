from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.crm.models import Customer
from app.domains.fleet.models import Vehicle, VehicleAuditLog, VehicleStatus


class VehicleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _active_filter(self):
        return Vehicle.deleted_at.is_(None)

    async def get_by_id(self, vehicle_id: int) -> Vehicle | None:
        result = await self._session.execute(
            select(Vehicle).where(Vehicle.id == vehicle_id, self._active_filter())
        )
        return result.scalar_one_or_none()

    async def get_by_plate(self, plate: str, *, exclude_id: int | None = None) -> Vehicle | None:
        query = select(Vehicle).where(Vehicle.plate == plate, self._active_filter())
        if exclude_id is not None:
            query = query.where(Vehicle.id != exclude_id)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_chassis(self, chassis: str, *, exclude_id: int | None = None) -> Vehicle | None:
        query = select(Vehicle).where(Vehicle.chassis == chassis, self._active_filter())
        if exclude_id is not None:
            query = query.where(Vehicle.id != exclude_id)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def create(self, vehicle: Vehicle) -> Vehicle:
        self._session.add(vehicle)
        await self._session.flush()
        await self._session.refresh(vehicle)
        return vehicle

    async def update(self, vehicle: Vehicle) -> Vehicle:
        await self._session.flush()
        await self._session.refresh(vehicle)
        return vehicle

    async def soft_delete(self, vehicle: Vehicle) -> None:
        vehicle.deleted_at = datetime.now(UTC)
        vehicle.status = VehicleStatus.INACTIVE.value
        await self._session.flush()

    async def count_all(self) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(Vehicle).where(self._active_filter())
        )
        return int(result.scalar_one())

    async def count_by_status(self, status: VehicleStatus) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(Vehicle)
            .where(self._active_filter(), Vehicle.status == status.value)
        )
        return int(result.scalar_one())

    async def count_by_customer(self, customer_id: int) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(Vehicle)
            .where(self._active_filter(), Vehicle.customer_id == customer_id)
        )
        return int(result.scalar_one())

    async def list_vehicles(
        self,
        *,
        customer_id: int | None,
        search: str | None,
        status: VehicleStatus | None,
        category: str | None,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[Vehicle], int]:
        query = select(Vehicle).where(self._active_filter())

        if customer_id is not None:
            query = query.where(Vehicle.customer_id == customer_id)

        if status is not None:
            query = query.where(Vehicle.status == status.value)

        if category is not None:
            query = query.where(Vehicle.category == category)

        if search:
            term = f"%{search.strip()}%"
            digits = "".join(c for c in search if c.isdigit())
            query = query.join(Customer, Vehicle.customer_id == Customer.id)
            filters = [
                Vehicle.plate.ilike(term),
                Vehicle.nickname.ilike(term),
                Vehicle.brand.ilike(term),
                Vehicle.model.ilike(term),
                Vehicle.chassis.ilike(term),
                Customer.full_name.ilike(term),
            ]
            if digits:
                filters.append(Vehicle.renavam.ilike(f"%{digits}%"))
            query = query.where(or_(*filters))

        count_query = select(func.count()).select_from(query.subquery())
        total = int((await self._session.execute(count_query)).scalar_one())

        sort_column = getattr(Vehicle, sort_by, Vehicle.plate)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(query)
        return list(result.scalars().all()), total


class VehicleAuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        vehicle_id: int | None,
        user_id: int | None,
        action: str,
        details: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> VehicleAuditLog:
        log = VehicleAuditLog(
            vehicle_id=vehicle_id,
            user_id=user_id,
            action=action,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._session.add(log)
        await self._session.flush()
        return log

    async def list_by_vehicle_id(self, vehicle_id: int) -> list[VehicleAuditLog]:
        result = await self._session.execute(
            select(VehicleAuditLog)
            .where(VehicleAuditLog.vehicle_id == vehicle_id)
            .order_by(VehicleAuditLog.created_at.asc())
        )
        return list(result.scalars().all())
