from abc import abstractmethod
from typing import List
from app.domain.login_attempt import LoginAttempt
from app.repositories.base import AbstractRepository


class AbstractLoginAttemptRepository(AbstractRepository[LoginAttempt]):
    """Abstract login attempt history repository interface."""

    @abstractmethod
    async def get_by_user_id(self, user_id: str) -> List[LoginAttempt]:
        """Fetch all login attempts logged for a specific user ID."""
        pass
