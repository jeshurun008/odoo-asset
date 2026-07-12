import pytest
from datetime import datetime, timezone
from httpx import AsyncClient
from app.core.dependencies.auth import (
    user_repository_instance,
    asset_category_repository_instance,
    asset_repository_instance
)
from app.domain.user import User, Role
from app.domain.asset_category import AssetCategory
from app.security.password import hash_password

pytestmark = pytest.mark.asyncio


async def _create_admin_and_login(client: AsyncClient):
    """Helper to seed admin and return headers."""
    user_repository_instance._users.clear()
    asset_category_repository_instance._categories.clear()
    asset_repository_instance._assets.clear()
    asset_repository_instance._tag_counter = 0

    pwd = "AdminPass123!"
    admin = User(email="admin-asset@assetflow.com", hashed_password=hash_password(pwd), name="Admin User", role=Role.ADMIN)
    await user_repository_instance.create(admin)

    form_data = {"username": admin.email, "password": pwd}
    res = await client.post("/api/v1/auth/login", data=form_data)
    token = res.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_register_asset_success(client: AsyncClient):
    """Verify that registering an asset auto-generates the tag and links to active category."""
    headers = await _create_admin_and_login(client)

    # Seed active Category
    category = AssetCategory(name="Electronics", description="Electronics category")
    await asset_category_repository_instance.create(category)

    payload = {
        "name": "MacBook Pro M3",
        "category_id": category.id,
        "serial_number": "SN-MAC-0001",
        "acquisition_date": "2026-07-12T00:00:00Z",
        "acquisition_cost": 2499.99,
        "condition": "NEW",
        "location": "HQ - Floor 3"
    }

    # 1. First registration -> tag AF-0001
    res1 = await client.post("/api/v1/assets", json=payload, headers=headers)
    assert res1.status_code == 201
    data1 = res1.json()["data"]
    assert data1["asset_tag"] == "AF-0001"
    assert data1["status"] == "AVAILABLE"

    # 2. Second registration (different serial) -> tag AF-0002
    payload["serial_number"] = "SN-MAC-0002"
    res2 = await client.post("/api/v1/assets", json=payload, headers=headers)
    assert res2.status_code == 201
    data2 = res2.json()["data"]
    assert data2["asset_tag"] == "AF-0002"


async def test_register_asset_inactive_category_rejected(client: AsyncClient):
    """Verify registration fails if category is inactive."""
    headers = await _create_admin_and_login(client)

    # Seed inactive Category
    category = AssetCategory(name="Furniture", description="Furniture category", is_active=False)
    await asset_category_repository_instance.create(category)

    payload = {
        "name": "Office Desk",
        "category_id": category.id,
        "serial_number": "SN-DESK-0001",
        "acquisition_date": "2026-07-12T00:00:00Z",
        "acquisition_cost": 350.00,
        "condition": "GOOD",
        "location": "HQ - Floor 1"
    }
    response = await client.post("/api/v1/assets", json=payload, headers=headers)
    assert response.status_code == 409
    assert "is inactive. Cannot link assets" in response.json()["error"]["message"]


async def test_asset_history_aggregates_properly(client: AsyncClient):
    """Verify GET /assets/{id}/history aggregates allocation records, transfer logs and stubs maintenance logs."""
    headers = await _create_admin_and_login(client)

    # Seed Category
    category = AssetCategory(name="Electronics")
    await asset_category_repository_instance.create(category)

    # Seed Users
    priya = User(email="priya@assetflow.com", hashed_password=hash_password("Pass123!"), name="Priya", role=Role.EMPLOYEE)
    raj = User(email="raj@assetflow.com", hashed_password=hash_password("Pass123!"), name="Raj", role=Role.EMPLOYEE)
    await user_repository_instance.create(priya)
    await user_repository_instance.create(raj)

    # 1. Seed asset
    res_asset = await client.post("/api/v1/assets", json={
        "name": "Test Asset",
        "category_id": category.id,
        "serial_number": "SN-TEST-1234",
        "acquisition_date": "2026-07-12T00:00:00Z",
        "acquisition_cost": 100.0,
        "condition": "GOOD",
        "location": "HQ"
    }, headers=headers)
    asset_id = res_asset.json()["data"]["id"]

    # 2. Check out asset to Priya
    await client.post("/api/v1/allocations", json={
        "asset_id": asset_id,
        "allocated_to_type": "EMPLOYEE",
        "allocated_to_id": priya.id
    }, headers=headers)

    # 3. Create Transfer request to Raj
    await client.post("/api/v1/transfers", json={
        "asset_id": asset_id,
        "requested_to_type": "EMPLOYEE",
        "requested_to_id": raj.id,
        "reason": "Development needs"
    }, headers=headers)

    # 4. Query asset history
    response = await client.get(f"/api/v1/assets/{asset_id}/history", headers=headers)
    assert response.status_code == 200
    history = response.json()["data"]
    assert history["asset_id"] == asset_id
    assert len(history["allocations"]) == 1
    assert len(history["transfers"]) == 1
    assert history["maintenance_history"] == []  # Phase 4 stub check
