import asyncio
from typing import Dict, List, Optional
from app.domain.login_attempt import LoginAttempt
from app.repositories.login_history import AbstractLoginAttemptRepository


class InMemoryLoginAttemptRepository(AbstractLoginAttemptRepository):
    """
    Thread-safe, in-memory implementation of AbstractLoginAttemptRepository.
    Stores and queries login history records for audits.
    """
    def __init__(self):
        self._attempts: Dict[str, LoginAttempt] = {}
        self._lock = asyncio.Lock()

    async def get_by_id(self, id: str) -> Optional[LoginAttempt]:
        async with self._lock:
            return self._attempts.get(id)

    async def list(self, skip: int = 0, limit: int = 100) -> List[LoginAttempt]:
        async with self._lock:
            attempts_list = list(self._attempts.values())
            # Default sort is timestamp descending (newest first)
            attempts_list.sort(key=lambda a: a.timestamp, reverse=True)
            return attempts_list[skip : skip + limit]

    async def list_paginated(
        self,
        skip: int = 0,
        limit: int = 20,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        search: Optional[str] = None,
        filters: Optional[dict] = None
    ) -> tuple[List[LoginAttempt], int]:
        async with self._lock:
            items = list(self._attempts.values())

            # 1. Search filter
            if search:
                search_lower = search.lower()
                items = [a for a in items if search_lower in a.email_attempted.lower()]

            # 2. Key-value filters
            if filters:
                for key, val in filters.items():
                    items = [a for a in items if getattr(a, key, None) == val]

            # 3. Sorting
            if sort_by:
                reverse = (sort_order.lower() == "desc")
                items.sort(key=lambda x: getattr(x, sort_by, None) or "", reverse=reverse)
            else:
                items.sort(key=lambda x: x.timestamp, reverse=True)

            total = len(items)
            paginated_items = items[skip : skip + limit]
            return paginated_items, total

    async def create(self, entity: LoginAttempt) -> LoginAttempt:
        async with self._lock:
            self._attempts[entity.id] = entity
            return entity

    async def update(self, entity: LoginAttempt) -> LoginAttempt:
        async with self._lock:
            self._attempts[entity.id] = entity
            return entity

    async def delete(self, id: str) -> bool:
        async with self._lock:
            if id in self._attempts:
                del self._attempts[id]
                return True
            return False

    async def get_by_user_id(self, user_id: str) -> List[LoginAttempt]:
        async with self._lock:
            return [a for a in self._attempts.values() if a.user_id == user_id]
