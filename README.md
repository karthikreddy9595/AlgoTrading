# AlgoTrading Platform

A full-stack algorithmic trading platform for Indian retail traders and HNIs.

## Features

- **Strategy Marketplace**: Browse and subscribe to professionally curated trading strategies
- **Paper & Live Trading**: Toggle between simulated and real-money trading
- **Risk Management**: Built-in safeguards including stop-loss, max drawdown limits, and kill switch
- **Multi-Broker Support**: Integrates with Fyers, Zerodha, Angel One, and more
- **Real-time Dashboard**: Live P&L, positions, and trade history
- **Secure Authentication**: JWT + Google OAuth support

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, Zustand |
| Backend | Python 3.11+, FastAPI, SQLAlchemy, Pydantic |
| Database | PostgreSQL 15, Redis 7 |
| Auth | JWT, OAuth 2.0 (Google), Argon2 |
| Broker | Fyers API v3 (primary) |
| Containerization | Docker, Docker Compose |

## Project Structure

```
algotrading/
├── backend/
│   ├── app/                    # FastAPI application
│   │   ├── api/v1/            # API endpoints
│   │   ├── core/              # Config, security, database
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas
│   │   └── services/          # Business logic
│   ├── brokers/               # Broker integrations
│   ├── execution_engine/      # Strategy execution
│   └── strategies/            # Trading strategies
├── frontend/
│   ├── src/
│   │   ├── app/               # Next.js pages
│   │   ├── components/        # React components
│   │   ├── hooks/             # Custom hooks
│   │   ├── lib/               # Utilities & API client
│   │   ├── stores/            # Zustand stores
│   │   └── types/             # TypeScript types
└── docker-compose.yml
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 20+ (for frontend development)
- Python 3.11+ (for backend development)

### 1. Clone and Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd AlgoTrading

# Copy environment file
cp .env.example .env

# Edit .env with your configuration
# At minimum, change SECRET_KEY to a secure random string
```

### 2. Start with Docker (Recommended)

```bash
# Start all services (PostgreSQL, Redis, Backend, Frontend)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

Access the application:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### 3. Development Setup (Without Docker)

#### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL and Redis (using Docker)
docker-compose -f ../docker-compose.dev.yml up -d

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | JWT signing key (change in production!) | - |
| `DATABASE_URL` | PostgreSQL connection string | postgresql+asyncpg://... |
| `REDIS_URL` | Redis connection string | redis://localhost:6379/0 |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | - |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret | - |
| `FYERS_APP_ID` | Fyers API app ID | - |
| `FYERS_SECRET_KEY` | Fyers API secret key | - |

### Broker Setup (Fyers)

1. Create a Fyers developer account at https://myapi.fyers.in/
2. Create a new app and get your App ID and Secret Key
3. Add credentials to `.env`:
   ```
   FYERS_APP_ID=your-app-id
   FYERS_SECRET_KEY=your-secret-key
   ```

### Google OAuth Setup

1. Go to Google Cloud Console
2. Create OAuth 2.0 credentials
3. Add `http://localhost:8000/api/v1/auth/google/callback` as authorized redirect URI
4. Add credentials to `.env`:
   ```
   GOOGLE_CLIENT_ID=your-client-id
   GOOGLE_CLIENT_SECRET=your-client-secret
   ```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login with email/password
- `POST /api/v1/auth/refresh` - Refresh access token
- `GET /api/v1/auth/google/login` - Initiate Google OAuth

### Users
- `GET /api/v1/users/me` - Get current user profile
- `PATCH /api/v1/users/me` - Update profile
- `GET /api/v1/users/me/broker-connections` - List broker connections

### Strategies
- `GET /api/v1/strategies` - List available strategies
- `GET /api/v1/strategies/{id}` - Get strategy details
- `POST /api/v1/strategies/subscribe` - Subscribe to a strategy
- `POST /api/v1/strategies/subscriptions/{id}/action` - Start/stop/pause strategy

### Portfolio
- `GET /api/v1/portfolio/summary` - Portfolio overview
- `GET /api/v1/portfolio/positions` - Open positions
- `GET /api/v1/portfolio/trades` - Trade history

### Broker (Fyers)
- `GET /api/v1/broker/fyers/auth-url` - Get Fyers OAuth URL
- `GET /api/v1/broker/fyers/callback` - Handle OAuth callback
- `GET /api/v1/broker/fyers/status` - Check connection status

### Notifications
- `GET /api/v1/notifications` - Get user notifications
- `GET /api/v1/notifications/unread-count` - Get unread count
- `POST /api/v1/notifications/{id}/read` - Mark as read
- `GET /api/v1/notifications/preferences` - Get preferences
- `PUT /api/v1/notifications/preferences` - Update preferences

### Reports
- `GET /api/v1/reports/trades/csv` - Download trades CSV
- `GET /api/v1/reports/orders/csv` - Download orders CSV
- `GET /api/v1/reports/portfolio/summary` - Portfolio summary
- `GET /api/v1/reports/portfolio/pdf` - Download portfolio PDF
- `GET /api/v1/reports/performance` - Performance report

### WebSocket
- `WS /ws/portfolio?token=<jwt>` - Real-time portfolio updates
- `WS /ws/market?token=<jwt>` - Real-time market data

### Admin
- `GET /api/v1/admin/monitoring/dashboard` - Monitoring dashboard
- `POST /api/v1/admin/monitoring/kill-switch/activate` - Activate kill switch
- `POST /api/v1/admin/monitoring/kill-switch/deactivate` - Deactivate kill switch
- `GET /api/v1/admin/strategies` - List all strategies
- `POST /api/v1/admin/strategies` - Create strategy
- `GET /api/v1/admin/users` - List users

## Creating a Strategy

All strategies inherit from `BaseStrategy`:

```python
from strategies.base import BaseStrategy, MarketData, Order, Signal

class MyStrategy(BaseStrategy):
    name = "My Custom Strategy"
    description = "Description of my strategy"
    min_capital = 10000
    supported_symbols = ["NSE:RELIANCE", "NSE:TCS"]
    timeframe = "5min"

    def on_market_data(self, data: MarketData) -> Optional[Order]:
        # Your trading logic here
        if should_buy:
            return Order(
                symbol=data.symbol,
                exchange="NSE",
                signal=Signal.BUY,
                quantity=10,
                order_type=OrderType.MARKET,
                reason="Buy signal generated"
            )
        return None
```

## Development

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

### Code Formatting

```bash
# Backend
cd backend
black .
isort .

# Frontend
cd frontend
npm run lint
```

## Deployment

### Production Checklist

- [ ] Change `SECRET_KEY` to a secure random value
- [ ] Set `DEBUG=false`
- [ ] Configure proper database credentials
- [ ] Set up SSL/TLS certificates
- [ ] Configure CORS origins for production domain
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Configure backup strategy for database

### Docker Production Build

```bash
# Build production images
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# Deploy
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│    Frontend     │────▶│   API Gateway   │
│   (Next.js)     │     │    (FastAPI)    │
└─────────────────┘     └────────┬────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        ▼                        ▼                        ▼
┌───────────────┐     ┌───────────────────┐     ┌───────────────┐
│   PostgreSQL  │     │  Execution Engine │     │     Redis     │
│   (Database)  │     │  (Strategy Runs)  │     │  (Cache/PubSub)│
└───────────────┘     └─────────┬─────────┘     └───────────────┘
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
            ┌───────────────┐       ┌───────────────┐
            │  Fyers API    │       │  Paper Broker │
            │  (Live)       │       │  (Simulated)  │
            └───────────────┘       └───────────────┘
```

## License

Private - All rights reserved

## Support

For issues and questions, please create an issue in the repository.
