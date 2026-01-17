"""
Optimization API endpoints for Monte Carlo parameter optimization.
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from uuid import UUID
import math

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models import (
    User, Strategy, Backtest, BrokerConnection,
    Optimization, OptimizationResult
)
from app.schemas.optimization import (
    OptimizationCreate,
    OptimizationResponse,
    OptimizationListResponse,
    OptimizationProgressResponse,
    OptimizationResultItem,
    OptimizationResultsResponse,
    HeatmapDataPoint,
    HeatmapResponse,
    OptimizationStatus,
)
from backtest.engine import BacktestEngine, BacktestConfig
from backtest.optimizer import MonteCarloOptimizer, ParameterRange, OptimizationConfig
from brokers.factory import BrokerFactory
from app.core.config import settings


router = APIRouter(prefix="/optimization", tags=["Optimization"])


# ==================== Run Optimization ====================


@router.post("/run", response_model=OptimizationResponse, status_code=status.HTTP_201_CREATED)
async def run_optimization(
    data: OptimizationCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Start a new Monte Carlo parameter optimization.

    Requires a completed backtest as source. Returns immediately with optimization ID.
    Execution happens asynchronously.
    """
    # Get source backtest
    result = await db.execute(
        select(Backtest).where(
            Backtest.id == data.source_backtest_id,
            Backtest.user_id == current_user.id,
        )
    )
    source_backtest = result.scalar_one_or_none()

    if not source_backtest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source backtest not found",
        )

    if source_backtest.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source backtest must be completed",
        )

    # Validate strategy exists
    result = await db.execute(
        select(Strategy).where(Strategy.id == source_backtest.strategy_id)
    )
    strategy = result.scalar_one_or_none()

    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found",
        )

    # Convert parameter ranges to dict format for storage
    param_ranges_dict = {
        name: {"min": pr.min, "max": pr.max, "step": pr.step}
        for name, pr in data.parameter_ranges.items()
    }

    # Create optimization record
    optimization = Optimization(
        user_id=current_user.id,
        strategy_id=source_backtest.strategy_id,
        source_backtest_id=source_backtest.id,
        status="pending",
        symbol=source_backtest.symbol,
        exchange=source_backtest.exchange,
        interval=source_backtest.interval,
        start_date=source_backtest.start_date,
        end_date=source_backtest.end_date,
        initial_capital=source_backtest.initial_capital,
        num_samples=data.num_samples,
        parameter_ranges=param_ranges_dict,
        objective_metric=data.objective_metric.value,
        progress=0,
        completed_samples=0,
    )
    db.add(optimization)
    await db.commit()
    await db.refresh(optimization)

    # Queue background task
    background_tasks.add_task(
        execute_optimization_task,
        optimization_id=str(optimization.id),
        strategy_module=strategy.module_path,
        strategy_class=strategy.class_name,
        user_id=str(current_user.id),
    )

    return optimization


async def execute_optimization_task(
    optimization_id: str,
    strategy_module: str,
    strategy_class: str,
    user_id: str,
):
    """Background task to execute optimization."""
    from app.core.database import AsyncSessionLocal
    import logging
    import importlib

    logger = logging.getLogger(__name__)

    async with AsyncSessionLocal() as db:
        try:
            logger.info(f"Starting optimization {optimization_id}")

            # Get optimization record
            result = await db.execute(
                select(Optimization).where(Optimization.id == optimization_id)
            )
            optimization = result.scalar_one_or_none()

            if not optimization:
                return

            # Update status to running
            optimization.status = "running"
            optimization.started_at = datetime.utcnow()
            await db.commit()

            # Get broker connection for historical data
            broker_result = await db.execute(
                select(BrokerConnection).where(
                    BrokerConnection.user_id == user_id,
                    BrokerConnection.is_active == True,
                )
            )
            connection = broker_result.scalar_one_or_none()

            if not connection:
                optimization.status = "failed"
                optimization.error_message = "No active broker connection found."
                await db.commit()
                return

            # Fetch historical data
            try:
                config = _get_broker_config(connection.broker)
                broker = await BrokerFactory.create_and_connect(
                    connection.broker,
                    {
                        "api_key": connection.api_key,
                        "api_secret": connection.api_secret,
                        "access_token": connection.access_token,
                        "client_id": config.get("app_id", connection.api_key),
                    },
                )

                historical_data = await broker.get_historical_data(
                    symbol=optimization.symbol,
                    exchange=optimization.exchange,
                    interval=optimization.interval,
                    from_date=datetime.combine(optimization.start_date, datetime.min.time()),
                    to_date=datetime.combine(optimization.end_date, datetime.max.time()),
                )

                await broker.disconnect()

                if not historical_data:
                    optimization.status = "failed"
                    optimization.error_message = "No historical data available."
                    await db.commit()
                    return

                logger.info(f"Optimization {optimization_id}: Loaded {len(historical_data)} candles")

            except Exception as e:
                optimization.status = "failed"
                optimization.error_message = f"Failed to fetch historical data: {str(e)}"
                await db.commit()
                return

            # Get strategy configurable params to determine param types
            try:
                module = importlib.import_module(strategy_module)
                strategy_cls = getattr(module, strategy_class)
                configurable_params = strategy_cls.get_configurable_params()
                param_types = {p.name: p.param_type for p in configurable_params}
            except Exception:
                param_types = {}

            # Build parameter ranges
            parameter_ranges = []
            for name, range_config in optimization.parameter_ranges.items():
                param_type = param_types.get(name, "float")
                parameter_ranges.append(ParameterRange(
                    name=name,
                    min_value=range_config["min"],
                    max_value=range_config["max"],
                    step=range_config["step"],
                    param_type=param_type,
                ))

            # Create backtest config
            bt_config = BacktestConfig(
                strategy_module_path=strategy_module,
                strategy_class_name=strategy_class,
                symbol=optimization.symbol,
                exchange=optimization.exchange,
                interval=optimization.interval,
                start_date=optimization.start_date,
                end_date=optimization.end_date,
                initial_capital=optimization.initial_capital,
            )

            # Create optimization config
            opt_config = OptimizationConfig(
                backtest_config=bt_config,
                parameter_ranges=parameter_ranges,
                num_samples=optimization.num_samples,
                objective_metric=optimization.objective_metric,
            )

            # Progress callback
            async def update_progress(completed: int, total: int, message: str):
                optimization.progress = int((completed / total) * 100)
                optimization.completed_samples = completed
                await db.commit()

            # Run optimization
            optimizer = MonteCarloOptimizer()
            results = await optimizer.run(
                config=opt_config,
                historical_data=historical_data,
                on_progress=update_progress,
            )

            # Save results to database
            best_value = float('-inf')
            best_result_id = None

            for i, sample_result in enumerate(results):
                is_best = i == 0 and sample_result.error is None  # First result after sorting is best

                opt_result = OptimizationResult(
                    optimization_id=optimization.id,
                    parameters=sample_result.parameters,
                    total_return=Decimal(str(sample_result.metrics.get('total_return', 0))) if not sample_result.error else None,
                    total_return_percent=Decimal(str(sample_result.metrics.get('total_return_percent', 0))) if not sample_result.error else None,
                    sharpe_ratio=Decimal(str(sample_result.metrics.get('sharpe_ratio', 0))) if not sample_result.error else None,
                    sortino_ratio=Decimal(str(sample_result.metrics.get('sortino_ratio', 0))) if not sample_result.error else None,
                    max_drawdown=Decimal(str(sample_result.metrics.get('max_drawdown', 0))) if not sample_result.error else None,
                    win_rate=Decimal(str(sample_result.metrics.get('win_rate', 0))) if not sample_result.error else None,
                    profit_factor=Decimal(str(sample_result.metrics.get('profit_factor', 0))) if not sample_result.error else None,
                    calmar_ratio=Decimal(str(sample_result.metrics.get('calmar_ratio', 0))) if not sample_result.error else None,
                    total_trades=sample_result.trades_count,
                    full_metrics=sample_result.metrics if not sample_result.error else None,
                    is_best=is_best,
                )
                db.add(opt_result)

            # Update optimization status
            optimization.status = "completed"
            optimization.progress = 100
            optimization.completed_at = datetime.utcnow()
            await db.commit()

            logger.info(f"Optimization {optimization_id} completed with {len(results)} samples")

        except Exception as e:
            logger.exception(f"Optimization {optimization_id} failed")
            optimization.status = "failed"
            optimization.error_message = f"Unexpected error: {str(e)}"
            await db.commit()


# ==================== Get Optimization Details ====================


@router.get("/{optimization_id}", response_model=OptimizationResponse)
async def get_optimization(
    optimization_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full optimization details."""
    result = await db.execute(
        select(Optimization).where(
            Optimization.id == optimization_id,
            Optimization.user_id == current_user.id,
        )
    )
    optimization = result.scalar_one_or_none()

    if not optimization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Optimization not found",
        )

    return optimization


# ==================== Get Optimization Status ====================


@router.get("/{optimization_id}/status", response_model=OptimizationProgressResponse)
async def get_optimization_status(
    optimization_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current progress of an optimization."""
    result = await db.execute(
        select(Optimization).where(
            Optimization.id == optimization_id,
            Optimization.user_id == current_user.id,
        )
    )
    optimization = result.scalar_one_or_none()

    if not optimization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Optimization not found",
        )

    return OptimizationProgressResponse(
        id=optimization.id,
        status=OptimizationStatus(optimization.status),
        progress=optimization.progress,
        completed_samples=optimization.completed_samples,
        total_samples=optimization.num_samples,
        error_message=optimization.error_message,
    )


# ==================== Get Optimization Results ====================


@router.get("/{optimization_id}/results", response_model=OptimizationResultsResponse)
async def get_optimization_results(
    optimization_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all results from a completed optimization."""
    result = await db.execute(
        select(Optimization).where(
            Optimization.id == optimization_id,
            Optimization.user_id == current_user.id,
        )
    )
    optimization = result.scalar_one_or_none()

    if not optimization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Optimization not found",
        )

    # Get all results sorted by objective metric
    objective = optimization.objective_metric
    order_column = getattr(OptimizationResult, objective, OptimizationResult.total_return_percent)

    results_query = await db.execute(
        select(OptimizationResult)
        .where(OptimizationResult.optimization_id == optimization_id)
        .order_by(order_column.desc())
    )
    all_results = results_query.scalars().all()

    # Find best result
    best_result = None
    for r in all_results:
        if r.is_best:
            best_result = OptimizationResultItem.model_validate(r)
            break

    return OptimizationResultsResponse(
        optimization_id=optimization.id,
        status=OptimizationStatus(optimization.status),
        objective_metric=optimization.objective_metric,
        total_samples=len(all_results),
        best_result=best_result,
        all_results=[OptimizationResultItem.model_validate(r) for r in all_results],
    )


# ==================== Get Heatmap Data ====================


@router.get("/{optimization_id}/heatmap", response_model=HeatmapResponse)
async def get_heatmap_data(
    optimization_id: UUID,
    param_x: str = Query(..., description="Parameter for X axis"),
    param_y: str = Query(..., description="Parameter for Y axis"),
    metric: Optional[str] = Query(None, description="Metric to display"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get heatmap data for two parameters."""
    result = await db.execute(
        select(Optimization).where(
            Optimization.id == optimization_id,
            Optimization.user_id == current_user.id,
        )
    )
    optimization = result.scalar_one_or_none()

    if not optimization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Optimization not found",
        )

    # Use objective metric if not specified
    metric = metric or optimization.objective_metric

    # Validate parameters exist in ranges
    param_names = list(optimization.parameter_ranges.keys())
    if param_x not in param_names:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Parameter '{param_x}' not found in optimization",
        )
    if param_y not in param_names:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Parameter '{param_y}' not found in optimization",
        )
    if param_x == param_y:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="param_x and param_y must be different",
        )

    # Get all results
    results_query = await db.execute(
        select(OptimizationResult)
        .where(OptimizationResult.optimization_id == optimization_id)
    )
    all_results = results_query.scalars().all()

    # Group by (x, y) values and calculate averages
    from collections import defaultdict

    grouped = defaultdict(list)
    x_values = set()
    y_values = set()

    for r in all_results:
        x_val = r.parameters.get(param_x)
        y_val = r.parameters.get(param_y)
        metric_val = getattr(r, metric, None) or (r.full_metrics or {}).get(metric, 0)

        if x_val is not None and y_val is not None and metric_val is not None:
            grouped[(float(x_val), float(y_val))].append(float(metric_val))
            x_values.add(float(x_val))
            y_values.add(float(y_val))

    # Build data points
    data = []
    best_x, best_y, best_value = None, None, float('-inf')

    for (x, y), values in grouped.items():
        avg_value = sum(values) / len(values)
        data.append(HeatmapDataPoint(x=x, y=y, value=round(avg_value, 4)))
        if avg_value > best_value:
            best_x, best_y, best_value = x, y, avg_value

    return HeatmapResponse(
        param_x=param_x,
        param_y=param_y,
        x_values=sorted(x_values),
        y_values=sorted(y_values),
        data=data,
        best_x=best_x,
        best_y=best_y,
        best_value=round(best_value, 4) if best_value != float('-inf') else None,
        metric=metric,
    )


# ==================== Get Optimization History ====================


@router.get("/history", response_model=List[OptimizationListResponse])
async def get_optimization_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List past optimizations for current user."""
    query = (
        select(Optimization)
        .where(Optimization.user_id == current_user.id)
        .order_by(Optimization.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(query)
    optimizations = result.scalars().all()

    # Get best results for completed optimizations
    opt_ids = [o.id for o in optimizations if o.status == "completed"]
    best_results_map = {}

    if opt_ids:
        best_query = await db.execute(
            select(OptimizationResult)
            .where(
                OptimizationResult.optimization_id.in_(opt_ids),
                OptimizationResult.is_best == True,
            )
        )
        for r in best_query.scalars().all():
            best_results_map[r.optimization_id] = r

    # Build response
    response = []
    for opt in optimizations:
        best = best_results_map.get(opt.id)
        response.append(
            OptimizationListResponse(
                id=opt.id,
                strategy_id=opt.strategy_id,
                source_backtest_id=opt.source_backtest_id,
                status=OptimizationStatus(opt.status),
                symbol=opt.symbol,
                exchange=opt.exchange,
                interval=opt.interval,
                start_date=opt.start_date,
                end_date=opt.end_date,
                initial_capital=opt.initial_capital,
                num_samples=opt.num_samples,
                objective_metric=opt.objective_metric,
                progress=opt.progress,
                completed_samples=opt.completed_samples,
                created_at=opt.created_at,
                completed_at=opt.completed_at,
                best_return_percent=best.total_return_percent if best else None,
            )
        )

    return response


# ==================== Delete/Cancel Optimization ====================


@router.delete("/{optimization_id}")
async def delete_optimization(
    optimization_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a running optimization or delete a completed one."""
    result = await db.execute(
        select(Optimization).where(
            Optimization.id == optimization_id,
            Optimization.user_id == current_user.id,
        )
    )
    optimization = result.scalar_one_or_none()

    if not optimization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Optimization not found",
        )

    if optimization.status == "running":
        optimization.status = "cancelled"
        await db.commit()
        return {"message": "Optimization cancelled"}
    else:
        await db.delete(optimization)
        await db.commit()
        return {"message": "Optimization deleted"}


# ==================== Helper Functions ====================


def _get_broker_config(broker_name: str) -> dict:
    """Get broker configuration from settings."""
    config_mapping = {
        "fyers": {
            "app_id": settings.FYERS_APP_ID,
            "secret_key": settings.FYERS_SECRET_KEY,
            "redirect_uri": settings.FYERS_REDIRECT_URI,
        },
    }
    return config_mapping.get(broker_name, {})
