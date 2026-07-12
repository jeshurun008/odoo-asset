import pytest
from httpx import AsyncClient
from app.core.dependencies.auth import user_repository_instance
from app.domain.user import User, Role
from app.security.password import hash_password

pytestmark = pytest.mark.asyncio


async def _seed_users():
    """Seeds an Admin and an Employee user."""
    user_repository_instance._users.clear()
    
    pwd = "Password123!"
    admin = User(email="admin-promo@assetflow.com", hashed_password=hash_password(pwd), name="Admin User", role=Role.ADMIN)
    await user_repository_instance.create(admin)
    
    emp = User(email="emp-promo@assetflow.com", hashed_password=hash_password(pwd), name="Employee", role=Role.EMPLOYEE)
    await user_repository_instance.create(emp)
    
    return {
        "admin": admin,
        "emp": emp,
        "password": pwd
    }


async def test_role_promotion_success(client: AsyncClient):
    """Admin successfully promotes employee to Asset Manager."""
    data = await _seed_users()
    
    # Login as Admin
    form_data = {"username": data["admin"].email, "password": data["password"]}
    res_login = await client.post("/api/v1/auth/login", data=form_data)
    token = res_login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Promote Employee to ASSET_MANAGER
    payload = {"role": "ASSET_MANAGER"}
    response = await client.post(f"/api/v1/employees/{data['emp'].id}/promote", json=payload, headers=headers)
    assert response.status_code == 200
    updated_user = response.json()["data"]
    assert updated_user["role"] == "ASSET_MANAGER"


async def test_role_promotion_forbidden_for_non_admin(client: AsyncClient):
    """Non-admin user is blocked from promoting users."""
    data = await _seed_users()
    
    # Login as Employee
    form_data = {"username": data["emp"].email, "password": data["password"]}
    res_login = await client.post("/api/v1/auth/login", data=form_data)
    token = res_login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Try promoting target employee to ASSET_MANAGER
    payload = {"role": "ASSET_MANAGER"}
    response = await client.post(f"/api/v1/employees/{data['emp'].id}/promote", json=payload, headers=headers)
    assert response.status_code == 403


async def test_last_admin_lockout_safeguard(client: AsyncClient):
    """Ensure demoting the last active administrator is rejected with 409."""
    data = await _seed_users()
    
    # Login as Admin
    form_data = {"username": data["admin"].email, "password": data["password"]}
    res_login = await client.post("/api/v1/auth/login", data=form_data)
    token = res_login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Attempt demoting the last admin to EMPLOYEE (should fail)
    payload = {"role": "EMPLOYEE"}
    response = await client.post(f"/api/v1/employees/{data['admin'].id}/promote", json=payload, headers=headers)
    assert response.status_code == 409
    assert "cannot demote or deactivate the last remaining administrator" in response.json()["error"]["message"]
