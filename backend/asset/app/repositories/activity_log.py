from abc import abstractmethod
from app.domain.activity_log import ActivityLog
from app.repositories.base import AbstractRepository

class AbstractActivityLogRepository(AbstractRepository[ActivityLog]):
    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Activity entries are immutable and cannot be deleted."""
        raise NotImplementedError
