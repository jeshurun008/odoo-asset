from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import uuid


@dataclass
class Booking:
    """Domain model entity representing a calendar time-slot reservation booking for an asset."""
    asset_id: str
    booked_by: str  # User.id
    start_time: datetime
    end_time: datetime
    booked_for_department_id: Optional[str] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def computed_status(self) -> str:
        """Computes status dynamically: CANCELLED, UPCOMING, COMPLETED, or ONGOING."""
        if self.cancelled_at is not None:
            return "CANCELLED"
        now = datetime.now(timezone.utc)
        
        start = self.start_time
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
            
        end = self.end_time
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)

        if now < start:
            return "UPCOMING"
        if now > end:
            return "COMPLETED"
        return "ONGOING"
