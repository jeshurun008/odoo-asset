from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional
import uuid


class AuditStatus(str, Enum):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    CLOSED = "CLOSED"


class AuditItemResult(str, Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    MISSING = "MISSING"
    DAMAGED = "DAMAGED"


@dataclass
class AuditCycle:
    name: str
    start_date: date
    end_date: date
    created_by: str
    department_id: Optional[str] = None
    category_id: Optional[str] = None
    status: AuditStatus = AuditStatus.PLANNED
    assigned_auditor_ids: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    closed_at: Optional[datetime] = None
    closed_by: Optional[str] = None


@dataclass
class AuditItem:
    audit_cycle_id: str
    asset_id: str
    expected_location: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    result: AuditItemResult = AuditItemResult.PENDING
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None
    notes: Optional[str] = None
