import math
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.devices.health import resolve_health_status
from app.domains.devices.models import (
    InstallationStatus,
    InstallationType,
    Tracker,
    TrackerAssignment,
    TrackerAuditAction,
    TrackerStatus,
)
from app.domains.devices.repositories import (
    TrackerAssignmentRepository,
    TrackerAuditRepository,
    TrackerRepository,
)
from app.domains.devices.schemas import (
    TrackerAssignmentCreate,
    TrackerAssignmentUnassign,
    TrackerCreate,
    TrackerListResponse,
    TrackerResponse,
    TrackerStats,
    TrackerStatusUpdate,
    TrackerUpdate,
)
from app.domains.fleet.repositories import VehicleRepository
from app.domains.identity.models import User
from app.kernel.logger import get_logger

logger = get_logger(__name__)


def _to_response(tracker: Tracker) -> TrackerResponse:
    response = TrackerResponse.model_validate(tracker)
    return response.model_copy(
        update={"health_status": resolve_health_status(tracker.last_seen_at)}
    )


class TrackerService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._trackers = TrackerRepository(session)
        self._assignments = TrackerAssignmentRepository(session)
        self._audit = TrackerAuditRepository(session)
        self._vehicles = VehicleRepository(session)

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
    ) -> TrackerListResponse:
        items, total = await self._trackers.list_trackers(
            search=search,
            status=status,
            origin=origin,
            health=health,
            carrier=carrier,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        stats = TrackerStats(
            total=await self._trackers.count_all(),
            in_stock=await self._trackers.count_by_status(TrackerStatus.IN_STOCK),
            installed=await self._trackers.count_by_status(TrackerStatus.INSTALLED),
            maintenance=await self._trackers.count_by_status(TrackerStatus.MAINTENANCE),
            blocked=await self._trackers.count_by_status(TrackerStatus.BLOCKED),
        )
        total_pages = max(1, math.ceil(total / page_size)) if total else 1
        return TrackerListResponse(
            items=[_to_response(t) for t in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            stats=stats,
        )

    async def get_tracker(self, tracker_id: int) -> Tracker:
        tracker = await self._trackers.get_by_id(tracker_id)
        if tracker is None:
            raise ValueError("tracker_not_found")
        return tracker

    def serialize(self, tracker: Tracker) -> TrackerResponse:
        return _to_response(tracker)

    async def _ensure_unique_imei(self, imei: str, *, exclude_id: int | None = None) -> None:
        existing = await self._trackers.get_by_imei(imei, exclude_id=exclude_id)
        if existing is not None:
            raise ValueError("imei_already_exists")

    def _apply_payload(self, tracker: Tracker, payload: TrackerCreate | TrackerUpdate) -> None:
        tracker.imei = payload.imei
        tracker.model = payload.model
        tracker.manufacturer = payload.manufacturer
        tracker.firmware = payload.firmware
        tracker.tracker_phone_number = payload.tracker_phone_number
        tracker.sim_iccid = payload.sim_iccid
        tracker.sim_imei = payload.sim_imei
        tracker.carrier = payload.carrier
        tracker.apn = payload.apn
        tracker.serial_number = payload.serial_number
        tracker.notes = payload.notes
        tracker.origin = payload.origin.value

    async def create_tracker(
        self,
        payload: TrackerCreate,
        *,
        user: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Tracker:
        await self._ensure_unique_imei(payload.imei)
        initial_status = payload.status.value if payload.status is not None else TrackerStatus.NEW.value
        tracker = Tracker(status=initial_status)
        self._apply_payload(tracker, payload)
        try:
            created = await self._trackers.create(tracker)
            await self._audit.create(
                tracker_id=created.id,
                user_id=user.id,
                action=TrackerAuditAction.CREATED.value,
                details=f"Rastreador criado: {created.imei}",
                ip_address=ip_address,
                user_agent=user_agent,
            )
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise ValueError("imei_already_exists") from exc
        logger.info("Tracker created id=%s by user_id=%s", created.id, user.id)
        return created

    async def update_tracker(
        self,
        tracker_id: int,
        payload: TrackerUpdate,
        *,
        user: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Tracker:
        tracker = await self.get_tracker(tracker_id)
        await self._ensure_unique_imei(payload.imei, exclude_id=tracker_id)
        self._apply_payload(tracker, payload)
        try:
            updated = await self._trackers.update(tracker)
            await self._audit.create(
                tracker_id=updated.id,
                user_id=user.id,
                action=TrackerAuditAction.UPDATED.value,
                details=f"Rastreador atualizado: {updated.imei}",
                ip_address=ip_address,
                user_agent=user_agent,
            )
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise ValueError("imei_already_exists") from exc
        logger.info("Tracker updated id=%s by user_id=%s", updated.id, user.id)
        return updated

    async def _release_active_assignments(
        self,
        tracker: Tracker,
        *,
        user: User,
        reason: str,
    ) -> None:
        """Encerra qualquer instalação ativa e libera o vínculo com o veículo."""
        active = await self._assignments.get_active_by_tracker(tracker.id)
        while active is not None:
            active.status = InstallationStatus.REMOVED.value
            active.removed_at = datetime.now(UTC)
            active.removed_by = user.id
            active.removal_reason = reason
            await self._assignments.update(active)
            active = await self._assignments.get_active_by_tracker(tracker.id)

    async def update_status(
        self,
        tracker_id: int,
        payload: TrackerStatusUpdate,
        *,
        user: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Tracker:
        tracker = await self.get_tracker(tracker_id)
        previous = tracker.status

        # Consistência de domínio: "Instalado" é derivado de uma instalação,
        # não pode ser definido manualmente.
        if payload.status == TrackerStatus.INSTALLED:
            raise ValueError("tracker_status_install_forbidden")

        # Regra operacional: ao voltar para "Em estoque" o equipamento é
        # liberado — remove instalação ativa e vínculo com o veículo.
        if payload.status == TrackerStatus.IN_STOCK:
            await self._release_active_assignments(
                tracker,
                user=user,
                reason=f"Rastreador movido para estoque por {user.email}",
            )

        tracker.status = payload.status.value
        updated = await self._trackers.update(tracker)
        await self._audit.create(
            tracker_id=updated.id,
            user_id=user.id,
            action=TrackerAuditAction.STATUS_CHANGED.value,
            details=f"Status alterado de {previous} para {payload.status.value}",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self._session.commit()
        logger.info(
            "Tracker status changed id=%s status=%s by user_id=%s",
            updated.id,
            payload.status.value,
            user.id,
        )
        return updated

    async def delete_tracker(
        self,
        tracker_id: int,
        *,
        user: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        tracker = await self.get_tracker(tracker_id)
        active = await self._assignments.get_active_by_tracker(tracker_id)
        if active is not None:
            raise ValueError("tracker_has_active_assignment")
        await self._trackers.soft_delete(tracker)
        await self._audit.create(
            tracker_id=tracker.id,
            user_id=user.id,
            action=TrackerAuditAction.DELETED.value,
            details=f"Rastreador excluído (soft delete): {tracker.imei}",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self._session.commit()
        logger.info("Tracker soft-deleted id=%s by user_id=%s", tracker.id, user.id)

    async def assign_tracker(
        self,
        payload: TrackerAssignmentCreate,
        *,
        user: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> TrackerAssignment:
        tracker = await self.get_tracker(payload.tracker_id)
        vehicle = await self._vehicles.get_by_id(payload.vehicle_id)
        if vehicle is None:
            raise ValueError("vehicle_not_found")

        active = await self._assignments.get_active_by_tracker(payload.tracker_id)
        if active is not None:
            raise ValueError("tracker_already_assigned")

        assignment = TrackerAssignment(
            tracker_id=payload.tracker_id,
            vehicle_id=payload.vehicle_id,
            installed_by=user.id,
            installation_type=InstallationType.PRIMARY.value,
            status=InstallationStatus.INSTALLED.value,
        )
        created = await self._assignments.create(assignment)
        tracker.status = TrackerStatus.INSTALLED.value
        await self._trackers.update(tracker)
        await self._audit.create(
            tracker_id=tracker.id,
            user_id=user.id,
            action=TrackerAuditAction.ASSIGNED.value,
            details=f"Rastreador {tracker.imei} vinculado ao veículo {vehicle.plate}",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self._session.commit()
        logger.info(
            "Tracker assigned tracker_id=%s vehicle_id=%s by user_id=%s",
            tracker.id,
            vehicle.id,
            user.id,
        )
        return created

    async def unassign_tracker(
        self,
        assignment_id: int,
        payload: TrackerAssignmentUnassign,
        *,
        user: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> TrackerAssignment:
        result = await self._session.get(TrackerAssignment, assignment_id)
        if result is None or result.removed_at is not None:
            raise ValueError("assignment_not_found")

        tracker = await self.get_tracker(result.tracker_id)
        result.removed_at = datetime.now(UTC)
        result.removed_by = user.id
        result.removal_reason = payload.removal_reason
        result.status = InstallationStatus.REMOVED.value
        updated = await self._assignments.update(result)

        active = await self._assignments.get_active_by_tracker(tracker.id)
        if active is None:
            tracker.status = TrackerStatus.IN_STOCK.value
            await self._trackers.update(tracker)

        await self._audit.create(
            tracker_id=tracker.id,
            user_id=user.id,
            action=TrackerAuditAction.UNASSIGNED.value,
            details=f"Rastreador {tracker.imei} desvinculado do veículo {result.vehicle_id}",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self._session.commit()
        logger.info(
            "Tracker unassigned assignment_id=%s by user_id=%s",
            assignment_id,
            user.id,
        )
        return updated
