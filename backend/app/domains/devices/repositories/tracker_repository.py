from datetime import UTC, datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.devices.health import COMPUTED_HEALTH_STATUSES, health_conditions
from app.domains.devices.models import (
    HealthStatus,
    InstallationStatus,
    InstallationType,
    Tracker,
    TrackerAssignment,
    TrackerAuditLog,
    TrackerStatus,
)

_ACTIVE_INSTALLATION_STATUSES = (
    InstallationStatus.PENDING.value,
    InstallationStatus.IN_PROGRESS.value,
    InstallationStatus.INSTALLED.value,
)


class TrackerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _active_filter(self):
        return Tracker.deleted_at.is_(None)

    async def get_by_id(self, tracker_id: int) -> Tracker | None:
        result = await self._session.execute(
            select(Tracker).where(Tracker.id == tracker_id, self._active_filter())
        )
        return result.scalar_one_or_none()

    async def get_by_imei(self, imei: str, *, exclude_id: int | None = None) -> Tracker | None:
        query = select(Tracker).where(Tracker.imei == imei, self._active_filter())
        if exclude_id is not None:
            query = query.where(Tracker.id != exclude_id)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def create(self, tracker: Tracker) -> Tracker:
        self._session.add(tracker)
        await self._session.flush()
        await self._session.refresh(tracker)
        return tracker

    async def update(self, tracker: Tracker) -> Tracker:
        await self._session.flush()
        await self._session.refresh(tracker)
        return tracker

    async def soft_delete(self, tracker: Tracker) -> None:
        tracker.deleted_at = datetime.now(UTC)
        tracker.status = TrackerStatus.DISPOSED.value
        await self._session.flush()

    async def count_all(self) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(Tracker).where(self._active_filter())
        )
        return int(result.scalar_one())

    async def count_by_status(self, status: TrackerStatus) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(Tracker)
            .where(self._active_filter(), Tracker.status == status.value)
        )
        return int(result.scalar_one())

    async def list_trackers(
        self,
        *,
        search: str | None,
        status: TrackerStatus | None,
        origin: str | None = None,
        health: str | None = None,
        carrier: str | None = None,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[Tracker], int]:
        query = select(Tracker).where(self._active_filter())

        if status is not None:
            query = query.where(Tracker.status == status.value)

        if origin is not None:
            query = query.where(Tracker.origin == origin)

        if health is not None:
            try:
                status_value = HealthStatus(health)
            except ValueError:
                status_value = None
            if status_value in COMPUTED_HEALTH_STATUSES:
                query = query.where(*health_conditions(status_value))
            else:
                query = query.where(Tracker.health_status == health)

        if carrier is not None:
            query = query.where(Tracker.carrier.ilike(f"%{carrier.strip()}%"))

        if search:
            term = f"%{search.strip()}%"
            digits = "".join(c for c in search if c.isdigit())
            filters = [
                Tracker.imei.ilike(term),
                Tracker.model.ilike(term),
                Tracker.manufacturer.ilike(term),
                Tracker.serial_number.ilike(term),
                Tracker.sim_iccid.ilike(term),
                Tracker.carrier.ilike(term),
                Tracker.firmware.ilike(term),
            ]
            if digits:
                filters.append(Tracker.imei.ilike(f"%{digits}%"))
                filters.append(Tracker.sim_iccid.ilike(f"%{digits}%"))
                filters.append(Tracker.sim_imei.ilike(f"%{digits}%"))
                filters.append(Tracker.tracker_phone_number.ilike(f"%{digits}%"))
            query = query.where(or_(*filters))

        count_query = select(func.count()).select_from(query.subquery())
        total = int((await self._session.execute(count_query)).scalar_one())

        sort_column = getattr(Tracker, sort_by, Tracker.imei)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(query)
        return list(result.scalars().all()), total


class TrackerAssignmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _active_installation_filter(self):
        return and_(
            TrackerAssignment.removed_at.is_(None),
            TrackerAssignment.status.in_(_ACTIVE_INSTALLATION_STATUSES),
        )

    async def get_by_id(self, assignment_id: int) -> TrackerAssignment | None:
        result = await self._session.execute(
            select(TrackerAssignment).where(TrackerAssignment.id == assignment_id)
        )
        return result.scalar_one_or_none()

    async def get_active_by_tracker(self, tracker_id: int) -> TrackerAssignment | None:
        result = await self._session.execute(
            select(TrackerAssignment).where(
                TrackerAssignment.tracker_id == tracker_id,
                self._active_installation_filter(),
            )
        )
        return result.scalar_one_or_none()

    async def get_active_primary_by_vehicle(self, vehicle_id: int) -> TrackerAssignment | None:
        result = await self._session.execute(
            select(TrackerAssignment).where(
                TrackerAssignment.vehicle_id == vehicle_id,
                TrackerAssignment.installation_type == InstallationType.PRIMARY.value,
                self._active_installation_filter(),
            )
        )
        return result.scalar_one_or_none()

    async def get_active_by_vehicle(self, vehicle_id: int) -> list[TrackerAssignment]:
        result = await self._session.execute(
            select(TrackerAssignment)
            .where(
                TrackerAssignment.vehicle_id == vehicle_id,
                self._active_installation_filter(),
            )
            .order_by(TrackerAssignment.installed_at.desc())
        )
        return list(result.scalars().all())

    async def list_by_tracker(self, tracker_id: int) -> list[TrackerAssignment]:
        result = await self._session.execute(
            select(TrackerAssignment)
            .where(TrackerAssignment.tracker_id == tracker_id)
            .order_by(TrackerAssignment.installed_at.desc())
        )
        return list(result.scalars().all())

    async def create(self, assignment: TrackerAssignment) -> TrackerAssignment:
        self._session.add(assignment)
        await self._session.flush()
        await self._session.refresh(assignment)
        return assignment

    async def update(self, assignment: TrackerAssignment) -> TrackerAssignment:
        await self._session.flush()
        await self._session.refresh(assignment)
        return assignment


class TrackerAuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        tracker_id: int | None,
        user_id: int | None,
        action: str,
        details: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> TrackerAuditLog:
        log = TrackerAuditLog(
            tracker_id=tracker_id,
            user_id=user_id,
            action=action,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._session.add(log)
        await self._session.flush()
        return log

    async def list_by_tracker_id(self, tracker_id: int) -> list[TrackerAuditLog]:
        result = await self._session.execute(
            select(TrackerAuditLog)
            .where(TrackerAuditLog.tracker_id == tracker_id)
            .order_by(TrackerAuditLog.created_at.asc())
        )
        return list(result.scalars().all())
