from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.identity.services import AuthService
from app.kernel.logger import get_logger

logger = get_logger(__name__)

BOOTSTRAP_ADMIN_EMAIL = "admin@example.com"
LEGACY_BOOTSTRAP_EMAILS = ("admin@local", "admin@tracker.local")
BOOTSTRAP_ADMIN_PASSWORD = "admin123"
BOOTSTRAP_ADMIN_NAME = "Administrador"
BOOTSTRAP_ADMIN_ROLE = "admin"


async def run_bootstrap(session: AsyncSession) -> None:
    service = AuthService(session)

    for legacy_email in LEGACY_BOOTSTRAP_EMAILS:
        legacy_user = await service._users.get_by_email(legacy_email)
        if legacy_user is not None:
            legacy_user.email = BOOTSTRAP_ADMIN_EMAIL
            await session.commit()
            logger.info(
                "Migrated legacy bootstrap email %s -> %s",
                legacy_email,
                BOOTSTRAP_ADMIN_EMAIL,
            )
            break

    user_count = await service._users.count()
    if user_count > 0:
        logger.info("Bootstrap skipped: users already exist")
        return

    await service.create_user_with_role(
        email=BOOTSTRAP_ADMIN_EMAIL,
        password=BOOTSTRAP_ADMIN_PASSWORD,
        full_name=BOOTSTRAP_ADMIN_NAME,
        role_slug=BOOTSTRAP_ADMIN_ROLE,
    )
    await session.commit()
    logger.info("Bootstrap admin user created email=%s", BOOTSTRAP_ADMIN_EMAIL)
