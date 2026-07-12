from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.domain.user import Role


class EmployeeResponse(BaseModel):
    """Profile response format for Employees."""
    id: str
    email: EmailStr
    name: str
    role: Role
    is_active: bool
    department_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmployeeAssignDepartment(BaseModel):
    department_id: Optional[str] = Field(default=None, description="Department UUID string to link employee to, or null to clear link")


class EmployeePromotionRequest(BaseModel):
    role: Role = Field(..., description="Target role (ADMIN, ASSET_MANAGER, DEPARTMENT_HEAD, EMPLOYEE)")
