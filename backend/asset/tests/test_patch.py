import uuid
from datetime import datetime, timezone
import pytest
import jwt
from httpx import AsyncClient
from app.core.config import settings
from app.core.dependencies.auth import (
    user_repository_instance,
    login_attempt_repository_instance
)
from app.domain.user import User, Role
from app.security.password import hash_password

pytestmark = pytest.mark.asyncio


async def test_user_repository_pagination():
    """Test pagination, sorting, and search on the in-memory user repository."""
    # Seed 5 users
    user_repository_instance._users.clear()
    for i in range(5):
        user = User(
            email=f"user{i}@assetflow.com",
            hashed_password="Password123!",
            name=f"User {chr(65 + i)}",  # User A, User B, User C, User D, User E
            role=Role.EMPLOYEE
        )
        await user_repository_instance.create(user)

    # 1. Test standard pagination (limit=2, skip=0)
    items, total = await user_repository_instance.list_paginated(skip=0, limit=2)
    assert len(items) == 2
    assert total == 5

    # 2. Test sorting by name ascending
    items_asc, _ = await user_repository_instance.list_paginated(skip=0, limit=5, sort_by="name", sort_order="asc")
    assert items_asc[0].name == "User A"
    assert items_asc[-1].name == "User E"

    # 3. Test sorting by name descending
    items_desc, _ = await user_repository_instance.list_paginated(skip=0, limit=5, sort_by="name", sort_order="desc")
    assert items_desc[0].name == "User E"
    assert items_desc[-1].name == "User A"

    # 4. Test case-insensitive search
    items_search, total_search = await user_repository_instance.list_paginated(search="USER B")
    assert len(items_search) == 1
    assert items_search[0].name == "User B"

    # 5. Test empty results search
    items_empty, total_empty = await user_repository_instance.list_paginated(search="non-existent")
    assert len(items_empty) == 0
    assert total_empty == 0


async def test_login_history_records(client: AsyncClient):
    """Test that login history records successful and failed login attempts with correct metadata."""
    login_attempt_repository_instance._attempts.clear()
    user_repository_instance._users.clear()

    # Seed user
    email = "history-test@assetflow.com"
    pwd = "Password123!"
    hashed_pwd = hash_password(pwd)
    user = User(email=email, hashed_password=hashed_pwd, name="History User")
    await user_repository_instance.create(user)

    # 1. Perform successful login
    form_data = {"username": email, "password": pwd}
    res1 = await client.post("/api/v1/auth/login", data=form_data)
    assert res1.status_code == 200
    corr_id_1 = res1.headers.get("X-Correlation-Id")

    # 2. Perform failed login (wrong password)
    form_data_failed = {"username": email, "password": "WrongPassword!"}
    res2 = await client.post("/api/v1/auth/login", data=form_data_failed)
    assert res2.status_code == 401
    corr_id_2 = res2.headers.get("X-Correlation-Id")

    # 3. Perform failed login (non-existent email)
    form_data_missing = {"username": "missing@assetflow.com", "password": pwd}
    res3 = await client.post("/api/v1/auth/login", data=form_data_missing)
    assert res3.status_code == 401

    # Verify history
    attempts = list(login_attempt_repository_instance._attempts.values())
    assert len(attempts) == 3

    # Sort attempts by timestamp to evaluate them sequentially
    attempts.sort(key=lambda a: a.timestamp)

    # Check Success Login
    assert attempts[0].email_attempted == email
    assert attempts[0].success is True
    assert attempts[0].user_id == user.id
    assert attempts[0].correlation_id == corr_id_1

    # Check Failed Login (wrong password)
    assert attempts[1].email_attempted == email
    assert attempts[1].success is False
    assert attempts[1].user_id == user.id
    assert attempts[1].correlation_id == corr_id_2

    # Check Failed Login (missing user)
    assert attempts[2].email_attempted == "missing@assetflow.com"
    assert attempts[2].success is False
    assert attempts[2].user_id is None


async def test_remember_me_expiry(client: AsyncClient):
    """Test that login remember_me=True extends the refresh token expiration."""
    user_repository_instance._users.clear()
    
    email = "rememberme@assetflow.com"
    pwd = "Password123!"
    hashed_pwd = hash_password(pwd)
    user = User(email=email, hashed_password=hashed_pwd, name="Remember User")
    await user_repository_instance.create(user)

    # 1. Login with remember_me = False (Default)
    payload_default = {
        "email": email,
        "password": pwd,
        "remember_me": False
    }
    res_default = await client.post("/api/v1/auth/login", json=payload_default)
    assert res_default.status_code == 200
    token_default = res_default.json()["data"]["refresh_token"]
    
    decoded_default = jwt.decode(token_default, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    exp_default = decoded_default["exp"]
    iat_default = decoded_default["iat"]
    duration_default_mins = (exp_default - iat_default) / 60
    # Allow 1-2 minutes boundary offset due to timing delay
    assert abs(duration_default_mins - settings.REFRESH_TOKEN_EXPIRE_MINUTES) < 2

    # 2. Login with remember_me = True
    payload_remember = {
        "email": email,
        "password": pwd,
        "remember_me": True
    }
    res_remember = await client.post("/api/v1/auth/login", json=payload_remember)
    assert res_remember.status_code == 200
    token_remember = res_remember.json()["data"]["refresh_token"]

    decoded_remember = jwt.decode(token_remember, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    exp_remember = decoded_remember["exp"]
    iat_remember = decoded_remember["iat"]
    duration_remember_mins = (exp_remember - iat_remember) / 60
    assert abs(duration_remember_mins - settings.REMEMBER_ME_REFRESH_TOKEN_EXPIRE_MINUTES) < 2


async def test_uuid_enforcement():
    """Verify that User and LoginAttempt entities generate valid UUID identifiers."""
    user = User(email="uuid@assetflow.com", hashed_password="Password!", name="UUID")
    # Verify User ID is a valid UUIDv4 structure
    user_uuid = uuid.UUID(user.id)
    assert user_uuid.version == 4

    from app.domain.login_attempt import LoginAttempt
    attempt = LoginAttempt(
        email_attempted="uuid@assetflow.com",
        success=True,
        ip_address="127.0.0.1",
        correlation_id="corr-123"
    )
    # Verify LoginAttempt ID is a valid UUIDv4 structure
    attempt_uuid = uuid.UUID(attempt.id)
    assert attempt_uuid.version == 4


async def test_admin_list_users_pagination(client: AsyncClient):
    """Test GET /api/v1/users works with pagination, sorting, and search via API request."""
    user_repository_instance._users.clear()

    # Create an ADMIN user
    admin_pwd = hash_password("AdminPass123!")
    admin = User(email="admin-list@assetflow.com", hashed_password=admin_pwd, name="Admin User", role=Role.ADMIN)
    await user_repository_instance.create(admin)

    # Create 3 EMPLOYEE users
    for i in range(3):
        emp_user = User(
            email=f"emp{i}@assetflow.com",
            hashed_password=hash_password("EmpPass123!"),
            name=f"Employee {chr(65 + i)}",  # Employee A, Employee B, Employee C
            role=Role.EMPLOYEE
        )
        await user_repository_instance.create(emp_user)

    # Login as admin to get token
    form_data = {"username": "admin-list@assetflow.com", "password": "AdminPass123!"}
    login_res = await client.post("/api/v1/auth/login", data=form_data)
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Test pagination (page=1, page_size=2)
    response = await client.get("/api/v1/users?page=1&page_size=2", headers=headers)
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"
    assert len(json_data["data"]["items"]) == 2
    assert json_data["data"]["total"] == 4
    assert json_data["data"]["total_pages"] == 2

    # 2. Test sorting by name desc
    response_sort = await client.get("/api/v1/users?page=1&page_size=4&sort_by=name&sort_order=desc", headers=headers)
    assert response_sort.status_code == 200
    items = response_sort.json()["data"]["items"]
    assert items[0]["name"] == "Employee C"
    assert items[-1]["name"] == "Admin User"

    # 3. Test search case-insensitive
    response_search = await client.get("/api/v1/users?search=EMPLOYEE B", headers=headers)
    assert response_search.status_code == 200
    search_items = response_search.json()["data"]["items"]
    assert len(search_items) == 1
    assert search_items[0]["name"] == "Employee B"

    # 4. Test permission denied for non-admin
    form_data_emp = {"username": "emp0@assetflow.com", "password": "EmpPass123!"}
    login_res_emp = await client.post("/api/v1/auth/login", data=form_data_emp)
    emp_token = login_res_emp.json()["data"]["access_token"]
    emp_headers = {"Authorization": f"Bearer {emp_token}"}

    response_denied = await client.get("/api/v1/users", headers=emp_headers)
    assert response_denied.status_code == 403


def override_cors_origins(allowed_origins: list[str]):
    """Helper to dynamically modify origins of CORSMiddleware in compiled ASGI wrapper tree."""
    from app.main import app
    from fastapi.middleware.cors import CORSMiddleware
    current_app = app.middleware_stack
    while current_app is not None:
        if isinstance(current_app, CORSMiddleware):
            current_app.allow_origins = allowed_origins
            current_app.allow_all_origins = "*" in allowed_origins
            if hasattr(current_app, "compile_allow_origins"):
                current_app.compile_allow_origins(allowed_origins)
        current_app = getattr(current_app, "app", None)


async def test_cors_allowed_origin(client: AsyncClient):
    """Test that requests from an allowed origin receive the Access-Control-Allow-Origin header."""
    override_cors_origins(["http://localhost:3000"])
    try:
        headers = {"Origin": "http://localhost:3000"}
        response = await client.get("/", headers=headers)
        assert response.status_code == 200
        assert response.headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"
    finally:
        override_cors_origins([])


async def test_cors_disallowed_origin(client: AsyncClient):
    """Test that requests from a disallowed origin do not receive the Access-Control-Allow-Origin header."""
    override_cors_origins(["http://localhost:3000"])
    try:
        headers = {"Origin": "http://malicious.com"}
        response = await client.get("/", headers=headers)
        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" not in response.headers
    finally:
        override_cors_origins([])
