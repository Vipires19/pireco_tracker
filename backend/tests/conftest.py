import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import db_manager
from app.main import app


@pytest.fixture(autouse=True)
async def database_lifecycle() -> None:
    db_manager.init()
    yield
    await db_manager.close()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
