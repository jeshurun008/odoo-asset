import asyncio
import time
from typing import Dict, Optional
from app.repositories.token_store import AbstractTokenStore


class InMemoryTokenStore(AbstractTokenStore):
    """
    Thread-safe, in-memory implementation of AbstractTokenStore.
    Replicates Redis caching behavior for checking token revocation status.
    """
    def __init__(self):
        # Maps jti -> dict properties
        self._tokens: Dict[str, dict] = {}
        self._lock = asyncio.Lock()

    async def save_token(self, jti: str, user_id: str, expires_at: float, parent_jti: Optional[str] = None) -> None:
        async with self._lock:
            self._tokens[jti] = {
                "user_id": user_id,
                "expires_at": expires_at,
                "parent_jti": parent_jti,
                "is_used": False,
                "is_revoked": False,
            }

    async def is_revoked(self, jti: str) -> bool:
        async with self._lock:
            token = self._tokens.get(jti)
            if not token:
                return True
            # Clean up expired tokens lazily
            if token["expires_at"] < time.time():
                token["is_revoked"] = True
            return token["is_revoked"]

    async def is_used(self, jti: str) -> bool:
        async with self._lock:
            token = self._tokens.get(jti)
            return token["is_used"] if token else False

    async def mark_as_used(self, jti: str) -> None:
        async with self._lock:
            if jti in self._tokens:
                self._tokens[jti]["is_used"] = True

    async def revoke(self, jti: str) -> None:
        async with self._lock:
            if jti in self._tokens:
                self._tokens[jti]["is_revoked"] = True

    async def revoke_user_tokens(self, user_id: str) -> None:
        async with self._lock:
            for token in self._tokens.values():
                if token["user_id"] == user_id:
                    token["is_revoked"] = True
