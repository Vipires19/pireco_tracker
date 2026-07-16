from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.crm.models import CustomerUser
from app.domains.crm.repositories import CustomerRepository, CustomerUserRepository
from app.domains.crm.schemas.customer_user import (
    CustomerUserCreate,
    CustomerUserListResponse,
    CustomerUserResetPassword,
    CustomerUserResponse,
    CustomerUserStatusUpdate,
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

    def _to_response(self, user: CustomerUser) -> CustomerUserResponse:
        return CustomerUserResponse.model_validate(user)

    async def _get_or_raise(self, user_id: int) -> CustomerUser:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise ValueError("customer_user_not_found")
        return user

    async def _ensure_customer(self, customer_id: int) -> None:
        customer = await self._customers.get_by_id(customer_id)
        if customer is None:
            raise ValueError("customer_not_found")

    async def list_users(self, *, customer_id: int | None = None) -> CustomerUserListResponse:
        if customer_id is not None:
            await self._ensure_customer(customer_id)
        items, total = await self._users.list_users(customer_id=customer_id)
        return CustomerUserListResponse(
            items=[self._to_response(item) for item in items],
            total=total,
        )

    async def create_user(self, payload: CustomerUserCreate) -> CustomerUserResponse:
        await self._ensure_customer(payload.customer_id)
        if await self._users.get_by_email(payload.email) is not None:
            raise ValueError("customer_user_email_exists")

        user = CustomerUser(
            customer_id=payload.customer_id,
            full_name=payload.full_name.strip(),
            email=str(payload.email).lower(),
            password_hash=hash_password(payload.password),
            role=payload.role.value,
            status=payload.status.value,
            must_change_password=payload.must_change_password,
        )
        created = await self._users.create(user)
        await self._session.commit()
        logger.info(
            "Customer user created id=%s customer_id=%s",
            created.id,
            payload.customer_id,
        )
        return self._to_response(created)

    async def update_user(self, user_id: int, payload: CustomerUserUpdate) -> CustomerUserResponse:
        user = await self._get_or_raise(user_id)

        if payload.full_name is not None:
            user.full_name = payload.full_name.strip()
        if payload.email is not None:
            existing = await self._users.get_by_email(str(payload.email), exclude_id=user_id)
            if existing is not None:
                raise ValueError("customer_user_email_exists")
            user.email = str(payload.email).lower()
        if payload.role is not None:
            user.role = payload.role.value
        if payload.must_change_password is not None:
            user.must_change_password = payload.must_change_password

        updated = await self._users.update(user)
        await self._session.commit()
        return self._to_response(updated)

    async def update_status(
        self, user_id: int, payload: CustomerUserStatusUpdate
    ) -> CustomerUserResponse:
        user = await self._get_or_raise(user_id)
        user.status = payload.status.value
        updated = await self._users.update(user)
        await self._session.commit()
        return self._to_response(updated)

    async def reset_password(
        self, user_id: int, payload: CustomerUserResetPassword
    ) -> CustomerUserResponse:
        user = await self._get_or_raise(user_id)
        user.password_hash = hash_password(payload.password)
        user.must_change_password = payload.must_change_password
        updated = await self._users.update(user)
        await self._session.commit()
        logger.info("Customer user password reset id=%s", user_id)
        return self._to_response(updated)

    async def delete_user(self, user_id: int) -> None:
        user = await self._get_or_raise(user_id)
        await self._users.delete(user)
        await self._session.commit()
        logger.info("Customer user deleted id=%s", user_id)
