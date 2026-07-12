from abc import abstractmethod
from typing import Optional
from app.domain.user import User
from app.repositories.base import AbstractRepository


class AbstractUserRepository(AbstractRepository[User]):
    """Abstract user repository interface extending generic repository operations."""

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """Fetch a User entity by their unique email address."""
        pass
