from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from uuid import UUID
from decimal import Decimal


class PositionResponse(BaseModel):
    id: UUID
    subscription_id: UUID
    symbol: str
    exchange: str
    quantity: int
    avg_price: Decimal
    current_price: Optional[Decimal]
    unrealized_pnl: Optional[Decimal]
    opened_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    id: UUID
    subscription_id: UUID
    broker_order_id: Optional[str]
    symbol: str
    exchange: str
    order_type: str
    transaction_type: str
    quantity: int
    price: Optional[Decimal]
    trigger_price: Optional[Decimal]
    status: str
    filled_quantity: int
    filled_price: Optional[Decimal]
    reason: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    orders: List[OrderResponse]
    total: int
    page: int
    page_size: int


class TradeResponse(BaseModel):
    id: UUID
    subscription_id: UUID
    symbol: str
    exchange: str
    side: str
    quantity: int
    entry_price: Decimal
    exit_price: Optional[Decimal]
    pnl: Optional[Decimal]
    pnl_percent: Optional[Decimal]
    entry_time: datetime
    exit_time: Optional[datetime]
    duration_seconds: Optional[int]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class TradeListResponse(BaseModel):
    trades: List[TradeResponse]
    total: int
    page: int
    page_size: int


class PortfolioSummary(BaseModel):
    total_capital: Decimal
    allocated_capital: Decimal
    available_capital: Decimal
    total_pnl: Decimal
    today_pnl: Decimal
    active_strategies: int
    open_positions: int
    total_trades: int


class PnLSummary(BaseModel):
    period: str  # daily, weekly, monthly, yearly
    pnl: Decimal
    pnl_percent: Decimal
    trades: int
    winning_trades: int
    losing_trades: int
    win_rate: Decimal
    avg_win: Decimal
    avg_loss: Decimal
    max_drawdown: Decimal


class ReportRequest(BaseModel):
    start_date: datetime
    end_date: datetime
    format: str = Field(default="csv", pattern="^(csv|pdf)$")
    include_trades: bool = True
    include_orders: bool = False
