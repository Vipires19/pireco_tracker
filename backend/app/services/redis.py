import redis.asyncio as redis

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RedisService:
    def __init__(self) -> None:
        self._client: redis.Redis | None = None

    async def connect(self) -> None:
        settings = get_settings()
        self._client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        await self._client.ping()
        logger.info("Redis connected")

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info("Redis disconnected")

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            raise RuntimeError("Redis client not initialized")
        return self._client

    async def ping(self) -> bool:
        return bool(await self.client.ping())

    async def stream_length(self, stream_key: str) -> int:
        return await self.client.xlen(stream_key)


redis_service = RedisService()
