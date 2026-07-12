from abc import abstractmethod
from typing import Optional
from app.domain.asset import Asset
from app.repositories.base import AbstractRepository


class AbstractAssetRepository(AbstractRepository[Asset]):
    """Abstract Asset repository interface."""

    @abstractmethod
    async def get_by_asset_tag(self, tag: str) -> Optional[Asset]:
        """Fetch an Asset by its unique asset tag."""
        pass

    @abstractmethod
    async def generate_next_tag(self) -> str:
        """Atomically generate the next sequential unique asset tag (e.g. AF-0001)."""
        pass

    @abstractmethod
    async def count_active_by_category(self, category_id: str) -> int:
        """Count how many active assets (non-RETIRED, non-DISPOSED) reference this category ID."""
        pass
