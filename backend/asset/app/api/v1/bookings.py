import math
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from app.core.dependencies.auth import (
    get_booking_service,
    get_booking_repository,
    require_role,
    get_current_user
)
from app.domain.user import Role, User
from app.exceptions.exceptions import NotFoundException
from app.repositories.booking import AbstractBookingRepository
from app.schemas.booking import BookingCancelRequest, BookingCreate, BookingResponse, BookingRescheduleRequest
from app.schemas.envelope import SuccessResponse
from app.schemas.query import PaginatedResponse, PaginationParams, SearchParams, SortParams
from app.services.booking_service import BookingService

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post(
    "",
    response_model=SuccessResponse[BookingResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create resource booking",
    description="Books an asset for a calendar range. Requires is_bookable asset flag.",
)
async def create_booking(
    payload: BookingCreate,
    current_user: User = Depends(get_current_user),
    booking_service: BookingService = Depends(get_booking_service)
) -> SuccessResponse[BookingResponse]:
    booking = await booking_service.create_booking(
        asset_id=payload.asset_id,
        booked_by=current_user.id,
        start_time=payload.start_time,
        end_time=payload.end_time,
        booked_for_department_id=payload.booked_for_department_id
    )
    return SuccessResponse(data=BookingResponse.model_validate(booking))


@router.get(
    "",
    response_model=SuccessResponse[PaginatedResponse[BookingResponse]],
    summary="List resource bookings",
    description="Retrieves calendar bookings. Scoping: Employees only see their own bookings.",
)
async def list_bookings(
    pagination: PaginationParams = Depends(),
    sort: SortParams = Depends(),
    search: SearchParams = Depends(),
    asset_id: Optional[str] = Query(default=None),
    booked_by: Optional[str] = Query(default=None),
    booked_for_department_id: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
    booking_repo: AbstractBookingRepository = Depends(get_booking_repository)
) -> SuccessResponse[PaginatedResponse[BookingResponse]]:
    skip = (pagination.page - 1) * pagination.page_size
    limit = pagination.page_size

    filters = {}
    if asset_id is not None:
        filters["asset_id"] = asset_id
    if booked_by is not None:
        filters["booked_by"] = booked_by
    if booked_for_department_id is not None:
        filters["booked_for_department_id"] = booked_for_department_id
    if status_filter is not None:
        filters["status"] = status_filter

    # Scoping rule: Employee can only see their own bookings
    if current_user.role == Role.EMPLOYEE:
        filters["booked_by"] = current_user.id

    items, total = await booking_repo.list_paginated(
        skip=skip,
        limit=limit,
        sort_by=sort.sort_by,
        sort_order=sort.sort_order,
        search=search.search,
        filters=filters
    )

    total_pages = math.ceil(total / pagination.page_size) if total > 0 else 0
    responses = [BookingResponse.model_validate(i) for i in items]

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
    response_model=SuccessResponse[BookingResponse],
    summary="Get booking details",
)
async def get_booking(
    id: str,
    current_user: User = Depends(get_current_user),
    booking_repo: AbstractBookingRepository = Depends(get_booking_repository)
) -> SuccessResponse[BookingResponse]:
    booking = await booking_repo.get_by_id(id)
    if not booking:
        raise NotFoundException(f"Booking with ID {id} not found.")
    return SuccessResponse(data=BookingResponse.model_validate(booking))


@router.patch(
    "/{id}/cancel",
    response_model=SuccessResponse[BookingResponse],
    summary="Cancel resource booking",
    description="Cancels an upcoming or ongoing booking. Booker, department head, or admins only.",
)
async def cancel_booking(
    id: str,
    payload: BookingCancelRequest,
    current_user: User = Depends(get_current_user),
    booking_service: BookingService = Depends(get_booking_service)
) -> SuccessResponse[BookingResponse]:
    booking = await booking_service.cancel_booking(
        booking_id=id,
        actor_id=current_user.id,
        reason=payload.cancellation_reason
    )
    return SuccessResponse(data=BookingResponse.model_validate(booking))


@router.patch(
    "/{id}/reschedule",
    response_model=SuccessResponse[BookingResponse],
    summary="Reschedule booking",
    description="Modifies the calendar range of an upcoming booking, checking new overlap conflicts.",
)
async def reschedule_booking(
    id: str,
    payload: BookingRescheduleRequest,
    current_user: User = Depends(get_current_user),
    booking_service: BookingService = Depends(get_booking_service)
) -> SuccessResponse[BookingResponse]:
    booking = await booking_service.reschedule_booking(
        booking_id=id,
        start_time=payload.start_time,
        end_time=payload.end_time,
        actor_id=current_user.id
    )
    return SuccessResponse(data=BookingResponse.model_validate(booking))
