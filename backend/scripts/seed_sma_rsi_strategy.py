#!/usr/bin/env python3
"""
Seed script to register the SMA RSI Crossover strategy in the database.

Prerequisites:
    - Backend dependencies installed (pip install -r requirements.txt)
    - Database running and accessible
    - .env file configured with DATABASE_URL

Run from the backend directory:
    cd backend
    python scripts/seed_sma_rsi_strategy.py

Or with poetry:
    cd backend
    poetry run python scripts/seed_sma_rsi_strategy.py

Or with the virtual environment activated:
    cd backend
    .venv/Scripts/activate  (Windows)
    source .venv/bin/activate  (Linux/Mac)
    python scripts/seed_sma_rsi_strategy.py
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path for imports
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models import Strategy, StrategyVersion


async def seed_strategy():
    """Insert SMA RSI Crossover strategy into the database."""

    async with AsyncSessionLocal() as db:
        # Check if strategy already exists
        result = await db.execute(
            select(Strategy).where(Strategy.slug == "sma-rsi-crossover")
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"Strategy 'SMA RSI Crossover' already exists (ID: {existing.id})")
            print("Skipping creation.")
            return existing.id

        # Create new strategy
        strategy = Strategy(
            name="SMA RSI Crossover",
            slug="sma-rsi-crossover",
            description="Combines SMA crossover with RSI confirmation for filtered entries",
            long_description="""
This strategy combines two popular technical indicators for higher-quality trading signals:

**Indicators Used:**
- Simple Moving Average (SMA) crossover: Fast (9) and Slow (21) periods
- Relative Strength Index (RSI): 14-period with overbought level at 70

**Entry Rules (BUY):**
1. Fast MA crosses above Slow MA (bullish trend confirmation)
2. RSI is below 70 (not overbought, room to run)
3. No existing position in the symbol

**Exit Rules:**
1. Fast MA crosses below Slow MA (trend reversal), OR
2. RSI exceeds 70 (overbought, profit taking)

**Risk Management:**
- 2% stop loss per trade
- 4% take profit target
- Risk-based position sizing (2% of capital per trade)

**Best For:**
- Trending markets
- Swing trading on 15-minute to daily timeframes
- Stocks with good liquidity

**Note:** This strategy filters out false crossover signals by requiring RSI confirmation, reducing whipsaws in choppy markets.
            """.strip(),
            version="1.0.0",
            author="Platform",
            min_capital=10000,
            expected_return_percent=15.0,
            max_drawdown_percent=10.0,
            timeframe="15min",
            supported_symbols=[
                "NSE:NIFTY50-INDEX",
                "NSE:BANKNIFTY-INDEX",
                "NSE:RELIANCE",
                "NSE:TCS",
                "NSE:INFY",
                "NSE:HDFCBANK",
            ],
            tags=["momentum", "trend-following", "sma", "rsi", "crossover"],
            is_active=True,
            is_featured=False,
            module_path="strategies.implementations.sma_rsi_crossover",
            class_name="SMARSICrossover",
        )

        db.add(strategy)
        await db.flush()  # Get the ID

        # Create initial version
        version = StrategyVersion(
            strategy_id=strategy.id,
            version="1.0.0",
            changelog="Initial release of SMA RSI Crossover strategy",
            is_current=True,
        )
        db.add(version)

        await db.commit()

        print("=" * 60)
        print("Strategy registered successfully!")
        print("=" * 60)
        print(f"  ID:          {strategy.id}")
        print(f"  Name:        {strategy.name}")
        print(f"  Slug:        {strategy.slug}")
        print(f"  Module:      {strategy.module_path}")
        print(f"  Class:       {strategy.class_name}")
        print(f"  Timeframe:   {strategy.timeframe}")
        print(f"  Min Capital: {strategy.min_capital}")
        print("=" * 60)
        print()
        print("The strategy should now appear in:")
        print("  - Backtest strategy dropdown")
        print("  - Dashboard strategies page")
        print()

        return strategy.id


if __name__ == "__main__":
    asyncio.run(seed_strategy())
