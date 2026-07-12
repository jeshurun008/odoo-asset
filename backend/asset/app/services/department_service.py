from datetime import datetime, timezone
from typing import List, Optional
from app.domain.department import Department
from app.domain.user import Role
from app.exceptions.exceptions import ConflictException, NotFoundException, ValidationException
from app.logging.logger import business_logger
from app.repositories.department import AbstractDepartmentRepository
from app.repositories.user import AbstractUserRepository


class DepartmentService:
    """
    Service Layer managing Department business logic, validation, hierarchy constraint checks,
    and deactivation blocks.
    """
    def __init__(self, dept_repository: AbstractDepartmentRepository, user_repository: AbstractUserRepository):
        self.dept_repo = dept_repository
        self.user_repo = user_repository

    async def create_department(
        self,
        name: str,
        description: Optional[str] = None,
        parent_department_id: Optional[str] = None,
        department_head_id: Optional[str] = None
    ) -> Department:
        """Creates a new Department, enforcing parent validations and manager checks."""
        # 1. Uniqueness check
        existing = await self.dept_repo.get_by_name(name)
        if existing:
            raise ConflictException(f"Department with name '{name}' already exists.")

        # 2. Parent validation
        if parent_department_id:
            parent = await self.dept_repo.get_by_id(parent_department_id)
            if not parent:
                raise NotFoundException(f"Parent department with ID {parent_department_id} not found.")
            if not parent.is_active:
                raise ConflictException("Parent department is inactive. Cannot link to inactive parents.")

        # 3. Department Head validation
        if department_head_id:
            await self._validate_department_head(department_head_id)

        new_dept = Department(
            name=name,
            description=description,
            parent_department_id=parent_department_id,
            department_head_id=department_head_id
        )
        created = await self.dept_repo.create(new_dept)
        business_logger.info(f"Department created: '{created.name}' (ID: {created.id})")
        return created

    async def update_department(
        self,
        dept_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        parent_department_id: Optional[str] = None,
        department_head_id: Optional[str] = None
    ) -> Department:
        """Updates an existing Department's attributes and validates the structural changes."""
        dept = await self.dept_repo.get_by_id(dept_id)
        if not dept:
            raise NotFoundException(f"Department with ID {dept_id} not found.")

        # 1. Name uniqueness check
        if name and name.lower() != dept.name.lower():
            existing = await self.dept_repo.get_by_name(name)
            if existing:
                raise ConflictException(f"Department with name '{name}' already exists.")
            dept.name = name

        if description is not None:
            dept.description = description

        # 2. Parent validation & Circular Hierarchy check
        if parent_department_id is not None:
            if parent_department_id == dept_id:
                raise ConflictException("A department cannot be its own parent.")
            if parent_department_id != dept.parent_department_id:
                if parent_department_id != "":
                    # Verify parent exists and is active
                    parent = await self.dept_repo.get_by_id(parent_department_id)
                    if not parent:
                        raise NotFoundException(f"Parent department with ID {parent_department_id} not found.")
                    if not parent.is_active:
                        raise ConflictException("Parent department is inactive. Cannot link to inactive parents.")
                    # Circular dependency check
                    await self._check_circular_hierarchy(dept_id, parent_department_id)
                    dept.parent_department_id = parent_department_id
                else:
                    dept.parent_department_id = None

        # 3. Department Head validation
        if department_head_id is not None:
            if department_head_id != dept.department_head_id:
                if department_head_id != "":
                    await self._validate_department_head(department_head_id)
                    dept.department_head_id = department_head_id
                else:
                    dept.department_head_id = None

        dept.updated_at = datetime.now(timezone.utc)
        updated = await self.dept_repo.update(dept)
        business_logger.info(f"Department updated: '{updated.name}' (ID: {updated.id})")
        return updated

    async def deactivate_department(self, dept_id: str) -> Department:
        """Deactivates a department soft-flipping its status, blocking if active employees or sub-departments remain."""
        dept = await self.dept_repo.get_by_id(dept_id)
        if not dept:
            raise NotFoundException(f"Department with ID {dept_id} not found.")

        if not dept.is_active:
            return dept  # Already inactive

        # 1. Check active children sub-departments
        active_children = await self.dept_repo.list_active_children(dept_id)

        # 2. Check active employees assigned to this department
        _, active_emp_count = await self.user_repo.list_paginated(
            limit=1,
            filters={"department_id": dept_id, "is_active": True}
        )

        if active_children or active_emp_count > 0:
            blockers = []
            if active_emp_count > 0:
                blockers.append(f"{active_emp_count} active employee(s)")
            if active_children:
                blockers.append(f"{len(active_children)} active sub-department(s)")

            blockers_str = " and ".join(blockers)
            raise ConflictException(
                f"Cannot deactivate department: {blockers_str} still assigned."
            )

        dept.is_active = False
        dept.updated_at = datetime.now(timezone.utc)
        updated = await self.dept_repo.update(dept)
        business_logger.info(f"Department deactivated: '{updated.name}' (ID: {updated.id})")
        return updated

    async def _validate_department_head(self, user_id: str) -> None:
        """Validates that a user is eligible to head a department."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundException(f"User with ID {user_id} not found.")
        if not user.is_active:
            raise ConflictException(f"User '{user.name}' is inactive and cannot head a department.")
        if user.role not in (Role.DEPARTMENT_HEAD, Role.ADMIN):
            raise ConflictException(
                f"User '{user.name}' does not possess the DEPARTMENT_HEAD or ADMIN role. "
                "You must promote the user first before assigning them as a Department Head."
            )

    async def _check_circular_hierarchy(self, dept_id: str, proposed_parent_id: str) -> None:
        """Traces the hierarchy path upwards to detect and prevent circular reference cycles."""
        visited = set()
        current_id = proposed_parent_id
        while current_id:
            if current_id == dept_id:
                raise ConflictException("Circular hierarchy detected: A department cannot be a descendant of itself.")
            if current_id in visited:
                break
            visited.add(current_id)
            parent = await self.dept_repo.get_by_id(current_id)
            if not parent:
                break
            current_id = parent.parent_department_id
