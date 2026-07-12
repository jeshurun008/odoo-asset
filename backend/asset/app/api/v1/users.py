import math
from fastapi import APIRouter, Depends
from app.auth.schemas import UserResponse
from app.core.dependencies.auth import get_user_repository, require_role
from app.domain.user import Role, User
from app.repositories.user import AbstractUserRepository
from app.schemas.envelope import SuccessResponse
from app.schemas.query import PaginatedResponse, PaginationParams, SearchParams, SortParams

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "",
    response_model=SuccessResponse[PaginatedResponse[UserResponse]],
    summary="List paginated user directory",
    description="Fetches a paginated, sorted, and searched list of users. Access is restricted to ADMIN only.",
)
async def list_users(
    pagination: PaginationParams = Depends(),
    sort: SortParams = Depends(),
    search: SearchParams = Depends(),
    current_user: User = Depends(require_role(Role.ADMIN)),
    user_repo: AbstractUserRepository = Depends(get_user_repository)
) -> SuccessResponse[PaginatedResponse[UserResponse]]:
    skip = (pagination.page - 1) * pagination.page_size
    limit = pagination.page_size

    users, total = await user_repo.list_paginated(
        skip=skip,
        limit=limit,
        sort_by=sort.sort_by,
        sort_order=sort.sort_order,
        search=search.search
    )

    total_pages = math.ceil(total / pagination.page_size) if total > 0 else 0
    user_responses = [UserResponse.model_validate(u) for u in users]

    data = PaginatedResponse(
        items=user_responses,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages
    )
    return SuccessResponse(data=data)
