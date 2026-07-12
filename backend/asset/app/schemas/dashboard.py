from pydantic import BaseModel
class DashboardKpisResponse(BaseModel):
    assets_available: int; assets_allocated: int; maintenance_today: int; upcoming_bookings: int
    pending_transfers: int; upcoming_returns: int; overdue_assets: int; unread_notifications: int
