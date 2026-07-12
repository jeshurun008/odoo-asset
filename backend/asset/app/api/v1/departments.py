import math
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from app.core.dependencies.auth import get_department_service, get_department_repository, require_role
from app.domain.user import Role, User
from app.exceptions.exceptions import NotFoundException
from app.repositories.department import AbstractDepartmentRepository
from app.schemas.department import DepartmentCreate, DepartmentResponse, DepartmentUpdate
from app.schemas.envelope import SuccessResponse
from app.schemas.query import PaginatedResponse, PaginationParams, SearchParams, SortParams
from app.services.department_service import DepartmentService

router = APIRouter(prefix="/departments", tags=["Departments"])


@router.post(
    "",
    response_model=SuccessResponse[DepartmentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new department",
    description=(
        "Registers a new department. Restricted to ADMIN only. "
        "\n\n*Note on Department Head*: If department_head_id is assigned, the target user must exist, "
        "be Active, and possess the DEPARTMENT_HEAD or ADMIN role, otherwise the request is rejected with a ConflictException (409)."
    ),
)
async def create_department(
    payload: DepartmentCreate,
    current_user: User = Depends(require_role(Role.ADMIN)),
    dept_service: DepartmentService = Depends(get_department_service)
) -> SuccessResponse[DepartmentResponse]:
    dept = await dept_service.create_department(
        name=payload.name,
        description=payload.description,
        parent_department_id=payload.parent_department_id,
        department_head_id=payload.department_head_id
    )
    return SuccessResponse(data=DepartmentResponse.model_validate(dept))


@router.get(
    "",
    response_model=SuccessResponse[PaginatedResponse[DepartmentResponse]],
    summary="List and filter departments",
    description="Lists all departments with paginated, sorted, and searched filters. Open to all authenticated users.",
)
async def list_departments(
    pagination: PaginationParams = Depends(),
    sort: SortParams = Depends(),
    search: SearchParams = Depends(),
    parent_department_id: Optional[str] = Query(default=None),
    status_filter: Optional[bool] = Query(default=None, alias="status"),
    current_user: User = Depends(require_role(Role.ADMIN, Role.ASSET_MANAGER, Role.DEPARTMENT_HEAD, Role.EMPLOYEE)),
    dept_repo: AbstractDepartmentRepository = Depends(get_department_repository)
) -> SuccessResponse[PaginatedResponse[DepartmentResponse]]:
    skip = (pagination.page - 1) * pagination.page_size
    limit = pagination.page_size

    filters = {}
    if status_filter is not None:
        filters["status"] = status_filter
    if parent_department_id is not None:
        filters["parent_department_id"] = parent_department_id

    items, total = await dept_repo.list_paginated(
        skip=skip,
        limit=limit,
        sort_by=sort.sort_by,
        sort_order=sort.sort_order,
        search=search.search,
        filters=filters
    )

    total_pages = math.ceil(total / pagination.page_size) if total > 0 else 0
    responses = [DepartmentResponse.model_validate(i) for i in items]

    data = PaginatedResponse(
        items=responses,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages
    )
    return SuccessResponse(data=data)


@router.get(
    "/{id}",
    response_model=SuccessResponse[DepartmentResponse],
    summary="Get department details",
    description="Fetches a department profile by ID. Open to all authenticated users.",
)
async def get_department(
    id: str,
    current_user: User = Depends(require_role(Role.ADMIN, Role.ASSET_MANAGER, Role.DEPARTMENT_HEAD, Role.EMPLOYEE)),
    dept_repo: AbstractDepartmentRepository = Depends(get_department_repository)
) -> SuccessResponse[DepartmentResponse]:
    dept = await dept_repo.get_by_id(id)
    if not dept:
        raise NotFoundException(f"Department with ID {id} not found.")
    return SuccessResponse(data=DepartmentResponse.model_validate(dept))


@router.patch(
    "/{id}",
    response_model=SuccessResponse[DepartmentResponse],
    summary="Update department attributes",
    description=(
        "Updates structural department details (name, description, head, parent). Restricted to ADMIN only. "
        "\n\n*Note on Department Head*: If department_head_id is assigned, the target user must exist, "
        "be Active, and possess the DEPARTMENT_HEAD or ADMIN role, otherwise the request is rejected with a ConflictException (409)."
    ),
)
async def update_department(
    id: str,
    payload: DepartmentUpdate,
    current_user: User = Depends(require_role(Role.ADMIN)),
    dept_service: DepartmentService = Depends(get_department_service)
) -> SuccessResponse[DepartmentResponse]:
    dept = await dept_service.update_department(
        dept_id=id,
        name=payload.name,
        description=payload.description,
        parent_department_id=payload.parent_department_id,
        department_head_id=payload.department_head_id
    )
    return SuccessResponse(data=DepartmentResponse.model_validate(dept))


@router.patch(
    "/{id}/deactivate",
    response_model=SuccessResponse[DepartmentResponse],
    summary="Soft-deactivate a department",
    description="Sets department status to Inactive. Blocks if active children or active employees remain. Restricted to ADMIN only.",
)
async def deactivate_department(
    id: str,
    current_user: User = Depends(require_role(Role.ADMIN)),
    dept_service: DepartmentService = Depends(get_department_service)
) -> SuccessResponse[DepartmentResponse]:
    dept = await dept_service.deactivate_department(id)
    return SuccessResponse(data=DepartmentResponse.model_validate(dept))
