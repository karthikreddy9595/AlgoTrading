"""
Market data schemas for API responses.
"""

from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime


class IndicatorDataPoint(BaseModel):
    """Single data point for an indicator."""

    time: str  # ISO format datetime
    value: Optional[float] = None


class ChartIndicator(BaseModel):
    """Indicator configuration and data for chart display."""

    name: str  # Display name: "Fast SMA (9)", "RSI (14)"
    type: str  # Indicator type: "sma", "rsi", "ema", etc.
    pane: str  # Chart pane: "main", "oscillator"
    color: str  # Hex color for display
    data: List[IndicatorDataPoint]
    params: Dict[str, Any]  # e.g., {"period": 14, "overbought": 70}


class TradeMarker(BaseModel):
    """Trade marker for displaying entry/exit points on chart."""

    time: datetime
    price: float
    type: str  # "entry" or "exit"
    side: str  # "buy" or "sell" (for entry), determines marker direction
    quantity: int
    pnl: Optional[float] = None  # For exit trades
    pnl_percent: Optional[float] = None  # For exit trades
    order_id: str
    trade_id: Optional[str] = None


class HistoricalCandle(BaseModel):
    """Single OHLC candle."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class ChartDataResponse(BaseModel):
    """Response containing chart data with indicators and trade markers."""

    symbol: str
    exchange: str
    interval: str
    strategy_name: str
    strategy_slug: str
    candles: List[HistoricalCandle]
    indicators: List[ChartIndicator]
    trades: List[TradeMarker]
    message: Optional[str] = None
