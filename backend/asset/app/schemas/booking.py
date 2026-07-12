from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, computed_field


class BookingCreate(BaseModel):
    asset_id: str = Field(...)
    start_time: datetime = Field(...)
    end_time: datetime = Field(...)
    booked_for_department_id: Optional[str] = Field(default=None)


class BookingRescheduleRequest(BaseModel):
    start_time: datetime = Field(...)
    end_time: datetime = Field(...)


class BookingCancelRequest(BaseModel):
    cancellation_reason: Optional[str] = Field(default=None, max_length=500)


class BookingResponse(BaseModel):
    id: str
    asset_id: str
    booked_by: str
    booked_for_department_id: Optional[str]
    start_time: datetime
    end_time: datetime
    cancelled_at: Optional[datetime]
    cancellation_reason: Optional[str]
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def status(self) -> str:
        """Computes booking status dynamically: CANCELLED, UPCOMING, COMPLETED, or ONGOING."""
        if self.cancelled_at is not None:
            return "CANCELLED"
        now = datetime.now(timezone.utc)
        
        start = self.start_time
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
            
        end = self.end_time
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)

        if now < start:
            return "UPCOMING"
        if now > end:
            return "COMPLETED"
        return "ONGOING"

    model_config = ConfigDict(from_attributes=True)
