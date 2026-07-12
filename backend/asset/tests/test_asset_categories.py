import pytest
from httpx import AsyncClient
from app.core.dependencies.auth import (
    user_repository_instance,
    asset_category_repository_instance
)
from app.domain.user import User, Role
from app.security.password import hash_password

pytestmark = pytest.mark.asyncio


async def _create_admin_and_login(client: AsyncClient):
    """Helper to seed admin and return headers."""
    user_repository_instance._users.clear()
    asset_category_repository_instance._categories.clear()
    
    pwd = "AdminPass123!"
    admin = User(email="admin-cat@assetflow.com", hashed_password=hash_password(pwd), name="Admin User", role=Role.ADMIN)
    await user_repository_instance.create(admin)
    
    form_data = {"username": admin.email, "password": pwd}
    res = await client.post("/api/v1/auth/login", data=form_data)
    token = res.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_create_and_read_category(client: AsyncClient):
    """Verify registration and reading of Asset Categories with custom fields."""
    headers = await _create_admin_and_login(client)
    
    payload = {
        "name": "Laptops",
        "description": "Company-provided laptop computers",
        "custom_fields": [
            {"name": "Warranty Expire", "type": "DATE", "required": True},
            {"name": "RAM Size", "type": "NUMBER", "required": False}
        ]
    }
    response = await client.post("/api/v1/asset-categories", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "Laptops"
    assert len(data["custom_fields"]) == 2
    
    # Read category
    res_get = await client.get(f"/api/v1/asset-categories/{data['id']}", headers=headers)
    assert res_get.status_code == 200
    assert res_get.json()["data"]["name"] == "Laptops"


async def test_custom_fields_validation_failures(client: AsyncClient):
    """Verify validation constraints block bad field schemas."""
    headers = await _create_admin_and_login(client)
    
    # 1. Invalid Field Type
    payload_bad_type = {
        "name": "Electronics",
        "custom_fields": [
            {"name": "Voltage", "type": "FLOAT", "required": True}  # FLOAT is invalid, only TEXT/NUMBER/DATE/BOOLEAN
        ]
    }
    res_bad_type = await client.post("/api/v1/asset-categories", json=payload_bad_type, headers=headers)
    assert res_bad_type.status_code == 422  # Handled by Pydantic literal validation
    
    # 2. Duplicate Custom Field Names (fails in service business layer)
    payload_dup = {
        "name": "Vehicles",
        "custom_fields": [
            {"name": "vin", "type": "TEXT", "required": True},
            {"name": "VIN ", "type": "TEXT", "required": False}  # Duplicate Vin
        ]
    }
    res_dup = await client.post("/api/v1/asset-categories", json=payload_dup, headers=headers)
    assert res_dup.status_code == 422
    assert "Duplicate custom field name" in res_dup.json()["error"]["message"]


async def test_asset_category_duplicate_active_name_rejected(client: AsyncClient):
    """Verify that duplicate category names are rejected among active categories (case-insensitive), but inactive names can be reused."""
    headers = await _create_admin_and_login(client)

    # 1. Create category "Laptops"
    res1 = await client.post("/api/v1/asset-categories", json={"name": "Laptops"}, headers=headers)
    assert res1.status_code == 201
    cat_id = res1.json()["data"]["id"]

    # 2. Attempt to create another "laptops" (different casing) -> Should fail with 409
    res2 = await client.post("/api/v1/asset-categories", json={"name": "laptops"}, headers=headers)
    assert res2.status_code == 409
    assert "already exists" in res2.json()["error"]["message"]

    # 3. Deactivate the first "Laptops" category
    await client.patch(f"/api/v1/asset-categories/{cat_id}/deactivate", headers=headers)

    # 4. Attempt to create "laptops" again -> Should now succeed
    res3 = await client.post("/api/v1/asset-categories", json={"name": "laptops"}, headers=headers)
    assert res3.status_code == 201


async def test_deactivate_category_blocked_by_active_assets(client: AsyncClient):
    """Verify that deactivating a category is blocked when referenced by active assets, but allowed if only retired/disposed assets exist."""
    headers = await _create_admin_and_login(client)

    # 1. Create a category
    res_cat = await client.post("/api/v1/asset-categories", json={"name": "Furniture"}, headers=headers)
    assert res_cat.status_code == 201
    cat_id = res_cat.json()["data"]["id"]

    # 2. Register an asset referencing this category (starts as AVAILABLE/active)
    res_asset = await client.post("/api/v1/assets", json={
        "name": "Ergonomic Chair",
        "category_id": cat_id,
        "serial_number": "CHAIR-001",
        "acquisition_date": "2026-07-12T00:00:00Z",
        "acquisition_cost": 299.99,
        "condition": "NEW",
        "location": "HQ"
    }, headers=headers)
    assert res_asset.status_code == 201
    asset_id = res_asset.json()["data"]["id"]

    # 3. Attempt to deactivate category -> Should fail with 409 and clear message
    res_deact = await client.patch(f"/api/v1/asset-categories/{cat_id}/deactivate", headers=headers)
    assert res_deact.status_code == 409
    assert "Cannot deactivate category: 1 active asset(s) still reference this category." in res_deact.json()["error"]["message"]

    # 4. Retire the asset (makes it inactive/terminal)
    res_retire = await client.patch(f"/api/v1/assets/{asset_id}/retire", headers=headers)
    assert res_retire.status_code == 200
    assert res_retire.json()["data"]["status"] == "RETIRED"

    # 5. Attempt to deactivate category again -> Should now succeed
    res_deact2 = await client.patch(f"/api/v1/asset-categories/{cat_id}/deactivate", headers=headers)
    assert res_deact2.status_code == 200
    assert res_deact2.json()["data"]["is_active"] is False
