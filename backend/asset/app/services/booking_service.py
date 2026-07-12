from datetime import datetime, timezone
from typing import Optional
from app.domain.booking import Booking
from app.domain.user import Role
from app.exceptions.exceptions import ConflictException, ForbiddenException, NotFoundException, ValidationException
from app.logging.logger import business_logger
from app.repositories.booking import AbstractBookingRepository
from app.repositories.asset import AbstractAssetRepository
from app.repositories.user import AbstractUserRepository


class BookingService:
    """
    Service Layer managing Resource Bookings, overlap checkouts, cancellations,
    and rescheduling parameters.
    """
    def __init__(
        self,
        booking_repository: AbstractBookingRepository,
        asset_repository: AbstractAssetRepository,
        user_repository: AbstractUserRepository
    ):
        self.booking_repo = booking_repository
        self.asset_repo = asset_repository
        self.user_repo = user_repository

    async def create_booking(
        self,
        asset_id: str,
        booked_by: str,
        start_time: datetime,
        end_time: datetime,
        booked_for_department_id: Optional[str] = None
    ) -> Booking:
        """Creates a new reservation booking, enforcing bookable flags and overlap constraints."""
        asset = await self.asset_repo.get_by_id(asset_id)
        if not asset:
            raise NotFoundException(f"Asset with ID {asset_id} not found.")

        # 1. Validation: check is_bookable flag
        if not asset.is_bookable:
            raise ConflictException(f"Asset '{asset.asset_tag}' is not marked as bookable.")

        # Align timezone awareness
        start_aware = start_time.replace(tzinfo=timezone.utc) if start_time.tzinfo is None else start_time
        end_aware = end_time.replace(tzinfo=timezone.utc) if end_time.tzinfo is None else end_time
        now = datetime.now(timezone.utc)

        # 2. Validation: start time in future (422 validation exception)
        if start_aware < now:
            raise ValidationException("Booking start time must be in the future.")

        # 3. Validation: end_time > start_time (422 validation exception)
        if end_aware <= start_aware:
            raise ValidationException("Booking end time must be after the start time.")

        # 4. Overlap check query (strict inequality: start < b.end AND end > b.start)
        overlaps = await self.booking_repo.list_overlapping(asset_id, start_aware, end_aware)
        if overlaps:
            raise ConflictException("The asset is already booked during the requested time period.")

        new_booking = Booking(
            asset_id=asset_id,
            booked_by=booked_by,
            start_time=start_aware,
            end_time=end_aware,
            booked_for_department_id=booked_for_department_id
        )
        created = await self.booking_repo.create(new_booking)
        business_logger.info(f"Booking created for asset '{asset.asset_tag}' (ID: {created.id})")
        return created

    async def cancel_booking(self, booking_id: str, actor_id: str, reason: Optional[str] = None) -> Booking:
        """Cancels a booking, checking role permissions and status boundaries."""
        booking = await self.booking_repo.get_by_id(booking_id)
        if not booking:
            raise NotFoundException(f"Booking with ID {booking_id} not found.")

        # 1. Validate computed status
        status = booking.computed_status
        if status in ("COMPLETED", "CANCELLED"):
            raise ConflictException("Cannot cancel a completed or already cancelled booking.")

        # 2. Scoped cancellation permissions checking
        await self._enforce_booking_permission(booking, actor_id)

        booking.cancelled_at = datetime.now(timezone.utc)
        booking.cancellation_reason = reason or "Cancelled by user request."
        booking.updated_at = datetime.now(timezone.utc)

        updated = await self.booking_repo.update(booking)
        business_logger.info(f"Booking cancelled: ID {booking_id}")
        return updated

    async def reschedule_booking(
        self,
        booking_id: str,
        start_time: datetime,
        end_time: datetime,
        actor_id: str
    ) -> Booking:
        """Reschedules an upcoming booking in-place, executing overlap and validation checks."""
        booking = await self.booking_repo.get_by_id(booking_id)
        if not booking:
            raise NotFoundException(f"Booking with ID {booking_id} not found.")

        # 1. Validate current computed status
        status = booking.computed_status
        if status in ("COMPLETED", "CANCELLED"):
            raise ConflictException("Cannot reschedule a completed or cancelled booking.")

        # 2. Permissions validation
        await self._enforce_booking_permission(booking, actor_id)

        # Align timezone awareness
        start_aware = start_time.replace(tzinfo=timezone.utc) if start_time.tzinfo is None else start_time
        end_aware = end_time.replace(tzinfo=timezone.utc) if end_time.tzinfo is None else end_time
        now = datetime.now(timezone.utc)

        # 3. Validation: start time in future
        if start_aware < now:
            raise ValidationException("Reschedule start time must be in the future.")

        # 4. Validation: end_time > start_time
        if end_aware <= start_aware:
            raise ValidationException("Reschedule end time must be after the start time.")

        # 5. Overlap check query (excluding the booking itself)
        overlaps = await self.booking_repo.list_overlapping(
            asset_id=booking.asset_id,
            start=start_aware,
            end=end_aware,
            exclude_booking_id=booking_id
        )
        if overlaps:
            raise ConflictException("The asset is already booked during the requested new time period.")

        booking.start_time = start_aware
        booking.end_time = end_aware
        booking.updated_at = datetime.now(timezone.utc)

        updated = await self.booking_repo.update(booking)
        business_logger.info(f"Booking rescheduled: ID {booking_id}")
        return updated

    async def _enforce_booking_permission(self, booking: Booking, actor_id: str) -> None:
        """Helper to enforce booking access scoping permissions."""
        actor = await self.user_repo.get_by_id(actor_id)
        if not actor:
            raise NotFoundException(f"Actor user with ID {actor_id} not found.")

        if actor.role in (Role.ADMIN, Role.ASSET_MANAGER):
            return

        if booking.booked_by == actor_id:
            return

        # Scoped Department Head verification
        if actor.role == Role.DEPARTMENT_HEAD:
            if booking.booked_for_department_id == actor.department_id:
                return

        raise ForbiddenException("Access denied. Insufficient permissions to modify this booking.")
