import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from app.domain.allocation import AssetAllocation
from app.repositories.allocation import AbstractAssetAllocationRepository


class InMemoryAssetAllocationRepository(AbstractAssetAllocationRepository):
    """
    Thread-safe, in-memory implementation of AbstractAssetAllocationRepository.
    Simulates database persistence for Asset Allocation history.
    """
    def __init__(self):
        self._allocations: Dict[str, AssetAllocation] = {}
        self._lock = asyncio.Lock()

    async def get_by_id(self, id: str) -> Optional[AssetAllocation]:
        async with self._lock:
            return self._allocations.get(id)

    async def list(self, skip: int = 0, limit: int = 100) -> List[AssetAllocation]:
        async with self._lock:
            allocs = list(self._allocations.values())
            allocs.sort(key=lambda a: a.created_at, reverse=True)
            return allocs[skip : skip + limit]

    async def list_paginated(
        self,
        skip: int = 0,
        limit: int = 20,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        search: Optional[str] = None,
        filters: Optional[dict] = None
    ) -> tuple[List[AssetAllocation], int]:
        async with self._lock:
            items = list(self._allocations.values())

            # 1. Apply overdue filter if requested in repository layer
            if filters and filters.get("overdue") is True:
                items = [a for a in items if a.computed_status == "OVERDUE"]

            # 2. General filters
            if filters:
                for key, val in filters.items():
                    if key == "overdue":
                        continue
                    items = [a for a in items if getattr(a, key, None) == val]

            # 3. Sort
            if sort_by:
                reverse = (sort_order.lower() == "desc")
                items.sort(key=lambda x: getattr(x, sort_by, None) or "", reverse=reverse)
            else:
                items.sort(key=lambda x: x.created_at, reverse=True)

            total = len(items)
            paginated_items = items[skip : skip + limit]
            return paginated_items, total

    async def create(self, entity: AssetAllocation) -> AssetAllocation:
        async with self._lock:
            self._allocations[entity.id] = entity
            return entity

    async def update(self, entity: AssetAllocation) -> AssetAllocation:
        async with self._lock:
            self._allocations[entity.id] = entity
            return entity

    async def delete(self, id: str) -> bool:
        async with self._lock:
            if id in self._allocations:
                del self._allocations[id]
                return True
            return False

    async def list_active_by_asset(self, asset_id: str) -> List[AssetAllocation]:
        async with self._lock:
            return [
                a for a in self._allocations.values()
                if a.asset_id == asset_id and a.computed_status in ("ACTIVE", "OVERDUE")
            ]

    async def list_overdue(self) -> List[AssetAllocation]:
        async with self._lock:
            return [
                a for a in self._allocations.values()
                if a.computed_status == "OVERDUE"
            ]

    async def list_by_asset(self, asset_id: str) -> List[AssetAllocation]:
        async with self._lock:
            allocs = [a for a in self._allocations.values() if a.asset_id == asset_id]
            allocs.sort(key=lambda a: a.allocated_at, reverse=True)
            return allocs

    async def list_upcoming_returns(self, days: int):
        async with self._lock:
            now, end = datetime.now(timezone.utc), datetime.now(timezone.utc) + timedelta(days=days)
            return [a for a in self._allocations.values() if a.returned_at is None and a.expected_return_date and now <= (a.expected_return_date.replace(tzinfo=timezone.utc) if a.expected_return_date.tzinfo is None else a.expected_return_date) <= end]
