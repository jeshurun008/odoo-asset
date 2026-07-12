from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import uuid


@dataclass
class LoginAttempt:
    """Domain model entity representing a single login attempt transaction."""
    email_attempted: str
    success: bool
    ip_address: str
    correlation_id: str
    user_id: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
