import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from app.domain.booking import Booking
from app.repositories.booking import AbstractBookingRepository


class InMemoryBookingRepository(AbstractBookingRepository):
    """
    Thread-safe, in-memory implementation of AbstractBookingRepository.
    Simulates database persistence for Resource Bookings.
    """
    def __init__(self):
        self._bookings: Dict[str, Booking] = {}
        self._lock = asyncio.Lock()

    async def get_by_id(self, id: str) -> Optional[Booking]:
        async with self._lock:
            return self._bookings.get(id)

    async def list(self, skip: int = 0, limit: int = 100) -> List[Booking]:
        async with self._lock:
            items = list(self._bookings.values())
            items.sort(key=lambda b: b.created_at, reverse=True)
            return items[skip : skip + limit]

    async def list_paginated(
        self,
        skip: int = 0,
        limit: int = 20,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        search: Optional[str] = None,
        filters: Optional[dict] = None
    ) -> tuple[List[Booking], int]:
        async with self._lock:
            items = list(self._bookings.values())

            # Apply filters
            if filters:
                for key, val in filters.items():
                    if key == "status" and val is not None:
                        items = [b for b in items if b.computed_status == val]
                    elif key == "start_date" and val is not None:
                        # Match bookings starting on or after start_date
                        items = [b for b in items if b.start_time >= val]
                    elif key == "end_date" and val is not None:
                        # Match bookings ending on or before end_date
                        items = [b for b in items if b.end_time <= val]
                    else:
                        items = [b for b in items if getattr(b, key, None) == val]

            # Sort
            if sort_by:
                reverse = (sort_order.lower() == "desc")
                items.sort(key=lambda x: getattr(x, sort_by, None) or "", reverse=reverse)
            else:
                items.sort(key=lambda x: x.created_at, reverse=True)

            total = len(items)
            paginated_items = items[skip : skip + limit]
            return paginated_items, total

    async def create(self, entity: Booking) -> Booking:
        async with self._lock:
            self._bookings[entity.id] = entity
            return entity

    async def update(self, entity: Booking) -> Booking:
        async with self._lock:
            self._bookings[entity.id] = entity
            return entity

    async def delete(self, id: str) -> bool:
        async with self._lock:
            if id in self._bookings:
                del self._bookings[id]
                return True
            return False

    async def list_overlapping(
        self,
        asset_id: str,
        start: datetime,
        end: datetime,
        exclude_booking_id: Optional[str] = None
    ) -> List[Booking]:
        async with self._lock:
            # Align timezones for incoming parameters
            start_aware = start.replace(tzinfo=timezone.utc) if start.tzinfo is None else start
            end_aware = end.replace(tzinfo=timezone.utc) if end.tzinfo is None else end

            overlapping = []
            for b in self._bookings.values():
                if b.asset_id != asset_id:
                    continue
                if exclude_booking_id and b.id == exclude_booking_id:
                    continue
                # Overlaps only apply to non-cancelled and non-completed bookings
                if b.computed_status not in ("UPCOMING", "ONGOING"):
                    continue

                b_start = b.start_time.replace(tzinfo=timezone.utc) if b.start_time.tzinfo is None else b.start_time
                b_end = b.end_time.replace(tzinfo=timezone.utc) if b.end_time.tzinfo is None else b.end_time

                # Strict inequality boundary overlap check: existing.start < new.end AND existing.end > new.start
                if b_start < end_aware and b_end > start_aware:
                    overlapping.append(b)

            return overlapping

    async def list_bookings_starting_within(self, minutes: int) -> List[Booking]:
        async with self._lock:
            now = datetime.now(timezone.utc)
            window_end = now + timedelta(minutes=minutes)
            return [
                b for b in self._bookings.values()
                if b.cancelled_at is None and now <= (b.start_time.replace(tzinfo=timezone.utc) if b.start_time.tzinfo is None else b.start_time) <= window_end
            ]

