from typing import Optional
from fastapi import APIRouter, Depends, Form, Request
from fastapi.security import OAuth2PasswordRequestForm
from app.auth.schemas import (
    ForgotPasswordRequest,
    RefreshRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
    UserSignupRequest,
    LoginRequest,
)
from app.logging.logger import correlation_id_ctx
from app.exceptions.exceptions import ValidationException, UnauthorizedException
from app.core.dependencies.auth import get_auth_service, get_current_user, require_role
from app.auth.service import AuthService
from app.domain.user import Role, User
from app.schemas.envelope import SuccessResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/signup",
    response_model=SuccessResponse[UserResponse],
    status_code=201,
    summary="Register a new employee account",
    description="Creates a new account. By default, all signups are assigned the role of EMPLOYEE.",
)
async def signup(
    request: UserSignupRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> SuccessResponse[UserResponse]:
    user = await auth_service.register_user(request)
    # Convert domain entity to Pydantic-compatible structure
    user_data = UserResponse.model_validate(user)
    return SuccessResponse(data=user_data)


@router.post(
    "/login",
    response_model=SuccessResponse[TokenResponse],
    summary="Authenticate credentials & obtain session tokens",
    description=(
        "Authenticates credentials (OAuth2 Password Flow or JSON LoginRequest). "
        "Returns access token and a refresh token wrapped in the response envelope."
    ),
)
async def login(
    request: Request,
    username: Optional[str] = Form(None, description="OAuth2 username (email)"),
    password: Optional[str] = Form(None, description="OAuth2 password"),
    remember_me: Optional[bool] = Form(None, description="Flag for a longer-lived session"),
    auth_service: AuthService = Depends(get_auth_service)
) -> SuccessResponse[TokenResponse]:
    content_type = request.headers.get("content-type", "")
    resolved_email = ""
    resolved_password = ""
    resolved_remember_me = False

    if "application/json" in content_type:
        try:
            body = await request.json()
            login_req = LoginRequest.model_validate(body)
            resolved_email = login_req.email
            resolved_password = login_req.password
            resolved_remember_me = login_req.remember_me
        except Exception as e:
            raise ValidationException("Invalid login data payload", details={"body": str(e)})
    else:
        # Standard form parsing compatibility for OAuth2 Password Flow / Swagger UI
        resolved_email = username
        resolved_password = password
        resolved_remember_me = remember_me in ("true", "1", True) or False

        if not resolved_email or not resolved_password:
            # Fallback if Form variables weren't bound correctly by FastAPI
            try:
                form_data = await request.form()
                resolved_email = form_data.get("username")
                resolved_password = form_data.get("password")
                resolved_remember_me = form_data.get("remember_me") in ("true", "1", True)
            except Exception:
                pass

        if not resolved_email or not resolved_password:
            raise UnauthorizedException("Invalid username or password credentials.")

    ip_address = request.client.host if request.client else "127.0.0.1"
    correlation_id = correlation_id_ctx.get()

    user = await auth_service.authenticate_user(
        email=resolved_email,
        password=resolved_password,
        ip_address=ip_address,
        correlation_id=correlation_id
    )
    access_token, refresh_token, expires_in = await auth_service.create_session(user, remember_me=resolved_remember_me)

    token_data = TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in
    )
    return SuccessResponse(data=token_data)


@router.post(
    "/refresh",
    response_model=SuccessResponse[TokenResponse],
    summary="Rotate refresh token for new access and refresh tokens",
    description="Submits an active refresh token to rotate it for a fresh access and refresh pair.",
)
async def refresh(
    request: RefreshRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> SuccessResponse[TokenResponse]:
    access_token, refresh_token, expires_in = await auth_service.refresh_session(request.refresh_token)
    
    token_data = TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in
    )
    return SuccessResponse(data=token_data)


@router.post(
    "/logout",
    response_model=SuccessResponse[dict],
    summary="Terminate session / Revoke refresh token",
    description="Explicitly revokes a refresh token, rendering it unusable for subsequent refreshes.",
)
async def logout(
    request: RefreshRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> SuccessResponse[dict]:
    await auth_service.logout_user(request.refresh_token)
    return SuccessResponse(data={"message": "Logged out successfully."})


@router.post(
    "/forgot-password",
    response_model=SuccessResponse[dict],
    summary="Request a password reset link/token",
    description="Generates a secure password reset token and stubs transmission. Returns success representation.",
)
async def forgot_password(
    request: ForgotPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> SuccessResponse[dict]:
    await auth_service.forgot_password(request.email)
    return SuccessResponse(data={"message": "If the email is registered, a password reset token has been dispatched."})


@router.post(
    "/reset-password",
    response_model=SuccessResponse[dict],
    summary="Reset password using reset token",
    description="Uses a valid reset token to securely change user password to a new value.",
)
async def reset_password(
    request: ResetPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> SuccessResponse[dict]:
    await auth_service.reset_password(request.token, request.new_password)
    return SuccessResponse(data={"message": "Password has been successfully updated."})


@router.get(
    "/me",
    response_model=SuccessResponse[UserResponse],
    summary="Get current user details",
    description="Validates access token and returns the current user profile.",
)
async def me(
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[UserResponse]:
    user_data = UserResponse.model_validate(current_user)
    return SuccessResponse(data=user_data)


@router.get(
    "/admin-only",
    response_model=SuccessResponse[dict],
    summary="Protected endpoint proving RBAC works",
    description="Allows access only to users with the ADMIN role.",
)
async def admin_only(
    admin_user: User = Depends(require_role(Role.ADMIN))
) -> SuccessResponse[dict]:
    return SuccessResponse(data={"message": f"Hello Admin {admin_user.name}!"})
