import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from app.core.config import settings
from app.exceptions.exceptions import UnauthorizedException


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Generates an Access Token with a short lifetime.
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "sub": subject,
        "exp": expire,
        "type": "access",
        "jti": str(uuid.uuid4()),
        "iat": now
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str, jti: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Generates a Refresh Token with a longer lifetime.
    Uses the provided jti to enable tracking/replay-protection.
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "sub": subject,
        "exp": expire,
        "type": "refresh",
        "jti": jti,
        "iat": now
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decodes and validates a JWT token.
    Raises UnauthorizedException on invalid or expired signature.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException("Token signature has expired")
    except jwt.InvalidTokenError:
        raise UnauthorizedException("Invalid token signature or claim")


def create_reset_token(email: str) -> str:
    """
    Generates a secure password reset token with a 15-minute lifetime.
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=15)

    payload = {
        "sub": email,
        "exp": expire,
        "type": "reset",
        "jti": str(uuid.uuid4()),
        "iat": now
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_reset_token(token: str) -> str:
    """
    Decodes and validates a password reset token.
    Returns the email subject if valid, raises UnauthorizedException otherwise.
    """
    # Since decode_token already raises UnauthorizedException for expired/invalid signatures,
    # we just need to catch and handle the inner claims check.
    payload = decode_token(token)

    if payload.get("type") != "reset":
        raise UnauthorizedException("Invalid token scope. Reset token required.")

    email = payload.get("sub")
    if not email:
        raise UnauthorizedException("Malformed reset token claims.")

    return email
