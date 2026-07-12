from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class TransferRequestCreate(BaseModel):
    asset_id: str = Field(...)
    requested_to_type: Literal["EMPLOYEE", "DEPARTMENT"] = Field(...)
    requested_to_id: str = Field(...)
    reason: Optional[str] = Field(default=None, max_length=500)


class TransferRejectRequest(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=500)


class TransferRequestResponse(BaseModel):
    id: str
    asset_id: str
    current_allocation_id: str
    requested_by: str
    requested_to_type: Literal["EMPLOYEE", "DEPARTMENT"]
    requested_to_id: str
    status: str  # REQUESTED, APPROVED, REJECTED, COMPLETED
    approved_by: Optional[str]
    requested_at: datetime
    resolved_at: Optional[datetime]
    reason: Optional[str]

    model_config = ConfigDict(from_attributes=True)
