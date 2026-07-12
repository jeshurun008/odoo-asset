from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    parent_department_id: Optional[str] = Field(default=None, description="Optional parent Department UUID string")
    department_head_id: Optional[str] = Field(default=None, description="Optional Head User UUID string")


class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    parent_department_id: Optional[str] = Field(default=None)
    department_head_id: Optional[str] = Field(default=None)


class DepartmentResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    parent_department_id: Optional[str]
    department_head_id: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
