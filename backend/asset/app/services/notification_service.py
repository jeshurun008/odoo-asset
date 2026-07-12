from datetime import datetime, timezone
from typing import Protocol
from app.domain.notification import Notification, NotificationType
from app.repositories.booking import AbstractBookingRepository
from app.repositories.notification import AbstractNotificationRepository

class NotificationChannel(Protocol):
    async def dispatch(self, notification: Notification) -> Notification: ...
class InAppChannel:
    def __init__(self, repository: AbstractNotificationRepository): self.repository = repository
    async def dispatch(self, notification): return await self.repository.create(notification)
class NotificationService:
    """In-app delivery only; email, SMS, and push are future channel implementations."""
    def __init__(self, channel: NotificationChannel, booking_repo: AbstractBookingRepository | None = None): self.channel, self.booking_repo = channel, booking_repo
    async def notify(self, recipient_id: str, notification_type: NotificationType, payload: dict) -> Notification:
        return await self.channel.dispatch(Notification(recipient_user_id=recipient_id, type=notification_type, payload=payload))
    async def send_booking_reminders(self, minutes: int = 30) -> int:
        """Worker hook: invoke every N minutes from the future scheduler."""
        if not self.booking_repo: return 0
        bookings = await self.booking_repo.list_bookings_starting_within(minutes)
        for booking in bookings:
            await self.notify(booking.booked_by, NotificationType.BOOKING_REMINDER, {"entity_id": booking.id, "entity_type": "booking", "message": "Your booking starts soon."})
        return len(bookings)
