from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import redis.asyncio as redis

from app.core.config import settings
from app.core.database import init_db
from app.api.v1.router import api_router
from app.api.websocket import portfolio as ws_portfolio
from app.api.websocket import market_data as ws_market_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting AlgoTrading Platform...")

    # Initialize Redis connection
    app.state.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)

    # Initialize database (create tables if they don't exist)
    # In production, use Alembic migrations instead
    if settings.DEBUG:
        await init_db()

    yield

    # Shutdown
    print("Shutting down AlgoTrading Platform...")
    await app.state.redis.close()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Algorithmic Trading Platform for Indian Markets",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# Session middleware for OAuth
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# Include WebSocket routes
app.include_router(ws_portfolio.router, prefix="/ws", tags=["WebSocket"])
app.include_router(ws_market_data.router, prefix="/ws", tags=["WebSocket"])


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
