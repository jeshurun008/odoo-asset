from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import uuid


@dataclass
class TransferRequest:
    """Domain model entity representing a request to transfer an allocated asset to another user/department."""
    asset_id: str
    current_allocation_id: str  # The active AssetAllocation.id to terminate
    requested_by: str  # User.id of requester
    requested_to_type: str  # "EMPLOYEE" or "DEPARTMENT"
    requested_to_id: str  # Recipient User.id or Department.id
    status: str = "REQUESTED"  # REQUESTED, APPROVED, REJECTED, COMPLETED
    approved_by: Optional[str] = None  # User.id of approver
    reason: Optional[str] = None
    requested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
