from datetime import datetime
from fastapi import APIRouter, Depends, Query
from app.core.dependencies.auth import get_report_service, require_role
from app.domain.user import Role
from app.schemas.envelope import SuccessResponse
router=APIRouter(prefix="/reports",tags=["Reports"])
MANAGERS=(Role.ADMIN,Role.ASSET_MANAGER)
@router.get("/allocation-summary")
async def allocation_summary(user=Depends(require_role(*MANAGERS)),service=Depends(get_report_service)): return SuccessResponse(data=await service.allocation_summary())
@router.get("/maintenance-stats")
async def maintenance_stats(user=Depends(require_role(*MANAGERS)),service=Depends(get_report_service)): return SuccessResponse(data=await service.maintenance_stats())
@router.get("/booking-usage")
async def booking_usage(start_date: datetime|None=Query(None),end_date: datetime|None=Query(None),user=Depends(require_role(*MANAGERS)),service=Depends(get_report_service)): return SuccessResponse(data=await service.booking_usage(start_date,end_date))
@router.get("/audit-reports")
async def audit_reports(user=Depends(require_role(*MANAGERS)),service=Depends(get_report_service)): return SuccessResponse(data=await service.audit_reports())
@router.get("/department-summary")
async def department_summary(user=Depends(require_role(Role.ADMIN,Role.ASSET_MANAGER,Role.DEPARTMENT_HEAD)),service=Depends(get_report_service)):
    rows=await service.allocation_summary()
    return SuccessResponse(data=[r for r in rows if user.role != Role.DEPARTMENT_HEAD or r["department_id"] == user.department_id])
@router.get("/asset-utilization")
async def asset_utilization(user=Depends(require_role(*MANAGERS)),service=Depends(get_report_service)): return SuccessResponse(data=await service.booking_usage())
