import math
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from app.core.dependencies.auth import get_asset_category_service, get_asset_category_repository, require_role
from app.domain.user import Role, User
from app.exceptions.exceptions import NotFoundException
from app.repositories.asset_category import AbstractAssetCategoryRepository
from app.schemas.asset_category import AssetCategoryCreate, AssetCategoryResponse, AssetCategoryUpdate
from app.schemas.envelope import SuccessResponse
from app.schemas.query import PaginatedResponse, PaginationParams, SearchParams, SortParams
from app.services.asset_category_service import AssetCategoryService

router = APIRouter(prefix="/asset-categories", tags=["Asset Categories"])


@router.post(
    "",
    response_model=SuccessResponse[AssetCategoryResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new asset category",
    description="Registers a new asset category with custom field schemas. Restricted to ADMIN only.",
)
async def create_category(
    payload: AssetCategoryCreate,
    current_user: User = Depends(require_role(Role.ADMIN)),
    cat_service: AssetCategoryService = Depends(get_asset_category_service)
) -> SuccessResponse[AssetCategoryResponse]:
    custom_fields_dict = [f.model_dump() for f in payload.custom_fields]
    cat = await cat_service.create_category(
        name=payload.name,
        description=payload.description,
        custom_fields=custom_fields_dict
    )
    return SuccessResponse(data=AssetCategoryResponse.model_validate(cat))


@router.get(
    "",
    response_model=SuccessResponse[PaginatedResponse[AssetCategoryResponse]],
    summary="List asset categories",
    description="Lists all asset categories with paginated and filtered options. Open to all authenticated users.",
)
async def list_categories(
    pagination: PaginationParams = Depends(),
    sort: SortParams = Depends(),
    search: SearchParams = Depends(),
    status_filter: Optional[bool] = Query(default=None, alias="status"),
    current_user: User = Depends(require_role(Role.ADMIN, Role.ASSET_MANAGER, Role.DEPARTMENT_HEAD, Role.EMPLOYEE)),
    cat_repo: AbstractAssetCategoryRepository = Depends(get_asset_category_repository)
) -> SuccessResponse[PaginatedResponse[AssetCategoryResponse]]:
    skip = (pagination.page - 1) * pagination.page_size
    limit = pagination.page_size

    filters = {}
    if status_filter is not None:
        filters["status"] = status_filter

    items, total = await cat_repo.list_paginated(
        skip=skip,
        limit=limit,
        sort_by=sort.sort_by,
        sort_order=sort.sort_order,
        search=search.search,
        filters=filters
    )

    total_pages = math.ceil(total / pagination.page_size) if total > 0 else 0
    responses = [AssetCategoryResponse.model_validate(i) for i in items]

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
    response_model=SuccessResponse[AssetCategoryResponse],
    summary="Get asset category details",
    description="Fetches an asset category profile by ID. Open to all authenticated users.",
)
async def get_category(
    id: str,
    current_user: User = Depends(require_role(Role.ADMIN, Role.ASSET_MANAGER, Role.DEPARTMENT_HEAD, Role.EMPLOYEE)),
    cat_repo: AbstractAssetCategoryRepository = Depends(get_asset_category_repository)
) -> SuccessResponse[AssetCategoryResponse]:
    cat = await cat_repo.get_by_id(id)
    if not cat:
        raise NotFoundException(f"Asset Category with ID {id} not found.")
    return SuccessResponse(data=AssetCategoryResponse.model_validate(cat))


@router.patch(
    "/{id}",
    response_model=SuccessResponse[AssetCategoryResponse],
    summary="Update asset category attributes",
    description="Updates asset category name, description, and custom field definitions. Restricted to ADMIN only.",
)
async def update_category(
    id: str,
    payload: AssetCategoryUpdate,
    current_user: User = Depends(require_role(Role.ADMIN)),
    cat_service: AssetCategoryService = Depends(get_asset_category_service)
) -> SuccessResponse[AssetCategoryResponse]:
    custom_fields_dict = [f.model_dump() for f in payload.custom_fields] if payload.custom_fields is not None else None
    cat = await cat_service.update_category(
        cat_id=id,
        name=payload.name,
        description=payload.description,
        custom_fields=custom_fields_dict
    )
    return SuccessResponse(data=AssetCategoryResponse.model_validate(cat))


@router.patch(
    "/{id}/deactivate",
    response_model=SuccessResponse[AssetCategoryResponse],
    summary="Soft-deactivate an asset category",
    description="Sets category status to Inactive. Blocks if active assets reference it. Restricted to ADMIN only.",
)
async def deactivate_category(
    id: str,
    current_user: User = Depends(require_role(Role.ADMIN)),
    cat_service: AssetCategoryService = Depends(get_asset_category_service)
) -> SuccessResponse[AssetCategoryResponse]:
    cat = await cat_service.deactivate_category(id)
    return SuccessResponse(data=AssetCategoryResponse.model_validate(cat))
