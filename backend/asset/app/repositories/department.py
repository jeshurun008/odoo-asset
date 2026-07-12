from abc import abstractmethod
from typing import List, Optional
from app.domain.department import Department
from app.repositories.base import AbstractRepository


class AbstractDepartmentRepository(AbstractRepository[Department]):
    """Abstract Department repository interface."""

    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[Department]:
        """Fetch a Department by its unique name."""
        pass

    @abstractmethod
    async def list_active_children(self, parent_id: str) -> List[Department]:
        """Fetch all active child departments under the specified parent department ID."""
        pass
