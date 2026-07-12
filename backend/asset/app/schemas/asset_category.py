from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class CustomFieldSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: Literal["TEXT", "NUMBER", "DATE", "BOOLEAN"]
    required: bool = Field(default=False)


class AssetCategoryCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    custom_fields: List[CustomFieldSchema] = Field(default_factory=list)


class AssetCategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    custom_fields: Optional[List[CustomFieldSchema]] = None


class AssetCategoryResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    is_active: bool
    custom_fields: List[CustomFieldSchema]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
