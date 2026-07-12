from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from app.auth.service import AuthService
from app.domain.user import Role, User
from app.exceptions.exceptions import ForbiddenException, UnauthorizedException
from app.repositories.in_memory.token_store import InMemoryTokenStore
from app.repositories.in_memory.user import InMemoryUserRepository
from app.repositories.in_memory.login_history import InMemoryLoginAttemptRepository
from app.repositories.in_memory.department import InMemoryDepartmentRepository
from app.repositories.in_memory.asset_category import InMemoryAssetCategoryRepository
from app.repositories.in_memory.asset import InMemoryAssetRepository
from app.repositories.in_memory.allocation import InMemoryAssetAllocationRepository
from app.repositories.in_memory.transfer_request import InMemoryTransferRequestRepository
from app.repositories.in_memory.booking import InMemoryBookingRepository
from app.repositories.in_memory.maintenance_request import InMemoryMaintenanceRequestRepository
from app.repositories.token_store import AbstractTokenStore
from app.repositories.user import AbstractUserRepository
from app.repositories.login_history import AbstractLoginAttemptRepository
from app.repositories.department import AbstractDepartmentRepository
from app.repositories.asset_category import AbstractAssetCategoryRepository
from app.repositories.asset import AbstractAssetRepository
from app.repositories.allocation import AbstractAssetAllocationRepository
from app.repositories.transfer_request import AbstractTransferRequestRepository
from app.repositories.booking import AbstractBookingRepository
from app.repositories.maintenance_request import AbstractMaintenanceRequestRepository
from app.security.jwt import decode_token
from app.services.department_service import DepartmentService
from app.services.asset_category_service import AssetCategoryService
from app.services.employee_service import EmployeeService
from app.services.asset_lifecycle_service import AssetLifecycleService
from app.services.asset_service import AssetService
from app.services.allocation_service import AllocationService
from app.services.transfer_service import TransferService
from app.services.booking_service import BookingService
from app.services.maintenance_service import MaintenanceService

# Singletons representing in-memory tables for persistence
user_repository_instance = InMemoryUserRepository()
token_store_instance = InMemoryTokenStore()
login_attempt_repository_instance = InMemoryLoginAttemptRepository()
department_repository_instance = InMemoryDepartmentRepository()
asset_category_repository_instance = InMemoryAssetCategoryRepository()
asset_repository_instance = InMemoryAssetRepository()
allocation_repository_instance = InMemoryAssetAllocationRepository()
transfer_request_repository_instance = InMemoryTransferRequestRepository()
booking_repository_instance = InMemoryBookingRepository()
maintenance_request_repository_instance = InMemoryMaintenanceRequestRepository()


def get_user_repository() -> AbstractUserRepository:
    """Dependency injector for User Repository."""
    return user_repository_instance


def get_token_store() -> AbstractTokenStore:
    """Dependency injector for Token Store."""
    return token_store_instance


def get_login_attempt_repository() -> AbstractLoginAttemptRepository:
    """Dependency injector for Login Attempt Repository."""
    return login_attempt_repository_instance


def get_department_repository() -> AbstractDepartmentRepository:
    """Dependency injector for Department Repository."""
    return department_repository_instance


def get_asset_category_repository() -> AbstractAssetCategoryRepository:
    """Dependency injector for Asset Category Repository."""
    return asset_category_repository_instance


def get_asset_repository() -> AbstractAssetRepository:
    """Dependency injector for Asset Repository."""
    return asset_repository_instance


def get_allocation_repository() -> AbstractAssetAllocationRepository:
    """Dependency injector for Asset Allocation Repository."""
    return allocation_repository_instance


def get_transfer_request_repository() -> AbstractTransferRequestRepository:
    """Dependency injector for Transfer Request Repository."""
    return transfer_request_repository_instance


def get_booking_repository() -> AbstractBookingRepository:
    """Dependency injector for Booking Repository."""
    return booking_repository_instance


def get_maintenance_request_repository() -> AbstractMaintenanceRequestRepository:
    """Dependency injector for Maintenance Request Repository."""
    return maintenance_request_repository_instance


def get_auth_service(
    user_repo: AbstractUserRepository = Depends(get_user_repository),
    token_store: AbstractTokenStore = Depends(get_token_store),
    login_attempt_repo: AbstractLoginAttemptRepository = Depends(get_login_attempt_repository)
) -> AuthService:
    """Dependency injector for Authentication Service."""
    return AuthService(user_repo, token_store, login_attempt_repo)


def get_department_service(
    dept_repo: AbstractDepartmentRepository = Depends(get_department_repository),
    user_repo: AbstractUserRepository = Depends(get_user_repository)
) -> DepartmentService:
    """Dependency injector for Department Service."""
    return DepartmentService(dept_repo, user_repo)


def get_asset_category_service(
    cat_repo: AbstractAssetCategoryRepository = Depends(get_asset_category_repository),
    asset_repo: AbstractAssetRepository = Depends(get_asset_repository)
) -> AssetCategoryService:
    """Dependency injector for Asset Category Service (wired to AssetRepo for deactivation blocks)."""
    return AssetCategoryService(cat_repo, asset_repo)


def get_employee_service(
    user_repo: AbstractUserRepository = Depends(get_user_repository),
    dept_repo: AbstractDepartmentRepository = Depends(get_department_repository)
) -> EmployeeService:
    """Dependency injector for Employee Service."""
    return EmployeeService(user_repo, dept_repo)


def get_asset_lifecycle_service(
    asset_repo: AbstractAssetRepository = Depends(get_asset_repository)
) -> AssetLifecycleService:
    """Dependency injector for Asset Lifecycle State Machine Service."""
    return AssetLifecycleService(asset_repo)


def get_asset_service(
    asset_repo: AbstractAssetRepository = Depends(get_asset_repository),
    category_repo: AbstractAssetCategoryRepository = Depends(get_asset_category_repository),
    allocation_repo: AbstractAssetAllocationRepository = Depends(get_allocation_repository),
    transfer_repo: AbstractTransferRequestRepository = Depends(get_transfer_request_repository),
    maintenance_repo: AbstractMaintenanceRequestRepository = Depends(get_maintenance_request_repository)
) -> AssetService:
    """Dependency injector for Asset Service."""
    return AssetService(asset_repo, category_repo, allocation_repo, transfer_repo, maintenance_repo)


def get_allocation_service(
    alloc_repo: AbstractAssetAllocationRepository = Depends(get_allocation_repository),
    asset_repo: AbstractAssetRepository = Depends(get_asset_repository),
    user_repo: AbstractUserRepository = Depends(get_user_repository),
    dept_repo: AbstractDepartmentRepository = Depends(get_department_repository),
    lifecycle_service: AssetLifecycleService = Depends(get_asset_lifecycle_service)
) -> AllocationService:
    """Dependency injector for Asset Allocation Service."""
    return AllocationService(alloc_repo, asset_repo, user_repo, dept_repo, lifecycle_service)


def get_transfer_service(
    transfer_repo: AbstractTransferRequestRepository = Depends(get_transfer_request_repository),
    alloc_repo: AbstractAssetAllocationRepository = Depends(get_allocation_repository),
    asset_repo: AbstractAssetRepository = Depends(get_asset_repository),
    user_repo: AbstractUserRepository = Depends(get_user_repository),
    dept_repo: AbstractDepartmentRepository = Depends(get_department_repository)
) -> TransferService:
    """Dependency injector for Asset Transfer Service."""
    return TransferService(transfer_repo, alloc_repo, asset_repo, user_repo, dept_repo)


def get_booking_service(
    booking_repo: AbstractBookingRepository = Depends(get_booking_repository),
    asset_repo: AbstractAssetRepository = Depends(get_asset_repository),
    user_repo: AbstractUserRepository = Depends(get_user_repository)
) -> BookingService:
    """Dependency injector for Booking Service."""
    return BookingService(booking_repo, asset_repo, user_repo)


def get_maintenance_service(
    maintenance_repo: AbstractMaintenanceRequestRepository = Depends(get_maintenance_request_repository),
    asset_repo: AbstractAssetRepository = Depends(get_asset_repository),
    lifecycle_service: AssetLifecycleService = Depends(get_asset_lifecycle_service)
) -> MaintenanceService:
    """Dependency injector for Maintenance Service."""
    return MaintenanceService(maintenance_repo, asset_repo, lifecycle_service)


# OAuth2 password bearer configuration pointing to the login path
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    user_repo: AbstractUserRepository = Depends(get_user_repository)
) -> User:
    """
    Decodes the Bearer token and returns the current authenticated User.
    Raises UnauthorizedException if token is invalid, expired, or user is inactive.
    """
    payload = decode_token(token)
    
    if payload.get("type") != "access":
        raise UnauthorizedException("Invalid token scope. Access token required.")

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException("Malformed token credentials.")

    user = await user_repo.get_by_id(user_id)
    if not user:
        raise UnauthorizedException("Authenticated user record not found.")

    if not user.is_active:
        raise UnauthorizedException("User account is inactive.")

    return user


def require_role(*allowed_roles: Role):
    """
    Dependency factory enforcing Role-Based Access Control (RBAC).
    Verifies that the current user possesses one of the allowed roles.
    """
    async def role_dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise ForbiddenException("Access denied. Insufficient role permissions.")
        return current_user
    return role_dependency
