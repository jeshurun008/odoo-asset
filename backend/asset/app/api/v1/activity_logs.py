import math
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from app.core.dependencies.auth import get_activity_log_repository, require_role
from app.domain.user import Role
from app.repositories.activity_log import AbstractActivityLogRepository
from app.schemas.envelope import SuccessResponse
from app.schemas.query import PaginatedResponse, PaginationParams, SearchParams, SortParams
router = APIRouter(prefix="/activity-logs", tags=["Activity Logs"])
@router.get("")
async def list_logs(pagination: PaginationParams=Depends(), sort: SortParams=Depends(), search: SearchParams=Depends(), entity_type: Optional[str]=None, entity_id: Optional[str]=None, actor: Optional[str]=None, start_date: Optional[datetime]=Query(None), end_date: Optional[datetime]=Query(None), user=Depends(require_role(Role.ADMIN, Role.ASSET_MANAGER)), repo: AbstractActivityLogRepository=Depends(get_activity_log_repository)):
    filters={"entity_type":entity_type,"entity_id":entity_id,"user_id":actor,"start_date":start_date,"end_date":end_date}
    logs,total=await repo.list_paginated(skip=(pagination.page-1)*pagination.page_size,limit=pagination.page_size,sort_by=sort.sort_by,sort_order=sort.sort_order,search=search.search,filters=filters)
    return SuccessResponse(data=PaginatedResponse(items=[{"id":x.id,"user_id":x.user_id,"action":x.action,"entity_type":x.entity_type,"entity_id":x.entity_id,"previous_value":x.previous_value,"new_value":x.new_value,"timestamp":x.timestamp,"correlation_id":x.correlation_id} for x in logs],total=total,page=pagination.page,page_size=pagination.page_size,total_pages=math.ceil(total/pagination.page_size) if total else 0))
