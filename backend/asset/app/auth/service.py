import time
from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid
from app.auth.schemas import UserSignupRequest
from app.core.config import settings
from app.domain.user import Role, User
from app.domain.login_attempt import LoginAttempt
from app.exceptions.exceptions import ConflictException, LockedException, NotFoundException, UnauthorizedException
from app.logging.logger import auth_logger, security_logger
from app.repositories.token_store import AbstractTokenStore
from app.repositories.user import AbstractUserRepository
from app.repositories.login_history import AbstractLoginAttemptRepository
from app.security.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    create_reset_token,
    decode_reset_token,
)
from app.security.password import hash_password, verify_password


class AuthService:
    """
    Principal Authentication Service managing User registration, session tokens,
    lockouts, rotation, replay protection, and password resets.
    """
    def __init__(
        self,
        user_repository: AbstractUserRepository,
        token_store: AbstractTokenStore,
        login_attempt_repository: AbstractLoginAttemptRepository
    ):
        self.user_repo = user_repository
        self.token_store = token_store
        self.login_attempt_repo = login_attempt_repository

    async def register_user(self, request: UserSignupRequest) -> User:
        """Registers a new User. Forces Role.EMPLOYEE for security."""
        existing_user = await self.user_repo.get_by_email(request.email)
        if existing_user:
            security_logger.warning(f"Registration failed: Email {request.email} already exists.")
            raise ConflictException("Email is already registered.")

        hashed_pwd = hash_password(request.password)
        new_user = User(
            email=request.email,
            hashed_password=hashed_pwd,
            name=request.name,
            role=Role.EMPLOYEE  # Mass assignment protection: ignore any role selection input
        )
        
        created = await self.user_repo.create(new_user)
        auth_logger.info(f"User registered successfully: {created.email} (ID: {created.id})")
        return created

    async def authenticate_user(self, email: str, password: str, ip_address: str, correlation_id: str) -> User:
        """Authenticates user credentials. Evaluates status, locks, and logs history."""
        user = await self.user_repo.get_by_email(email)
        if not user:
            # Audit log attempt (unknown user)
            attempt = LoginAttempt(
                email_attempted=email,
                success=False,
                ip_address=ip_address,
                correlation_id=correlation_id,
                user_id=None
            )
            await self.login_attempt_repo.create(attempt)

            auth_logger.info(f"Login failed: Email {email} not found.")
            raise UnauthorizedException("Invalid credentials.")

        # Account status validation
        if not user.is_active:
            # Audit log attempt (inactive user)
            attempt = LoginAttempt(
                email_attempted=email,
                success=False,
                ip_address=ip_address,
                correlation_id=correlation_id,
                user_id=user.id
            )
            await self.login_attempt_repo.create(attempt)

            security_logger.warning(f"Login blocked: Inactive account access attempt by {email}")
            raise UnauthorizedException("Account is inactive. Please contact support.")

        # Check soft-lockout status
        if user.is_locked:
            # Audit log attempt (locked user)
            attempt = LoginAttempt(
                email_attempted=email,
                success=False,
                ip_address=ip_address,
                correlation_id=correlation_id,
                user_id=user.id
            )
            await self.login_attempt_repo.create(attempt)

            security_logger.warning(f"Login blocked: Locked-out account access attempt by {email}")
            raise LockedException("Account is temporarily locked due to too many failed login attempts.")

        # Credential validation
        if verify_password(password, user.hashed_password):
            # Audit log attempt (success)
            attempt = LoginAttempt(
                email_attempted=email,
                success=True,
                ip_address=ip_address,
                correlation_id=correlation_id,
                user_id=user.id
            )
            await self.login_attempt_repo.create(attempt)

            if user.failed_login_count > 0:
                user.reset_failed_login()
                await self.user_repo.update(user)
                
            auth_logger.info(f"User login successful: {email}")
            return user
        else:
            # Audit log attempt (failed password)
            attempt = LoginAttempt(
                email_attempted=email,
                success=False,
                ip_address=ip_address,
                correlation_id=correlation_id,
                user_id=user.id
            )
            await self.login_attempt_repo.create(attempt)

            user.increment_failed_login(
                max_attempts=settings.MAX_FAILED_LOGIN_ATTEMPTS,
                lock_duration_minutes=settings.LOCKOUT_DURATION_MINUTES
            )
            await self.user_repo.update(user)

            if user.is_locked:
                security_logger.critical(f"Account locked: {email} exceeded max login attempts.")
                raise LockedException("Account is temporarily locked due to too many failed login attempts.")
            else:
                auth_logger.info(f"Login failed: Invalid password for {email}. Attempt {user.failed_login_count}/{settings.MAX_FAILED_LOGIN_ATTEMPTS}")
                raise UnauthorizedException("Invalid credentials.")

    async def create_session(self, user: User, remember_me: bool = False) -> tuple[str, str, int]:
        """Creates an access and refresh token session pair."""
        # Calculate refresh expiration based on remember_me option
        refresh_minutes = (
            settings.REMEMBER_ME_REFRESH_TOKEN_EXPIRE_MINUTES
            if remember_me
            else settings.REFRESH_TOKEN_EXPIRE_MINUTES
        )

        refresh_jti = str(uuid.uuid4())
        
        access_token = create_access_token(subject=user.id)
        refresh_token = create_refresh_token(
            subject=user.id,
            jti=refresh_jti,
            expires_delta=timedelta(minutes=refresh_minutes)
        )

        # Register token in token store
        expires_at_timestamp = time.time() + (refresh_minutes * 60)
        await self.token_store.save_token(
            jti=refresh_jti,
            user_id=user.id,
            expires_at=expires_at_timestamp
        )

        expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        return access_token, refresh_token, expires_in

    async def refresh_session(self, refresh_token: str) -> tuple[str, str, int]:
        """Rotates a refresh token (1-time use) and issues a new pair. Provides replay protection."""
        payload = decode_token(refresh_token)
        
        if payload.get("type") != "refresh":
            raise UnauthorizedException("Invalid token type. Refresh token required.")

        user_id = payload.get("sub")
        jti = payload.get("jti")
        
        if not user_id or not jti:
            raise UnauthorizedException("Malformed token claims.")

        # Replay attack detection
        if await self.token_store.is_used(jti):
            security_logger.critical(f"Replay attack detected: Token reuse of JTI {jti} by user {user_id}. Revoking all user tokens!")
            await self.token_store.revoke_user_tokens(user_id)
            raise UnauthorizedException("Replay attack detected. Session terminated.")

        # Revocation validation
        if await self.token_store.is_revoked(jti):
            raise UnauthorizedException("Refresh token has been revoked or expired.")

        user = await self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise UnauthorizedException("Associated user is inactive or not found.")

        # Invalidate old token and issue rotated pair
        await self.token_store.mark_as_used(jti)
        await self.token_store.revoke(jti)

        # Standard rotation creates new access & refresh
        access_token, new_refresh_token, expires_in = await self.create_session(user, remember_me=False)
        
        # Link new refresh token to its parent JTI in history
        new_payload = decode_token(new_refresh_token)
        new_jti = new_payload.get("jti")
        if new_jti:
            expires_at_timestamp = time.time() + (settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60)
            await self.token_store.save_token(
                jti=new_jti,
                user_id=user.id,
                expires_at=expires_at_timestamp,
                parent_jti=jti
            )

        auth_logger.info(f"Session rotated successfully for User: {user.email}")
        return access_token, new_refresh_token, expires_in

    async def logout_user(self, refresh_token: str) -> None:
        """Revokes the refresh token."""
        try:
            payload = decode_token(refresh_token)
            jti = payload.get("jti")
            if jti:
                await self.token_store.revoke(jti)
                auth_logger.info(f"User logged out. Revoked refresh token JTI: {jti}")
        except Exception:
            # Gracefully handle logout failure (e.g. if token is already expired)
            pass

    async def forgot_password(self, email: str) -> None:
        """Handles password forgot request. Generates JWT reset token and stubs notification."""
        user = await self.user_repo.get_by_email(email)
        # Prevent email enumeration: silently return even if user doesn't exist
        if not user or not user.is_active:
            auth_logger.info(f"Forgot password: Request for email {email} ignored (not active or not found).")
            return

        # Issue 15 minute reset token via security layer
        reset_token = create_reset_token(user.email)
        
        # Stub the notification transmission step
        auth_logger.info(f"Password reset generated for {user.email}: token = {reset_token}")
        # In production, dispatch this to the Notification Router / Email worker

    async def reset_password(self, token: str, new_password: str) -> None:
        """Validates password reset token and updates the user's password."""
        email = decode_reset_token(token)

        user = await self.user_repo.get_by_email(email)
        if not user or not user.is_active:
            raise UnauthorizedException("User account is inactive or not found.")

        # Update credential
        user.hashed_password = hash_password(new_password)
        user.reset_failed_login()
        await self.user_repo.update(user)
        
        auth_logger.info(f"Password reset successful for user: {user.email}")
