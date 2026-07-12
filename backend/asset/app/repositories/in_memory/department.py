import asyncio
from typing import Dict, List, Optional
from app.domain.department import Department
from app.repositories.department import AbstractDepartmentRepository


class InMemoryDepartmentRepository(AbstractDepartmentRepository):
    """
    Thread-safe, in-memory implementation of AbstractDepartmentRepository.
    Simulates database persistence for Departments.
    """
    def __init__(self):
        self._departments: Dict[str, Department] = {}
        self._lock = asyncio.Lock()

    async def get_by_id(self, id: str) -> Optional[Department]:
        async with self._lock:
            return self._departments.get(id)

    async def list(self, skip: int = 0, limit: int = 100) -> List[Department]:
        async with self._lock:
            depts = list(self._departments.values())
            depts.sort(key=lambda d: d.created_at, reverse=True)
            return depts[skip : skip + limit]

    async def list_paginated(
        self,
        skip: int = 0,
        limit: int = 20,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        search: Optional[str] = None,
        filters: Optional[dict] = None
    ) -> tuple[List[Department], int]:
        async with self._lock:
            items = list(self._departments.values())

            # 1. Apply free-text search (on name)
            if search:
                search_lower = search.lower()
                items = [d for d in items if search_lower in d.name.lower()]

            # 2. Apply field filters
            if filters:
                for key, val in filters.items():
                    # Support status filter mapping 'status' to 'is_active'
                    attr_name = "is_active" if key == "status" else key
                    items = [d for d in items if getattr(d, attr_name, None) == val]

            # 3. Apply sorting
            if sort_by:
                reverse = (sort_order.lower() == "desc")
                items.sort(key=lambda x: getattr(x, sort_by, None) or "", reverse=reverse)
            else:
                items.sort(key=lambda x: x.created_at, reverse=True)

            total = len(items)
            paginated_items = items[skip : skip + limit]
            return paginated_items, total

    async def create(self, entity: Department) -> Department:
        async with self._lock:
            self._departments[entity.id] = entity
            return entity

    async def update(self, entity: Department) -> Department:
        async with self._lock:
            self._departments[entity.id] = entity
            return entity

    async def delete(self, id: str) -> bool:
        async with self._lock:
            if id in self._departments:
                del self._departments[id]
                return True
            return False

    async def get_by_name(self, name: str) -> Optional[Department]:
        async with self._lock:
            name_lower = name.lower()
            for dept in self._departments.values():
                if dept.name.lower() == name_lower and dept.is_active:
                    return dept
            return None

    async def list_active_children(self, parent_id: str) -> List[Department]:
        async with self._lock:
            return [
                d for d in self._departments.values()
                if d.parent_department_id == parent_id and d.is_active
            ]
