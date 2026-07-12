from datetime import datetime, timezone
class ReportService:
    def __init__(self, assets, allocations, bookings, maintenance, audit): self.assets, self.allocations, self.bookings, self.maintenance, self.audit = assets, allocations, bookings, maintenance, audit
    async def allocation_summary(self):
        assets, _ = await self.assets.list_paginated(limit=10000); result = {}
        for a in assets:
            row = result.setdefault(a.department_id or "unassigned", {"department_id":a.department_id,"asset_count":0,"by_category":{},"by_status":{}}); row["asset_count"] += 1; row["by_category"][a.category_id] = row["by_category"].get(a.category_id,0)+1; row["by_status"][a.status.value] = row["by_status"].get(a.status.value,0)+1
        return list(result.values())
    async def maintenance_stats(self):
        requests = await self.maintenance.list(limit=10000); priorities={}; statuses={}; durations=[]
        for r in requests:
            priorities[r.priority.value]=priorities.get(r.priority.value,0)+1; statuses[r.status.value]=statuses.get(r.status.value,0)+1
            if r.resolved_at: durations.append((r.resolved_at-r.raised_at).total_seconds())
        return {"by_priority":priorities,"by_status":statuses,"average_resolution_seconds":sum(durations)/len(durations) if durations else 0}
    async def booking_usage(self, start=None, end=None):
        bookings = await self.bookings.list(limit=10000); result={}
        for b in bookings:
            if b.cancelled_at or (start and b.start_time < start) or (end and b.end_time > end): continue
            row=result.setdefault(b.asset_id,{"asset_id":b.asset_id,"booking_count":0,"hours":0}); row["booking_count"]+=1; row["hours"]+=(b.end_time-b.start_time).total_seconds()/3600
        return list(result.values())
    async def audit_reports(self):
        cycles=await self.audit.list(limit=10000); return [{"audit_cycle_id":c.id,"name":c.name,"status":c.status.value,"discrepancies":len(await self.audit.list_items(c.id)) - len([i for i in await self.audit.list_items(c.id) if i.result.value == "VERIFIED"])} for c in cycles]
