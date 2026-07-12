import asyncio
from typing import Dict, List, Optional
from app.domain.asset_category import AssetCategory
from app.repositories.asset_category import AbstractAssetCategoryRepository


class InMemoryAssetCategoryRepository(AbstractAssetCategoryRepository):
    """
    Thread-safe, in-memory implementation of AbstractAssetCategoryRepository.
    Simulates database persistence for Asset Categories.
    """
    def __init__(self):
        self._categories: Dict[str, AssetCategory] = {}
        self._lock = asyncio.Lock()

    async def get_by_id(self, id: str) -> Optional[AssetCategory]:
        async with self._lock:
            return self._categories.get(id)

    async def list(self, skip: int = 0, limit: int = 100) -> List[AssetCategory]:
        async with self._lock:
            cats = list(self._categories.values())
            cats.sort(key=lambda c: c.created_at, reverse=True)
            return cats[skip : skip + limit]

    async def list_paginated(
        self,
        skip: int = 0,
        limit: int = 20,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        search: Optional[str] = None,
        filters: Optional[dict] = None
    ) -> tuple[List[AssetCategory], int]:
        async with self._lock:
            items = list(self._categories.values())

            # 1. Apply free-text search (on name)
            if search:
                search_lower = search.lower()
                items = [c for c in items if search_lower in c.name.lower()]

            # 2. Apply field filters
            if filters:
                for key, val in filters.items():
                    attr_name = "is_active" if key == "status" else key
                    items = [c for c in items if getattr(c, attr_name, None) == val]

            # 3. Apply sorting
            if sort_by:
                reverse = (sort_order.lower() == "desc")
                items.sort(key=lambda x: getattr(x, sort_by, None) or "", reverse=reverse)
            else:
                items.sort(key=lambda x: x.created_at, reverse=True)

            total = len(items)
            paginated_items = items[skip : skip + limit]
            return paginated_items, total

    async def create(self, entity: AssetCategory) -> AssetCategory:
        async with self._lock:
            self._categories[entity.id] = entity
            return entity

    async def update(self, entity: AssetCategory) -> AssetCategory:
        async with self._lock:
            self._categories[entity.id] = entity
            return entity

    async def delete(self, id: str) -> bool:
        async with self._lock:
            if id in self._categories:
                del self._categories[id]
                return True
            return False

    async def get_by_name(self, name: str) -> Optional[AssetCategory]:
        async with self._lock:
            name_lower = name.lower()
            for cat in self._categories.values():
                if cat.name.lower() == name_lower and cat.is_active:
                    return cat
            return None
