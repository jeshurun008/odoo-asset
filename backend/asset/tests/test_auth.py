import asyncio
from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient
from app.core.dependencies.auth import user_repository_instance
from app.domain.user import Role, User
from app.security.password import hash_password

pytestmark = pytest.mark.asyncio


async def test_signup_success(client: AsyncClient):
    """Test successful user registration assigns the EMPLOYEE role by default."""
    payload = {
        "email": "employee@assetflow.com",
        "name": "John Doe",
        "password": "Password123!"
    }
    response = await client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == 201
    
    json_data = response.json()
    assert json_data["status"] == "success"
    assert json_data["data"]["email"] == "employee@assetflow.com"
    assert json_data["data"]["name"] == "John Doe"
    assert json_data["data"]["role"] == "EMPLOYEE"
    assert "id" in json_data["data"]


async def test_signup_role_injection_ignored(client: AsyncClient):
    """Test that role fields in registration payload are ignored for protection."""
    payload = {
        "email": "injected@assetflow.com",
        "name": "Hacker Bob",
        "password": "Password123!",
        "role": "ADMIN"  # Attempting privilege escalation
    }
    response = await client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == 201
    
    json_data = response.json()
    assert json_data["data"]["role"] == "EMPLOYEE"  # Must remain EMPLOYEE


async def test_signup_duplicate_email(client: AsyncClient):
    """Test that registering an already registered email throws a 409 conflict."""
    payload = {
        "email": "duplicate@assetflow.com",
        "name": "First User",
        "password": "Password123!"
    }
    # Register once
    response = await client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == 201

    # Register twice
    response2 = await client.post("/api/v1/auth/signup", json=payload)
    assert response2.status_code == 409
    assert response2.json()["status"] == "error"
    assert response2.json()["error"]["code"] == "CONFLICT"


async def test_signup_weak_password(client: AsyncClient):
    """Test that weak password inputs fail Pydantic validation."""
    payload = {
        "email": "weak@assetflow.com",
        "name": "Weak Pass",
        "password": "123"
    }
    response = await client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == 422
    assert response.json()["status"] == "error"
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "password" in response.json()["error"]["details"]


async def test_login_success(client: AsyncClient):
    """Test successful user login returning access and refresh token pair."""
    # Seed user in repo
    hashed_pwd = hash_password("Password123!")
    user = User(
        email="login@assetflow.com",
        hashed_password=hashed_pwd,
        name="Login User"
    )
    await user_repository_instance.create(user)

    # Login using OAuth2 form-data standard
    form_data = {
        "username": "login@assetflow.com",
        "password": "Password123!"
    }
    response = await client.post("/api/v1/auth/login", data=form_data)
    assert response.status_code == 200
    
    json_data = response.json()
    assert json_data["status"] == "success"
    assert "access_token" in json_data["data"]
    assert "refresh_token" in json_data["data"]
    assert json_data["data"]["token_type"] == "bearer"


async def test_login_invalid_password(client: AsyncClient):
    """Test login fails with incorrect password."""
    hashed_pwd = hash_password("Password123!")
    user = User(
        email="wrongpass@assetflow.com",
        hashed_password=hashed_pwd,
        name="Wrong Pass"
    )
    await user_repository_instance.create(user)

    form_data = {
        "username": "wrongpass@assetflow.com",
        "password": "WrongPassword!"
    }
    response = await client.post("/api/v1/auth/login", data=form_data)
    assert response.status_code == 401
    assert response.json()["status"] == "error"
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


async def test_login_inactive_account(client: AsyncClient):
    """Test login is blocked for inactive user accounts."""
    hashed_pwd = hash_password("Password123!")
    user = User(
        email="inactive@assetflow.com",
        hashed_password=hashed_pwd,
        name="Inactive User",
        is_active=False
    )
    await user_repository_instance.create(user)

    form_data = {
        "username": "inactive@assetflow.com",
        "password": "Password123!"
    }
    response = await client.post("/api/v1/auth/login", data=form_data)
    assert response.status_code == 401
    assert "inactive" in response.json()["error"]["message"].lower()


async def test_login_soft_lockout_triggers(client: AsyncClient):
    """Test account soft lockout is triggered after 5 consecutive failed login attempts."""
    hashed_pwd = hash_password("Password123!")
    email = "lockout@assetflow.com"
    user = User(
        email=email,
        hashed_password=hashed_pwd,
        name="Lockout User"
    )
    await user_repository_instance.create(user)

    form_data = {
        "username": email,
        "password": "WrongPassword!"
    }

    # Attempt 1 to 4 fail with UNAUTHORIZED
    for _ in range(4):
        response = await client.post("/api/v1/auth/login", data=form_data)
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "UNAUTHORIZED"

    # 5th attempt triggers lockout
    response_lock = await client.post("/api/v1/auth/login", data=form_data)
    assert response_lock.status_code == 423
    assert response_lock.json()["error"]["code"] == "ACCOUNT_LOCKED"

    # A 6th attempt (even with the correct password) is immediately blocked by lockout duration
    correct_form_data = {
        "username": email,
        "password": "Password123!"
    }
    response_blocked = await client.post("/api/v1/auth/login", data=correct_form_data)
    assert response_blocked.status_code == 423
    assert response_blocked.json()["error"]["code"] == "ACCOUNT_LOCKED"


async def test_refresh_token_rotation_and_replay_protection(client: AsyncClient):
    """Test standard refresh token rotation and replay-attack security protection."""
    # Seed user
    hashed_pwd = hash_password("Password123!")
    user = User(email="rotation@assetflow.com", hashed_password=hashed_pwd, name="Rotation")
    await user_repository_instance.create(user)

    # Login to get initial tokens
    form_data = {"username": "rotation@assetflow.com", "password": "Password123!"}
    login_res = await client.post("/api/v1/auth/login", data=form_data)
    initial_refresh = login_res.json()["data"]["refresh_token"]

    # 1. Rotate refresh token once
    refresh_res = await client.post("/api/v1/auth/refresh", json={"refresh_token": initial_refresh})
    assert refresh_res.status_code == 200
    rotated_data = refresh_res.json()["data"]
    assert "access_token" in rotated_data
    assert "refresh_token" in rotated_data
    new_refresh = rotated_data["refresh_token"]

    # 2. Replay Attack: Re-use the initial refresh token again
    replay_res = await client.post("/api/v1/auth/refresh", json={"refresh_token": initial_refresh})
    assert replay_res.status_code == 401
    assert "replay" in replay_res.json()["error"]["message"].lower()

    # 3. Validation: Newly issued refresh token must also be revoked due to the replay attack
    after_replay_res = await client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh})
    assert after_replay_res.status_code == 401


async def test_logout_revokes_token(client: AsyncClient):
    """Test logout invalidates the refresh token."""
    # Seed user
    hashed_pwd = hash_password("Password123!")
    user = User(email="logout@assetflow.com", hashed_password=hashed_pwd, name="Logout")
    await user_repository_instance.create(user)

    # Login
    form_data = {"username": "logout@assetflow.com", "password": "Password123!"}
    login_res = await client.post("/api/v1/auth/login", data=form_data)
    refresh_token = login_res.json()["data"]["refresh_token"]

    # Logout
    logout_res = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert logout_res.status_code == 200
    assert logout_res.json()["status"] == "success"

    # Refresh with revoked token should fail
    refresh_res = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_res.status_code == 401


async def test_forgot_and_reset_password_flow(client: AsyncClient):
    """Test forgot-password triggers log stub and reset-password updates credentials."""
    # Seed user
    hashed_pwd = hash_password("Password123!")
    user = User(email="resetpwd@assetflow.com", hashed_password=hashed_pwd, name="Reset")
    await user_repository_instance.create(user)

    # Forgot password triggers token generation logged server-side
    forgot_res = await client.post("/api/v1/auth/forgot-password", json={"email": "resetpwd@assetflow.com"})
    assert forgot_res.status_code == 200

    # Since we stubbed email, let's create a valid reset token directly using the same mechanism for testing
    import jwt
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=15)
    reset_payload = {
        "sub": "resetpwd@assetflow.com",
        "exp": expire,
        "type": "reset",
        "jti": "test-reset-jti",
        "iat": now
    }
    from app.core.config import settings
    token = jwt.encode(reset_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    # Perform password reset
    reset_res = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "NewPassword123!"}
    )
    assert reset_res.status_code == 200
    assert reset_res.json()["status"] == "success"

    # Login with new password
    form_data = {"username": "resetpwd@assetflow.com", "password": "NewPassword123!"}
    login_res = await client.post("/api/v1/auth/login", data=form_data)
    assert login_res.status_code == 200
