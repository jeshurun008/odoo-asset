from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid


@dataclass
class AssetCategory:
    """Domain model entity representing an Asset Category."""
    name: str
    description: Optional[str] = None
    is_active: bool = True
    # Struct: [{"name": str, "type": str, "required": bool}]
    custom_fields: List[Dict[str, Any]] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
