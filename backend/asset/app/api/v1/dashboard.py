from fastapi import APIRouter, Depends
from app.core.dependencies.auth import get_current_user, get_dashboard_service
from app.domain.user import User
from app.schemas.dashboard import DashboardKpisResponse
from app.schemas.envelope import SuccessResponse
router=APIRouter(prefix="/dashboard",tags=["Dashboard"])
@router.get("/kpis",response_model=SuccessResponse[DashboardKpisResponse])
async def kpis(user: User=Depends(get_current_user), service=Depends(get_dashboard_service)): return SuccessResponse(data=DashboardKpisResponse(**await service.kpis(user)))
