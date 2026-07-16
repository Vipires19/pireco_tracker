from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.crm.models import CustomerUser


class CustomerUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: int) -> CustomerUser | None:
        result = await self._session.execute(
            select(CustomerUser).where(CustomerUser.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str, *, exclude_id: int | None = None) -> CustomerUser | None:
        query = select(CustomerUser).where(func.lower(CustomerUser.email) == email.lower())
        if exclude_id is not None:
            query = query.where(CustomerUser.id != exclude_id)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def list_by_customer(self, customer_id: int) -> tuple[list[CustomerUser], int]:
        query = (
            select(CustomerUser)
            .where(CustomerUser.customer_id == customer_id)
            .order_by(CustomerUser.full_name.asc())
        )
        total = int(
            (
                await self._session.execute(
                    select(func.count()).select_from(query.subquery())
                )
            ).scalar_one()
        )
        result = await self._session.execute(query)
        return list(result.scalars().all()), total

    async def create(self, user: CustomerUser) -> CustomerUser:
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def update(self, user: CustomerUser) -> CustomerUser:
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def delete(self, user: CustomerUser) -> None:
        await self._session.delete(user)
        await self._session.flush()
