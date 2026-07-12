from typing import Any, Optional
from app.domain.activity_log import ActivityLog
from app.logging.logger import correlation_id_ctx
from app.repositories.activity_log import AbstractActivityLogRepository

class ActivityLogService:
    def __init__(self, repository: AbstractActivityLogRepository): self.repository = repository
    async def record(self, *, user_id: str, action: str, entity_type: str, entity_id: str, previous_value: Optional[Any] = None, new_value: Optional[Any] = None) -> ActivityLog:
        correlation_id = correlation_id_ctx.get(None)
        return await self.repository.create(ActivityLog(user_id=user_id, action=action, entity_type=entity_type, entity_id=entity_id, previous_value=previous_value, new_value=new_value, correlation_id=correlation_id))
