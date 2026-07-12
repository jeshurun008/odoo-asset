import asyncio
from typing import Dict, List, Optional
from app.domain.user import User
from app.repositories.user import AbstractUserRepository


class InMemoryUserRepository(AbstractUserRepository):
    """
    Thread-safe, in-memory implementation of AbstractUserRepository.
    Used for local testing and standalone execution in Phase 1.
    """
    def __init__(self):
        self._users: Dict[str, User] = {}
        self._lock = asyncio.Lock()

    async def get_by_id(self, id: str) -> Optional[User]:
        async with self._lock:
            return self._users.get(id)

    async def get_by_email(self, email: str) -> Optional[User]:
        async with self._lock:
            email_lower = email.lower()
            for user in self._users.values():
                if user.email.lower() == email_lower:
                    return user
            return None

    async def list(self, skip: int = 0, limit: int = 100) -> List[User]:
        async with self._lock:
            users_list = list(self._users.values())
            # Sort by created_at desc to maintain standard order
            users_list.sort(key=lambda u: u.created_at, reverse=True)
            return users_list[skip : skip + limit]

    async def create(self, entity: User) -> User:
        async with self._lock:
            self._users[entity.id] = entity
            return entity

    async def update(self, entity: User) -> User:
        async with self._lock:
            self._users[entity.id] = entity
            return entity

    async def delete(self, id: str) -> bool:
        async with self._lock:
            if id in self._users:
                del self._users[id]
                return True
            return False

    async def list_paginated(
        self,
        skip: int = 0,
        limit: int = 20,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        search: Optional[str] = None,
        filters: Optional[dict] = None
    ) -> tuple[List[User], int]:
        async with self._lock:
            items = list(self._users.values())

            # 1. Apply free-text search (email and name)
            if search:
                search_lower = search.lower()
                items = [
                    u for u in items
                    if search_lower in u.email.lower() or search_lower in u.name.lower()
                ]

            # 2. Apply field filters
            if filters:
                for key, val in filters.items():
                    items = [u for u in items if getattr(u, key, None) == val]

            # 3. Apply sorting
            if sort_by:
                reverse = (sort_order.lower() == "desc")
                items.sort(key=lambda x: getattr(x, sort_by, None) or "", reverse=reverse)
            else:
                # Default fallback sort is created_at descending
                items.sort(key=lambda x: x.created_at, reverse=True)

            total = len(items)
            paginated_items = items[skip : skip + limit]
            return paginated_items, total
