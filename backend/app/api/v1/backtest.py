"""
Backtest API endpoints for running and managing backtests.
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID
import math

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models import User, Strategy, Backtest, BacktestResult, BacktestTrade, BacktestEquityCurve, BrokerConnection, StrategySubscription, Optimization, OptimizationResult
from app.schemas.backtest import (
    BacktestCreate,
    BacktestResponse,
    BacktestListResponse,
    BacktestProgressResponse,
    BacktestResultResponse,
    BacktestTradeResponse,
    BacktestTradeListResponse,
    BacktestChartData,
    CandleData,
    ChartMarker,
    EquityCurvePoint,
    IndicatorSeries,
    IndicatorDataPoint,
    BacktestStatus,
)
from pydantic import BaseModel, Field
from backtest.engine import BacktestEngine, BacktestConfig
from brokers.factory import BrokerFactory
from app.core.config import settings


router = APIRouter(prefix="/backtest", tags=["Backtest"])


# ==================== Run Backtest ====================


@router.post("/run", response_model=BacktestResponse, status_code=status.HTTP_201_CREATED)
async def run_backtest(
    data: BacktestCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Start a new backtest.

    Returns immediately with backtest ID. Execution happens asynchronously.
    """
    # Validate strategy exists
    result = await db.execute(
        select(Strategy).where(Strategy.id == data.strategy_id, Strategy.is_active == True)
    )
    strategy = result.scalar_one_or_none()

    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found or inactive",
        )

    # Validate date range
    if data.end_date <= data.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date must be after start date",
        )

    # Create backtest record
    backtest = Backtest(
        user_id=current_user.id,
        strategy_id=data.strategy_id,
        status="pending",
        symbol=data.symbol.upper(),
        exchange=data.exchange.upper(),
        interval=data.interval.value,
        start_date=data.start_date,
        end_date=data.end_date,
        initial_capital=data.initial_capital,
        config=data.config,
        progress=0,
    )
    db.add(backtest)
    await db.commit()
    await db.refresh(backtest)

    # Queue background task
    background_tasks.add_task(
        execute_backtest_task,
        backtest_id=str(backtest.id),
        strategy_module=strategy.module_path,
        strategy_class=strategy.class_name,
        user_id=str(current_user.id),
    )

    return backtest


async def execute_backtest_task(
    backtest_id: str,
    strategy_module: str,
    strategy_class: str,
    user_id: str,
):
    """Background task to execute backtest."""
    from app.core.database import AsyncSessionLocal
    import logging

    logger = logging.getLogger(__name__)

    async with AsyncSessionLocal() as db:
        try:
            logger.info(f"Starting backtest {backtest_id} with strategy {strategy_module}.{strategy_class}")
            # Get backtest record
            result = await db.execute(
                select(Backtest).where(Backtest.id == backtest_id)
            )
            backtest = result.scalar_one_or_none()

            if not backtest:
                return

            # Update status to running
            backtest.status = "running"
            backtest.started_at = datetime.utcnow()
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
                backtest.status = "failed"
                backtest.error_message = "No active broker connection found. Please connect a broker first."
                logger.error(f"Backtest {backtest_id} failed: No active broker connection for user {user_id}")
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

                # Get historical data
                historical_data = await broker.get_historical_data(
                    symbol=backtest.symbol,
                    exchange=backtest.exchange,
                    interval=backtest.interval,
                    from_date=datetime.combine(backtest.start_date, datetime.min.time()),
                    to_date=datetime.combine(backtest.end_date, datetime.max.time()),
                )

                await broker.disconnect()

                if not historical_data:
                    backtest.status = "failed"
                    backtest.error_message = f"No historical data available for {backtest.symbol} ({backtest.exchange}) from {backtest.start_date} to {backtest.end_date}"
                    logger.error(f"Backtest {backtest_id} failed: No historical data for {backtest.exchange}:{backtest.symbol}")
                    await db.commit()
                    return

                logger.info(f"Backtest {backtest_id}: Loaded {len(historical_data)} candles")

            except Exception as e:
                backtest.status = "failed"
                backtest.error_message = f"Failed to fetch historical data: {str(e)}"
                logger.exception(f"Backtest {backtest_id} failed to fetch historical data")
                await db.commit()
                return

            # Run backtest engine
            engine = BacktestEngine()
            bt_config = BacktestConfig(
                strategy_module_path=strategy_module,
                strategy_class_name=strategy_class,
                symbol=backtest.symbol,
                exchange=backtest.exchange,
                interval=backtest.interval,
                start_date=backtest.start_date,
                end_date=backtest.end_date,
                initial_capital=backtest.initial_capital,
                strategy_config=backtest.config or {},
            )

            # Progress callback to update database
            async def update_progress(progress: int, message: str):
                backtest.progress = progress
                await db.commit()

            bt_result = await engine.run(
                config=bt_config,
                historical_data=historical_data,
                on_progress=update_progress,
            )

            if bt_result.error:
                backtest.status = "failed"
                backtest.error_message = bt_result.error
                await db.commit()
                return

            # Save results
            backtest_result = BacktestResult(
                backtest_id=backtest.id,
                total_return=bt_result.metrics.total_return,
                total_return_percent=bt_result.metrics.total_return_percent,
                cagr=bt_result.metrics.cagr,
                sharpe_ratio=bt_result.metrics.sharpe_ratio,
                sortino_ratio=bt_result.metrics.sortino_ratio,
                calmar_ratio=bt_result.metrics.calmar_ratio,
                max_drawdown=bt_result.metrics.max_drawdown,
                avg_drawdown=bt_result.metrics.avg_drawdown,
                win_rate=bt_result.metrics.win_rate,
                profit_factor=bt_result.metrics.profit_factor,
                total_trades=bt_result.metrics.total_trades,
                winning_trades=bt_result.metrics.winning_trades,
                losing_trades=bt_result.metrics.losing_trades,
                avg_trade_duration=bt_result.metrics.avg_trade_duration,
                final_capital=bt_result.metrics.final_capital,
                max_capital=bt_result.metrics.max_capital,
            )
            db.add(backtest_result)

            # Save trades
            for trade in bt_result.trades:
                bt_trade = BacktestTrade(
                    backtest_id=backtest.id,
                    signal="BUY",  # Entry signal
                    entry_price=trade.entry_price,
                    exit_price=trade.exit_price,
                    quantity=trade.quantity,
                    entry_time=trade.entry_time,
                    exit_time=trade.exit_time,
                    pnl=trade.pnl,
                    pnl_percent=trade.pnl_percent,
                    is_open=False,
                )
                db.add(bt_trade)

            # Save equity curve (sample every N points to avoid too much data)
            max_equity_points = 500
            equity_len = len(bt_result.equity_curve)
            step = max(1, equity_len // max_equity_points)

            for i in range(0, equity_len, step):
                timestamp, equity = bt_result.equity_curve[i]
                peak = max(eq for _, eq in bt_result.equity_curve[: i + 1])
                drawdown = ((peak - equity) / peak * 100) if peak > 0 else Decimal("0")

                eq_point = BacktestEquityCurve(
                    backtest_id=backtest.id,
                    timestamp=timestamp,
                    equity=equity,
                    drawdown=drawdown,
                )
                db.add(eq_point)

            # Update backtest status
            backtest.status = "completed"
            backtest.progress = 100
            backtest.completed_at = datetime.utcnow()
            await db.commit()

        except Exception as e:
            logger.exception(f"Backtest {backtest_id} failed with unexpected error")
            backtest.status = "failed"
            backtest.error_message = f"Unexpected error: {str(e)}"
            await db.commit()


# ==================== Get Backtest Status ====================


@router.get("/{backtest_id}/status", response_model=BacktestProgressResponse)
async def get_backtest_status(
    backtest_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current progress of a backtest."""
    result = await db.execute(
        select(Backtest).where(
            Backtest.id == backtest_id,
            Backtest.user_id == current_user.id,
        )
    )
    backtest = result.scalar_one_or_none()

    if not backtest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest not found",
        )

    return BacktestProgressResponse(
        id=backtest.id,
        status=BacktestStatus(backtest.status),
        progress=backtest.progress,
        error_message=backtest.error_message,
        started_at=backtest.started_at,
        completed_at=backtest.completed_at,
    )


# ==================== Get Backtest Results ====================


@router.get("/{backtest_id}/results", response_model=BacktestResultResponse)
async def get_backtest_results(
    backtest_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get results of a completed backtest."""
    # Get backtest
    result = await db.execute(
        select(Backtest).where(
            Backtest.id == backtest_id,
            Backtest.user_id == current_user.id,
        )
    )
    backtest = result.scalar_one_or_none()

    if not backtest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest not found",
        )

    if backtest.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Backtest is not completed. Status: {backtest.status}",
        )

    # Get results
    result = await db.execute(
        select(BacktestResult).where(BacktestResult.backtest_id == backtest_id)
    )
    bt_result = result.scalar_one_or_none()

    if not bt_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest results not found",
        )

    return bt_result


# ==================== Get Backtest Trades ====================


@router.get("/{backtest_id}/trades", response_model=BacktestTradeListResponse)
async def get_backtest_trades(
    backtest_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated list of trades from a backtest."""
    # Verify backtest belongs to user
    result = await db.execute(
        select(Backtest).where(
            Backtest.id == backtest_id,
            Backtest.user_id == current_user.id,
        )
    )
    backtest = result.scalar_one_or_none()

    if not backtest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest not found",
        )

    # Get total count
    count_result = await db.execute(
        select(func.count(BacktestTrade.id)).where(
            BacktestTrade.backtest_id == backtest_id
        )
    )
    total = count_result.scalar()

    # Get trades with pagination
    offset = (page - 1) * page_size
    result = await db.execute(
        select(BacktestTrade)
        .where(BacktestTrade.backtest_id == backtest_id)
        .order_by(BacktestTrade.entry_time)
        .offset(offset)
        .limit(page_size)
    )
    trades = result.scalars().all()

    return BacktestTradeListResponse(
        trades=[BacktestTradeResponse.from_orm(t) for t in trades],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


# ==================== Helper Functions for Indicators ====================


def _calculate_sma(prices: List[float], period: int) -> Optional[float]:
    """Calculate Simple Moving Average."""
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period


def _calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
    """Calculate Relative Strength Index."""
    if len(prices) < period + 1:
        return None

    gains = []
    losses = []

    for i in range(1, len(prices)):
        change = prices[i] - prices[i - 1]
        if change > 0:
            gains.append(change)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(abs(change))

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi


def _calculate_macd(prices: List[float], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
    """Calculate MACD, Signal, and Histogram."""
    if len(prices) < slow_period + signal_period:
        return None, None, None

    # Calculate EMAs
    def ema(data: List[float], period: int) -> List[float]:
        multiplier = 2 / (period + 1)
        ema_values = [sum(data[:period]) / period]  # Start with SMA
        for price in data[period:]:
            ema_values.append((price - ema_values[-1]) * multiplier + ema_values[-1])
        return ema_values

    fast_ema = ema(prices, fast_period)
    slow_ema = ema(prices, slow_period)

    # Align arrays
    offset = fast_period - slow_period
    if offset < 0:
        fast_ema = [0] * abs(offset) + fast_ema
    elif offset > 0:
        slow_ema = [0] * offset + slow_ema

    # Calculate MACD line
    macd_line = [f - s for f, s in zip(fast_ema, slow_ema)]

    # Calculate signal line
    signal_line = ema(macd_line[-len(macd_line):], signal_period) if len(macd_line) >= signal_period else []

    # Calculate histogram
    histogram = []
    if signal_line:
        for i in range(len(signal_line)):
            idx = len(macd_line) - len(signal_line) + i
            histogram.append(macd_line[idx] - signal_line[i])

    return macd_line[-1] if macd_line else None, signal_line[-1] if signal_line else None, histogram[-1] if histogram else None


def _calculate_indicators_for_strategy(
    strategy_class_name: str,
    candles: List[dict],
    config: Optional[dict] = None,
) -> List[IndicatorSeries]:
    """Calculate indicators based on strategy type."""
    indicators = []

    if not candles:
        return indicators

    # Extract close prices and timestamps
    closes = [float(c.get("close", 0)) for c in candles]
    timestamps = [int(c.get("timestamp").timestamp()) if isinstance(c.get("timestamp"), datetime) else int(datetime.now().timestamp()) for c in candles]

    # Strategy-specific indicator calculations
    if "SMARSICrossover" in strategy_class_name or "SMA" in strategy_class_name and "RSI" in strategy_class_name:
        # SMA + RSI Crossover Strategy
        fast_period = config.get("fast_ma_period", 9) if config else 9
        slow_period = config.get("slow_ma_period", 21) if config else 21
        rsi_period = config.get("rsi_period", 14) if config else 14

        # Calculate Fast SMA
        fast_sma_data = []
        for i in range(len(closes)):
            fast_sma = _calculate_sma(closes[: i + 1], fast_period)
            fast_sma_data.append(IndicatorDataPoint(time=timestamps[i], value=fast_sma))

        indicators.append(
            IndicatorSeries(
                name=f"Fast SMA ({fast_period})",
                data=fast_sma_data,
                type="line",
                pane="main",
                color="#3B82F6",  # Blue
            )
        )

        # Calculate Slow SMA
        slow_sma_data = []
        for i in range(len(closes)):
            slow_sma = _calculate_sma(closes[: i + 1], slow_period)
            slow_sma_data.append(IndicatorDataPoint(time=timestamps[i], value=slow_sma))

        indicators.append(
            IndicatorSeries(
                name=f"Slow SMA ({slow_period})",
                data=slow_sma_data,
                type="line",
                pane="main",
                color="#F59E0B",  # Orange
            )
        )

        # Calculate RSI
        rsi_data = []
        for i in range(len(closes)):
            rsi = _calculate_rsi(closes[: i + 1], rsi_period)
            rsi_data.append(IndicatorDataPoint(time=timestamps[i], value=rsi))

        indicators.append(
            IndicatorSeries(
                name=f"RSI ({rsi_period})",
                data=rsi_data,
                type="line",
                pane="rsi",
                color="#8B5CF6",  # Purple
            )
        )

    elif "SimpleMovingAverageCrossover" in strategy_class_name or ("MA" in strategy_class_name and "Crossover" in strategy_class_name):
        # Simple MA Crossover Strategy
        fast_period = config.get("fast_period", 9) if config else 9
        slow_period = config.get("slow_period", 21) if config else 21

        # Calculate Fast SMA
        fast_sma_data = []
        for i in range(len(closes)):
            fast_sma = _calculate_sma(closes[: i + 1], fast_period)
            fast_sma_data.append(IndicatorDataPoint(time=timestamps[i], value=fast_sma))

        indicators.append(
            IndicatorSeries(
                name=f"Fast SMA ({fast_period})",
                data=fast_sma_data,
                type="line",
                pane="main",
                color="#3B82F6",
            )
        )

        # Calculate Slow SMA
        slow_sma_data = []
        for i in range(len(closes)):
            slow_sma = _calculate_sma(closes[: i + 1], slow_period)
            slow_sma_data.append(IndicatorDataPoint(time=timestamps[i], value=slow_sma))

        indicators.append(
            IndicatorSeries(
                name=f"Slow SMA ({slow_period})",
                data=slow_sma_data,
                type="line",
                pane="main",
                color="#F59E0B",
            )
        )

    elif "RSIMomentum" in strategy_class_name or "RSI" in strategy_class_name:
        # RSI Momentum Strategy
        rsi_period = config.get("rsi_period", 14) if config else 14

        # Calculate RSI
        rsi_data = []
        for i in range(len(closes)):
            rsi = _calculate_rsi(closes[: i + 1], rsi_period)
            rsi_data.append(IndicatorDataPoint(time=timestamps[i], value=rsi))

        indicators.append(
            IndicatorSeries(
                name=f"RSI ({rsi_period})",
                data=rsi_data,
                type="line",
                pane="rsi",
                color="#8B5CF6",
            )
        )

    # Add MACD if strategy name contains "MACD"
    if "MACD" in strategy_class_name:
        fast_period = config.get("macd_fast", 12) if config else 12
        slow_period = config.get("macd_slow", 26) if config else 26
        signal_period = config.get("macd_signal", 9) if config else 9

        macd_data = []
        signal_data = []
        histogram_data = []

        for i in range(len(closes)):
            macd, signal, hist = _calculate_macd(closes[: i + 1], fast_period, slow_period, signal_period)
            macd_data.append(IndicatorDataPoint(time=timestamps[i], value=macd))
            signal_data.append(IndicatorDataPoint(time=timestamps[i], value=signal))
            histogram_data.append(IndicatorDataPoint(time=timestamps[i], value=hist))

        indicators.append(
            IndicatorSeries(
                name="MACD",
                data=macd_data,
                type="line",
                pane="macd",
                color="#3B82F6",
                signal_line=signal_data,
                histogram=histogram_data,
            )
        )

    return indicators


# ==================== Get Chart Data ====================


@router.get("/{backtest_id}/chart-data", response_model=BacktestChartData)
async def get_chart_data(
    backtest_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get OHLC data with trade markers and strategy indicators for chart."""
    # Verify backtest belongs to user
    result = await db.execute(
        select(Backtest).where(
            Backtest.id == backtest_id,
            Backtest.user_id == current_user.id,
        )
    )
    backtest = result.scalar_one_or_none()

    if not backtest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest not found",
        )

    # Get broker connection for historical data
    broker_result = await db.execute(
        select(BrokerConnection).where(
            BrokerConnection.user_id == current_user.id,
            BrokerConnection.is_active == True,
        )
    )
    connection = broker_result.scalar_one_or_none()

    candles = []
    if connection:
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
                symbol=backtest.symbol,
                exchange=backtest.exchange,
                interval=backtest.interval,
                from_date=datetime.combine(backtest.start_date, datetime.min.time()),
                to_date=datetime.combine(backtest.end_date, datetime.max.time()),
            )
            await broker.disconnect()

            for candle in historical_data:
                ts = candle.get("timestamp")
                if isinstance(ts, datetime):
                    unix_ts = int(ts.timestamp())
                else:
                    unix_ts = int(datetime.now().timestamp())

                candles.append(
                    CandleData(
                        time=unix_ts,
                        open=float(candle.get("open", 0)),
                        high=float(candle.get("high", 0)),
                        low=float(candle.get("low", 0)),
                        close=float(candle.get("close", 0)),
                        volume=int(candle.get("volume", 0)),
                    )
                )
        except Exception:
            pass

    # Get trades for markers
    trades_result = await db.execute(
        select(BacktestTrade)
        .where(BacktestTrade.backtest_id == backtest_id)
        .order_by(BacktestTrade.entry_time)
    )
    trades = trades_result.scalars().all()

    markers = []
    for trade in trades:
        # Entry marker (buy)
        markers.append(
            ChartMarker(
                time=int(trade.entry_time.timestamp()),
                position="belowBar",
                color="#10B981",  # Green
                shape="arrowUp",
                text=f"BUY @ {float(trade.entry_price):.2f}",
            )
        )

        # Exit marker (sell)
        if trade.exit_time and trade.exit_price:
            color = "#10B981" if trade.pnl and trade.pnl > 0 else "#EF4444"
            markers.append(
                ChartMarker(
                    time=int(trade.exit_time.timestamp()),
                    position="aboveBar",
                    color=color,
                    shape="arrowDown",
                    text=f"SELL @ {float(trade.exit_price):.2f}",
                )
            )

    # Get equity curve
    equity_result = await db.execute(
        select(BacktestEquityCurve)
        .where(BacktestEquityCurve.backtest_id == backtest_id)
        .order_by(BacktestEquityCurve.timestamp)
    )
    equity_points = equity_result.scalars().all()

    equity_curve = [
        EquityCurvePoint(
            time=int(point.timestamp.timestamp()),
            value=float(point.equity),
        )
        for point in equity_points
    ]

    # Get strategy information to calculate indicators
    strategy_result = await db.execute(
        select(Strategy).where(Strategy.id == backtest.strategy_id)
    )
    strategy = strategy_result.scalar_one_or_none()

    indicators = []
    if strategy and historical_data:
        # Calculate indicators based on strategy class
        indicators = _calculate_indicators_for_strategy(
            strategy_class_name=strategy.class_name,
            candles=historical_data,
            config=backtest.config,
        )

    return BacktestChartData(
        candles=candles,
        markers=markers,
        equity_curve=equity_curve,
        indicators=indicators,
    )


# ==================== Get Backtest History ====================


@router.get("/history", response_model=List[BacktestListResponse])
async def get_backtest_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    strategy_id: Optional[UUID] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List past backtests for current user."""
    query = select(Backtest).where(Backtest.user_id == current_user.id)

    if strategy_id:
        query = query.where(Backtest.strategy_id == strategy_id)

    if status_filter:
        query = query.where(Backtest.status == status_filter)

    query = query.order_by(Backtest.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    backtests = result.scalars().all()

    # Get results for completed backtests
    backtest_ids = [bt.id for bt in backtests if bt.status == "completed"]
    results_map = {}

    if backtest_ids:
        results = await db.execute(
            select(BacktestResult).where(BacktestResult.backtest_id.in_(backtest_ids))
        )
        for r in results.scalars().all():
            results_map[r.backtest_id] = r

    # Build response
    response = []
    for bt in backtests:
        bt_result = results_map.get(bt.id)
        response.append(
            BacktestListResponse(
                id=bt.id,
                strategy_id=bt.strategy_id,
                status=BacktestStatus(bt.status),
                symbol=bt.symbol,
                exchange=bt.exchange,
                interval=bt.interval,
                start_date=bt.start_date,
                end_date=bt.end_date,
                initial_capital=bt.initial_capital,
                progress=bt.progress,
                created_at=bt.created_at,
                completed_at=bt.completed_at,
                total_return_percent=bt_result.total_return_percent if bt_result else None,
                total_trades=bt_result.total_trades if bt_result else None,
                error_message=bt.error_message if bt.status == "failed" else None,
            )
        )

    return response


# ==================== Get Backtest Details ====================


@router.get("/{backtest_id}", response_model=BacktestResponse)
async def get_backtest(
    backtest_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full backtest details."""
    result = await db.execute(
        select(Backtest).where(
            Backtest.id == backtest_id,
            Backtest.user_id == current_user.id,
        )
    )
    backtest = result.scalar_one_or_none()

    if not backtest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest not found",
        )

    return backtest


# ==================== Delete/Cancel Backtest ====================


@router.delete("/{backtest_id}")
async def delete_backtest(
    backtest_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a running backtest or delete a completed one."""
    result = await db.execute(
        select(Backtest).where(
            Backtest.id == backtest_id,
            Backtest.user_id == current_user.id,
        )
    )
    backtest = result.scalar_one_or_none()

    if not backtest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest not found",
        )

    if backtest.status == "running":
        backtest.status = "cancelled"
        await db.commit()
        return {"message": "Backtest cancelled"}
    else:
        await db.delete(backtest)
        await db.commit()
        return {"message": "Backtest deleted"}


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


# ==================== Subscribe from Backtest ====================


class SubscribeFromBacktestRequest(BaseModel):
    """Request body for subscribing from a backtest."""
    capital_allocated: Decimal = Field(..., ge=10000)
    broker_connection_id: Optional[UUID] = None
    is_paper_trading: bool = True
    max_drawdown_percent: Decimal = Field(default=10, ge=1, le=50)
    daily_loss_limit: Optional[Decimal] = None
    per_trade_stop_loss_percent: Decimal = Field(default=2, ge=0.5, le=10)
    max_positions: int = Field(default=5, ge=1, le=20)


@router.post("/{backtest_id}/subscribe")
async def subscribe_from_backtest(
    backtest_id: UUID,
    request: SubscribeFromBacktestRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a strategy subscription from a completed backtest.

    This endpoint allows users to go live with a strategy after backtesting.
    If optimization was performed, it will use the best optimized parameters.
    Otherwise, it will use the default parameters from the backtest config.
    """
    # Get backtest
    result = await db.execute(
        select(Backtest).where(
            Backtest.id == backtest_id,
            Backtest.user_id == current_user.id,
        )
    )
    backtest = result.scalar_one_or_none()

    if not backtest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest not found",
        )

    if backtest.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only subscribe from completed backtests",
        )

    # Get strategy
    strategy_result = await db.execute(
        select(Strategy).where(Strategy.id == backtest.strategy_id, Strategy.is_active == True)
    )
    strategy = strategy_result.scalar_one_or_none()

    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found",
        )

    # Check if already subscribed to this strategy
    existing_sub = await db.execute(
        select(StrategySubscription).where(
            StrategySubscription.user_id == current_user.id,
            StrategySubscription.strategy_id == backtest.strategy_id,
        )
    )
    if existing_sub.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already subscribed to this strategy. Please unsubscribe first.",
        )

    # Check minimum capital
    if request.capital_allocated < strategy.min_capital:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Minimum capital required is {strategy.min_capital}",
        )

    # Look for optimization results for this backtest
    optimization_result = await db.execute(
        select(Optimization).where(
            Optimization.source_backtest_id == backtest_id,
            Optimization.user_id == current_user.id,
            Optimization.status == "completed",
        ).order_by(Optimization.created_at.desc())
    )
    optimization = optimization_result.scalars().first()

    # Get config parameters - use optimized if available, otherwise use backtest config
    config_params = {}
    if optimization:
        # Get best optimization result
        best_result = await db.execute(
            select(OptimizationResult).where(
                OptimizationResult.optimization_id == optimization.id,
                OptimizationResult.is_best == True,
            )
        )
        best = best_result.scalar_one_or_none()
        if best and best.parameters:
            config_params = best.parameters

    # Fall back to backtest config if no optimization
    if not config_params and backtest.config:
        config_params = backtest.config

    # Verify broker connection if not paper trading
    if not request.is_paper_trading and request.broker_connection_id:
        broker_conn_result = await db.execute(
            select(BrokerConnection).where(
                BrokerConnection.id == request.broker_connection_id,
                BrokerConnection.user_id == current_user.id,
                BrokerConnection.is_active == True,
            )
        )
        if not broker_conn_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Broker connection not found or inactive",
            )

    # Create subscription
    subscription = StrategySubscription(
        user_id=current_user.id,
        strategy_id=strategy.id,
        broker_connection_id=request.broker_connection_id,
        capital_allocated=request.capital_allocated,
        is_paper_trading=request.is_paper_trading,
        max_drawdown_percent=request.max_drawdown_percent,
        daily_loss_limit=request.daily_loss_limit,
        per_trade_stop_loss_percent=request.per_trade_stop_loss_percent,
        max_positions=request.max_positions,
        config_params=config_params,
        selected_symbols=[backtest.symbol],  # Use the symbol from backtest
        status="inactive",  # Will be activated by user
    )

    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)

    return {
        "message": "Successfully created subscription from backtest",
        "subscription_id": str(subscription.id),
        "used_optimization": optimization is not None,
        "config_params": config_params,
    }
