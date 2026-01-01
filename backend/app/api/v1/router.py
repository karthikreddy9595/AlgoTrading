from fastapi import APIRouter

from app.api.v1 import auth, users, strategies, portfolio, broker, notifications, reports
from app.api.v1.admin import strategies as admin_strategies
from app.api.v1.admin import users as admin_users
from app.api.v1.admin import monitoring as admin_monitoring

api_router = APIRouter()

# Public routes
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(strategies.router)
api_router.include_router(portfolio.router)
api_router.include_router(broker.router)
api_router.include_router(notifications.router)
api_router.include_router(reports.router)

# Admin routes
admin_router = APIRouter(prefix="/admin", tags=["Admin"])
admin_router.include_router(admin_strategies.router)
admin_router.include_router(admin_users.router)
admin_router.include_router(admin_monitoring.router)
api_router.include_router(admin_router)
