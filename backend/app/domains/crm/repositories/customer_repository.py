from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.crm.models import Customer, CustomerAuditLog, CustomerStatus


class CustomerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _active_filter(self):
        return Customer.deleted_at.is_(None)

    async def get_by_id(self, customer_id: int) -> Customer | None:
        result = await self._session.execute(
            select(Customer).where(Customer.id == customer_id, self._active_filter())
        )
        return result.scalar_one_or_none()

    async def get_by_document(self, document: str, *, exclude_id: int | None = None) -> Customer | None:
        query = select(Customer).where(Customer.document == document, self._active_filter())
        if exclude_id is not None:
            query = query.where(Customer.id != exclude_id)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def create(self, customer: Customer) -> Customer:
        self._session.add(customer)
        await self._session.flush()
        await self._session.refresh(customer)
        return customer

    async def update(self, customer: Customer) -> Customer:
        await self._session.flush()
        await self._session.refresh(customer)
        return customer

    async def soft_delete(self, customer: Customer) -> None:
        customer.deleted_at = datetime.now(UTC)
        customer.status = CustomerStatus.INACTIVE
        await self._session.flush()

    async def count_all(self) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(Customer).where(self._active_filter())
        )
        return int(result.scalar_one())

    async def count_by_status(self, status: CustomerStatus) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(Customer)
            .where(self._active_filter(), Customer.status == status.value)
        )
        return int(result.scalar_one())

    async def list_customers(
        self,
        *,
        search: str | None,
        status: CustomerStatus | None,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[Customer], int]:
        query = select(Customer).where(self._active_filter())

        if status is not None:
            query = query.where(Customer.status == status.value)

        if search:
            term = f"%{search.strip()}%"
            digits = "".join(c for c in search if c.isdigit())
            filters = [
                Customer.full_name.ilike(term),
                Customer.email.ilike(term),
                Customer.city.ilike(term),
            ]
            if digits:
                filters.append(Customer.document.ilike(f"%{digits}%"))
                filters.append(Customer.phone.ilike(f"%{digits}%"))
                filters.append(Customer.secondary_phone.ilike(f"%{digits}%"))
            query = query.where(or_(*filters))

        count_query = select(func.count()).select_from(query.subquery())
        total = int((await self._session.execute(count_query)).scalar_one())

        sort_column = getattr(Customer, sort_by, Customer.full_name)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(query)
        return list(result.scalars().all()), total


class CustomerAuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        customer_id: int | None,
        user_id: int | None,
        action: str,
        details: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> CustomerAuditLog:
        log = CustomerAuditLog(
            customer_id=customer_id,
            user_id=user_id,
            action=action,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._session.add(log)
        await self._session.flush()
        return log
