import pytest
from httpx import AsyncClient
from app.core.dependencies.auth import (
    user_repository_instance,
    asset_category_repository_instance,
    asset_repository_instance
)
from app.domain.user import User, Role
from app.domain.asset import Asset, AssetStatus
from app.domain.asset_category import AssetCategory
from app.security.password import hash_password

pytestmark = pytest.mark.asyncio


async def _create_user_and_login(client: AsyncClient, email: str, role: Role):
    """Helper to seed a user and return auth headers."""
    pwd = "Password123!"
    user = User(email=email, hashed_password=hash_password(pwd), name="Test User", role=role)
    await user_repository_instance.create(user)

    form_data = {"username": email, "password": pwd}
    res = await client.post("/api/v1/auth/login", data=form_data)
    token = res.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_valid_lifecycle_transitions(client: AsyncClient):
    """Verify that manual endpoints execute valid transitions successfully."""
    user_repository_instance._users.clear()
    asset_category_repository_instance._categories.clear()
    asset_repository_instance._assets.clear()
    
    headers = await _create_user_and_login(client, "admin-lc@assetflow.com", Role.ADMIN)

    # Seed Category & Asset
    cat = AssetCategory(name="Laptops")
    await asset_category_repository_instance.create(cat)
    asset = Asset(
        name="Dell XPS",
        category_id=cat.id,
        serial_number="SN-DELL-999",
        acquisition_date="2026-07-12T00:00:00Z",
        acquisition_cost=1500.0,
        condition="GOOD",
        location="HQ",
        asset_tag="AF-0001"
    )
    await asset_repository_instance.create(asset)

    # 1. AVAILABLE -> RESERVED
    res1 = await client.patch(f"/api/v1/assets/{asset.id}/reserve", headers=headers)
    assert res1.status_code == 200
    assert res1.json()["data"]["status"] == "RESERVED"

    # 2. RESERVED -> AVAILABLE (Release)
    res2 = await client.patch(f"/api/v1/assets/{asset.id}/release", headers=headers)
    assert res2.status_code == 200
    assert res2.json()["data"]["status"] == "AVAILABLE"

    # 3. AVAILABLE -> LOST
    res3 = await client.patch(f"/api/v1/assets/{asset.id}/mark-lost", headers=headers)
    assert res3.status_code == 200
    assert res3.json()["data"]["status"] == "LOST"

    # 4. LOST -> RETIRED
    res4 = await client.patch(f"/api/v1/assets/{asset.id}/retire", headers=headers)
    assert res4.status_code == 200
    assert res4.json()["data"]["status"] == "RETIRED"

    # 5. RETIRED -> DISPOSED
    res5 = await client.patch(f"/api/v1/assets/{asset.id}/dispose", headers=headers)
    assert res5.status_code == 200
    assert res5.json()["data"]["status"] == "DISPOSED"


async def test_invalid_lifecycle_transitions_rejected(client: AsyncClient):
    """Verify that illegal lifecycle transitions are rejected with 409 Conflict."""
    user_repository_instance._users.clear()
    asset_category_repository_instance._categories.clear()
    asset_repository_instance._assets.clear()
    
    headers = await _create_user_and_login(client, "admin-lc-fail@assetflow.com", Role.ADMIN)

    # Seed Category & Asset
    cat = AssetCategory(name="Laptops")
    await asset_category_repository_instance.create(cat)
    asset = Asset(
        name="Dell XPS",
        category_id=cat.id,
        serial_number="SN-DELL-888",
        acquisition_date="2026-07-12T00:00:00Z",
        acquisition_cost=1500.0,
        condition="GOOD",
        location="HQ",
        status=AssetStatus.DISPOSED,  # Start directly at DISPOSED (terminal)
        asset_tag="AF-0002"
    )
    await asset_repository_instance.create(asset)

    # Try transitioning DISPOSED -> AVAILABLE (release) -> Should fail 409
    res = await client.patch(f"/api/v1/assets/{asset.id}/release", headers=headers)
    assert res.status_code == 409
    assert "Invalid lifecycle transition" in res.json()["error"]["message"]


async def test_rbac_lifecycle_endpoints(client: AsyncClient):
    """Verify that only Admin and Asset Manager can access lifecycle mutations, but Employees are blocked."""
    user_repository_instance._users.clear()
    asset_category_repository_instance._categories.clear()
    asset_repository_instance._assets.clear()

    # Seed Category & Asset
    cat = AssetCategory(name="Laptops")
    await asset_category_repository_instance.create(cat)
    asset = Asset(
        name="MacBook",
        category_id=cat.id,
        serial_number="SN-MAC-LC",
        acquisition_date="2026-07-12T00:00:00Z",
        acquisition_cost=1500.0,
        condition="GOOD",
        location="HQ",
        asset_tag="AF-0003"
    )
    await asset_repository_instance.create(asset)

    # 1. Login as Employee
    headers_emp = await _create_user_and_login(client, "emp-lc@assetflow.com", Role.EMPLOYEE)
    # Attempt to reserve -> Should be forbidden (403)
    res_emp = await client.patch(f"/api/v1/assets/{asset.id}/reserve", headers=headers_emp)
    assert res_emp.status_code == 403

    # 2. Login as Asset Manager
    headers_mgr = await _create_user_and_login(client, "mgr-lc@assetflow.com", Role.ASSET_MANAGER)
    # Attempt to reserve -> Should succeed (200)
    res_mgr = await client.patch(f"/api/v1/assets/{asset.id}/reserve", headers=headers_mgr)
    assert res_mgr.status_code == 200
