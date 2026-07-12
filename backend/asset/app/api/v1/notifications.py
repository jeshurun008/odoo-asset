import math
from fastapi import APIRouter, Depends
from app.core.dependencies.auth import get_current_user, get_notification_repository
from app.domain.user import User
from app.exceptions.exceptions import NotFoundException
from app.repositories.notification import AbstractNotificationRepository
from app.schemas.envelope import SuccessResponse
from app.schemas.notification import NotificationResponse
from app.schemas.query import PaginatedResponse, PaginationParams
router=APIRouter(prefix="/notifications",tags=["Notifications"])
@router.get("",response_model=SuccessResponse[PaginatedResponse[NotificationResponse]])
async def list_notifications(pagination: PaginationParams=Depends(), user: User=Depends(get_current_user), repo: AbstractNotificationRepository=Depends(get_notification_repository)):
    items,total=await repo.list_for_recipient(user.id,(pagination.page-1)*pagination.page_size,pagination.page_size)
    return SuccessResponse(data=PaginatedResponse(items=[NotificationResponse.model_validate(x) for x in items],total=total,page=pagination.page,page_size=pagination.page_size,total_pages=math.ceil(total/pagination.page_size) if total else 0))
@router.patch("/{id}/read",response_model=SuccessResponse[NotificationResponse])
async def mark_read(id: str,user: User=Depends(get_current_user),repo: AbstractNotificationRepository=Depends(get_notification_repository)):
    n=await repo.get_by_id(id)
    if not n or n.recipient_user_id != user.id: raise NotFoundException("Notification not found.")
    from datetime import datetime, timezone
    n.read=True; n.read_at=datetime.now(timezone.utc)
    return SuccessResponse(data=NotificationResponse.model_validate(await repo.update(n)))
