from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.domain.asset import AssetStatus


class AssetCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    category_id: str = Field(...)
    serial_number: str = Field(..., min_length=2, max_length=100)
    acquisition_date: datetime = Field(...)
    acquisition_cost: float = Field(..., ge=0.0)
    condition: str = Field(..., description="NEW, GOOD, FAIR, POOR")
    location: str = Field(..., min_length=2, max_length=100)
    department_id: Optional[str] = Field(default=None)
    is_bookable: bool = Field(default=False)
    document_refs: List[str] = Field(default_factory=list)


class AssetUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    category_id: Optional[str] = Field(default=None)
    serial_number: Optional[str] = Field(default=None, min_length=2, max_length=100)
    acquisition_date: Optional[datetime] = Field(default=None)
    acquisition_cost: Optional[float] = Field(default=None, ge=0.0)
    condition: Optional[str] = Field(default=None)
    location: Optional[str] = Field(default=None, min_length=2, max_length=100)
    department_id: Optional[str] = Field(default=None)
    is_bookable: Optional[bool] = Field(default=None)
    document_refs: Optional[List[str]] = Field(default=None)


class AssetResponse(BaseModel):
    id: str
    name: str
    category_id: str
    asset_tag: str
    serial_number: str
    acquisition_date: datetime
    acquisition_cost: float
    condition: str
    location: str
    department_id: Optional[str]
    is_bookable: bool
    document_refs: List[str]
    status: AssetStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
