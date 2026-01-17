# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AlgoTrading is a full-stack algorithmic trading platform for Indian retail traders. It enables users to subscribe to trading strategies, connect broker accounts (Fyers), and run automated trading with risk management.

**Stack**: FastAPI (Python 3.11+) backend, Next.js 14 (TypeScript) frontend, PostgreSQL 15, Redis 7

## Common Commands

### Backend (from `backend/` directory)
```bash
# Setup (using uv - https://docs.astral.sh/uv/)
uv sync                                       # Install all dependencies
uv sync --dev                                 # Install with dev dependencies

# Run server
uv run uvicorn app.main:app --reload --port 8000

# Database migrations
uv run alembic upgrade head                   # Apply migrations
uv run alembic revision --autogenerate -m "message"  # Create migration

# Tests
uv run pytest                                 # All tests
uv run pytest tests/test_api/                 # API tests only
uv run pytest tests/test_brokers/             # Broker tests only
uv run pytest --cov                           # With coverage

# Code quality
uv run black .                                # Format
uv run isort .                                # Sort imports
uv run flake8 .                               # Lint
uv run mypy .                                 # Type check
uv run ruff check .                           # Fast linting with ruff

# Dependency management
uv add <package>                              # Add a dependency
uv add --dev <package>                        # Add a dev dependency
uv lock                                       # Update lock file
uv pip compile pyproject.toml -o requirements.txt  # Generate requirements.txt (if needed)
```

### Frontend (from `frontend/` directory)
```bash
npm install                                   # Install deps
npm run dev                                   # Dev server (port 3000)
npm run build                                 # Production build
npm run lint                                  # ESLint
npm run type-check                            # TypeScript check
```

### Docker
```bash
docker-compose -f docker-compose.dev.yml up -d    # Dev (PostgreSQL, Redis, Adminer)
docker-compose up -d                              # Full stack
```

## Architecture

### Backend Structure (`backend/`)

```
app/
├── main.py                 # FastAPI entry, middleware setup
├── core/                   # Config, database, security (JWT)
├── api/
│   ├── v1/                 # REST endpoints (auth, strategies, portfolio, broker, backtest)
│   ├── websocket/          # WebSocket handlers (portfolio, market_data)
│   └── deps.py             # Dependency injection (get_current_user, get_db)
├── models/                 # SQLAlchemy async models
├── schemas/                # Pydantic request/response schemas
└── services/               # Business logic (notifications, reports)

brokers/
├── base.py                 # BaseBroker abstract class
├── factory.py              # BrokerFactory pattern
├── paper.py                # Paper trading simulator
└── plugins/fyers/          # Fyers broker plugin (OAuth, orders, market data)

strategies/
├── base.py                 # BaseStrategy with StrategyContext
└── implementations/        # Strategy implementations (sma_rsi_crossover, ma_crossover)

execution_engine/
├── engine.py               # Main execution orchestrator
├── strategy_runner.py      # Strategy execution context
├── risk_manager.py         # Drawdown, daily loss, position limits
└── kill_switch.py          # Emergency shutdown (global/user/strategy scope)

backtest/
├── engine.py               # Backtest orchestrator
├── simulator.py            # Market simulator
└── metrics.py              # Performance metrics
```

### Frontend Structure (`frontend/src/`)

```
app/
├── (auth)/                 # Login, register pages
├── (dashboard)/dashboard/  # Protected pages (strategies, portfolio, broker, backtest)
└── admin/                  # Admin pages

lib/api.ts                  # Axios client with JWT interceptors (auto-refresh on 401)
stores/                     # Zustand state management
hooks/                      # Custom React hooks
types/                      # TypeScript type definitions
```

### Key Patterns

**API Authentication**: JWT tokens stored in localStorage. Frontend Axios interceptor auto-injects `Authorization: Bearer` header and refreshes tokens on 401.

**Broker Plugin System**: Brokers implement `BaseBroker` abstract class and are loaded from `brokers/plugins/`. Each has a `plugin.json` with capabilities and auth config.

**Strategy System**: Strategies extend `BaseStrategy` and implement `on_market_data(data: MarketData) -> Optional[Order]`. Context provides capital, positions, P&L. Other lifecycle methods: `on_start`, `on_stop`, `on_order_filled`, `on_risk_limit_hit`.

**Real-time Updates**: WebSocket endpoints at `/ws/portfolio` and `/ws/market` (JWT via query param).

**Risk Management**: Per-subscription limits (max_drawdown_percent, daily_loss_limit, per_trade_sl_percent, max_positions). Kill switch has global, user, and strategy scopes.

### Database

- **Async SQLAlchemy** with asyncpg driver
- Key models: User, BrokerConnection, Strategy, StrategySubscription, Order, Trade, Backtest
- Migrations in `backend/alembic/versions/`

### API Endpoints

- **Auth**: `/api/v1/auth/*` (register, login, refresh, Google OAuth)
- **Strategies**: `/api/v1/strategies/*` (list, subscribe, start/stop/pause)
- **Portfolio**: `/api/v1/portfolio/*` (summary, positions, orders, trades)
- **Broker**: `/api/v1/broker/{name}/*` (connect, status, disconnect)
- **Backtest**: `/api/v1/backtest/*` (run, status, results)
- **Admin**: `/api/v1/admin/*` (strategies CRUD, users, kill switch)
- **Docs**: `/docs` (Swagger UI, debug mode only)

## Creating a New Strategy

```python
from strategies.base import BaseStrategy, MarketData, Order, Signal, OrderType

class MyStrategy(BaseStrategy):
    name = "My Strategy"
    description = "Description"
    min_capital = 10000
    supported_symbols = ["NSE:RELIANCE"]
    timeframe = "5min"

    def on_market_data(self, data: MarketData) -> Optional[Order]:
        # Trading logic - return Order or None
        pass
```

## Environment Setup

Copy `.env.example` to `.env`. Key variables:
- `SECRET_KEY` - JWT signing (32+ chars)
- `DATABASE_URL` - PostgreSQL async connection string
- `REDIS_URL` - Redis connection
- `FYERS_APP_ID`, `FYERS_SECRET_KEY` - Broker credentials
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` - OAuth credentials
