from datetime import UTC, datetime

import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.domains.identity.models import RefreshToken, User
from app.domains.identity.repositories import (
    LoginAuditRepository,
    RefreshTokenRepository,
    RoleRepository,
    UserRepository,
)
from app.domains.identity.schemas import LoginRequest, LoginResponse, UserResponse
from app.kernel.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.services.redis import redis_service
from app.kernel.logger import get_logger

logger = get_logger(__name__)


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._roles = RoleRepository(session)
        self._refresh_tokens = RefreshTokenRepository(session)
        self._audit = LoginAuditRepository(session)

    async def check_rate_limit(self, ip_address: str | None) -> bool:
        settings = get_settings()
        if not ip_address:
            return True
        key = f"ratelimit:login:{ip_address}"
        try:
            client = redis_service.client
        except RuntimeError:
            return True
        count = await client.incr(key)
        if count == 1:
            await client.expire(key, settings.login_rate_limit_window_seconds)
        return count <= settings.login_rate_limit

    async def login(
        self,
        payload: LoginRequest,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[LoginResponse, str]:
        settings = get_settings()
        email = payload.email.lower()

        if not await self.check_rate_limit(ip_address):
            await self._audit.create(
                email=email,
                success=False,
                ip_address=ip_address,
                user_agent=user_agent,
                failure_reason="rate_limit_exceeded",
            )
            await self._session.commit()
            raise ValueError("rate_limit_exceeded")

        user = await self._users.get_by_email(email)
        if user is None or not verify_password(user.password_hash, payload.password):
            await self._audit.create(
                email=email,
                success=False,
                user_id=user.id if user else None,
                ip_address=ip_address,
                user_agent=user_agent,
                failure_reason="invalid_credentials",
            )
            await self._session.commit()
            raise ValueError("invalid_credentials")

        if not user.is_active:
            await self._audit.create(
                email=email,
                success=False,
                user_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
                failure_reason="user_inactive",
            )
            await self._session.commit()
            raise ValueError("user_inactive")

        access_token = create_access_token(
            str(user.id),
            {"email": user.email, "roles": [r.slug for r in user.roles]},
        )
        refresh_token, jti, expires_at = create_refresh_token(str(user.id))
        await self._refresh_tokens.create(
            RefreshToken(
                user_id=user.id,
                token_jti=jti,
                expires_at=expires_at,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        )
        await self._audit.create(
            email=email,
            success=True,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self._session.commit()

        logger.info("User logged in user_id=%s email=%s", user.id, user.email)
        return LoginResponse(
            access_token=access_token,
            expires_in=settings.jwt_access_token_expire_minutes * 60,
            user=UserResponse.model_validate(user),
        ), refresh_token

    async def refresh(
        self,
        refresh_token: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[str, int, str]:
        settings = get_settings()
        try:
            payload = decode_token(refresh_token)
        except jwt.PyJWTError as exc:
            raise ValueError("invalid_refresh_token") from exc

        if payload.get("type") != "refresh":
            raise ValueError("invalid_refresh_token")

        jti = payload.get("jti")
        user_id = payload.get("sub")
        if not jti or not user_id:
            raise ValueError("invalid_refresh_token")

        stored = await self._refresh_tokens.get_by_jti(jti)
        if stored is None or stored.revoked_at is not None:
            raise ValueError("invalid_refresh_token")
        if stored.expires_at < datetime.now(UTC):
            raise ValueError("refresh_token_expired")

        user = await self._users.get_by_id(int(user_id))
        if user is None or not user.is_active:
            raise ValueError("user_inactive")

        await self._refresh_tokens.revoke(stored)
        new_access = create_access_token(
            str(user.id),
            {"email": user.email, "roles": [r.slug for r in user.roles]},
        )
        new_refresh, new_jti, expires_at = create_refresh_token(str(user.id))
        await self._refresh_tokens.create(
            RefreshToken(
                user_id=user.id,
                token_jti=new_jti,
                expires_at=expires_at,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        )
        await self._session.commit()
        return new_access, settings.jwt_access_token_expire_minutes * 60, new_refresh

    async def logout(self, refresh_token: str | None) -> None:
        if not refresh_token:
            return
        try:
            payload = decode_token(refresh_token)
        except jwt.PyJWTError:
            return
        jti = payload.get("jti")
        if not jti:
            return
        stored = await self._refresh_tokens.get_by_jti(jti)
        if stored and stored.revoked_at is None:
            await self._refresh_tokens.revoke(stored)
            await self._session.commit()

    async def get_user(self, user_id: int) -> User | None:
        return await self._users.get_by_id(user_id)

    async def create_user_with_role(
        self,
        *,
        email: str,
        password: str,
        full_name: str,
        role_slug: str,
    ) -> User:
        role = await self._roles.get_by_slug(role_slug)
        if role is None:
            raise ValueError(f"role_not_found:{role_slug}")

        user = User(
            email=email.lower(),
            password_hash=hash_password(password),
            full_name=full_name,
            is_active=True,
            roles=[role],
        )
        return await self._users.create(user)
