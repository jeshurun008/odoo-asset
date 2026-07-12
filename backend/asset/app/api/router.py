from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.departments import router as departments_router
from app.api.v1.asset_categories import router as categories_router
from app.api.v1.employees import router as employees_router
from app.api.v1.assets import router as assets_router
from app.api.v1.allocations import router as allocations_router
from app.api.v1.transfers import router as transfers_router
from app.api.v1.bookings import router as bookings_router
from app.api.v1.maintenance import router as maintenance_router
from app.api.v1.audits import router as audits_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.reports import router as reports_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.activity_logs import router as activity_logs_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(departments_router)
api_router.include_router(categories_router)
api_router.include_router(employees_router)
api_router.include_router(assets_router)
api_router.include_router(allocations_router)
api_router.include_router(transfers_router)
api_router.include_router(bookings_router)
api_router.include_router(maintenance_router)
api_router.include_router(audits_router)
api_router.include_router(dashboard_router)
api_router.include_router(reports_router)
api_router.include_router(notifications_router)
api_router.include_router(activity_logs_router)
