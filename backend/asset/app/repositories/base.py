from abc import ABC, abstractmethod
from typing import Generic, List, Optional, TypeVar

T = TypeVar("T")


class AbstractRepository(ABC, Generic[T]):
    """Abstract generic repository interface defining standard operations."""

    @abstractmethod
    async def get_by_id(self, id: str) -> Optional[T]:
        """Fetch a record by its unique identifier."""
        pass

    @abstractmethod
    async def list(self, skip: int = 0, limit: int = 100) -> List[T]:
        """Fetch a paginated list of records."""
        pass

    @abstractmethod
    async def create(self, entity: T) -> T:
        """Persist a new entity record."""
        pass

    @abstractmethod
    async def update(self, entity: T) -> T:
        """Update an existing entity record."""
        pass

    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Remove a record by its unique identifier."""
        pass

    @abstractmethod
    async def list_paginated(
        self,
        skip: int = 0,
        limit: int = 20,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        search: Optional[str] = None,
        filters: Optional[dict] = None
    ) -> tuple[List[T], int]:
        """Fetch a paginated, sorted, and filtered list of records, returning (items, total_count)."""
        pass
