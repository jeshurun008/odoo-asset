import pytest
from httpx import AsyncClient
from app.core.dependencies.auth import (
    user_repository_instance,
    asset_category_repository_instance,
    asset_repository_instance,
    allocation_repository_instance,
    transfer_request_repository_instance
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
    transfer_request_repository_instance._transfers.clear()

    # Admin
    pwd = "Password123!"
    admin = User(email="admin-trans@assetflow.com", hashed_password=hash_password(pwd), name="Admin User", role=Role.ADMIN)
    await user_repository_instance.create(admin)

    # Priya
    priya = User(email="priya@assetflow.com", hashed_password=hash_password(pwd), name="Priya", role=Role.EMPLOYEE)
    await user_repository_instance.create(priya)

    # Raj
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

    # Allocate to Priya
    form_data = {"username": admin.email, "password": pwd}
    res_login = await client.post("/api/v1/auth/login", data=form_data)
    token = res_login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    await client.post("/api/v1/allocations", json={
        "asset_id": asset.id,
        "allocated_to_type": "EMPLOYEE",
        "allocated_to_id": priya.id
    }, headers=headers)
    
    return {
        "headers": headers,
        "admin": admin,
        "priya": priya,
        "raj": raj,
        "asset": asset
    }


async def test_transfer_workflow_approve_success(client: AsyncClient):
    """Verify that requesting and approving a transfer atomically re-allocates the asset."""
    data = await _seed_data(client)
    headers = data["headers"]

    # 1. Raj requests a transfer of Priya's Dell Monitor
    payload = {
        "asset_id": data["asset"].id,
        "requested_to_type": "EMPLOYEE",
        "requested_to_id": data["raj"].id,
        "reason": "Need a secondary screen for development."
    }
    response = await client.post("/api/v1/transfers", json=payload, headers=headers)
    assert response.status_code == 201
    transfer_id = response.json()["data"]["id"]
    assert response.json()["data"]["status"] == "REQUESTED"

    # 2. Admin approves the transfer
    res_app = await client.patch(f"/api/v1/transfers/{transfer_id}/approve", headers=headers)
    assert res_app.status_code == 200
    assert res_app.json()["data"]["status"] == "COMPLETED"

    # 3. Verify allocations state:
    # Priya's allocation should be RETURNED
    allocs = list(allocation_repository_instance._allocations.values())
    allocs.sort(key=lambda a: a.created_at)
    
    assert len(allocs) == 2
    assert allocs[0].allocated_to_id == data["priya"].id
    assert allocs[0].returned_at is not None  # Closed
    
    # Raj's new allocation should be ACTIVE
    assert allocs[1].allocated_to_id == data["raj"].id
    assert allocs[1].returned_at is None  # Active
    assert allocs[1].computed_status == "ACTIVE"

    # 4. Verify Asset status remains ALLOCATED throughout
    asset = await asset_repository_instance.get_by_id(data["asset"].id)
    assert asset.status == AssetStatus.ALLOCATED


async def test_duplicate_pending_transfers_blocked(client: AsyncClient):
    """Verify that multiple pending transfer requests for the same asset are blocked."""
    data = await _seed_data(client)
    headers = data["headers"]

    # Raj requests transfer
    await client.post("/api/v1/transfers", json={
        "asset_id": data["asset"].id,
        "requested_to_type": "EMPLOYEE",
        "requested_to_id": data["raj"].id
    }, headers=headers)

    # Priya attempts to request transfer for same asset -> Should fail 409
    res_dup = await client.post("/api/v1/transfers", json={
        "asset_id": data["asset"].id,
        "requested_to_type": "EMPLOYEE",
        "requested_to_id": data["priya"].id
    }, headers=headers)
    assert res_dup.status_code == 409
    assert "pending transfer request already exists" in res_dup.json()["error"]["message"]


async def test_transfer_workflow_reject(client: AsyncClient):
    """Verify that rejecting a transfer leaves the allocations and asset status unmodified."""
    data = await _seed_data(client)
    headers = data["headers"]

    # Raj requests transfer
    res = await client.post("/api/v1/transfers", json={
        "asset_id": data["asset"].id,
        "requested_to_type": "EMPLOYEE",
        "requested_to_id": data["raj"].id
    }, headers=headers)
    transfer_id = res.json()["data"]["id"]

    # Reject transfer
    res_rej = await client.patch(f"/api/v1/transfers/{transfer_id}/reject", json={"reason": "Insufficient stock"}, headers=headers)
    assert res_rej.status_code == 200
    assert res_rej.json()["data"]["status"] == "REJECTED"

    # Verify allocations: Priya's allocation remains active
    allocs = list(allocation_repository_instance._allocations.values())
    assert len(allocs) == 1
    assert allocs[0].allocated_to_id == data["priya"].id
    assert allocs[0].returned_at is None


async def test_rbac_transfer_endpoints(client: AsyncClient):
    """Verify that Employees are blocked from approving or rejecting transfer requests."""
    data = await _seed_data(client)
    headers = data["headers"]
    pwd = "Password123!"

    # 1. Raj requests transfer
    res = await client.post("/api/v1/transfers", json={
        "asset_id": data["asset"].id,
        "requested_to_type": "EMPLOYEE",
        "requested_to_id": data["raj"].id
    }, headers=headers)
    assert res.status_code == 201
    transfer_id = res.json()["data"]["id"]

    # 2. Login as Employee Priya
    headers_emp = await _create_user_and_login_headers(client, data["priya"].email, pwd, Role.EMPLOYEE)

    # 3. Priya attempts to approve -> Should fail with 403
    res_app = await client.patch(f"/api/v1/transfers/{transfer_id}/approve", headers=headers_emp)
    assert res_app.status_code == 403

    # 4. Priya attempts to reject -> Should fail with 403
    res_rej = await client.patch(f"/api/v1/transfers/{transfer_id}/reject", json={"reason": "Deny"}, headers=headers_emp)
    assert res_rej.status_code == 403


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
