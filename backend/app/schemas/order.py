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


class OrderLogResponse(BaseModel):
    """Response schema for OrderLog entries."""
    id: UUID
    subscription_id: UUID
    order_id: Optional[UUID]
    symbol: str
    exchange: str
    order_type: str
    transaction_type: str
    quantity: int
    price: Optional[Decimal]
    trigger_price: Optional[Decimal]
    event_type: str  # generated, dry_run, submitted, placed, filled, rejected, failed
    is_dry_run: bool
    is_test_order: bool
    success: Optional[bool]
    broker_order_id: Optional[str]
    broker_name: Optional[str]
    broker_request: Optional[dict]
    broker_response: Optional[dict]
    error_message: Optional[str]
    strategy_name: Optional[str]
    reason: Optional[str]
    market_price: Optional[Decimal]
    created_at: datetime

    class Config:
        from_attributes = True


class OrderLogListResponse(BaseModel):
    """Paginated list of order logs."""
    logs: List[OrderLogResponse]
    total: int
    page: int
    page_size: int


class BrokerTestOrderRequest(BaseModel):
    """Request to place a test order with broker."""
    broker_connection_id: UUID
    symbol: str = Field(default="RELIANCE", description="Symbol to trade")
    exchange: str = Field(default="NSE", description="Exchange")
    quantity: int = Field(default=1, ge=1, le=10, description="Test quantity (1-10)")
    order_type: str = Field(default="LIMIT", pattern="^(MARKET|LIMIT)$")
    transaction_type: str = Field(default="BUY", pattern="^(BUY|SELL)$")
    price: Optional[Decimal] = Field(default=None, description="Price for LIMIT orders")


class BrokerTestOrderResponse(BaseModel):
    """Response from broker test order."""
    success: bool
    message: str
    order_log_id: Optional[UUID] = None
    broker_order_id: Optional[str] = None
    broker_response: Optional[dict] = None
    error: Optional[str] = None
