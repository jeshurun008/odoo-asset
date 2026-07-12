from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import uuid


@dataclass
class Department:
    """Domain model entity representing an organization Department."""
    name: str
    description: Optional[str] = None
    department_head_id: Optional[str] = None  # Reference to User.id (must be DEPARTMENT_HEAD or ADMIN)
    parent_department_id: Optional[str] = None  # Reference to self-referential Department.id
    is_active: bool = True
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
