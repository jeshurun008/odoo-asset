from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
import uuid


class AssetStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    ALLOCATED = "ALLOCATED"
    RESERVED = "RESERVED"
    UNDER_MAINTENANCE = "UNDER_MAINTENANCE"
    LOST = "LOST"
    RETIRED = "RETIRED"
    DISPOSED = "DISPOSED"


@dataclass
class Asset:
    """Domain model entity representing a registered capital/enterprise Asset."""
    name: str
    category_id: str  # References AssetCategory.id
    serial_number: str
    acquisition_date: datetime
    acquisition_cost: float
    condition: str  # NEW, GOOD, FAIR, POOR
    location: str
    department_id: Optional[str] = None  # Owner department ID
    is_bookable: bool = False  # Flag for scheduling/reservation scoping
    document_refs: List[str] = field(default_factory=list)
    status: AssetStatus = AssetStatus.AVAILABLE
    asset_tag: Optional[str] = None  # Sequential tag like AF-0001
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
