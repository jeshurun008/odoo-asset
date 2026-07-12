from abc import abstractmethod
from typing import List
from app.domain.allocation import AssetAllocation
from app.repositories.base import AbstractRepository


class AbstractAssetAllocationRepository(AbstractRepository[AssetAllocation]):
    """Abstract AssetAllocation repository interface."""

    @abstractmethod
    async def list_active_by_asset(self, asset_id: str) -> List[AssetAllocation]:
        """Fetch all active (unreturned) allocations for a specific asset ID."""
        pass

    @abstractmethod
    async def list_overdue(self) -> List[AssetAllocation]:
        """Fetch all active allocations whose expected return date is in the past."""
        pass

    @abstractmethod
    async def list_by_asset(self, asset_id: str) -> List[AssetAllocation]:
        """Fetch all allocations (both active and returned) for a specific asset ID."""
        pass
