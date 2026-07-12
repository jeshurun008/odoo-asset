from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
import uuid


class NotificationType(str, Enum):
    ASSET_ASSIGNED = "ASSET_ASSIGNED"
    TRANSFER_APPROVED = "TRANSFER_APPROVED"
    BOOKING_REMINDER = "BOOKING_REMINDER"
    MAINTENANCE_APPROVED = "MAINTENANCE_APPROVED"
    MAINTENANCE_REJECTED = "MAINTENANCE_REJECTED"
    AUDIT_ASSIGNED = "AUDIT_ASSIGNED"
    OVERDUE_RETURN = "OVERDUE_RETURN"
    AUDIT_DISCREPANCY = "AUDIT_DISCREPANCY"


@dataclass
class Notification:
    recipient_user_id: str
    type: NotificationType
    payload: dict[str, Any]
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    read: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    read_at: Optional[datetime] = None
