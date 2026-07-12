import pytest
from httpx import AsyncClient
from app.core.dependencies.auth import user_repository_instance
from app.domain.user import Role, User
from app.security.password import hash_password

pytestmark = pytest.mark.asyncio


async def test_me_unauthorized_missing_token(client: AsyncClient):
    """Test that requesting /me without a Bearer token returns 401 Unauthorized."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["status"] == "error"
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


async def test_me_authorized_success(client: AsyncClient):
    """Test that requesting /me with a valid Bearer token returns the user profile."""
    # Seed user
    hashed_pwd = hash_password("Password123!")
    user = User(
        email="me@assetflow.com",
        hashed_password=hashed_pwd,
        name="Me User",
        role=Role.EMPLOYEE
    )
    await user_repository_instance.create(user)

    # Login to obtain token
    form_data = {"username": "me@assetflow.com", "password": "Password123!"}
    login_res = await client.post("/api/v1/auth/login", data=form_data)
    token = login_res.json()["data"]["access_token"]

    # Request profile
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["data"]["email"] == "me@assetflow.com"


async def test_rbac_admin_only_granted_to_admin(client: AsyncClient):
    """Test that admin-only endpoint allows access to an ADMIN user."""
    # Seed admin user
    hashed_pwd = hash_password("Password123!")
    admin = User(
        email="admin@assetflow.com",
        hashed_password=hashed_pwd,
        name="Admin User",
        role=Role.ADMIN
    )
    await user_repository_instance.create(admin)

    # Login
    form_data = {"username": "admin@assetflow.com", "password": "Password123!"}
    login_res = await client.post("/api/v1/auth/login", data=form_data)
    token = login_res.json()["data"]["access_token"]

    # Request admin-only endpoint
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/api/v1/auth/admin-only", headers=headers)
    assert response.status_code == 200
    assert "Admin" in response.json()["data"]["message"]


async def test_rbac_admin_only_denied_to_employee(client: AsyncClient):
    """Test that admin-only endpoint denies access (403 Forbidden) to an EMPLOYEE user."""
    # Seed employee user
    hashed_pwd = hash_password("Password123!")
    employee = User(
        email="employee-check@assetflow.com",
        hashed_password=hashed_pwd,
        name="Employee User",
        role=Role.EMPLOYEE
    )
    await user_repository_instance.create(employee)

    # Login
    form_data = {"username": "employee-check@assetflow.com", "password": "Password123!"}
    login_res = await client.post("/api/v1/auth/login", data=form_data)
    token = login_res.json()["data"]["access_token"]

    # Request admin-only endpoint
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/api/v1/auth/admin-only", headers=headers)
    assert response.status_code == 403
    assert response.json()["status"] == "error"
    assert response.json()["error"]["code"] == "FORBIDDEN"
