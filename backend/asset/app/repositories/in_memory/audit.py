import asyncio
from typing import Optional
from app.domain.audit import AuditCycle, AuditItem
from app.repositories.audit import AbstractAuditRepository


class InMemoryAuditRepository(AbstractAuditRepository):
    def __init__(self):
        self._cycles: dict[str, AuditCycle] = {}
        self._items: dict[str, AuditItem] = {}
        self._lock = asyncio.Lock()
    async def get_by_id(self, id: str) -> Optional[AuditCycle]:
        async with self._lock: return self._cycles.get(id)
    async def list(self, skip=0, limit=100):
        async with self._lock: return sorted(self._cycles.values(), key=lambda c: c.created_at, reverse=True)[skip:skip+limit]
    async def list_paginated(self, skip=0, limit=20, sort_by=None, sort_order="asc", search=None, filters=None):
        async with self._lock:
            items = list(self._cycles.values())
            if search: items = [c for c in items if search.lower() in c.name.lower()]
            for key, value in (filters or {}).items():
                if value is not None: items = [c for c in items if getattr(c, key, None) == value or (key == "auditor_id" and value in c.assigned_auditor_ids)]
            items.sort(key=lambda c: getattr(c, sort_by, None) if sort_by else c.created_at, reverse=sort_order == "desc" or not sort_by)
            return items[skip:skip+limit], len(items)
    async def create(self, entity):
        async with self._lock: self._cycles[entity.id] = entity; return entity
    async def update(self, entity):
        async with self._lock: self._cycles[entity.id] = entity; return entity
    async def delete(self, id): return False
    async def create_item(self, item):
        async with self._lock: self._items[item.id] = item; return item
    async def get_item(self, cycle_id, item_id):
        async with self._lock:
            item = self._items.get(item_id); return item if item and item.audit_cycle_id == cycle_id else None
    async def list_items(self, cycle_id):
        async with self._lock: return [i for i in self._items.values() if i.audit_cycle_id == cycle_id]
    async def update_item(self, item):
        async with self._lock: self._items[item.id] = item; return item
