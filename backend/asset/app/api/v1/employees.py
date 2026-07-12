import math
from typing import Optional
from fastapi import APIRouter, Depends, Query
from app.core.dependencies.auth import get_employee_service, require_role
from app.domain.user import Role, User
from app.schemas.employee import EmployeeAssignDepartment, EmployeePromotionRequest, EmployeeResponse
from app.schemas.envelope import SuccessResponse
from app.schemas.query import PaginatedResponse, PaginationParams, SearchParams, SortParams
from app.services.employee_service import EmployeeService

router = APIRouter(prefix="/employees", tags=["Employees"])


@router.get(
    "",
    response_model=SuccessResponse[PaginatedResponse[EmployeeResponse]],
    summary="List employee directory",
    description=(
        "Retrieves a paginated list of employees. Restricted to ADMIN, ASSET_MANAGER, and DEPARTMENT_HEAD. "
        "Scoping Rule: DEPARTMENT_HEADs can only retrieve employees belonging to their own department."
    ),
)
async def list_employees(
    pagination: PaginationParams = Depends(),
    sort: SortParams = Depends(),
    search: SearchParams = Depends(),
    department_id: Optional[str] = Query(default=None),
    role: Optional[Role] = Query(default=None),
    status_filter: Optional[bool] = Query(default=None, alias="status"),
    current_user: User = Depends(require_role(Role.ADMIN, Role.ASSET_MANAGER, Role.DEPARTMENT_HEAD)),
    emp_service: EmployeeService = Depends(get_employee_service)
) -> SuccessResponse[PaginatedResponse[EmployeeResponse]]:
    skip = (pagination.page - 1) * pagination.page_size
    limit = pagination.page_size

    filters = {}
    if status_filter is not None:
        filters["status"] = status_filter
    if department_id is not None:
        filters["department_id"] = department_id
    if role is not None:
        filters["role"] = role

    items, total = await emp_service.list_employees(
        caller=current_user,
        skip=skip,
        limit=limit,
        sort_by=sort.sort_by,
        sort_order=sort.sort_order,
        search=search.search,
        filters=filters
    )

    total_pages = math.ceil(total / pagination.page_size) if total > 0 else 0
    responses = [EmployeeResponse.model_validate(i) for i in items]

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
    response_model=SuccessResponse[EmployeeResponse],
    summary="View employee profile",
    description=(
        "Fetches profile detail of a specific employee. Open to ADMIN, ASSET_MANAGER, and DEPARTMENT_HEAD. "
        "Also open to the Employee themselves for self-service profiles. "
        "Scoping Rule: DEPARTMENT_HEADs can only query employees in their own department."
    ),
)
async def get_employee(
    id: str,
    current_user: User = Depends(require_role(Role.ADMIN, Role.ASSET_MANAGER, Role.DEPARTMENT_HEAD, Role.EMPLOYEE)),
    emp_service: EmployeeService = Depends(get_employee_service)
) -> SuccessResponse[EmployeeResponse]:
    emp = await emp_service.get_employee_detail(employee_id=id, caller=current_user)
    return SuccessResponse(data=EmployeeResponse.model_validate(emp))


@router.patch(
    "/{id}/department",
    response_model=SuccessResponse[EmployeeResponse],
    summary="Assign employee department",
    description="Updates the employee's assigned department. Restricted to ADMIN only.",
)
async def assign_department(
    id: str,
    payload: EmployeeAssignDepartment,
    current_user: User = Depends(require_role(Role.ADMIN)),
    emp_service: EmployeeService = Depends(get_employee_service)
) -> SuccessResponse[EmployeeResponse]:
    emp = await emp_service.assign_department(employee_id=id, department_id=payload.department_id)
    return SuccessResponse(data=EmployeeResponse.model_validate(emp))


@router.patch(
    "/{id}/activate",
    response_model=SuccessResponse[EmployeeResponse],
    summary="Administrative activation",
    description="Activates an employee account. Restricted to ADMIN only.",
)
async def activate_employee(
    id: str,
    current_user: User = Depends(require_role(Role.ADMIN)),
    emp_service: EmployeeService = Depends(get_employee_service)
) -> SuccessResponse[EmployeeResponse]:
    emp = await emp_service.activate_employee(id)
    return SuccessResponse(data=EmployeeResponse.model_validate(emp))


@router.patch(
    "/{id}/deactivate",
    response_model=SuccessResponse[EmployeeResponse],
    summary="Administrative deactivation",
    description="Deactivates an employee account. Enforces last Admin lockout protection. Restricted to ADMIN only.",
)
async def deactivate_employee(
    id: str,
    current_user: User = Depends(require_role(Role.ADMIN)),
    emp_service: EmployeeService = Depends(get_employee_service)
) -> SuccessResponse[EmployeeResponse]:
    emp = await emp_service.deactivate_employee(id)
    return SuccessResponse(data=EmployeeResponse.model_validate(emp))


@router.post(
    "/{id}/promote",
    response_model=SuccessResponse[EmployeeResponse],
    summary="Role Promotion and demotion",
    description=(
        "Updates an active employee's role (ADMIN, DEPARTMENT_HEAD, ASSET_MANAGER, EMPLOYEE). "
        "Protects the system from demoting the last active Administrator. Restricted to ADMIN only. "
        "\n\n*Note on Linking*: Promoting a user to DEPARTMENT_HEAD flags their capability but does NOT "
        "automatically assign them to head any department. You must explicitly associate them to a department "
        "using the PATCH /api/v1/departments/{id} endpoint."
    ),
)
async def promote_employee(
    id: str,
    payload: EmployeePromotionRequest,
    current_user: User = Depends(require_role(Role.ADMIN)),
    emp_service: EmployeeService = Depends(get_employee_service)
) -> SuccessResponse[EmployeeResponse]:
    emp = await emp_service.promote_employee(
        actor_user_id=current_user.id,
        target_user_id=id,
        target_role=payload.role
    )
    return SuccessResponse(data=EmployeeResponse.model_validate(emp))
