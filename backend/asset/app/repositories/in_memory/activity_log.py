import asyncio
from typing import Optional
from app.domain.activity_log import ActivityLog
from app.repositories.activity_log import AbstractActivityLogRepository

class InMemoryActivityLogRepository(AbstractActivityLogRepository):
    def __init__(self): self._logs: dict[str, ActivityLog] = {}; self._lock = asyncio.Lock()
    async def get_by_id(self, id: str) -> Optional[ActivityLog]:
        async with self._lock: return self._logs.get(id)
    async def list(self, skip=0, limit=100):
        async with self._lock: return sorted(self._logs.values(), key=lambda x: x.timestamp, reverse=True)[skip:skip + limit]
    async def list_paginated(self, skip=0, limit=20, sort_by=None, sort_order="asc", search=None, filters=None):
        async with self._lock:
            logs = list(self._logs.values())
            for key, value in (filters or {}).items():
                if value is None: continue
                if key == "start_date": logs = [x for x in logs if x.timestamp >= value]
                elif key == "end_date": logs = [x for x in logs if x.timestamp <= value]
                else: logs = [x for x in logs if getattr(x, key, None) == value]
            if search: logs = [x for x in logs if search.lower() in x.action.lower()]
            logs.sort(key=lambda x: getattr(x, sort_by, None) if sort_by else x.timestamp, reverse=sort_order == "desc" or not sort_by)
            return logs[skip:skip + limit], len(logs)
    async def create(self, entity):
        async with self._lock: self._logs[entity.id] = entity; return entity
    async def update(self, entity): raise RuntimeError("Activity logs are immutable.")
    async def delete(self, id): raise RuntimeError("Activity logs are immutable.")
