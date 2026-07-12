import asyncio
from datetime import datetime, timezone
from app.domain.notification import Notification
from app.repositories.notification import AbstractNotificationRepository


class InMemoryNotificationRepository(AbstractNotificationRepository):
    def __init__(self): self._notifications = {}; self._lock = asyncio.Lock()
    async def get_by_id(self, id):
        async with self._lock: return self._notifications.get(id)
    async def list(self, skip=0, limit=100):
        async with self._lock: return sorted(self._notifications.values(), key=lambda n: n.created_at, reverse=True)[skip:skip+limit]
    async def list_paginated(self, skip=0, limit=20, sort_by=None, sort_order="asc", search=None, filters=None):
        items = await self.list(); return items[skip:skip+limit], len(items)
    async def create(self, entity):
        async with self._lock: self._notifications[entity.id] = entity; return entity
    async def update(self, entity):
        async with self._lock: self._notifications[entity.id] = entity; return entity
    async def delete(self, id): return False
    async def list_for_recipient(self, recipient_id, skip, limit):
        async with self._lock:
            items = sorted((n for n in self._notifications.values() if n.recipient_user_id == recipient_id), key=lambda n: n.created_at, reverse=True)
            return items[skip:skip+limit], len(items)
    async def count_unread(self, recipient_id):
        async with self._lock: return sum(not n.read for n in self._notifications.values() if n.recipient_user_id == recipient_id)
