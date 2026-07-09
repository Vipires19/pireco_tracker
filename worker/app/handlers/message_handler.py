from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.messages import DomainMessage
from app.core.observability import get_logger

from app.services.persistence import PersistenceService

logger = get_logger(__name__)


class MessageHandler:
    def __init__(self, persistence: PersistenceService) -> None:
        self._persistence = persistence

    async def handle(self, session: AsyncSession, message: DomainMessage) -> None:
        await self._persistence.process(session, message)
