import math
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from app.core.dependencies.auth import get_audit_repository, get_audit_service, get_current_user, require_role
from app.domain.user import Role, User
from app.repositories.audit import AbstractAuditRepository
from app.schemas.audit import AssignAuditorsRequest, AuditCreate, AuditCycleResponse, AuditItemResponse, VerifyAuditItemRequest
from app.schemas.envelope import SuccessResponse
from app.schemas.query import PaginatedResponse, PaginationParams, SearchParams, SortParams
from app.services.audit_service import AuditService
router = APIRouter(prefix="/audits", tags=["Audits"])
MANAGERS=(Role.ADMIN, Role.ASSET_MANAGER)
@router.post("", status_code=status.HTTP_201_CREATED, response_model=SuccessResponse[AuditCycleResponse])
async def create(payload: AuditCreate, user: User=Depends(require_role(*MANAGERS)), service: AuditService=Depends(get_audit_service)):
    return SuccessResponse(data=AuditCycleResponse.model_validate(await service.create_cycle(**payload.model_dump(), created_by=user.id)))
@router.get("", response_model=SuccessResponse[PaginatedResponse[AuditCycleResponse]])
async def list_cycles(pagination: PaginationParams=Depends(), sort: SortParams=Depends(), search: SearchParams=Depends(), status_filter: Optional[str]=Query(None,alias="status"), user: User=Depends(get_current_user), repo: AbstractAuditRepository=Depends(get_audit_repository)):
    filters={"status":status_filter} if status_filter else {}
    if user.role == Role.DEPARTMENT_HEAD: filters["department_id"]=user.department_id
    if user.role == Role.EMPLOYEE: filters["auditor_id"]=user.id
    items,total=await repo.list_paginated(skip=(pagination.page-1)*pagination.page_size,limit=pagination.page_size,sort_by=sort.sort_by,sort_order=sort.sort_order,search=search.search,filters=filters)
    return SuccessResponse(data=PaginatedResponse(items=[AuditCycleResponse.model_validate(x) for x in items],total=total,page=pagination.page,page_size=pagination.page_size,total_pages=math.ceil(total/pagination.page_size) if total else 0))
@router.get("/{id}", response_model=SuccessResponse[dict])
async def get_cycle(id: str, user: User=Depends(get_current_user), repo: AbstractAuditRepository=Depends(get_audit_repository)):
    cycle=await repo.get_by_id(id)
    from app.exceptions.exceptions import NotFoundException, ForbiddenException
    if not cycle: raise NotFoundException("Audit cycle not found.")
    if user.role == Role.EMPLOYEE and user.id not in cycle.assigned_auditor_ids: raise ForbiddenException("Access denied.")
    return SuccessResponse(data={"cycle":AuditCycleResponse.model_validate(cycle).model_dump(),"items":[AuditItemResponse.model_validate(i).model_dump() for i in await repo.list_items(id)]})
@router.patch("/{id}/assign-auditors", response_model=SuccessResponse[AuditCycleResponse])
async def assign(id: str,payload: AssignAuditorsRequest,user: User=Depends(require_role(*MANAGERS)),service: AuditService=Depends(get_audit_service)):
    return SuccessResponse(data=AuditCycleResponse.model_validate(await service.assign_auditors(id,payload.assigned_auditor_ids)))
@router.patch("/{id}/items/{item_id}/verify", response_model=SuccessResponse[AuditItemResponse])
async def verify(id: str,item_id: str,payload: VerifyAuditItemRequest,user: User=Depends(get_current_user),service: AuditService=Depends(get_audit_service)):
    return SuccessResponse(data=AuditItemResponse.model_validate(await service.verify_item(id,item_id,user.id,user.role in MANAGERS,payload.result,payload.notes)))
@router.patch("/{id}/close", response_model=SuccessResponse[AuditCycleResponse])
async def close(id: str,user: User=Depends(require_role(*MANAGERS)),service: AuditService=Depends(get_audit_service)):
    return SuccessResponse(data=AuditCycleResponse.model_validate(await service.close_cycle(id,user.id)))
@router.get("/{id}/discrepancy-report", response_model=SuccessResponse[list[AuditItemResponse]])
async def report(id: str,user: User=Depends(get_current_user),service: AuditService=Depends(get_audit_service)):
    return SuccessResponse(data=[AuditItemResponse.model_validate(i) for i in await service.discrepancy_report(id)])
