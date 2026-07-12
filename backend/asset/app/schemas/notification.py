from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict
from app.domain.notification import NotificationType
class NotificationResponse(BaseModel):
    id: str; recipient_user_id: str; type: NotificationType; payload: dict[str, Any]; read: bool; created_at: datetime; read_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)
