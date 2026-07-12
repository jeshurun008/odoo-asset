from datetime import date, datetime, timedelta, timezone
import pytest
from app.domain.asset import Asset, AssetStatus
from app.domain.audit import AuditItemResult
from app.domain.maintenance_request import MaintenancePriority, MaintenanceRequest, MaintenanceStatus
from app.domain.user import Role, User
from app.repositories.in_memory.asset import InMemoryAssetRepository
from app.repositories.in_memory.audit import InMemoryAuditRepository
from app.repositories.in_memory.booking import InMemoryBookingRepository
from app.repositories.in_memory.notification import InMemoryNotificationRepository
from app.repositories.in_memory.activity_log import InMemoryActivityLogRepository
from app.repositories.in_memory.allocation import InMemoryAssetAllocationRepository
from app.repositories.in_memory.user import InMemoryUserRepository
from app.repositories.in_memory.department import InMemoryDepartmentRepository
from app.services.activity_log_service import ActivityLogService
from app.services.asset_lifecycle_service import AssetLifecycleService
from app.services.audit_service import AuditService
from app.services.notification_service import InAppChannel, NotificationService
from app.services.allocation_service import AllocationService
from app.services.dashboard_service import DashboardService
from app.services.report_service import ReportService
from app.security.password import hash_password

pytestmark = pytest.mark.asyncio

def make_asset(): return Asset(name="Camera", category_id="cat", serial_number="1", acquisition_date="2026-01-01", acquisition_cost=1, condition="GOOD", location="HQ")
async def make_audit():
    assets, audits = InMemoryAssetRepository(), InMemoryAuditRepository(); asset=make_asset(); await assets.create(asset)
    notify=NotificationService(InAppChannel(InMemoryNotificationRepository()))
    service=AuditService(audits,assets,AssetLifecycleService(assets),notify)
    cycle=await service.create_cycle(name="July",start_date=date(2026,7,1),end_date=date(2026,7,2),created_by="manager")
    await service.assign_auditors(cycle.id,["auditor"])
    return service,audits,assets,cycle,asset

async def test_audit_missing_item_drives_asset_to_lost():
    service,audits,assets,cycle,asset=await make_audit(); calls=[]
    original=service.lifecycle.transition_to
    async def spy(*args,**kwargs): calls.append(kwargs.get("target_status") or args[1]); return await original(*args,**kwargs)
    service.lifecycle.transition_to=spy
    await service.close_cycle(cycle.id,"manager")
    assert calls == [AssetStatus.LOST]

async def test_audit_verification_rejected_on_closed_cycle():
    service,audits,_,cycle,_=await make_audit(); await service.close_cycle(cycle.id,"manager")
    from app.exceptions.exceptions import ConflictException
    with pytest.raises(ConflictException): await service.verify_item(cycle.id,(await audits.list_items(cycle.id))[0].id,"auditor",False,AuditItemResult.VERIFIED)

async def test_audit_close_autoflags_pending_as_missing():
    service,audits,_,cycle,_=await make_audit(); await service.close_cycle(cycle.id,"manager")
    assert (await audits.list_items(cycle.id))[0].result == AuditItemResult.MISSING

async def test_rbac_audit_endpoints(client):
    from app.core.dependencies.auth import user_repository_instance
    employee=User(email="audit-employee@example.com",hashed_password=hash_password("Password123!"),name="Employee",role=Role.EMPLOYEE); await user_repository_instance.create(employee)
    login=await client.post("/api/v1/auth/login",data={"username":employee.email,"password":"Password123!"})
    response=await client.post("/api/v1/audits",json={"name":"Audit","start_date":"2026-07-01","end_date":"2026-07-02"},headers={"Authorization":f"Bearer {login.json()['data']['access_token']}"})
    assert response.status_code == 403

async def test_notification_created_on_allocation():
    assets, allocs, users, depts = InMemoryAssetRepository(), InMemoryAssetAllocationRepository(), InMemoryUserRepository(), InMemoryDepartmentRepository()
    asset=make_asset(); await assets.create(asset); recipient=User(email="holder@example.com",hashed_password="x",name="Holder"); await users.create(recipient)
    notifications=InMemoryNotificationRepository(); service=AllocationService(allocs,assets,users,depts,AssetLifecycleService(assets),NotificationService(InAppChannel(notifications)))
    await service.allocate_asset(asset.id,"EMPLOYEE",recipient.id,"manager")
    records,total=await notifications.list_for_recipient(recipient.id,0,20)
    assert total == 1 and records[0].type.value == "ASSET_ASSIGNED"

async def test_notification_privacy(client):
    from app.core.dependencies.auth import user_repository_instance, notification_repository_instance
    a=User(email="notify-a@example.com",hashed_password=hash_password("Password123!"),name="A"); b=User(email="notify-b@example.com",hashed_password=hash_password("Password123!"),name="B")
    await user_repository_instance.create(a); await user_repository_instance.create(b)
    await notification_repository_instance.create(__import__('app.domain.notification',fromlist=['Notification']).Notification(recipient_user_id=a.id,type=__import__('app.domain.notification',fromlist=['NotificationType']).NotificationType.AUDIT_ASSIGNED,payload={}))
    login=await client.post("/api/v1/auth/login",data={"username":b.email,"password":"Password123!"})
    result=await client.get("/api/v1/notifications",headers={"Authorization":f"Bearer {login.json()['data']['access_token']}"})
    assert result.status_code == 200 and result.json()["data"]["total"] == 0

async def test_dashboard_kpi_no_n_plus_1():
    class Assets:
        calls=0
        async def count_by_status(self, department_id=None): self.calls+=1; return {"AVAILABLE":4,"ALLOCATED":2}
        async def list_paginated(self,*a,**k): raise AssertionError("Dashboard must use count_by_status")
    class Empty:
        async def list_maintenance_today(self): return []
        async def list_bookings_starting_within(self,x): return []
        async def list_paginated(self,**kwargs): return [],0
        async def list_overdue(self): return []
        async def list_upcoming_returns(self,x): return []
        async def count_unread(self,x): return 0
    assets,empty=Assets(),Empty(); result=await DashboardService(assets,empty,empty,empty,empty,empty).kpis(User(email="a@b.com",hashed_password="x",name="A",role=Role.ADMIN))
    assert assets.calls == 1 and result["assets_available"] == 4

async def test_maintenance_avg_resolution_time():
    now=datetime.now(timezone.utc)
    class Maint:
        async def list(self,limit): return [MaintenanceRequest(asset_id="a",raised_by="u",issue_description="issue",priority=MaintenancePriority.LOW,status=MaintenanceStatus.RESOLVED,raised_at=now-timedelta(hours=2),resolved_at=now), MaintenanceRequest(asset_id="b",raised_by="u",issue_description="issue",priority=MaintenancePriority.HIGH,status=MaintenanceStatus.RESOLVED,raised_at=now-timedelta(hours=6),resolved_at=now)]
    result=await ReportService(None,None,None,Maint(),None).maintenance_stats()
    assert result["average_resolution_seconds"] == 14400

async def test_activity_log_is_queryable_and_rbac_protected(client):
    from app.core.dependencies.auth import user_repository_instance, asset_repository_instance, activity_log_repository_instance
    activity_log_repository_instance._logs.clear(); asset_repository_instance._assets.clear()
    admin=User(email="log-admin@example.com",hashed_password=hash_password("Password123!"),name="Admin",role=Role.ADMIN); employee=User(email="log-employee@example.com",hashed_password=hash_password("Password123!"),name="Employee")
    await user_repository_instance.create(admin); await user_repository_instance.create(employee)
    asset=make_asset(); await asset_repository_instance.create(asset)
    await AssetLifecycleService(asset_repository_instance,ActivityLogService(activity_log_repository_instance)).transition_to(asset,AssetStatus.LOST,admin.id,"Audit")
    admin_login=await client.post("/api/v1/auth/login",data={"username":admin.email,"password":"Password123!"}); emp_login=await client.post("/api/v1/auth/login",data={"username":employee.email,"password":"Password123!"})
    headers={"Authorization":f"Bearer {admin_login.json()['data']['access_token']}"}; response=await client.get("/api/v1/activity-logs?entity_id="+asset.id,headers=headers)
    assert response.status_code == 200 and response.json()["data"]["items"][0]["action"] == "ASSET_LIFECYCLE_TRANSITION"
    assert (await client.get("/api/v1/activity-logs",headers={"Authorization":f"Bearer {emp_login.json()['data']['access_token']}"})).status_code == 403
