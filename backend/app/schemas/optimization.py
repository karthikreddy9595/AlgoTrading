"""
Pydantic schemas for Monte Carlo parameter optimization.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, date
from uuid import UUID
from decimal import Decimal
from enum import Enum


class OptimizationStatus(str, Enum):
    """Status of an optimization run."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ObjectiveMetric(str, Enum):
    """Metrics available for optimization objective."""
    TOTAL_RETURN_PERCENT = "total_return_percent"
    SHARPE_RATIO = "sharpe_ratio"
    SORTINO_RATIO = "sortino_ratio"
    PROFIT_FACTOR = "profit_factor"
    WIN_RATE = "win_rate"
    CALMAR_RATIO = "calmar_ratio"


class ParameterRange(BaseModel):
    """Range specification for a single parameter."""
    min: float
    max: float
    step: float


class OptimizationCreate(BaseModel):
    """Request body for starting an optimization."""
    source_backtest_id: UUID
    parameter_ranges: Dict[str, ParameterRange]
    num_samples: int = Field(default=100, ge=50, le=200)
    objective_metric: ObjectiveMetric = ObjectiveMetric.TOTAL_RETURN_PERCENT


class OptimizationResponse(BaseModel):
    """Full optimization record response."""
    id: UUID
    user_id: UUID
    strategy_id: UUID
    source_backtest_id: Optional[UUID] = None
    status: OptimizationStatus
    symbol: str
    exchange: str
    interval: str
    start_date: date
    end_date: date
    initial_capital: Decimal
    num_samples: int
    parameter_ranges: Dict[str, Any]
    objective_metric: str
    progress: int
    completed_samples: int
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class OptimizationListResponse(BaseModel):
    """List item for optimization history."""
    id: UUID
    strategy_id: UUID
    source_backtest_id: Optional[UUID] = None
    status: OptimizationStatus
    symbol: str
    exchange: str
    interval: str
    start_date: date
    end_date: date
    initial_capital: Decimal
    num_samples: int
    objective_metric: str
    progress: int
    completed_samples: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    # Best result summary
    best_return_percent: Optional[Decimal] = None

    class Config:
        from_attributes = True


class OptimizationProgressResponse(BaseModel):
    """Progress polling response."""
    id: UUID
    status: OptimizationStatus
    progress: int
    completed_samples: int
    total_samples: int
    error_message: Optional[str] = None


class OptimizationResultItem(BaseModel):
    """Individual optimization result."""
    id: UUID
    parameters: Dict[str, Any]
    total_return: Optional[Decimal] = None
    total_return_percent: Optional[Decimal] = None
    sharpe_ratio: Optional[Decimal] = None
    sortino_ratio: Optional[Decimal] = None
    max_drawdown: Optional[Decimal] = None
    win_rate: Optional[Decimal] = None
    profit_factor: Optional[Decimal] = None
    calmar_ratio: Optional[Decimal] = None
    total_trades: int = 0
    is_best: bool = False

    class Config:
        from_attributes = True


class OptimizationResultsResponse(BaseModel):
    """Full results response with best result highlighted."""
    optimization_id: UUID
    status: OptimizationStatus
    objective_metric: str
    total_samples: int
    best_result: Optional[OptimizationResultItem] = None
    all_results: List[OptimizationResultItem] = []


class HeatmapDataPoint(BaseModel):
    """Single point in the heatmap."""
    x: float
    y: float
    value: float


class HeatmapResponse(BaseModel):
    """Heatmap data for visualization."""
    param_x: str
    param_y: str
    x_values: List[float]
    y_values: List[float]
    data: List[HeatmapDataPoint]
    best_x: Optional[float] = None
    best_y: Optional[float] = None
    best_value: Optional[float] = None
    metric: str
