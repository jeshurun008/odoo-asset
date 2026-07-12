import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_security_headers_present(client: AsyncClient):
    """Test that standard security headers are applied to the response."""
    response = await client.get("/")
    assert response.status_code == 200
    
    headers = response.headers
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-XSS-Protection") == "1; mode=block"
    assert "default-src 'self'" in headers.get("Content-Security-Policy", "")
    assert headers.get("Referrer-Policy") == "no-referrer"


async def test_correlation_id_generated_and_returned(client: AsyncClient):
    """Test that correlation and request IDs are generated and returned in headers."""
    response = await client.get("/")
    assert response.status_code == 200
    
    assert "X-Correlation-Id" in response.headers
    assert "X-Request-Id" in response.headers
    assert len(response.headers["X-Correlation-Id"]) > 0


async def test_correlation_id_propagates_from_request(client: AsyncClient):
    """Test that an incoming X-Correlation-Id header is propagated to the response."""
    custom_corr_id = "test-custom-correlation-123"
    headers = {"X-Correlation-Id": custom_corr_id}
    
    response = await client.get("/", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("X-Correlation-Id") == custom_corr_id
