from abc import abstractmethod
from datetime import datetime
from typing import List, Optional
from app.domain.booking import Booking
from app.repositories.base import AbstractRepository


class AbstractBookingRepository(AbstractRepository[Booking]):
    """Abstract Booking repository interface."""

    @abstractmethod
    async def list_overlapping(
        self,
        asset_id: str,
        start: datetime,
        end: datetime,
        exclude_booking_id: Optional[str] = None
    ) -> List[Booking]:
        """Fetch bookings for the same asset overlapping the given range (start < existing.end AND end > existing.start)."""
        pass

    @abstractmethod
    async def list_bookings_starting_within(self, minutes: int) -> List[Booking]:
        """Fetch upcoming bookings starting in the next N minutes (for reminder notifications hook)."""
        pass
