from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.crm.models import CustomerUser
from app.domains.crm.repositories import CustomerRepository, CustomerUserRepository
from app.domains.crm.schemas.customer_user import (
    CustomerUserCreate,
    CustomerUserListResponse,
    CustomerUserResponse,
    CustomerUserUpdate,
)
from app.kernel.logger import get_logger
from app.kernel.security.passwords import hash_password

logger = get_logger(__name__)


class CustomerUserService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._customers = CustomerRepository(session)
        self._users = CustomerUserRepository(session)

    async def _ensure_customer(self, customer_id: int) -> None:
        customer = await self._customers.get_by_id(customer_id)
        if customer is None:
            raise ValueError("customer_not_found")

    async def list_users(self, customer_id: int) -> CustomerUserListResponse:
        await self._ensure_customer(customer_id)
        items, total = await self._users.list_by_customer(customer_id)
        return CustomerUserListResponse(
            items=[CustomerUserResponse.model_validate(item) for item in items],
            total=total,
        )

    async def create_user(
        self, customer_id: int, payload: CustomerUserCreate
    ) -> CustomerUserResponse:
        await self._ensure_customer(customer_id)
        if await self._users.get_by_email(payload.email) is not None:
            raise ValueError("customer_user_email_exists")

        user = CustomerUser(
            customer_id=customer_id,
            full_name=payload.full_name.strip(),
            email=payload.email.lower(),
            password_hash=hash_password(payload.password),
            role=payload.role.value,
            status=payload.status.value,
        )
        created = await self._users.create(user)
        await self._session.commit()
        logger.info("Customer user created id=%s customer_id=%s", created.id, customer_id)
        return CustomerUserResponse.model_validate(created)

    async def update_user(
        self, customer_id: int, user_id: int, payload: CustomerUserUpdate
    ) -> CustomerUserResponse:
        await self._ensure_customer(customer_id)
        user = await self._users.get_by_id(user_id)
        if user is None or user.customer_id != customer_id:
            raise ValueError("customer_user_not_found")

        if payload.full_name is not None:
            user.full_name = payload.full_name.strip()
        if payload.password is not None:
            user.password_hash = hash_password(payload.password)
        if payload.role is not None:
            user.role = payload.role.value
        if payload.status is not None:
            user.status = payload.status.value

        updated = await self._users.update(user)
        await self._session.commit()
        return CustomerUserResponse.model_validate(updated)

    async def delete_user(self, customer_id: int, user_id: int) -> None:
        await self._ensure_customer(customer_id)
        user = await self._users.get_by_id(user_id)
        if user is None or user.customer_id != customer_id:
            raise ValueError("customer_user_not_found")
        await self._users.delete(user)
        await self._session.commit()
        logger.info("Customer user deleted id=%s customer_id=%s", user_id, customer_id)
