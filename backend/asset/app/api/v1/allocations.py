import math
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from app.core.dependencies.auth import (
    get_allocation_service,
    get_allocation_repository,
    require_role
)
from app.domain.user import Role, User
from app.exceptions.exceptions import NotFoundException
from app.repositories.allocation import AbstractAssetAllocationRepository
from app.schemas.allocation import AssetAllocationCreate, AssetAllocationResponse, AssetReturnRequest
from app.schemas.envelope import SuccessResponse
from app.schemas.query import PaginatedResponse, PaginationParams, SearchParams, SortParams
from app.services.allocation_service import AllocationService

router = APIRouter(prefix="/allocations", tags=["Allocations"])


@router.post(
    "",
    response_model=SuccessResponse[AssetAllocationResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Allocate an asset",
    description="Checks out an available asset to a specific employee or department. Restricted to ADMIN and ASSET_MANAGER.",
)
async def allocate_asset(
    payload: AssetAllocationCreate,
    current_user: User = Depends(require_role(Role.ADMIN, Role.ASSET_MANAGER)),
    alloc_service: AllocationService = Depends(get_allocation_service)
) -> SuccessResponse[AssetAllocationResponse]:
    alloc = await alloc_service.allocate_asset(
        asset_id=payload.asset_id,
        allocated_to_type=payload.allocated_to_type,
        allocated_to_id=payload.allocated_to_id,
        allocated_by=current_user.id,
        expected_return_date=payload.expected_return_date
    )
    return SuccessResponse(data=AssetAllocationResponse.model_validate(alloc))


@router.get(
    "",
    response_model=SuccessResponse[PaginatedResponse[AssetAllocationResponse]],
    summary="List asset allocations",
    description="Lists all allocations with pagination and filters (including overdue status). Open to all authenticated users.",
)
async def list_allocations(
    pagination: PaginationParams = Depends(),
    sort: SortParams = Depends(),
    search: SearchParams = Depends(),
    asset_id: Optional[str] = Query(default=None),
    allocated_to_id: Optional[str] = Query(default=None),
    overdue: Optional[bool] = Query(default=None),
    current_user: User = Depends(require_role(Role.ADMIN, Role.ASSET_MANAGER, Role.DEPARTMENT_HEAD, Role.EMPLOYEE)),
    alloc_repo: AbstractAssetAllocationRepository = Depends(get_allocation_repository)
) -> SuccessResponse[PaginatedResponse[AssetAllocationResponse]]:
    skip = (pagination.page - 1) * pagination.page_size
    limit = pagination.page_size

    filters = {}
    if asset_id is not None:
        filters["asset_id"] = asset_id
    if allocated_to_id is not None:
        filters["allocated_to_id"] = allocated_to_id
    if overdue is not None:
        filters["overdue"] = overdue

    items, total = await alloc_repo.list_paginated(
        skip=skip,
        limit=limit,
        sort_by=sort.sort_by,
        sort_order=sort.sort_order,
        search=search.search,
        filters=filters
    )

    total_pages = math.ceil(total / pagination.page_size) if total > 0 else 0
    responses = [AssetAllocationResponse.model_validate(i) for i in items]

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
    response_model=SuccessResponse[AssetAllocationResponse],
    summary="Get allocation details",
    description="Fetches details of an allocation checkout record by ID. Open to all authenticated users.",
)
async def get_allocation(
    id: str,
    current_user: User = Depends(require_role(Role.ADMIN, Role.ASSET_MANAGER, Role.DEPARTMENT_HEAD, Role.EMPLOYEE)),
    alloc_repo: AbstractAssetAllocationRepository = Depends(get_allocation_repository)
) -> SuccessResponse[AssetAllocationResponse]:
    alloc = await alloc_repo.get_by_id(id)
    if not alloc:
        raise NotFoundException(f"Allocation record with ID {id} not found.")
    return SuccessResponse(data=AssetAllocationResponse.model_validate(alloc))


@router.patch(
    "/{id}/return",
    response_model=SuccessResponse[AssetAllocationResponse],
    summary="Return/check-in an asset",
    description=(
        "Checks in an allocated asset, recording condition notes and setting status back to AVAILABLE. "
        "Restricted to ADMIN, ASSET_MANAGER, or the DEPARTMENT_HEAD of the department holding the asset."
    ),
)
async def return_asset(
    id: str,
    payload: AssetReturnRequest,
    current_user: User = Depends(require_role(Role.ADMIN, Role.ASSET_MANAGER, Role.DEPARTMENT_HEAD)),
    alloc_service: AllocationService = Depends(get_allocation_service)
) -> SuccessResponse[AssetAllocationResponse]:
    alloc = await alloc_service.return_asset(
        allocation_id=id,
        condition_check_in_notes=payload.condition_check_in_notes,
        return_actor_id=current_user.id
    )
    return SuccessResponse(data=AssetAllocationResponse.model_validate(alloc))
