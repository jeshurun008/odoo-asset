import asyncio
from typing import Dict, List, Optional
from app.domain.asset import Asset, AssetStatus
from app.repositories.asset import AbstractAssetRepository


class InMemoryAssetRepository(AbstractAssetRepository):
    """
    Thread-safe, in-memory implementation of AbstractAssetRepository.
    Simulates database persistence and atomically generates unique asset tags.
    """
    def __init__(self):
        self._assets: Dict[str, Asset] = {}
        self._tag_counter = 0
        self._lock = asyncio.Lock()

    async def get_by_id(self, id: str) -> Optional[Asset]:
        async with self._lock:
            return self._assets.get(id)

    async def list(self, skip: int = 0, limit: int = 100) -> List[Asset]:
        async with self._lock:
            assets = list(self._assets.values())
            assets.sort(key=lambda a: a.created_at, reverse=True)
            return assets[skip : skip + limit]

    async def list_paginated(
        self,
        skip: int = 0,
        limit: int = 20,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        search: Optional[str] = None,
        filters: Optional[dict] = None
    ) -> tuple[List[Asset], int]:
        async with self._lock:
            items = list(self._assets.values())

            # 1. Apply free-text search (on name or asset_tag or serial_number)
            if search:
                search_lower = search.lower()
                items = [
                    a for a in items
                    if (search_lower in a.name.lower() or
                        (a.asset_tag and search_lower in a.asset_tag.lower()) or
                        search_lower in a.serial_number.lower())
                ]

            # 2. Apply filters
            if filters:
                for key, val in filters.items():
                    # Handle my_assets employee scoping filter
                    if key == "allocated_to_employee_id" and val is not None:
                        # This scoping filter will be resolved via allocations,
                        # but if passed directly as a filter we match the allocated IDs.
                        # For service-level queries, the service aggregates/scopes list.
                        continue
                    
                    # Exact field filtering
                    items = [a for a in items if getattr(a, key, None) == val]

            # 3. Apply sorting
            if sort_by:
                reverse = (sort_order.lower() == "desc")
                items.sort(key=lambda x: getattr(x, sort_by, None) or "", reverse=reverse)
            else:
                items.sort(key=lambda x: x.created_at, reverse=True)

            total = len(items)
            paginated_items = items[skip : skip + limit]
            return paginated_items, total

    async def create(self, entity: Asset) -> Asset:
        async with self._lock:
            self._assets[entity.id] = entity
            return entity

    async def update(self, entity: Asset) -> Asset:
        async with self._lock:
            self._assets[entity.id] = entity
            return entity

    async def delete(self, id: str) -> bool:
        async with self._lock:
            if id in self._assets:
                del self._assets[id]
                return True
            return False

    async def get_by_asset_tag(self, tag: str) -> Optional[Asset]:
        async with self._lock:
            tag_upper = tag.upper()
            for asset in self._assets.values():
                if asset.asset_tag and asset.asset_tag.upper() == tag_upper:
                    return asset
            return None

    async def generate_next_tag(self) -> str:
        async with self._lock:
            self._tag_counter += 1
            # e.g. AF-0001, AF-0012
            return f"AF-{self._tag_counter:04d}"

    async def count_active_by_category(self, category_id: str) -> int:
        async with self._lock:
            count = 0
            for asset in self._assets.values():
                if asset.category_id == category_id and asset.status not in (AssetStatus.RETIRED, AssetStatus.DISPOSED):
                    count += 1
            return count
