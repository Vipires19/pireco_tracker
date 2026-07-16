from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

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
from app.domains.fleet.repositories import VehicleRepository
from app.domains.identity.models import User
from app.domains.identity.repositories import UserRepository
from app.domains.operations.repositories import InstallationRepository
from app.domains.operations.schemas.installation import (
    CustomerSummary,
    InstallationCreate,
    InstallationFinish,
    InstallationListResponse,
    InstallationResponse,
    InstallationUpdate,
    TechnicianSummary,
    TrackerSummary,
    VehicleSummary,
)
from app.kernel.logger import get_logger

logger = get_logger(__name__)

# Consistência de domínio: só é possível iniciar instalação a partir destes estados.
_INSTALLABLE_STATUSES = (
    TrackerStatus.NEW,
    TrackerStatus.IN_STOCK,
    TrackerStatus.PENDING_INSTALLATION,
)


class InstallationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._installations = InstallationRepository(session)
        self._assignments = TrackerAssignmentRepository(session)
        self._trackers = TrackerRepository(session)
        self._vehicles = VehicleRepository(session)
        self._users = UserRepository(session)
        self._audit = TrackerAuditRepository(session)

    def _build_response(
        self,
        installation: TrackerAssignment,
        tracker: Tracker,
        vehicle,
        customer,
        technician: User | None,
    ) -> InstallationResponse:
        return InstallationResponse(
            id=installation.id,
            tracker_id=installation.tracker_id,
            vehicle_id=installation.vehicle_id,
            installation_type=InstallationType(installation.installation_type),
            status=InstallationStatus(installation.status),
            installed_at=installation.installed_at,
            installed_by=installation.installed_by,
            installation_notes=installation.installation_notes,
            power_connected=installation.power_connected,
            gps_ok=installation.gps_ok,
            gsm_ok=installation.gsm_ok,
            ignition_ok=installation.ignition_ok,
            blocking_ok=installation.blocking_ok,
            test_drive_completed=installation.test_drive_completed,
            customer_present=installation.customer_present,
            removed_at=installation.removed_at,
            removed_by=installation.removed_by,
            removal_reason=installation.removal_reason,
            created_at=installation.created_at,
            updated_at=installation.updated_at,
            tracker=TrackerSummary.model_validate(tracker),
            vehicle=VehicleSummary.model_validate(vehicle),
            customer=CustomerSummary.model_validate(customer),
            technician=(
                TechnicianSummary.model_validate(technician) if technician is not None else None
            ),
        )

    async def _get_detail_or_raise(self, installation_id: int) -> InstallationResponse:
        row = await self._installations.get_detail(installation_id)
        if row is None:
            raise ValueError("installation_not_found")
        installation, tracker, vehicle, customer, technician = row
        return self._build_response(installation, tracker, vehicle, customer, technician)

    async def _validate_tracker_installable(self, tracker: Tracker) -> None:
        if TrackerStatus(tracker.status) not in _INSTALLABLE_STATUSES:
            raise ValueError("tracker_not_installable")

    async def _validate_primary_unique(self, vehicle_id: int, *, exclude_id: int | None = None) -> None:
        existing = await self._assignments.get_active_primary_by_vehicle(vehicle_id)
        if existing is not None and existing.id != exclude_id:
            raise ValueError("vehicle_primary_exists")

    def _apply_checklist(self, installation: TrackerAssignment, checklist) -> None:
        installation.power_connected = checklist.power_connected
        installation.gps_ok = checklist.gps_ok
        installation.gsm_ok = checklist.gsm_ok
        installation.ignition_ok = checklist.ignition_ok
        installation.blocking_ok = checklist.blocking_ok
        installation.test_drive_completed = checklist.test_drive_completed
        installation.customer_present = checklist.customer_present

    async def _finalize_installed(
        self,
        installation: TrackerAssignment,
        tracker: Tracker,
        *,
        user: User,
        ip_address: str | None,
        user_agent: str | None,
    ) -> None:
        installation.status = InstallationStatus.INSTALLED.value
        if installation.installed_at is None:
            installation.installed_at = datetime.now(UTC)
        tracker.status = TrackerStatus.INSTALLED.value
        await self._trackers.update(tracker)
        await self._assignments.update(installation)
        await self._audit.create(
            tracker_id=tracker.id,
            user_id=user.id,
            action=TrackerAuditAction.ASSIGNED.value,
            details=f"Instalação concluída: rastreador {tracker.imei} no veículo {installation.vehicle_id}",
            ip_address=ip_address,
            user_agent=user_agent,
        )

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
    ) -> InstallationListResponse:
        rows, total = await self._installations.list_installations(
            search=search,
            status=status,
            installation_type=installation_type,
            vehicle_id=vehicle_id,
            tracker_id=tracker_id,
            customer_id=customer_id,
            active_only=active_only,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        items = [
            self._build_response(installation, tracker, vehicle, customer, technician)
            for installation, tracker, vehicle, customer, technician in rows
        ]
        return InstallationListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=self._installations.total_pages(total, page_size),
        )

    async def get_installation(self, installation_id: int) -> InstallationResponse:
        return await self._get_detail_or_raise(installation_id)

    async def create_installation(
        self,
        payload: InstallationCreate,
        *,
        user: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> InstallationResponse:
        tracker = await self._trackers.get_by_id(payload.tracker_id)
        if tracker is None:
            raise ValueError("tracker_not_found")

        vehicle = await self._vehicles.get_by_id(payload.vehicle_id)
        if vehicle is None:
            raise ValueError("vehicle_not_found")

        active = await self._assignments.get_active_by_tracker(payload.tracker_id)
        if active is not None:
            raise ValueError("tracker_already_assigned")

        await self._validate_tracker_installable(tracker)

        if payload.installation_type == InstallationType.PRIMARY:
            await self._validate_primary_unique(payload.vehicle_id)

        technician_id = payload.installed_by or user.id
        technician = await self._users.get_by_id(technician_id)
        if technician is None:
            raise ValueError("technician_not_found")

        installation = TrackerAssignment(
            tracker_id=payload.tracker_id,
            vehicle_id=payload.vehicle_id,
            installed_by=technician_id,
            installed_at=datetime.now(UTC),
            installation_type=payload.installation_type.value,
            status=InstallationStatus.IN_PROGRESS.value,
            installation_notes=payload.installation_notes,
        )
        self._apply_checklist(installation, payload.checklist)
        created = await self._installations.create(installation)

        if payload.complete:
            await self._finalize_installed(
                created,
                tracker,
                user=user,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        else:
            await self._audit.create(
                tracker_id=tracker.id,
                user_id=user.id,
                action=TrackerAuditAction.ASSIGNED.value,
                details=f"Instalação iniciada: rastreador {tracker.imei}",
                ip_address=ip_address,
                user_agent=user_agent,
            )

        await self._session.commit()
        logger.info(
            "Installation created id=%s tracker_id=%s vehicle_id=%s by user_id=%s",
            created.id,
            payload.tracker_id,
            payload.vehicle_id,
            user.id,
        )
        return await self._get_detail_or_raise(created.id)

    async def update_installation(
        self,
        installation_id: int,
        payload: InstallationUpdate,
        *,
        user: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> InstallationResponse:
        row = await self._installations.get_detail(installation_id)
        if row is None:
            raise ValueError("installation_not_found")
        installation, tracker, vehicle, _customer, _technician = row

        current_status = InstallationStatus(installation.status)
        if current_status in (InstallationStatus.REMOVED, InstallationStatus.CANCELLED):
            raise ValueError("installation_not_editable")

        if payload.installation_type == InstallationType.PRIMARY or (
            payload.installation_type is None
            and InstallationType(installation.installation_type) == InstallationType.PRIMARY
        ):
            target_type = payload.installation_type or InstallationType(installation.installation_type)
            if target_type == InstallationType.PRIMARY:
                await self._validate_primary_unique(installation.vehicle_id, exclude_id=installation.id)

        if payload.installation_type is not None:
            installation.installation_type = payload.installation_type.value
        if payload.installed_by is not None:
            technician = await self._users.get_by_id(payload.installed_by)
            if technician is None:
                raise ValueError("technician_not_found")
            installation.installed_by = payload.installed_by
        if payload.installation_notes is not None:
            installation.installation_notes = payload.installation_notes.strip() or None
        if payload.checklist is not None:
            self._apply_checklist(installation, payload.checklist)

        if payload.status is not None:
            await self._apply_status_change(
                installation,
                tracker,
                payload.status,
                user=user,
                removal_reason=payload.removal_reason,
                ip_address=ip_address,
                user_agent=user_agent,
            )

        await self._assignments.update(installation)
        await self._session.commit()
        return await self._get_detail_or_raise(installation_id)

    async def finish_installation(
        self,
        installation_id: int,
        payload: InstallationFinish,
        *,
        user: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> InstallationResponse:
        row = await self._installations.get_detail(installation_id)
        if row is None:
            raise ValueError("installation_not_found")
        installation, tracker, _vehicle, _customer, _technician = row

        status = InstallationStatus(installation.status)
        if status not in (InstallationStatus.PENDING, InstallationStatus.IN_PROGRESS):
            raise ValueError("installation_cannot_finish")

        if payload.installation_notes is not None:
            installation.installation_notes = payload.installation_notes.strip() or None

        await self._finalize_installed(
            installation,
            tracker,
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self._session.commit()
        logger.info("Installation finished id=%s by user_id=%s", installation_id, user.id)
        return await self._get_detail_or_raise(installation_id)

    async def _apply_status_change(
        self,
        installation: TrackerAssignment,
        tracker: Tracker,
        new_status: InstallationStatus,
        *,
        user: User,
        removal_reason: str | None,
        ip_address: str | None,
        user_agent: str | None,
    ) -> None:
        if new_status == InstallationStatus.REMOVED:
            installation.status = InstallationStatus.REMOVED.value
            installation.removed_at = datetime.now(UTC)
            installation.removed_by = user.id
            installation.removal_reason = removal_reason
            await self._assignments.update(installation)
            remaining = await self._assignments.get_active_by_tracker(tracker.id)
            if remaining is None:
                tracker.status = TrackerStatus.IN_STOCK.value
                await self._trackers.update(tracker)
            await self._audit.create(
                tracker_id=tracker.id,
                user_id=user.id,
                action=TrackerAuditAction.UNASSIGNED.value,
                details=f"Instalação finalizada: rastreador {tracker.imei}",
                ip_address=ip_address,
                user_agent=user_agent,
            )
        elif new_status == InstallationStatus.CANCELLED:
            installation.status = InstallationStatus.CANCELLED.value
            installation.removed_at = datetime.now(UTC)
            installation.removed_by = user.id
            installation.removal_reason = removal_reason or "Instalação cancelada"
            await self._assignments.update(installation)
            remaining = await self._assignments.get_active_by_tracker(tracker.id)
            if remaining is None and TrackerStatus(tracker.status) != TrackerStatus.INSTALLED:
                tracker.status = TrackerStatus.IN_STOCK.value
                await self._trackers.update(tracker)
        else:
            installation.status = new_status.value
