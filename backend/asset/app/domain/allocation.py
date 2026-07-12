from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import uuid


@dataclass
class AssetAllocation:
    """Domain model entity representing an allocation checkout record for an asset."""
    asset_id: str
    allocated_to_type: str  # "EMPLOYEE" or "DEPARTMENT"
    allocated_to_id: str  # User.id or Department.id
    allocated_by: str  # User.id of administrator performing allocation
    allocated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expected_return_date: Optional[datetime] = None
    returned_at: Optional[datetime] = None
    condition_check_in_notes: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def computed_status(self) -> str:
        """Computes status dynamically: RETURNED, OVERDUE, or ACTIVE."""
        if self.returned_at is not None:
            return "RETURNED"
        if self.expected_return_date is not None:
            now = datetime.now(timezone.utc)
            expected = self.expected_return_date
            if expected.tzinfo is None:
                expected = expected.replace(tzinfo=timezone.utc)
            if now > expected:
                return "OVERDUE"
        return "ACTIVE"
