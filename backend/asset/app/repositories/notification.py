from abc import abstractmethod
from typing import List
from app.domain.notification import Notification
from app.repositories.base import AbstractRepository


class AbstractNotificationRepository(AbstractRepository[Notification]):
    @abstractmethod
    async def list_for_recipient(self, recipient_id: str, skip: int, limit: int) -> tuple[List[Notification], int]: pass
    @abstractmethod
    async def count_unread(self, recipient_id: str) -> int: pass
