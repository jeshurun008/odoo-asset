from datetime import date
import pytest
from app.domain.asset import Asset, AssetStatus
from app.domain.audit import AuditItemResult, AuditStatus
from app.domain.notification import NotificationType
from app.repositories.in_memory.asset import InMemoryAssetRepository
from app.repositories.in_memory.audit import InMemoryAuditRepository
from app.repositories.in_memory.booking import InMemoryBookingRepository
from app.repositories.in_memory.notification import InMemoryNotificationRepository
from app.services.asset_lifecycle_service import AssetLifecycleService
from app.services.audit_service import AuditService
from app.services.notification_service import InAppChannel, NotificationService

pytestmark = pytest.mark.asyncio

async def test_audit_close_marks_pending_missing_and_transitions_asset_to_lost():
    assets, audits = InMemoryAssetRepository(), InMemoryAuditRepository()
    notifications = NotificationService(InAppChannel(InMemoryNotificationRepository()), InMemoryBookingRepository())
    asset = Asset(name="Camera", category_id="cat", serial_number="1", acquisition_date="2026-01-01", acquisition_cost=1, condition="GOOD", location="HQ")
    await assets.create(asset)
    service = AuditService(audits, assets, AssetLifecycleService(assets), notifications)
    cycle = await service.create_cycle(name="July", start_date=date(2026, 7, 1), end_date=date(2026, 7, 2), created_by="manager")
    await service.assign_auditors(cycle.id, ["auditor"])
    closed = await service.close_cycle(cycle.id, "manager")
    item = (await audits.list_items(cycle.id))[0]
    assert closed.status == AuditStatus.CLOSED
    assert item.result == AuditItemResult.MISSING
    assert (await assets.get_by_id(asset.id)).status == AssetStatus.LOST

async def test_notifications_are_private_and_marked_read():
    repo = InMemoryNotificationRepository(); service = NotificationService(InAppChannel(repo))
    n = await service.notify("user-a", NotificationType.AUDIT_ASSIGNED, {"message":"Assigned"})
    mine, total = await repo.list_for_recipient("user-a", 0, 20)
    other, other_total = await repo.list_for_recipient("user-b", 0, 20)
    assert total == 1 and mine[0].id == n.id
    assert other_total == 0 and other == []
    n.read = True; await repo.update(n)
    assert await repo.count_unread("user-a") == 0
