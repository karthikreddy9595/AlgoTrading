from fastapi import APIRouter

from app.api.v1 import auth, users, strategies, portfolio, broker, notifications, reports, market, backtest, optimization, blog, order_logs, payments
from app.api.v1.admin import strategies as admin_strategies
from app.api.v1.admin import users as admin_users
from app.api.v1.admin import monitoring as admin_monitoring
from app.api.v1.admin import blog as admin_blog

api_router = APIRouter()

# Public routes
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(strategies.router)
api_router.include_router(portfolio.router)
api_router.include_router(broker.router)
api_router.include_router(notifications.router)
api_router.include_router(reports.router)
api_router.include_router(market.router)
api_router.include_router(backtest.router)
api_router.include_router(optimization.router)
api_router.include_router(blog.router)
api_router.include_router(order_logs.router)
api_router.include_router(payments.router)

# Admin routes
admin_router = APIRouter(prefix="/admin", tags=["Admin"])
admin_router.include_router(admin_strategies.router)
admin_router.include_router(admin_users.router)
admin_router.include_router(admin_monitoring.router)
admin_router.include_router(admin_blog.router)
api_router.include_router(admin_router)
