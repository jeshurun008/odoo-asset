from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.domain.audit import AuditItemResult, AuditStatus

class AuditCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    start_date: date
    end_date: date
    department_id: Optional[str] = None
    category_id: Optional[str] = None
class AssignAuditorsRequest(BaseModel): assigned_auditor_ids: list[str]
class VerifyAuditItemRequest(BaseModel):
    result: AuditItemResult
    notes: Optional[str] = Field(default=None, max_length=1000)
class AuditItemResponse(BaseModel):
    id: str; audit_cycle_id: str; asset_id: str; expected_location: str; result: AuditItemResult
    verified_by: Optional[str]; verified_at: Optional[datetime]; notes: Optional[str]
    model_config = ConfigDict(from_attributes=True)
class AuditCycleResponse(BaseModel):
    id: str; name: str; start_date: date; end_date: date; department_id: Optional[str]; category_id: Optional[str]
    status: AuditStatus; assigned_auditor_ids: list[str]; created_by: str; created_at: datetime; closed_at: Optional[datetime]; closed_by: Optional[str]
    model_config = ConfigDict(from_attributes=True)
