from typing import Any, Dict, Generic, List, Literal, Optional, TypeVar
from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=20, ge=1, le=100, description="Number of items per page")


class SortParams(BaseModel):
    sort_by: Optional[str] = Field(default=None, description="Field name to sort by")
    sort_order: Literal["asc", "desc"] = Field(default="asc", description="Sorting direction")


class SearchParams(BaseModel):
    search: Optional[str] = Field(default=None, description="Search query string")


class QueryParams(PaginationParams, SortParams, SearchParams):
    """
    Unified query parameters class inheriting pagination, sorting, and searching parameters.
    Can contain dynamic key-value filters.
    """
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Key-value pairs for filtering records")


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated wrapper to be placed inside the standard SuccessResponse envelope."""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
