import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional
from app.domain.maintenance_request import MaintenanceRequest, MaintenanceStatus
from app.repositories.maintenance_request import AbstractMaintenanceRequestRepository


class InMemoryMaintenanceRequestRepository(AbstractMaintenanceRequestRepository):
    """
    Thread-safe, in-memory implementation of AbstractMaintenanceRequestRepository.
    Simulates database persistence for Asset Maintenance workflows.
    """
    def __init__(self):
        self._requests: Dict[str, MaintenanceRequest] = {}
        self._lock = asyncio.Lock()

    async def get_by_id(self, id: str) -> Optional[MaintenanceRequest]:
        async with self._lock:
            return self._requests.get(id)

    async def list(self, skip: int = 0, limit: int = 100) -> List[MaintenanceRequest]:
        async with self._lock:
            items = list(self._requests.values())
            items.sort(key=lambda r: r.raised_at, reverse=True)
            return items[skip : skip + limit]

    async def list_paginated(
        self,
        skip: int = 0,
        limit: int = 20,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        search: Optional[str] = None,
        filters: Optional[dict] = None
    ) -> tuple[List[MaintenanceRequest], int]:
        async with self._lock:
            items = list(self._requests.values())

            # Apply filters
            if filters:
                for key, val in filters.items():
                    if key == "maintenance_today" and val is True:
                        continue
                    items = [r for r in items if getattr(r, key, None) == val]

            # Special "maintenance today" filter (Dashboard KPI feeds)
            if filters and filters.get("maintenance_today") is True:
                today = datetime.now(timezone.utc).date()
                items = [
                    r for r in items
                    if r.status in (MaintenanceStatus.IN_PROGRESS, MaintenanceStatus.TECHNICIAN_ASSIGNED)
                    or (r.raised_at.date() == today and r.status != MaintenanceStatus.RESOLVED)
                ]

            # Sort
            if sort_by:
                reverse = (sort_order.lower() == "desc")
                items.sort(key=lambda x: getattr(x, sort_by, None) or "", reverse=reverse)
            else:
                items.sort(key=lambda x: x.raised_at, reverse=True)

            total = len(items)
            paginated_items = items[skip : skip + limit]
            return paginated_items, total

    async def create(self, entity: MaintenanceRequest) -> MaintenanceRequest:
        async with self._lock:
            self._requests[entity.id] = entity
            return entity

    async def update(self, entity: MaintenanceRequest) -> MaintenanceRequest:
        async with self._lock:
            self._requests[entity.id] = entity
            return entity

    async def delete(self, id: str) -> bool:
        async with self._lock:
            if id in self._requests:
                del self._requests[id]
                return True
            return False

    async def list_unresolved_by_asset(self, asset_id: str) -> List[MaintenanceRequest]:
        async with self._lock:
            return [
                r for r in self._requests.values()
                if r.asset_id == asset_id and r.status not in (MaintenanceStatus.RESOLVED, MaintenanceStatus.REJECTED)
            ]

    async def list_active_today(self) -> List[MaintenanceRequest]:
        async with self._lock:
            today = datetime.now(timezone.utc).date()
            return [
                r for r in self._requests.values()
                if r.status in (MaintenanceStatus.IN_PROGRESS, MaintenanceStatus.TECHNICIAN_ASSIGNED)
                or r.raised_at.date() == today
            ]

    async def list_maintenance_today(self) -> List[MaintenanceRequest]:
        async with self._lock:
            today = datetime.now(timezone.utc).date()
            return [
                r for r in self._requests.values()
                if r.status in (MaintenanceStatus.IN_PROGRESS, MaintenanceStatus.TECHNICIAN_ASSIGNED)
                or (r.raised_at.date() == today and r.status != MaintenanceStatus.RESOLVED)
            ]

