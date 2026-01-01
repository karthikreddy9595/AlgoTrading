from pydantic_settings import BaseSettings
from typing import Optional, List
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "AlgoTrading Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # API
    API_V1_PREFIX: str = "/api/v1"

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/algotrading"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # OAuth - Google
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"

    # Fyers Broker
    FYERS_APP_ID: Optional[str] = None
    FYERS_SECRET_KEY: Optional[str] = None
    FYERS_REDIRECT_URI: str = "http://localhost:8000/api/v1/broker/fyers/callback"

    # Email - SMTP
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    FROM_EMAIL: str = "noreply@algotrading.com"

    # Email - SendGrid (alternative)
    SENDGRID_API_KEY: Optional[str] = None

    # SMS Configuration
    SMS_API_KEY: Optional[str] = None
    SMS_SENDER_ID: str = "ALGOTD"
    SMS_PROVIDER: str = "msg91"  # msg91 or twilio

    # Twilio (alternative SMS provider)
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_FROM_NUMBER: Optional[str] = None

    # Trading
    MIN_CAPITAL: float = 10000.0
    DEFAULT_MAX_DRAWDOWN_PERCENT: float = 10.0
    DEFAULT_DAILY_LOSS_LIMIT_PERCENT: float = 5.0
    DEFAULT_PER_TRADE_SL_PERCENT: float = 2.0
    DEFAULT_MAX_POSITIONS: int = 5

    # Execution Engine
    STRATEGY_HEARTBEAT_INTERVAL: int = 5  # seconds
    ORDER_TIMEOUT: int = 30  # seconds

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
