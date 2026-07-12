from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid


class MaintenanceStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    TECHNICIAN_ASSIGNED = "TECHNICIAN_ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"


class MaintenancePriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class MaintenanceRequest:
    """Domain model entity representing an asset repair or inspection request."""
    asset_id: str
    raised_by: str  # User.id
    issue_description: str
    priority: MaintenancePriority
    photo_ref: Optional[str] = None
    status: MaintenanceStatus = MaintenanceStatus.PENDING
    assigned_technician: Optional[str] = None
    approved_by: Optional[str] = None
    rejected_reason: Optional[str] = None
    pre_maintenance_asset_status: Optional[str] = None  # Stores AssetStatus right before approval
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    raised_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
