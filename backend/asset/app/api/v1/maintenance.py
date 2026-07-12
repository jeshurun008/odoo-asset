import math
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from app.core.dependencies.auth import (
    get_maintenance_service,
    get_maintenance_request_repository,
    require_role,
    get_current_user
)
from app.domain.user import Role, User
from app.exceptions.exceptions import NotFoundException
from app.repositories.maintenance_request import AbstractMaintenanceRequestRepository
from app.schemas.maintenance import (
    MaintenanceAssignRequest,
    MaintenanceRejectRequest,
    MaintenanceRequestCreate,
    MaintenanceRequestResponse
)
from app.schemas.envelope import SuccessResponse
from app.schemas.query import PaginatedResponse, PaginationParams, SearchParams, SortParams
from app.services.maintenance_service import MaintenanceService

router = APIRouter(prefix="/maintenance-requests", tags=["Maintenance"])


@router.post(
    "",
    response_model=SuccessResponse[MaintenanceRequestResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Raise a maintenance request",
    description="Submits a new maintenance ticket in PENDING status. Open to all authenticated users.",
)
async def raise_maintenance_request(
    payload: MaintenanceRequestCreate,
    current_user: User = Depends(get_current_user),
    maintenance_service: MaintenanceService = Depends(get_maintenance_service)
) -> SuccessResponse[MaintenanceRequestResponse]:
    req = await maintenance_service.raise_request(
        asset_id=payload.asset_id,
        raised_by=current_user.id,
        issue_description=payload.issue_description,
        priority=payload.priority,
        photo_ref=payload.photo_ref
    )
    return SuccessResponse(data=MaintenanceRequestResponse.model_validate(req))


@router.get(
    "",
    response_model=SuccessResponse[PaginatedResponse[MaintenanceRequestResponse]],
    summary="List maintenance requests",
    description=(
        "Retrieves a list of maintenance requests. Supports filtering by status, priority, and date range. "
        "Scoping: Employees can only view requests they raised."
    ),
)
async def list_maintenance_requests(
    pagination: PaginationParams = Depends(),
    sort: SortParams = Depends(),
    search: SearchParams = Depends(),
    asset_id: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    priority: Optional[str] = Query(default=None),
    maintenance_today: Optional[bool] = Query(default=None, alias="today"),
    current_user: User = Depends(get_current_user),
    maintenance_repo: AbstractMaintenanceRequestRepository = Depends(get_maintenance_request_repository)
) -> SuccessResponse[PaginatedResponse[MaintenanceRequestResponse]]:
    skip = (pagination.page - 1) * pagination.page_size
    limit = pagination.page_size

    filters = {}
    if asset_id is not None:
        filters["asset_id"] = asset_id
    if status_filter is not None:
        filters["status"] = status_filter
    if priority is not None:
        filters["priority"] = priority
    if maintenance_today is not None:
        filters["maintenance_today"] = maintenance_today

    # Scoping: Employees only see their own requests
    if current_user.role == Role.EMPLOYEE:
        filters["raised_by"] = current_user.id

    items, total = await maintenance_repo.list_paginated(
        skip=skip,
        limit=limit,
        sort_by=sort.sort_by,
        sort_order=sort.sort_order,
        search=search.search,
        filters=filters
    )

    total_pages = math.ceil(total / pagination.page_size) if total > 0 else 0
    responses = [MaintenanceRequestResponse.model_validate(i) for i in items]

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
    response_model=SuccessResponse[MaintenanceRequestResponse],
    summary="Get maintenance request details",
)
async def get_maintenance_request(
    id: str,
    current_user: User = Depends(get_current_user),
    maintenance_repo: AbstractMaintenanceRequestRepository = Depends(get_maintenance_request_repository)
) -> SuccessResponse[MaintenanceRequestResponse]:
    req = await maintenance_repo.get_by_id(id)
    if not req:
        raise NotFoundException(f"Maintenance request with ID {id} not found.")
    return SuccessResponse(data=MaintenanceRequestResponse.model_validate(req))


@router.patch(
    "/{id}/approve",
    response_model=SuccessResponse[MaintenanceRequestResponse],
    summary="Approve maintenance request",
    description="Transitions request PENDING -> APPROVED. Asset transitions to UNDER_MAINTENANCE. Restricted to ADMIN/ASSET_MANAGER.",
)
async def approve_maintenance_request(
    id: str,
    current_user: User = Depends(require_role(Role.ADMIN, Role.ASSET_MANAGER)),
    maintenance_service: MaintenanceService = Depends(get_maintenance_service)
) -> SuccessResponse[MaintenanceRequestResponse]:
    req = await maintenance_service.approve_request(request_id=id, approver_id=current_user.id)
    return SuccessResponse(data=MaintenanceRequestResponse.model_validate(req))


@router.patch(
    "/{id}/reject",
    response_model=SuccessResponse[MaintenanceRequestResponse],
    summary="Reject maintenance request",
    description="Transitions request PENDING -> REJECTED. Requires rejection reason. Restricted to ADMIN/ASSET_MANAGER.",
)
async def reject_maintenance_request(
    id: str,
    payload: MaintenanceRejectRequest,
    current_user: User = Depends(require_role(Role.ADMIN, Role.ASSET_MANAGER)),
    maintenance_service: MaintenanceService = Depends(get_maintenance_service)
) -> SuccessResponse[MaintenanceRequestResponse]:
    req = await maintenance_service.reject_request(
        request_id=id,
        rejected_by=current_user.id,
        reason=payload.rejected_reason
    )
    return SuccessResponse(data=MaintenanceRequestResponse.model_validate(req))


@router.patch(
    "/{id}/assign-technician",
    response_model=SuccessResponse[MaintenanceRequestResponse],
    summary="Assign technician to request",
    description="Transitions APPROVED -> TECHNICIAN_ASSIGNED. Sets assigned technician name. Restricted to ADMIN/ASSET_MANAGER.",
)
async def assign_technician(
    id: str,
    payload: MaintenanceAssignRequest,
    current_user: User = Depends(require_role(Role.ADMIN, Role.ASSET_MANAGER)),
    maintenance_service: MaintenanceService = Depends(get_maintenance_service)
) -> SuccessResponse[MaintenanceRequestResponse]:
    req = await maintenance_service.assign_technician(
        request_id=id,
        technician_name=payload.assigned_technician,
        actor_id=current_user.id
    )
    return SuccessResponse(data=MaintenanceRequestResponse.model_validate(req))


@router.patch(
    "/{id}/start",
    response_model=SuccessResponse[MaintenanceRequestResponse],
    summary="Start maintenance work",
    description="Transitions TECHNICIAN_ASSIGNED -> IN_PROGRESS. Restricted to ADMIN/ASSET_MANAGER.",
)
async def start_maintenance_work(
    id: str,
    current_user: User = Depends(require_role(Role.ADMIN, Role.ASSET_MANAGER)),
    maintenance_service: MaintenanceService = Depends(get_maintenance_service)
) -> SuccessResponse[MaintenanceRequestResponse]:
    req = await maintenance_service.start_work(request_id=id, actor_id=current_user.id)
    return SuccessResponse(data=MaintenanceRequestResponse.model_validate(req))


@router.patch(
    "/{id}/resolve",
    response_model=SuccessResponse[MaintenanceRequestResponse],
    summary="Resolve maintenance request",
    description="Transitions IN_PROGRESS -> RESOLVED. Reverts asset back to pre-maintenance status. Restricted to ADMIN/ASSET_MANAGER.",
)
async def resolve_maintenance_request(
    id: str,
    current_user: User = Depends(require_role(Role.ADMIN, Role.ASSET_MANAGER)),
    maintenance_service: MaintenanceService = Depends(get_maintenance_service)
) -> SuccessResponse[MaintenanceRequestResponse]:
    req = await maintenance_service.resolve_request(request_id=id, actor_id=current_user.id)
    return SuccessResponse(data=MaintenanceRequestResponse.model_validate(req))
