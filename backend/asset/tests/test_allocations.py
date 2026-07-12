import pytest
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient
from app.core.dependencies.auth import (
    user_repository_instance,
    asset_category_repository_instance,
    asset_repository_instance,
    allocation_repository_instance,
    department_repository_instance
)
from app.domain.user import User, Role
from app.domain.asset import Asset, AssetStatus
from app.domain.asset_category import AssetCategory
from app.security.password import hash_password

pytestmark = pytest.mark.asyncio


async def _seed_data(client: AsyncClient):
    """Helper to seed directory database elements."""
    user_repository_instance._users.clear()
    asset_category_repository_instance._categories.clear()
    asset_repository_instance._assets.clear()
    allocation_repository_instance._allocations.clear()

    # Admin
    pwd = "Password123!"
    admin = User(email="admin-alloc@assetflow.com", hashed_password=hash_password(pwd), name="Admin User", role=Role.ADMIN)
    await user_repository_instance.create(admin)

    # Employee Priya
    priya = User(email="priya@assetflow.com", hashed_password=hash_password(pwd), name="Priya", role=Role.EMPLOYEE)
    await user_repository_instance.create(priya)

    # Employee Raj
    raj = User(email="raj@assetflow.com", hashed_password=hash_password(pwd), name="Raj", role=Role.EMPLOYEE)
    await user_repository_instance.create(raj)

    # Category & Asset
    cat = AssetCategory(name="Electronics")
    await asset_category_repository_instance.create(cat)
    asset = Asset(
        name="Dell Monitor",
        category_id=cat.id,
        serial_number="SN-MONITOR",
        acquisition_date="2026-07-12T00:00:00Z",
        acquisition_cost=300.0,
        condition="NEW",
        location="HQ",
        asset_tag="AF-0001"
    )
    await asset_repository_instance.create(asset)

    # Login Admin
    form_data = {"username": admin.email, "password": pwd}
    res = await client.post("/api/v1/auth/login", data=form_data)
    token = res.json()["data"]["access_token"]
    
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "admin": admin,
        "priya": priya,
        "raj": raj,
        "asset": asset
    }


async def test_allocation_success_and_double_allocation_blocked(client: AsyncClient):
    """Verify that allocating an asset succeeds and subsequent checkouts fail with holder details."""
    data = await _seed_data(client)
    headers = data["headers"]

    # 1. Allocate Dell Monitor to Priya
    payload = {
        "asset_id": data["asset"].id,
        "allocated_to_type": "EMPLOYEE",
        "allocated_to_id": data["priya"].id,
        "expected_return_date": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
    }
    response = await client.post("/api/v1/allocations", json=payload, headers=headers)
    assert response.status_code == 201
    assert response.json()["data"]["status"] == "ACTIVE"

    # Verify Asset is now ALLOCATED status
    asset = await asset_repository_instance.get_by_id(data["asset"].id)
    assert asset.status == AssetStatus.ALLOCATED

    # 2. Attempt to allocate the same Dell Monitor to Raj -> Should fail with double-allocation 409
    payload_raj = {
        "asset_id": data["asset"].id,
        "allocated_to_type": "EMPLOYEE",
        "allocated_to_id": data["raj"].id
    }
    res_fail = await client.post("/api/v1/allocations", json=payload_raj, headers=headers)
    assert res_fail.status_code == 409
    assert "currently held by Priya" in res_fail.json()["error"]["message"]


async def test_allocation_return_checkin(client: AsyncClient):
    """Verify returning an allocated asset completes check-in and resets asset status."""
    data = await _seed_data(client)
    headers = data["headers"]

    # Allocate to Priya
    res_alloc = await client.post("/api/v1/allocations", json={
        "asset_id": data["asset"].id,
        "allocated_to_type": "EMPLOYEE",
        "allocated_to_id": data["priya"].id
    }, headers=headers)
    alloc_id = res_alloc.json()["data"]["id"]

    # Return Check-in
    payload = {"condition_check_in_notes": "Returned in pristine condition, screen clean."}
    response = await client.patch(f"/api/v1/allocations/{alloc_id}/return", json=payload, headers=headers)
    assert response.status_code == 200
    
    data_ret = response.json()["data"]
    assert data_ret["status"] == "RETURNED"
    assert data_ret["condition_check_in_notes"] == "Returned in pristine condition, screen clean."

    # Verify Asset is now back to AVAILABLE status
    asset = await asset_repository_instance.get_by_id(data["asset"].id)
    assert asset.status == AssetStatus.AVAILABLE


async def test_overdue_allocations_listing(client: AsyncClient):
    """Verify that overdue allocations can be filtered correctly."""
    data = await _seed_data(client)
    headers = data["headers"]

    # Allocate to Priya with expected_return_date in the past (overdue)
    past_date = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    await client.post("/api/v1/allocations", json={
        "asset_id": data["asset"].id,
        "allocated_to_type": "EMPLOYEE",
        "allocated_to_id": data["priya"].id,
        "expected_return_date": past_date
    }, headers=headers)

    # Query overdue allocations listing
    res_list = await client.get("/api/v1/allocations?overdue=true", headers=headers)
    assert res_list.status_code == 200
    items = res_list.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["status"] == "OVERDUE"


async def test_rbac_allocation_endpoints(client: AsyncClient):
    """Verify that Employees are blocked from creating allocations."""
    data = await _seed_data(client)
    pwd = "Password123!"
    headers_emp = await _create_user_and_login_headers(client, "some-emp@assetflow.com", pwd, Role.EMPLOYEE)

    payload = {
        "asset_id": data["asset"].id,
        "allocated_to_type": "EMPLOYEE",
        "allocated_to_id": data["priya"].id
    }
    response = await client.post("/api/v1/allocations", json=payload, headers=headers_emp)
    assert response.status_code == 403


async def test_return_scoping_blocks_other_department_head(client: AsyncClient):
    """Verify that a Department Head is blocked from checking in assets belonging to another department, but can return assets from their own department."""
    data = await _seed_data(client)
    headers_admin = data["headers"]
    pwd = "Password123!"

    # 1. Seed two departments
    from app.domain.department import Department
    dept_a = Department(name="Dept A")
    dept_b = Department(name="Dept B")
    await department_repository_instance.create(dept_a)
    await department_repository_instance.create(dept_b)

    # 2. Seed two department heads
    head_a = User(email="heada@assetflow.com", hashed_password=hash_password(pwd), name="Head A", role=Role.DEPARTMENT_HEAD, department_id=dept_a.id)
    head_b = User(email="headb@assetflow.com", hashed_password=hash_password(pwd), name="Head B", role=Role.DEPARTMENT_HEAD, department_id=dept_b.id)
    await user_repository_instance.create(head_a)
    await user_repository_instance.create(head_b)

    # Log in both heads
    headers_head_a = await _create_user_and_login_headers(client, head_a.email, pwd, Role.DEPARTMENT_HEAD)
    headers_head_b = await _create_user_and_login_headers(client, head_b.email, pwd, Role.DEPARTMENT_HEAD)

    # 3. Create allocation for Dept B
    res_alloc = await client.post("/api/v1/allocations", json={
        "asset_id": data["asset"].id,
        "allocated_to_type": "DEPARTMENT",
        "allocated_to_id": dept_b.id
    }, headers=headers_admin)
    assert res_alloc.status_code == 201
    alloc_id = res_alloc.json()["data"]["id"]

    # 4. Department Head A attempts to check it in -> Should block with 403
    res_fail = await client.patch(f"/api/v1/allocations/{alloc_id}/return", json={"condition_check_in_notes": "Cleaned"}, headers=headers_head_a)
    assert res_fail.status_code == 403
    assert "Department heads can only check-in" in res_fail.json()["error"]["message"]

    # 5. Department Head B checks it in -> Should succeed with 200
    res_ok = await client.patch(f"/api/v1/allocations/{alloc_id}/return", json={"condition_check_in_notes": "Cleaned"}, headers=headers_head_b)
    assert res_ok.status_code == 200


async def _create_user_and_login_headers(client: AsyncClient, email: str, pwd: str, role: Role) -> dict:
    found = None
    for u in user_repository_instance._users.values():
        if u.email == email:
            found = u
            break
    if not found:
        user = User(email=email, hashed_password=hash_password(pwd), name="User Temp", role=role)
        await user_repository_instance.create(user)
    
    form_data = {"username": email, "password": pwd}
    res = await client.post("/api/v1/auth/login", data=form_data)
    token = res.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
