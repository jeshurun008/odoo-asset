from abc import abstractmethod
from typing import Optional
from app.domain.asset_category import AssetCategory
from app.repositories.base import AbstractRepository


class AbstractAssetCategoryRepository(AbstractRepository[AssetCategory]):
    """Abstract AssetCategory repository interface."""

    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[AssetCategory]:
        """Fetch an AssetCategory by its unique name."""
        pass
