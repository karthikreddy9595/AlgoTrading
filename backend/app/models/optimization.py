"""
SQLAlchemy models for Monte Carlo parameter optimization.
"""
from sqlalchemy import Column, String, Boolean, DateTime, Text, Numeric, Integer, Date, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class Optimization(Base):
    """Stores optimization run configuration and metadata."""
    __tablename__ = "optimizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False)
    source_backtest_id = Column(UUID(as_uuid=True), ForeignKey("backtests.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(20), nullable=False, default="pending")  # pending, running, completed, failed, cancelled

    # Backtest configuration (copied from source backtest)
    symbol = Column(String(50), nullable=False)
    exchange = Column(String(20), nullable=False, default="NSE")
    interval = Column(String(20), nullable=False)  # 1min, 5min, 15min, 30min, 1hour, 1day
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    initial_capital = Column(Numeric(15, 2), nullable=False)

    # Optimization settings
    num_samples = Column(Integer, nullable=False, default=100)  # Number of Monte Carlo samples
    parameter_ranges = Column(JSONB, nullable=False)  # {"param": {"min": x, "max": y, "step": z}}
    objective_metric = Column(String(50), nullable=False, default="total_return_percent")

    # Progress tracking
    progress = Column(Integer, default=0)  # 0-100
    completed_samples = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    # Timestamps
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="optimizations")
    strategy = relationship("Strategy", backref="optimizations")
    source_backtest = relationship("Backtest", backref="optimizations")
    results = relationship("OptimizationResult", back_populates="optimization", cascade="all, delete-orphan")


class OptimizationResult(Base):
    """Stores individual sample results from Monte Carlo optimization."""
    __tablename__ = "optimization_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    optimization_id = Column(UUID(as_uuid=True), ForeignKey("optimizations.id", ondelete="CASCADE"), nullable=False)

    # Parameter values used for this sample
    parameters = Column(JSONB, nullable=False)  # {"fast_ma_period": 9, "slow_ma_period": 21}

    # Key metrics (denormalized for fast queries and sorting)
    total_return = Column(Numeric(15, 4), nullable=True)
    total_return_percent = Column(Numeric(10, 4), nullable=True)
    sharpe_ratio = Column(Numeric(10, 4), nullable=True)
    sortino_ratio = Column(Numeric(10, 4), nullable=True)
    max_drawdown = Column(Numeric(10, 4), nullable=True)
    win_rate = Column(Numeric(6, 4), nullable=True)
    profit_factor = Column(Numeric(10, 4), nullable=True)
    calmar_ratio = Column(Numeric(10, 4), nullable=True)
    total_trades = Column(Integer, default=0)

    # Full metrics JSON (for detailed view)
    full_metrics = Column(JSONB, nullable=True)

    # Flag for best result
    is_best = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    optimization = relationship("Optimization", back_populates="results")
