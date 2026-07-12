from datetime import datetime, timezone
from typing import List, Optional, Tuple
from app.domain.user import Role, User
from app.exceptions.exceptions import ConflictException, ForbiddenException, NotFoundException, ValidationException
from app.logging.logger import business_logger, security_logger
from app.repositories.user import AbstractUserRepository
from app.repositories.department import AbstractDepartmentRepository


class EmployeeService:
    """
    Service Layer managing Employee directory profiles, scoping visibility queries,
    department alignments, status activations, and RBAC Role Promotion transactions.
    """
    def __init__(self, user_repository: AbstractUserRepository, dept_repository: AbstractDepartmentRepository):
        self.user_repo = user_repository
        self.dept_repo = dept_repository

    async def list_employees(
        self,
        caller: User,
        skip: int = 0,
        limit: int = 20,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        search: Optional[str] = None,
        filters: Optional[dict] = None
    ) -> Tuple[List[User], int]:
        """Lists, paginates, and searches employees applying role-based visibility constraints."""
        query_filters = (filters or {}).copy()

        # Enforce Department Head scoping rule
        if caller.role == Role.DEPARTMENT_HEAD:
            if not caller.department_id:
                # If a department head is not assigned to a department, they see no one
                return [], 0
            query_filters["department_id"] = caller.department_id

        # Enforce employee restriction (already handled in routes, but guard here as well)
        elif caller.role == Role.EMPLOYEE:
            raise ForbiddenException("Access denied. Employees cannot view the directory.")

        return await self.user_repo.list_paginated(
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
            search=search,
            filters=query_filters
        )

    async def get_employee_detail(self, employee_id: str, caller: User) -> User:
        """Fetches employee profile details, verifying visibility permissions."""
        user = await self.user_repo.get_by_id(employee_id)
        if not user:
            raise NotFoundException(f"Employee with ID {employee_id} not found.")

        # Scoping validation
        if caller.role == Role.DEPARTMENT_HEAD:
            if user.department_id != caller.department_id:
                raise ForbiddenException("Access denied. You can only view employees in your own department.")
        elif caller.role == Role.EMPLOYEE:
            if caller.id != employee_id:
                raise ForbiddenException("Access denied. You can only view your own profile.")

        return user

    async def assign_department(self, employee_id: str, department_id: Optional[str]) -> User:
        """Assigns an employee to a department, validating its existence and status."""
        user = await self.user_repo.get_by_id(employee_id)
        if not user:
            raise NotFoundException(f"Employee with ID {employee_id} not found.")

        if department_id:
            dept = await self.dept_repo.get_by_id(department_id)
            if not dept:
                raise NotFoundException(f"Department with ID {department_id} not found.")
            if not dept.is_active:
                raise ConflictException("Cannot assign employee to an inactive department.")
            user.department_id = department_id
        else:
            user.department_id = None

        user.updated_at = datetime.now(timezone.utc)
        updated = await self.user_repo.update(user)
        business_logger.info(
            f"Employee department reassigned: User {updated.email} linked to Department: {department_id}"
        )
        return updated

    async def activate_employee(self, employee_id: str) -> User:
        """Activates an employee account."""
        user = await self.user_repo.get_by_id(employee_id)
        if not user:
            raise NotFoundException(f"Employee with ID {employee_id} not found.")

        if user.is_active:
            return user

        user.is_active = True
        user.updated_at = datetime.now(timezone.utc)
        updated = await self.user_repo.update(user)
        business_logger.info(f"Employee account activated: {updated.email}")
        return updated

    async def deactivate_employee(self, employee_id: str) -> User:
        """Deactivates an employee account, preventing lockouts of the last Admin."""
        user = await self.user_repo.get_by_id(employee_id)
        if not user:
            raise NotFoundException(f"Employee with ID {employee_id} not found.")

        if not user.is_active:
            return user

        # Last Admin lockout safety check
        if user.role == Role.ADMIN:
            await self._ensure_not_last_admin(employee_id)

        user.is_active = False
        user.updated_at = datetime.now(timezone.utc)
        updated = await self.user_repo.update(user)
        business_logger.info(f"Employee account deactivated: {updated.email}")
        return updated

    async def promote_employee(self, actor_user_id: str, target_user_id: str, target_role: Role) -> User:
        """
        Enforces a role change transaction (promotion/demotion) on an active employee.
        Validates target exists and preserves the last administrator.
        """
        user = await self.user_repo.get_by_id(target_user_id)
        if not user:
            raise NotFoundException(f"Employee with ID {target_user_id} not found.")

        if not user.is_active:
            raise ConflictException("Cannot change the role of an inactive account. Activate the account first.")

        if user.role == target_role:
            return user  # No role change

        # Ensure we don't demote the last administrator
        if user.role == Role.ADMIN and target_role != Role.ADMIN:
            await self._ensure_not_last_admin(target_user_id)

        previous_role = user.role
        user.role = target_role
        user.updated_at = datetime.now(timezone.utc)
        updated = await self.user_repo.update(user)

        # Generate immutable audit activity log entry
        business_logger.info(
            f"ROLE_PROMOTION: Actor '{actor_user_id}' promoted user '{target_user_id}' "
            f"({updated.email}) from role '{previous_role}' to '{target_role}'."
        )
        return updated

    async def _ensure_not_last_admin(self, user_id: str) -> None:
        """Validates that a user is not the last remaining active administrator in the system."""
        # Query for all active admins
        _, active_admin_count = await self.user_repo.list_paginated(
            limit=2,
            filters={"role": Role.ADMIN, "is_active": True}
        )
        if active_admin_count <= 1:
            raise ConflictException(
                "Operation rejected. You cannot demote or deactivate the last remaining administrator."
            )
