from sqlalchemy import Column, String, Boolean, DateTime, Text, Numeric, Integer, Date, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class Backtest(Base):
    """Stores backtest configuration and metadata."""
    __tablename__ = "backtests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), nullable=False, default="pending")  # pending, running, completed, failed, cancelled
    symbol = Column(String(50), nullable=False)
    exchange = Column(String(20), nullable=False, default="NSE")
    interval = Column(String(20), nullable=False)  # 1min, 5min, 15min, 30min, 1hour, 1day
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    initial_capital = Column(Numeric(15, 2), nullable=False)
    config = Column(JSONB, nullable=True)  # Strategy-specific configuration
    progress = Column(Integer, default=0)  # 0-100
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="backtests")
    strategy = relationship("Strategy", backref="backtests")
    result = relationship("BacktestResult", back_populates="backtest", uselist=False, cascade="all, delete-orphan")
    trades = relationship("BacktestTrade", back_populates="backtest", cascade="all, delete-orphan")
    equity_curve = relationship("BacktestEquityCurve", back_populates="backtest", cascade="all, delete-orphan")


class BacktestResult(Base):
    """Stores computed performance metrics for a completed backtest."""
    __tablename__ = "backtest_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    backtest_id = Column(UUID(as_uuid=True), ForeignKey("backtests.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Return metrics
    total_return = Column(Numeric(15, 4), nullable=True)  # Absolute return in currency
    total_return_percent = Column(Numeric(10, 4), nullable=True)  # Return percentage
    cagr = Column(Numeric(10, 4), nullable=True)  # Compound Annual Growth Rate

    # Risk-adjusted metrics
    sharpe_ratio = Column(Numeric(10, 4), nullable=True)
    sortino_ratio = Column(Numeric(10, 4), nullable=True)
    calmar_ratio = Column(Numeric(10, 4), nullable=True)  # CAGR / Max Drawdown

    # Drawdown metrics
    max_drawdown = Column(Numeric(10, 4), nullable=True)  # Maximum drawdown percentage
    avg_drawdown = Column(Numeric(10, 4), nullable=True)  # Average drawdown

    # Trade statistics
    win_rate = Column(Numeric(6, 4), nullable=True)  # Percentage of winning trades
    profit_factor = Column(Numeric(10, 4), nullable=True)  # Gross profit / gross loss
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    avg_trade_duration = Column(Integer, nullable=True)  # Average duration in seconds

    # Capital metrics
    final_capital = Column(Numeric(15, 2), nullable=True)
    max_capital = Column(Numeric(15, 2), nullable=True)  # Peak capital reached

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    backtest = relationship("Backtest", back_populates="result")


class BacktestTrade(Base):
    """Stores individual trades executed during backtest."""
    __tablename__ = "backtest_trades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    backtest_id = Column(UUID(as_uuid=True), ForeignKey("backtests.id", ondelete="CASCADE"), nullable=False)
    signal = Column(String(20), nullable=False)  # BUY, SELL, EXIT_LONG, EXIT_SHORT
    entry_price = Column(Numeric(15, 4), nullable=False)
    exit_price = Column(Numeric(15, 4), nullable=True)
    quantity = Column(Integer, nullable=False)
    entry_time = Column(DateTime, nullable=False)
    exit_time = Column(DateTime, nullable=True)
    pnl = Column(Numeric(15, 4), nullable=True)  # Realized profit/loss
    pnl_percent = Column(Numeric(10, 4), nullable=True)  # Return percentage
    reason = Column(Text, nullable=True)  # Strategy reason for trade
    is_open = Column(Boolean, default=False)  # Whether position is still open
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    backtest = relationship("Backtest", back_populates="trades")


class BacktestEquityCurve(Base):
    """Stores equity curve data points for charting."""
    __tablename__ = "backtest_equity_curve"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    backtest_id = Column(UUID(as_uuid=True), ForeignKey("backtests.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    equity = Column(Numeric(15, 4), nullable=False)
    drawdown = Column(Numeric(10, 4), nullable=True)  # Current drawdown percentage

    # Relationships
    backtest = relationship("Backtest", back_populates="equity_curve")
