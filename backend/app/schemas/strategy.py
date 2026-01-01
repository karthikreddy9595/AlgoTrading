from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, time
from uuid import UUID
from decimal import Decimal


class StrategyBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(..., min_length=2, max_length=255, pattern="^[a-z0-9-]+$")
    description: Optional[str] = None
    long_description: Optional[str] = None
    version: str = "1.0.0"
    min_capital: Decimal = Field(default=10000, ge=10000)
    expected_return_percent: Optional[Decimal] = None
    max_drawdown_percent: Optional[Decimal] = None
    timeframe: Optional[str] = None
    supported_symbols: Optional[List[str]] = None
    tags: Optional[List[str]] = None


class StrategyCreate(StrategyBase):
    module_path: str
    class_name: str
    git_repo_url: Optional[str] = None
    git_branch: str = "main"


class StrategyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    long_description: Optional[str] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    expected_return_percent: Optional[Decimal] = None
    max_drawdown_percent: Optional[Decimal] = None
    tags: Optional[List[str]] = None


class StrategyResponse(StrategyBase):
    id: UUID
    author: str
    is_active: bool
    is_featured: bool
    module_path: str
    class_name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StrategyListResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    description: Optional[str]
    version: str
    min_capital: Decimal
    expected_return_percent: Optional[Decimal]
    max_drawdown_percent: Optional[Decimal]
    timeframe: Optional[str]
    tags: Optional[List[str]]
    is_featured: bool

    class Config:
        from_attributes = True


class StrategySubscriptionCreate(BaseModel):
    strategy_id: UUID
    broker_connection_id: Optional[UUID] = None
    capital_allocated: Decimal = Field(..., ge=10000)
    is_paper_trading: bool = True
    max_drawdown_percent: Decimal = Field(default=10, ge=1, le=50)
    daily_loss_limit: Optional[Decimal] = None
    per_trade_stop_loss_percent: Decimal = Field(default=2, ge=0.5, le=10)
    max_positions: int = Field(default=5, ge=1, le=20)
    scheduled_start: Optional[time] = None
    scheduled_stop: Optional[time] = None
    active_days: List[int] = Field(default=[1, 2, 3, 4, 5])


class StrategySubscriptionUpdate(BaseModel):
    capital_allocated: Optional[Decimal] = Field(None, ge=10000)
    is_paper_trading: Optional[bool] = None
    max_drawdown_percent: Optional[Decimal] = Field(None, ge=1, le=50)
    daily_loss_limit: Optional[Decimal] = None
    per_trade_stop_loss_percent: Optional[Decimal] = Field(None, ge=0.5, le=10)
    max_positions: Optional[int] = Field(None, ge=1, le=20)
    scheduled_start: Optional[time] = None
    scheduled_stop: Optional[time] = None
    active_days: Optional[List[int]] = None


class StrategySubscriptionResponse(BaseModel):
    id: UUID
    user_id: UUID
    strategy_id: UUID
    broker_connection_id: Optional[UUID]
    status: str
    capital_allocated: Decimal
    is_paper_trading: bool
    max_drawdown_percent: Decimal
    daily_loss_limit: Optional[Decimal]
    per_trade_stop_loss_percent: Decimal
    max_positions: int
    scheduled_start: Optional[time]
    scheduled_stop: Optional[time]
    active_days: List[int]
    current_pnl: Decimal
    today_pnl: Decimal
    last_started_at: Optional[datetime]
    last_stopped_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class StrategyAction(BaseModel):
    action: str = Field(..., pattern="^(start|stop|pause|resume)$")
