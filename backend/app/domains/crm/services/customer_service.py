import math

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.crm.models import Customer, CustomerAuditAction, CustomerStatus
from app.domains.crm.repositories import CustomerAuditRepository, CustomerRepository
from app.domains.crm.schemas import (
    CustomerCreate,
    CustomerListResponse,
    CustomerResponse,
    CustomerStats,
    CustomerStatusUpdate,
    CustomerUpdate,
)
from app.domains.crm.validators import CustomerValidationError
from app.domains.identity.models import User
from app.kernel.logger import get_logger

logger = get_logger(__name__)


class CustomerService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._customers = CustomerRepository(session)
        self._audit = CustomerAuditRepository(session)

    async def list_customers(
        self,
        *,
        search: str | None,
        status: CustomerStatus | None,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
    ) -> CustomerListResponse:
        items, total = await self._customers.list_customers(
            search=search,
            status=status,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        stats = CustomerStats(
            total=await self._customers.count_all(),
            active=await self._customers.count_by_status(CustomerStatus.ACTIVE),
            inactive=await self._customers.count_by_status(CustomerStatus.INACTIVE),
        )
        pages = max(1, math.ceil(total / page_size)) if total else 1
        return CustomerListResponse(
            items=[CustomerResponse.model_validate(c) for c in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
            stats=stats,
        )

    async def get_customer(self, customer_id: int) -> Customer:
        customer = await self._customers.get_by_id(customer_id)
        if customer is None:
            raise ValueError("customer_not_found")
        return customer

    async def create_customer(
        self,
        payload: CustomerCreate,
        *,
        user: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Customer:
        existing = await self._customers.get_by_document(payload.document)
        if existing is not None:
            raise ValueError("document_already_exists")

        customer = Customer(
            full_name=payload.full_name.strip(),
            document=payload.document,
            document_type=payload.document_type.value,
            phone=payload.phone,
            secondary_phone=payload.secondary_phone,
            email=payload.email.lower() if payload.email else None,
            zip_code=payload.zip_code,
            street=payload.street,
            number=payload.number,
            complement=payload.complement,
            district=payload.district,
            city=payload.city,
            state=payload.state,
            notes=payload.notes,
            status=CustomerStatus.ACTIVE.value,
        )
        created = await self._customers.create(customer)
        await self._audit.create(
            customer_id=created.id,
            user_id=user.id,
            action=CustomerAuditAction.CREATED.value,
            details=f"Cliente criado: {created.full_name}",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self._session.commit()
        logger.info("Customer created id=%s by user_id=%s", created.id, user.id)
        return created

    async def update_customer(
        self,
        customer_id: int,
        payload: CustomerUpdate,
        *,
        user: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Customer:
        customer = await self.get_customer(customer_id)
        existing = await self._customers.get_by_document(payload.document, exclude_id=customer_id)
        if existing is not None:
            raise ValueError("document_already_exists")

        customer.full_name = payload.full_name.strip()
        customer.document = payload.document
        customer.document_type = payload.document_type.value
        customer.phone = payload.phone
        customer.secondary_phone = payload.secondary_phone
        customer.email = payload.email.lower() if payload.email else None
        customer.zip_code = payload.zip_code
        customer.street = payload.street
        customer.number = payload.number
        customer.complement = payload.complement
        customer.district = payload.district
        customer.city = payload.city
        customer.state = payload.state
        customer.notes = payload.notes

        updated = await self._customers.update(customer)
        await self._audit.create(
            customer_id=updated.id,
            user_id=user.id,
            action=CustomerAuditAction.UPDATED.value,
            details=f"Cliente atualizado: {updated.full_name}",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self._session.commit()
        logger.info("Customer updated id=%s by user_id=%s", updated.id, user.id)
        return updated

    async def update_status(
        self,
        customer_id: int,
        payload: CustomerStatusUpdate,
        *,
        user: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Customer:
        customer = await self.get_customer(customer_id)
        previous = customer.status
        customer.status = payload.status.value
        updated = await self._customers.update(customer)
        await self._audit.create(
            customer_id=updated.id,
            user_id=user.id,
            action=CustomerAuditAction.STATUS_CHANGED.value,
            details=f"Status alterado de {previous} para {payload.status.value}",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self._session.commit()
        logger.info(
            "Customer status changed id=%s status=%s by user_id=%s",
            updated.id,
            payload.status.value,
            user.id,
        )
        return updated

    async def delete_customer(
        self,
        customer_id: int,
        *,
        user: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        customer = await self.get_customer(customer_id)
        await self._customers.soft_delete(customer)
        await self._audit.create(
            customer_id=customer.id,
            user_id=user.id,
            action=CustomerAuditAction.DELETED.value,
            details=f"Cliente excluído (soft delete): {customer.full_name}",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self._session.commit()
        logger.info("Customer soft-deleted id=%s by user_id=%s", customer.id, user.id)
