from datetime import datetime, timezone
from app.domain.asset import AssetStatus
from app.domain.audit import AuditCycle, AuditItem, AuditItemResult, AuditStatus
from app.domain.notification import NotificationType
from app.exceptions.exceptions import ConflictException, ForbiddenException, NotFoundException, ValidationException
from app.repositories.asset import AbstractAssetRepository
from app.repositories.audit import AbstractAuditRepository
from app.services.asset_lifecycle_service import AssetLifecycleService
from app.services.notification_service import NotificationService

AUDIT_TRANSITIONS = {AuditStatus.PLANNED: {AuditStatus.IN_PROGRESS}, AuditStatus.IN_PROGRESS: {AuditStatus.CLOSED}, AuditStatus.CLOSED: set()}
class AuditService:
    def __init__(self, audit_repo: AbstractAuditRepository, asset_repo: AbstractAssetRepository, lifecycle: AssetLifecycleService, notifications: NotificationService): self.audit_repo, self.asset_repo, self.lifecycle, self.notifications = audit_repo, asset_repo, lifecycle, notifications
    async def create_cycle(self, *, name, start_date, end_date, created_by, department_id=None, category_id=None):
        if end_date < start_date: raise ValidationException("end_date must be on or after start_date.")
        if department_id and category_id: raise ValidationException("An audit may scope to either a department or category, not both.")
        cycle = await self.audit_repo.create(AuditCycle(name=name, start_date=start_date, end_date=end_date, created_by=created_by, department_id=department_id, category_id=category_id))
        assets, _ = await self.asset_repo.list_paginated(limit=10000, filters={k:v for k,v in {"department_id":department_id, "category_id":category_id}.items() if v})
        for asset in assets: await self.audit_repo.create_item(AuditItem(audit_cycle_id=cycle.id, asset_id=asset.id, expected_location=asset.location))
        return cycle
    async def assign_auditors(self, cycle_id, auditor_ids):
        cycle = await self._cycle(cycle_id)
        if cycle.status == AuditStatus.CLOSED: raise ConflictException("Closed audit cycles are immutable.")
        cycle.assigned_auditor_ids = list(dict.fromkeys(auditor_ids))
        if cycle.assigned_auditor_ids and cycle.status == AuditStatus.PLANNED: cycle.status = AuditStatus.IN_PROGRESS
        await self.audit_repo.update(cycle)
        for user_id in cycle.assigned_auditor_ids: await self.notifications.notify(user_id, NotificationType.AUDIT_ASSIGNED, {"entity_id": cycle.id, "entity_type":"audit", "message": f"You were assigned to audit {cycle.name}."})
        return cycle
    async def verify_item(self, cycle_id, item_id, actor_id, is_manager, result, notes=None):
        cycle = await self._cycle(cycle_id)
        if cycle.status == AuditStatus.CLOSED: raise ConflictException("Closed audit cycles are immutable.")
        if not is_manager and actor_id not in cycle.assigned_auditor_ids: raise ForbiddenException("Only assigned auditors may verify this audit.")
        if result == AuditItemResult.PENDING: raise ValidationException("Verification result cannot be PENDING.")
        item = await self.audit_repo.get_item(cycle_id, item_id)
        if not item: raise NotFoundException("Audit item not found.")
        item.result, item.verified_by, item.verified_at, item.notes = result, actor_id, datetime.now(timezone.utc), notes
        return await self.audit_repo.update_item(item)
    async def close_cycle(self, cycle_id, actor_id):
        cycle = await self._cycle(cycle_id)
        if cycle.status == AuditStatus.CLOSED: raise ConflictException("Audit cycle is already closed.")
        if cycle.status not in AUDIT_TRANSITIONS or AuditStatus.CLOSED not in AUDIT_TRANSITIONS[cycle.status]: raise ConflictException("Audit cycle must be in progress before closing.")
        for item in await self.audit_repo.list_items(cycle_id):
            if item.result == AuditItemResult.PENDING: item.result, item.verified_by, item.verified_at = AuditItemResult.MISSING, actor_id, datetime.now(timezone.utc); await self.audit_repo.update_item(item)
            if item.result == AuditItemResult.MISSING:
                asset = await self.asset_repo.get_by_id(item.asset_id)
                if asset and asset.status != AssetStatus.LOST: await self.lifecycle.transition_to(asset, AssetStatus.LOST, actor_id, "Audit missing item")
        cycle.status, cycle.closed_at, cycle.closed_by = AuditStatus.CLOSED, datetime.now(timezone.utc), actor_id
        return await self.audit_repo.update(cycle)
    async def discrepancy_report(self, cycle_id):
        await self._cycle(cycle_id); items = await self.audit_repo.list_items(cycle_id)
        return [i for i in items if i.result != AuditItemResult.VERIFIED]
    async def _cycle(self, cycle_id):
        cycle = await self.audit_repo.get_by_id(cycle_id)
        if not cycle: raise NotFoundException("Audit cycle not found.")
        return cycle
