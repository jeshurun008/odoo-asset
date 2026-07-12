from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
import uuid

@dataclass
class ActivityLog:
    user_id: str
    action: str
    entity_type: str
    entity_id: str
    previous_value: Optional[Any] = None
    new_value: Optional[Any] = None
    correlation_id: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
