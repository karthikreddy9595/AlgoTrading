from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from uuid import UUID
from decimal import Decimal
from enum import Enum


class BacktestStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BacktestInterval(str, Enum):
    ONE_MIN = "1min"
    FIVE_MIN = "5min"
    FIFTEEN_MIN = "15min"
    THIRTY_MIN = "30min"
    ONE_HOUR = "1hour"
    ONE_DAY = "1day"


# ==================== Request Schemas ====================


class BacktestCreate(BaseModel):
    """Request body for creating a new backtest."""
    strategy_id: UUID
    symbol: str = Field(..., min_length=1, max_length=50, description="Stock symbol (e.g., RELIANCE)")
    exchange: str = Field(default="NSE", pattern="^(NSE|BSE|NFO|MCX|CDS)$")
    interval: BacktestInterval = BacktestInterval.ONE_DAY
    start_date: date
    end_date: date
    initial_capital: Decimal = Field(..., ge=10000, description="Starting capital for simulation")
    config: Optional[Dict[str, Any]] = None  # Strategy-specific configuration


# ==================== Response Schemas ====================


class BacktestResponse(BaseModel):
    """Response for a single backtest."""
    id: UUID
    user_id: UUID
    strategy_id: UUID
    status: BacktestStatus
    symbol: str
    exchange: str
    interval: str
    start_date: date
    end_date: date
    initial_capital: Decimal
    config: Optional[Dict[str, Any]]
    progress: int
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class BacktestListResponse(BaseModel):
    """Response for list of backtests (lightweight)."""
    id: UUID
    strategy_id: UUID
    status: BacktestStatus
    symbol: str
    exchange: str
    interval: str
    start_date: date
    end_date: date
    initial_capital: Decimal
    progress: int
    created_at: datetime
    completed_at: Optional[datetime]
    # Include summary metrics if completed
    total_return_percent: Optional[Decimal] = None
    total_trades: Optional[int] = None
    # Include error message for failed backtests
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class BacktestProgressResponse(BaseModel):
    """Response for backtest progress status."""
    id: UUID
    status: BacktestStatus
    progress: int
    message: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class BacktestResultResponse(BaseModel):
    """Response containing performance metrics."""
    id: UUID
    backtest_id: UUID

    # Return metrics
    total_return: Optional[Decimal]
    total_return_percent: Optional[Decimal]
    cagr: Optional[Decimal]

    # Risk-adjusted metrics
    sharpe_ratio: Optional[Decimal]
    sortino_ratio: Optional[Decimal]
    calmar_ratio: Optional[Decimal]

    # Drawdown metrics
    max_drawdown: Optional[Decimal]
    avg_drawdown: Optional[Decimal]

    # Trade statistics
    win_rate: Optional[Decimal]
    profit_factor: Optional[Decimal]
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_trade_duration: Optional[int]  # in seconds

    # Capital metrics
    final_capital: Optional[Decimal]
    max_capital: Optional[Decimal]

    created_at: datetime

    class Config:
        from_attributes = True


class BacktestTradeResponse(BaseModel):
    """Response for a single backtest trade."""
    id: UUID
    backtest_id: UUID
    signal: str  # BUY, SELL, EXIT_LONG, EXIT_SHORT
    entry_price: Decimal
    exit_price: Optional[Decimal]
    quantity: int
    entry_time: datetime
    exit_time: Optional[datetime]
    pnl: Optional[Decimal]
    pnl_percent: Optional[Decimal]
    reason: Optional[str]
    is_open: bool

    class Config:
        from_attributes = True


class BacktestTradeListResponse(BaseModel):
    """Paginated list of backtest trades."""
    trades: List[BacktestTradeResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ==================== Chart Data Schemas ====================


class CandleData(BaseModel):
    """OHLC candle data for charting."""
    time: int  # Unix timestamp
    open: float
    high: float
    low: float
    close: float
    volume: Optional[int] = None


class ChartMarker(BaseModel):
    """Trade marker for chart."""
    time: int  # Unix timestamp
    position: str  # "aboveBar" or "belowBar"
    color: str  # Hex color
    shape: str  # "arrowUp", "arrowDown", "circle"
    text: str  # Tooltip text


class EquityCurvePoint(BaseModel):
    """Equity curve data point."""
    time: int  # Unix timestamp
    value: float  # Equity value


class IndicatorDataPoint(BaseModel):
    """Single indicator data point."""
    time: int  # Unix timestamp
    value: Optional[float] = None  # Indicator value (can be None if not calculated yet)


class IndicatorSeries(BaseModel):
    """Time series data for an indicator."""
    name: str  # Indicator name (e.g., "RSI", "Fast SMA", "MACD")
    data: List[IndicatorDataPoint]
    type: str  # "line" for overlay, "histogram" for MACD, etc.
    pane: str  # "main" for price overlays, "rsi", "macd", etc. for separate panes
    color: Optional[str] = None  # Color for the indicator line

    # Optional MACD-specific fields
    signal_line: Optional[List[IndicatorDataPoint]] = None
    histogram: Optional[List[IndicatorDataPoint]] = None


class BacktestChartData(BaseModel):
    """Complete chart data for backtest results."""
    candles: List[CandleData]
    markers: List[ChartMarker]
    equity_curve: List[EquityCurvePoint]
    indicators: Optional[List[IndicatorSeries]] = None  # Strategy indicators (RSI, SMA, MACD, etc.)


# ==================== WebSocket Schemas ====================


class BacktestProgressUpdate(BaseModel):
    """WebSocket message for progress updates."""
    backtest_id: UUID
    status: BacktestStatus
    progress: int
    message: str
    current_date: Optional[str] = None  # Current date being processed
    trades_count: Optional[int] = None  # Number of trades so far
