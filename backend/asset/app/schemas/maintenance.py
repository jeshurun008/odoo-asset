from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.domain.maintenance_request import MaintenancePriority, MaintenanceStatus


class MaintenanceRequestCreate(BaseModel):
    asset_id: str = Field(...)
    issue_description: str = Field(..., min_length=5, max_length=1000)
    priority: MaintenancePriority = Field(...)
    photo_ref: Optional[str] = Field(default=None)


class MaintenanceRejectRequest(BaseModel):
    rejected_reason: str = Field(..., min_length=2, max_length=500)


class MaintenanceAssignRequest(BaseModel):
    assigned_technician: str = Field(..., min_length=2, max_length=100)


class MaintenanceRequestResponse(BaseModel):
    id: str
    asset_id: str
    raised_by: str
    issue_description: str
    priority: MaintenancePriority
    photo_ref: Optional[str]
    status: MaintenanceStatus
    assigned_technician: Optional[str]
    approved_by: Optional[str]
    rejected_reason: Optional[str]
    pre_maintenance_asset_status: Optional[str]
    raised_at: datetime
    resolved_at: Optional[datetime]
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
