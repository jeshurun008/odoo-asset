import asyncio
from typing import Dict, List, Optional
from app.domain.transfer_request import TransferRequest
from app.repositories.transfer_request import AbstractTransferRequestRepository


class InMemoryTransferRequestRepository(AbstractTransferRequestRepository):
    """
    Thread-safe, in-memory implementation of AbstractTransferRequestRepository.
    Simulates database persistence for Transfer requests.
    """
    def __init__(self):
        self._transfers: Dict[str, TransferRequest] = {}
        self._lock = asyncio.Lock()

    async def get_by_id(self, id: str) -> Optional[TransferRequest]:
        async with self._lock:
            return self._transfers.get(id)

    async def list(self, skip: int = 0, limit: int = 100) -> List[TransferRequest]:
        async with self._lock:
            reqs = list(self._transfers.values())
            reqs.sort(key=lambda t: t.requested_at, reverse=True)
            return reqs[skip : skip + limit]

    async def list_paginated(
        self,
        skip: int = 0,
        limit: int = 20,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        search: Optional[str] = None,
        filters: Optional[dict] = None
    ) -> tuple[List[TransferRequest], int]:
        async with self._lock:
            items = list(self._transfers.values())

            # Filters
            if filters:
                for key, val in filters.items():
                    items = [t for t in items if getattr(t, key, None) == val]

            # Sort
            if sort_by:
                reverse = (sort_order.lower() == "desc")
                items.sort(key=lambda x: getattr(x, sort_by, None) or "", reverse=reverse)
            else:
                items.sort(key=lambda x: x.requested_at, reverse=True)

            total = len(items)
            paginated_items = items[skip : skip + limit]
            return paginated_items, total

    async def create(self, entity: TransferRequest) -> TransferRequest:
        async with self._lock:
            self._transfers[entity.id] = entity
            return entity

    async def update(self, entity: TransferRequest) -> TransferRequest:
        async with self._lock:
            self._transfers[entity.id] = entity
            return entity

    async def delete(self, id: str) -> bool:
        async with self._lock:
            if id in self._transfers:
                del self._transfers[id]
                return True
            return False

    async def list_pending_by_asset(self, asset_id: str) -> List[TransferRequest]:
        async with self._lock:
            return [
                t for t in self._transfers.values()
                if t.asset_id == asset_id and t.status == "REQUESTED"
            ]
