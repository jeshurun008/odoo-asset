import math
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from app.core.dependencies.auth import (
    get_transfer_service,
    get_transfer_request_repository,
    require_role
)
from app.domain.user import Role, User
from app.repositories.transfer_request import AbstractTransferRequestRepository
from app.schemas.transfer import TransferRejectRequest, TransferRequestCreate, TransferRequestResponse
from app.schemas.envelope import SuccessResponse
from app.schemas.query import PaginatedResponse, PaginationParams, SearchParams, SortParams
from app.services.transfer_service import TransferService

router = APIRouter(prefix="/transfers", tags=["Transfers"])


@router.post(
    "",
    response_model=SuccessResponse[TransferRequestResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a transfer request",
    description="Submits a request to transfer an allocated asset. Open to any authenticated user.",
)
async def create_transfer_request(
    payload: TransferRequestCreate,
    current_user: User = Depends(require_role(Role.ADMIN, Role.ASSET_MANAGER, Role.DEPARTMENT_HEAD, Role.EMPLOYEE)),
    transfer_service: TransferService = Depends(get_transfer_service)
) -> SuccessResponse[TransferRequestResponse]:
    req = await transfer_service.create_transfer_request(
        asset_id=payload.asset_id,
        requested_by=current_user.id,
        requested_to_type=payload.requested_to_type,
        requested_to_id=payload.requested_to_id,
        reason=payload.reason
    )
    return SuccessResponse(data=TransferRequestResponse.model_validate(req))


@router.get(
    "",
    response_model=SuccessResponse[PaginatedResponse[TransferRequestResponse]],
    summary="List transfer requests",
    description="Lists all transfer requests with pagination. Open to all authenticated users.",
)
async def list_transfers(
    pagination: PaginationParams = Depends(),
    sort: SortParams = Depends(),
    search: SearchParams = Depends(),
    asset_id: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    current_user: User = Depends(require_role(Role.ADMIN, Role.ASSET_MANAGER, Role.DEPARTMENT_HEAD, Role.EMPLOYEE)),
    transfer_repo: AbstractTransferRequestRepository = Depends(get_transfer_request_repository)
) -> SuccessResponse[PaginatedResponse[TransferRequestResponse]]:
    skip = (pagination.page - 1) * pagination.page_size
    limit = pagination.page_size

    filters = {}
    if asset_id is not None:
        filters["asset_id"] = asset_id
    if status_filter is not None:
        filters["status"] = status_filter

    items, total = await transfer_repo.list_paginated(
        skip=skip,
        limit=limit,
        sort_by=sort.sort_by,
        sort_order=sort.sort_order,
        search=search.search,
        filters=filters
    )

    total_pages = math.ceil(total / pagination.page_size) if total > 0 else 0
    responses = [TransferRequestResponse.model_validate(i) for i in items]

    data = PaginatedResponse(
        items=responses,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages
    )
    return SuccessResponse(data=data)


@router.patch(
    "/{id}/approve",
    response_model=SuccessResponse[TransferRequestResponse],
    summary="Approve transfer request",
    description=(
        "Approves and completes the asset transfer request. "
        "Restricted to ADMIN, ASSET_MANAGER, or the DEPARTMENT_HEAD of the department currently holding the asset."
    ),
)
async def approve_transfer(
    id: str,
    current_user: User = Depends(require_role(Role.ADMIN, Role.ASSET_MANAGER, Role.DEPARTMENT_HEAD)),
    transfer_service: TransferService = Depends(get_transfer_service)
) -> SuccessResponse[TransferRequestResponse]:
    req = await transfer_service.approve_transfer(
        transfer_id=id,
        approver_id=current_user.id
    )
    return SuccessResponse(data=TransferRequestResponse.model_validate(req))


@router.patch(
    "/{id}/reject",
    response_model=SuccessResponse[TransferRequestResponse],
    summary="Reject transfer request",
    description=(
        "Rejects the asset transfer request. "
        "Restricted to ADMIN, ASSET_MANAGER, or the DEPARTMENT_HEAD of the department currently holding the asset."
    ),
)
async def reject_transfer(
    id: str,
    payload: TransferRejectRequest,
    current_user: User = Depends(require_role(Role.ADMIN, Role.ASSET_MANAGER, Role.DEPARTMENT_HEAD)),
    transfer_service: TransferService = Depends(get_transfer_service)
) -> SuccessResponse[TransferRequestResponse]:
    req = await transfer_service.reject_transfer(
        transfer_id=id,
        resolver_id=current_user.id,
        reason=payload.reason
    )
    return SuccessResponse(data=TransferRequestResponse.model_validate(req))
