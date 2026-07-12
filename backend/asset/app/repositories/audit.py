from abc import abstractmethod
from typing import List
from app.domain.audit import AuditCycle, AuditItem
from app.repositories.base import AbstractRepository


class AbstractAuditRepository(AbstractRepository[AuditCycle]):
    @abstractmethod
    async def create_item(self, item: AuditItem) -> AuditItem: pass
    @abstractmethod
    async def get_item(self, cycle_id: str, item_id: str) -> AuditItem | None: pass
    @abstractmethod
    async def list_items(self, cycle_id: str) -> List[AuditItem]: pass
    @abstractmethod
    async def update_item(self, item: AuditItem) -> AuditItem: pass
