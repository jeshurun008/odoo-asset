import asyncio
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.core.dependencies.auth import user_repository_instance, token_store_instance


@pytest.fixture(autouse=True)
async def clear_in_memory_databases():
    """
    Cleans up mock in-memory stores before each test scenario to ensure
    absolute isolation between test runs.
    """
    user_repository_instance._users.clear()
    token_store_instance._tokens.clear()
    yield


@pytest.fixture
async def client():
    """Generates an HTTPX AsyncClient bound directly to the FastAPI ASGI application."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac
