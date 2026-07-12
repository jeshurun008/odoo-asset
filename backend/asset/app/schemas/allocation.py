from datetime import datetime, timezone
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, computed_field


class AssetAllocationCreate(BaseModel):
    asset_id: str = Field(...)
    allocated_to_type: Literal["EMPLOYEE", "DEPARTMENT"] = Field(...)
    allocated_to_id: str = Field(...)
    expected_return_date: Optional[datetime] = Field(default=None)


class AssetReturnRequest(BaseModel):
    condition_check_in_notes: str = Field(..., min_length=2, max_length=500)


class AssetAllocationResponse(BaseModel):
    id: str
    asset_id: str
    allocated_to_type: Literal["EMPLOYEE", "DEPARTMENT"]
    allocated_to_id: str
    allocated_by: str
    allocated_at: datetime
    expected_return_date: Optional[datetime]
    returned_at: Optional[datetime]
    condition_check_in_notes: Optional[str]
    created_at: datetime

    @computed_field
    @property
    def status(self) -> str:
        """Computes status dynamically during serialization: RETURNED, OVERDUE, or ACTIVE."""
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

    model_config = ConfigDict(from_attributes=True)
