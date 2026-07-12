import math
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from app.core.dependencies.auth import (
    get_asset_service,
    get_asset_repository,
    get_allocation_repository,
    get_asset_lifecycle_service,
    require_role
)
from app.domain.asset import AssetStatus
from app.domain.user import Role, User
from app.exceptions.exceptions import NotFoundException
from app.repositories.asset import AbstractAssetRepository
from app.repositories.allocation import AbstractAssetAllocationRepository
from app.schemas.asset import AssetCreate, AssetResponse, AssetUpdate
from app.schemas.allocation import AssetAllocationResponse
from app.schemas.envelope import SuccessResponse
from app.schemas.query import PaginatedResponse, PaginationParams, SearchParams, SortParams
from app.services.asset_service import AssetService
from app.services.asset_lifecycle_service import AssetLifecycleService

router = APIRouter(prefix="/assets", tags=["Assets"])


@router.post(
    "",
    response_model=SuccessResponse[AssetResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new capital asset",
    description="Registers an asset in the directory with status AVAILABLE. Restricted to ADMIN and ASSET_MANAGER only.",
)
async def register_asset(
    payload: AssetCreate,
    current_user: User = Depends(require_role(Role.ADMIN, Role.ASSET_MANAGER)),
    asset_service: AssetService = Depends(get_asset_service)
) -> SuccessResponse[AssetResponse]:
    asset = await asset_service.register_asset(
        name=payload.name,
        category_id=payload.category_id,
        serial_number=payload.serial_number,
        acquisition_date=payload.acquisition_date,
        acquisition_cost=payload.acquisition_cost,
        condition=payload.condition,
        location=payload.location,
        department_id=payload.department_id,
        is_bookable=payload.is_bookable,
        document_refs=payload.document_refs
    )
    return SuccessResponse(data=AssetResponse.model_validate(asset))


@router.get(
    "",
    response_model=SuccessResponse[PaginatedResponse[AssetResponse]],
    summary="List and search assets",
    description=(
        "Retrieves a paginated list of assets. "
        "Scoping Rule: Employees can only view assets currently allocated to them."
    ),
)
async def list_assets(
    pagination: PaginationParams = Depends(),
    sort: SortParams = Depends(),
    search: SearchParams = Depends(),
    category_id: Optional[str] = Query(default=None),
    status_filter: Optional[AssetStatus] = Query(default=None, alias="status"),
    department_id: Optional[str] = Query(default=None),
    location: Optional[str] = Query(default=None),
    current_user: User = Depends(require_role(Role.ADMIN, Role.ASSET_MANAGER, Role.DEPARTMENT_HEAD, Role.EMPLOYEE)),
    asset_repo: AbstractAssetRepository = Depends(get_asset_repository),
    alloc_repo: AbstractAssetAllocationRepository = Depends(get_allocation_repository)
) -> SuccessResponse[PaginatedResponse[AssetResponse]]:
    skip = (pagination.page - 1) * pagination.page_size
    limit = pagination.page_size

    filters = {}
    if category_id is not None:
        filters["category_id"] = category_id
    if status_filter is not None:
        filters["status"] = status_filter
    if department_id is not None:
        filters["department_id"] = department_id
    if location is not None:
        filters["location"] = location

    # Employee Scoping: only see assets allocated to them
    if current_user.role == Role.EMPLOYEE:
        # Fetch active allocations for this employee
        allocs, _ = await alloc_repo.list_paginated(
            limit=1000,
            filters={"allocated_to_type": "EMPLOYEE", "allocated_to_id": current_user.id}
        )
        active_asset_ids = [a.asset_id for a in allocs if a.returned_at is None]
        
        # If no active assets are allocated, return empty response
        if not active_asset_ids:
            return SuccessResponse(
                data=PaginatedResponse(
                    items=[],
                    total=0,
                    page=pagination.page,
                    page_size=pagination.page_size,
                    total_pages=0
                )
            )
        # Apply asset IDs scope in memory filtering
        all_scoped_assets = []
        for asset_id in active_asset_ids:
            asset = await asset_repo.get_by_id(asset_id)
            if asset:
                # Apply filters manually
                match = True
                if category_id and asset.category_id != category_id:
                    match = False
                if status_filter and asset.status != status_filter:
                    match = False
                if department_id and asset.department_id != department_id:
                    match = False
                if location and asset.location != location:
                    match = False
                if search:
                    sl = search.search.lower()
                    if sl not in asset.name.lower() and (not asset.asset_tag or sl not in asset.asset_tag.lower()) and sl not in asset.serial_number.lower():
                        match = False
                if match:
                    all_scoped_assets.append(asset)
        
        total = len(all_scoped_assets)
        total_pages = math.ceil(total / pagination.page_size) if total > 0 else 0
        paginated_items = all_scoped_assets[skip : skip + limit]
        responses = [AssetResponse.model_validate(i) for i in paginated_items]
        
        data = PaginatedResponse(
            items=responses,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=total_pages
        )
        return SuccessResponse(data=data)

    # Scoped roles (Admin, Asset Manager, Department Head) see everything matching standard filters
    items, total = await asset_repo.list_paginated(
        skip=skip,
        limit=limit,
        sort_by=sort.sort_by,
        sort_order=sort.sort_order,
        search=search.search,
        filters=filters
    )

    total_pages = math.ceil(total / pagination.page_size) if total > 0 else 0
    responses = [AssetResponse.model_validate(i) for i in items]

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
    response_model=SuccessResponse[AssetResponse],
    summary="Get asset details",
    description="Fetches an asset directory profile by ID. Open to all authenticated users.",
)
async def get_asset(
    id: str,
    current_user: User = Depends(require_role(Role.ADMIN, Role.ASSET_MANAGER, Role.DEPARTMENT_HEAD, Role.EMPLOYEE)),
    asset_repo: AbstractAssetRepository = Depends(get_asset_repository)
) -> SuccessResponse[AssetResponse]:
    asset = await asset_repo.get_by_id(id)
    if not asset:
        raise NotFoundException(f"Asset with ID {id} not found.")
    return SuccessResponse(data=AssetResponse.model_validate(asset))


@router.patch(
    "/{id}",
    response_model=SuccessResponse[AssetResponse],
    summary="Update asset attributes",
    description="Updates non-lifecycle properties. Lifecycle changes are blocked here. Restricted to ADMIN and ASSET_MANAGER.",
)
async def update_asset(
    id: str,
    payload: AssetUpdate,
    current_user: User = Depends(require_role(Role.ADMIN, Role.ASSET_MANAGER)),
    asset_service: AssetService = Depends(get_asset_service)
) -> SuccessResponse[AssetResponse]:
    asset = await asset_service.update_asset(
        asset_id=id,
        name=payload.name,
        category_id=payload.category_id,
        serial_number=payload.serial_number,
        acquisition_date=payload.acquisition_date,
        acquisition_cost=payload.acquisition_cost,
        condition=payload.condition,
        location=payload.location,
        department_id=payload.department_id,
        is_bookable=payload.is_bookable,
        document_refs=payload.document_refs
    )
    return SuccessResponse(data=AssetResponse.model_validate(asset))


@router.get(
    "/{id}/history",
    response_model=SuccessResponse[dict],
    summary="Get asset checkout history",
    description="Fetches the full checkout allocations history and stubs maintenance events for an asset.",
)
async def get_asset_history(
    id: str,
    current_user: User = Depends(require_role(Role.ADMIN, Role.ASSET_MANAGER, Role.DEPARTMENT_HEAD, Role.EMPLOYEE)),
    asset_service: AssetService = Depends(get_asset_service)
) -> SuccessResponse[dict]:
    history = await asset_service.get_asset_history(id)
    
    # Map allocations to Response schema
    alloc_responses = [AssetAllocationResponse.model_validate(a).model_dump() for a in history["allocations"]]
    
    # Map transfers to Response schema
    transfer_responses = []
    if "transfers" in history:
        from app.schemas.transfer import TransferRequestResponse
        transfer_responses = [TransferRequestResponse.model_validate(t).model_dump() for t in history["transfers"]]

    # Map maintenance to Response schema
    maintenance_responses = []
    if "maintenance_history" in history:
        from app.schemas.maintenance import MaintenanceRequestResponse
        maintenance_responses = [MaintenanceRequestResponse.model_validate(m).model_dump() for m in history["maintenance_history"]]

    response_dict = {
        "asset_id": history["asset_id"],
        "asset_tag": history["asset_tag"],
        "allocations": alloc_responses,
        "transfers": transfer_responses,
        "maintenance_history": maintenance_responses
    }
    return SuccessResponse(data=response_dict)


@router.patch(
    "/{id}/retire",
    response_model=SuccessResponse[AssetResponse],
    summary="Retire an asset",
    description="Transitions status from AVAILABLE/LOST to RETIRED. Restricted to ADMIN and ASSET_MANAGER.",
)
async def retire_asset(
    id: str,
    reason: Optional[str] = Query(default=None),
    current_user: User = Depends(require_role(Role.ADMIN, Role.ASSET_MANAGER)),
    asset_repo: AbstractAssetRepository = Depends(get_asset_repository),
    lifecycle_service: AssetLifecycleService = Depends(get_asset_lifecycle_service)
) -> SuccessResponse[AssetResponse]:
    asset = await asset_repo.get_by_id(id)
    if not asset:
        raise NotFoundException(f"Asset with ID {id} not found.")
    
    updated = await lifecycle_service.transition_to(
        asset=asset,
        target_status=AssetStatus.RETIRED,
        actor_id=current_user.id,
        reason=reason
    )
    return SuccessResponse(data=AssetResponse.model_validate(updated))


@router.patch(
    "/{id}/dispose",
    response_model=SuccessResponse[AssetResponse],
    summary="Dispose an asset",
    description="Transitions status from RETIRED to DISPOSED. Restricted to ADMIN and ASSET_MANAGER.",
)
async def dispose_asset(
    id: str,
    reason: Optional[str] = Query(default=None),
    current_user: User = Depends(require_role(Role.ADMIN, Role.ASSET_MANAGER)),
    asset_repo: AbstractAssetRepository = Depends(get_asset_repository),
    lifecycle_service: AssetLifecycleService = Depends(get_asset_lifecycle_service)
) -> SuccessResponse[AssetResponse]:
    asset = await asset_repo.get_by_id(id)
    if not asset:
        raise NotFoundException(f"Asset with ID {id} not found.")
    
    updated = await lifecycle_service.transition_to(
        asset=asset,
        target_status=AssetStatus.DISPOSED,
        actor_id=current_user.id,
        reason=reason
    )
    return SuccessResponse(data=AssetResponse.model_validate(updated))


@router.patch(
    "/{id}/mark-lost",
    response_model=SuccessResponse[AssetResponse],
    summary="Mark an asset as lost",
    description="Transitions status from AVAILABLE/ALLOCATED to LOST. Restricted to ADMIN and ASSET_MANAGER.",
)
async def mark_lost_asset(
    id: str,
    reason: Optional[str] = Query(default=None),
    current_user: User = Depends(require_role(Role.ADMIN, Role.ASSET_MANAGER)),
    asset_repo: AbstractAssetRepository = Depends(get_asset_repository),
    lifecycle_service: AssetLifecycleService = Depends(get_asset_lifecycle_service)
) -> SuccessResponse[AssetResponse]:
    asset = await asset_repo.get_by_id(id)
    if not asset:
        raise NotFoundException(f"Asset with ID {id} not found.")
    
    updated = await lifecycle_service.transition_to(
        asset=asset,
        target_status=AssetStatus.LOST,
        actor_id=current_user.id,
        reason=reason
    )
    return SuccessResponse(data=AssetResponse.model_validate(updated))


@router.patch(
    "/{id}/reserve",
    response_model=SuccessResponse[AssetResponse],
    summary="Reserve an asset",
    description="Transitions status from AVAILABLE to RESERVED. Restricted to ADMIN and ASSET_MANAGER.",
)
async def reserve_asset(
    id: str,
    reason: Optional[str] = Query(default=None),
    current_user: User = Depends(require_role(Role.ADMIN, Role.ASSET_MANAGER)),
    asset_repo: AbstractAssetRepository = Depends(get_asset_repository),
    lifecycle_service: AssetLifecycleService = Depends(get_asset_lifecycle_service)
) -> SuccessResponse[AssetResponse]:
    asset = await asset_repo.get_by_id(id)
    if not asset:
        raise NotFoundException(f"Asset with ID {id} not found.")
    
    updated = await lifecycle_service.transition_to(
        asset=asset,
        target_status=AssetStatus.RESERVED,
        actor_id=current_user.id,
        reason=reason
    )
    return SuccessResponse(data=AssetResponse.model_validate(updated))


@router.patch(
    "/{id}/release",
    response_model=SuccessResponse[AssetResponse],
    summary="Release a reservation",
    description="Transitions status from RESERVED to AVAILABLE. Restricted to ADMIN and ASSET_MANAGER.",
)
async def release_asset(
    id: str,
    reason: Optional[str] = Query(default=None),
    current_user: User = Depends(require_role(Role.ADMIN, Role.ASSET_MANAGER)),
    asset_repo: AbstractAssetRepository = Depends(get_asset_repository),
    lifecycle_service: AssetLifecycleService = Depends(get_asset_lifecycle_service)
) -> SuccessResponse[AssetResponse]:
    asset = await asset_repo.get_by_id(id)
    if not asset:
        raise NotFoundException(f"Asset with ID {id} not found.")
    
    updated = await lifecycle_service.transition_to(
        asset=asset,
        target_status=AssetStatus.AVAILABLE,
        actor_id=current_user.id,
        reason=reason
    )
    return SuccessResponse(data=AssetResponse.model_validate(updated))
