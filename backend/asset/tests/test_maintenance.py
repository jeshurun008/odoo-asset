import pytest
from httpx import AsyncClient
from app.core.dependencies.auth import (
    user_repository_instance,
    asset_category_repository_instance,
    asset_repository_instance,
    maintenance_request_repository_instance,
    allocation_repository_instance
)
from app.domain.user import User, Role
from app.domain.asset import Asset, AssetStatus
from app.domain.asset_category import AssetCategory
from app.domain.maintenance_request import MaintenancePriority, MaintenanceStatus
from app.security.password import hash_password

pytestmark = pytest.mark.asyncio


async def _seed_data(client: AsyncClient):
    """Helper to seed directory database elements."""
    user_repository_instance._users.clear()
    asset_category_repository_instance._categories.clear()
    asset_repository_instance._assets.clear()
    maintenance_request_repository_instance._requests.clear()
    allocation_repository_instance._allocations.clear()

    pwd = "Password123!"
    admin = User(email="admin-maint@assetflow.com", hashed_password=hash_password(pwd), name="Admin User", role=Role.ADMIN)
    await user_repository_instance.create(admin)

    emp = User(email="emp-maint@assetflow.com", hashed_password=hash_password(pwd), name="Employee", role=Role.EMPLOYEE)
    await user_repository_instance.create(emp)

    cat = AssetCategory(name="Electronics")
    await asset_category_repository_instance.create(cat)

    asset = Asset(
        name="Lobby Display TV",
        category_id=cat.id,
        serial_number="TV-123",
        acquisition_date="2026-07-12T00:00:00Z",
        acquisition_cost=999.99,
        condition="GOOD",
        location="Lobby",
        asset_tag="AF-0001"
    )
    await asset_repository_instance.create(asset)

    # Login Admin
    form_admin = {"username": admin.email, "password": pwd}
    res_admin = await client.post("/api/v1/auth/login", data=form_admin)
    token_admin = res_admin.json()["data"]["access_token"]

    # Login Employee
    form_emp = {"username": emp.email, "password": pwd}
    res_emp = await client.post("/api/v1/auth/login", data=form_emp)
    token_emp = res_emp.json()["data"]["access_token"]

    return {
        "admin_headers": {"Authorization": f"Bearer {token_admin}"},
        "emp_headers": {"Authorization": f"Bearer {token_emp}"},
        "emp": emp,
        "asset": asset
    }


async def test_raise_maintenance_request_success(client: AsyncClient):
    """Verify that raising a maintenance request succeeds."""
    data = await _seed_data(client)
    headers = data["emp_headers"]

    payload = {
        "asset_id": data["asset"].id,
        "issue_description": "Screen is flickering heavily",
        "priority": "HIGH"
    }

    response = await client.post("/api/v1/maintenance-requests", json=payload, headers=headers)
    assert response.status_code == 201
    assert response.json()["data"]["status"] == "PENDING"


async def test_duplicate_maintenance_requests_blocked(client: AsyncClient):
    """Verify that only one unresolved maintenance request can be open at a time."""
    data = await _seed_data(client)
    headers = data["emp_headers"]

    payload = {
        "asset_id": data["asset"].id,
        "issue_description": "Screen is flickering heavily",
        "priority": "HIGH"
    }

    # Raise first
    await client.post("/api/v1/maintenance-requests", json=payload, headers=headers)

    # Attempt second -> Should fail 409
    response = await client.post("/api/v1/maintenance-requests", json=payload, headers=headers)
    assert response.status_code == 409
    assert "active maintenance request is already open" in response.json()["error"]["message"]


async def test_maintenance_workflow_path(client: AsyncClient):
    """Verify complete transition workflow PENDING -> APPROVED -> ASSIGNED -> IN_PROGRESS -> RESOLVED."""
    data = await _seed_data(client)
    headers_emp = data["emp_headers"]
    headers_admin = data["admin_headers"]
    asset_id = data["asset"].id

    # 1. Employee raises request
    res_raise = await client.post("/api/v1/maintenance-requests", json={
        "asset_id": asset_id,
        "issue_description": "Inspect fan noise",
        "priority": "MEDIUM"
    }, headers=headers_emp)
    request_id = res_raise.json()["data"]["id"]

    # Verify asset is still AVAILABLE
    asset = await asset_repository_instance.get_by_id(asset_id)
    assert asset.status == AssetStatus.AVAILABLE

    # 2. Admin approves request -> Asset becomes UNDER_MAINTENANCE
    res_app = await client.patch(f"/api/v1/maintenance-requests/{request_id}/approve", headers=headers_admin)
    assert res_app.status_code == 200
    assert res_app.json()["data"]["status"] == "APPROVED"
    
    asset = await asset_repository_instance.get_by_id(asset_id)
    assert asset.status == AssetStatus.UNDER_MAINTENANCE

    # 3. Admin assigns technician
    res_assign = await client.patch(f"/api/v1/maintenance-requests/{request_id}/assign-technician", json={
        "assigned_technician": "John Doe"
    }, headers=headers_admin)
    assert res_assign.status_code == 200
    assert res_assign.json()["data"]["assigned_technician"] == "John Doe"

    # 4. Admin starts work
    res_start = await client.patch(f"/api/v1/maintenance-requests/{request_id}/start", headers=headers_admin)
    assert res_start.status_code == 200
    assert res_start.json()["data"]["status"] == "IN_PROGRESS"

    # 5. Admin resolves request -> Asset returns to AVAILABLE (prior status)
    res_resolve = await client.patch(f"/api/v1/maintenance-requests/{request_id}/resolve", headers=headers_admin)
    assert res_resolve.status_code == 200
    assert res_resolve.json()["data"]["status"] == "RESOLVED"

    asset = await asset_repository_instance.get_by_id(asset_id)
    assert asset.status == AssetStatus.AVAILABLE


async def test_maintenance_resolution_reverts_to_allocated(client: AsyncClient):
    """Verify that resolving maintenance returns an allocated asset to ALLOCATED status (prior status aware)."""
    data = await _seed_data(client)
    headers_emp = data["emp_headers"]
    headers_admin = data["admin_headers"]
    asset_id = data["asset"].id

    # 1. Allocate asset to employee (status becomes ALLOCATED)
    from app.domain.allocation import AssetAllocation
    alloc = AssetAllocation(
        asset_id=asset_id,
        allocated_to_type="EMPLOYEE",
        allocated_to_id=data["emp"].id,
        allocated_by=data["emp"].id
    )
    await allocation_repository_instance.create(alloc)
    
    # Directly set status to ALLOCATED to simulate checkout
    asset = await asset_repository_instance.get_by_id(asset_id)
    asset.status = AssetStatus.ALLOCATED
    await asset_repository_instance.update(asset)

    # 2. Raise maintenance request
    res_raise = await client.post("/api/v1/maintenance-requests", json={
        "asset_id": asset_id,
        "issue_description": "Clean camera lens",
        "priority": "LOW"
    }, headers=headers_emp)
    request_id = res_raise.json()["data"]["id"]

    # 3. Approve -> Asset goes to UNDER_MAINTENANCE
    await client.patch(f"/api/v1/maintenance-requests/{request_id}/approve", headers=headers_admin)
    asset = await asset_repository_instance.get_by_id(asset_id)
    assert asset.status == AssetStatus.UNDER_MAINTENANCE

    # 4. Assign, start, resolve
    await client.patch(f"/api/v1/maintenance-requests/{request_id}/assign-technician", json={"assigned_technician": "Alice Smith"}, headers=headers_admin)
    await client.patch(f"/api/v1/maintenance-requests/{request_id}/start", headers=headers_admin)
    await client.patch(f"/api/v1/maintenance-requests/{request_id}/resolve", headers=headers_admin)

    # Verify asset is back to ALLOCATED status
    asset = await asset_repository_instance.get_by_id(asset_id)
    assert asset.status == AssetStatus.ALLOCATED


async def test_reject_maintenance_request(client: AsyncClient):
    """Verify that rejecting a request requires a reason and does not touch asset status."""
    data = await _seed_data(client)
    headers_emp = data["emp_headers"]
    headers_admin = data["admin_headers"]
    asset_id = data["asset"].id

    res_raise = await client.post("/api/v1/maintenance-requests", json={
        "asset_id": asset_id,
        "issue_description": "Fix broken key",
        "priority": "LOW"
    }, headers=headers_emp)
    request_id = res_raise.json()["data"]["id"]

    # Attempt reject without reason -> should fail 422 (validation error on payload)
    res_fail = await client.patch(f"/api/v1/maintenance-requests/{request_id}/reject", json={}, headers=headers_admin)
    assert res_fail.status_code == 422

    # Reject with reason -> succeeds, status is REJECTED
    res_ok = await client.patch(f"/api/v1/maintenance-requests/{request_id}/reject", json={"rejected_reason": "No issues found"}, headers=headers_admin)
    assert res_ok.status_code == 200
    assert res_ok.json()["data"]["status"] == "REJECTED"

    # Verify asset status is still AVAILABLE
    asset = await asset_repository_instance.get_by_id(asset_id)
    assert asset.status == AssetStatus.AVAILABLE


async def test_rbac_maintenance_endpoints(client: AsyncClient):
    """Verify that only Admin/Asset Manager can trigger workflow state changes (approve/resolve), blocking employees."""
    data = await _seed_data(client)
    headers_emp = data["emp_headers"]
    headers_admin = data["admin_headers"]
    asset_id = data["asset"].id

    res_raise = await client.post("/api/v1/maintenance-requests", json={
        "asset_id": asset_id,
        "issue_description": "Lens calibration",
        "priority": "HIGH"
    }, headers=headers_emp)
    request_id = res_raise.json()["data"]["id"]

    # Employee tries to approve -> Should fail 403
    res_fail = await client.patch(f"/api/v1/maintenance-requests/{request_id}/approve", headers=headers_emp)
    assert res_fail.status_code == 403

    # Admin approves -> succeeds
    res_ok = await client.patch(f"/api/v1/maintenance-requests/{request_id}/approve", headers=headers_admin)
    assert res_ok.status_code == 200


async def test_history_includes_maintenance(client: AsyncClient):
    """Verify GET /assets/{id}/history aggregates maintenance records."""
    data = await _seed_data(client)
    headers_admin = data["admin_headers"]
    headers_emp = data["emp_headers"]
    asset_id = data["asset"].id

    # Raise maintenance request
    await client.post("/api/v1/maintenance-requests", json={
        "asset_id": asset_id,
        "issue_description": "Clean camera lens",
        "priority": "LOW"
    }, headers=headers_emp)

    response = await client.get(f"/api/v1/assets/{asset_id}/history", headers=headers_admin)
    assert response.status_code == 200
    history = response.json()["data"]
    assert len(history["maintenance_history"]) == 1
    assert history["maintenance_history"][0]["issue_description"] == "Clean camera lens"
