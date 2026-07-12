from abc import ABC, abstractmethod
from typing import Optional


class AbstractTokenStore(ABC):
    """Abstract interface defining the token tracking store for JWT lifecycle operations."""

    @abstractmethod
    async def save_token(self, jti: str, user_id: str, expires_at: float, parent_jti: Optional[str] = None) -> None:
        """Register a new refresh token with its owner and expiry timestamp."""
        pass

    @abstractmethod
    async def is_revoked(self, jti: str) -> bool:
        """Check if a refresh token (by jti) has been explicitly revoked."""
        pass

    @abstractmethod
    async def is_used(self, jti: str) -> bool:
        """Check if a refresh token has already been rotated (used)."""
        pass

    @abstractmethod
    async def mark_as_used(self, jti: str) -> None:
        """Mark a refresh token as rotated (used)."""
        pass

    @abstractmethod
    async def revoke(self, jti: str) -> None:
        """Revoke a specific refresh token (by jti)."""
        pass

    @abstractmethod
    async def revoke_user_tokens(self, user_id: str) -> None:
        """Revoke all refresh tokens belonging to a user (e.g., when replay is detected)."""
        pass
