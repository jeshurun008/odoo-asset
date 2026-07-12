from app.domain.asset import AssetStatus
class DashboardService:
    """KPI composition only; repositories own filtering/counting logic."""
    def __init__(self, assets, maintenance, bookings, transfers, allocations, notifications): self.assets, self.maintenance, self.bookings, self.transfers, self.allocations, self.notifications = assets, maintenance, bookings, transfers, allocations, notifications
    async def kpis(self, user):
        department_id = user.department_id if user.role.value == "DEPARTMENT_HEAD" else None
        counts = await self.assets.count_by_status(department_id)
        maintenance = await self.maintenance.list_maintenance_today()
        bookings = await self.bookings.list_bookings_starting_within(30)
        transfers, _ = await self.transfers.list_paginated(limit=10000, filters={"status":"REQUESTED"})
        overdue, upcoming = await self.allocations.list_overdue(), await self.allocations.list_upcoming_returns(7)
        if user.role.value == "EMPLOYEE":
            maintenance = [m for m in maintenance if m.raised_by == user.id]; bookings = [b for b in bookings if b.booked_by == user.id]; transfers = []; overdue = []; upcoming = []
        return {"assets_available": counts.get(AssetStatus.AVAILABLE.value, 0), "assets_allocated": counts.get(AssetStatus.ALLOCATED.value, 0), "maintenance_today":len(maintenance), "upcoming_bookings":len(bookings), "pending_transfers":len(transfers), "upcoming_returns":len(upcoming), "overdue_assets":len(overdue), "unread_notifications":await self.notifications.count_unread(user.id)}
