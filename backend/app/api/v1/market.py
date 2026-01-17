"""
Market data API endpoints for fetching real-time market indices and historical data.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime, date
from pydantic import BaseModel

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models import User, BrokerConnection
from brokers.factory import BrokerFactory
from app.core.config import settings


router = APIRouter(prefix="/market", tags=["Market"])


# Index symbols in Fyers format
INDEX_SYMBOLS = {
    "NIFTY50": {"symbol": "NIFTY50-INDEX", "exchange": "NSE", "display_name": "NIFTY 50"},
    "BANKNIFTY": {"symbol": "NIFTYBANK-INDEX", "exchange": "NSE", "display_name": "BANK NIFTY"},
    "SENSEX": {"symbol": "SENSEX-INDEX", "exchange": "BSE", "display_name": "SENSEX"},
    "BANKEX": {"symbol": "BANKEX-INDEX", "exchange": "BSE", "display_name": "BANKEX"},
}


# ==================== Schemas ====================


class IndexValue(BaseModel):
    """Single index value."""
    symbol: str
    display_name: str
    ltp: Optional[float] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    prev_close: Optional[float] = None
    timestamp: Optional[str] = None


class IndicesResponse(BaseModel):
    """Response containing all index values."""
    connected: bool
    indices: List[IndexValue]
    message: Optional[str] = None


class HistoricalCandle(BaseModel):
    """Single OHLC candle."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class HistoricalDataResponse(BaseModel):
    """Response containing historical OHLC data."""
    symbol: str
    exchange: str
    interval: str
    candles: List[HistoricalCandle]
    message: Optional[str] = None


class SymbolInfo(BaseModel):
    """Information about a tradeable symbol."""
    symbol: str
    exchange: str
    name: str
    segment: Optional[str] = None


class SymbolSearchResponse(BaseModel):
    """Response containing search results for symbols."""
    symbols: List[SymbolInfo]


# Popular NSE symbols for quick selection
POPULAR_SYMBOLS = [
    SymbolInfo(symbol="RELIANCE", exchange="NSE", name="Reliance Industries Ltd"),
    SymbolInfo(symbol="TCS", exchange="NSE", name="Tata Consultancy Services Ltd"),
    SymbolInfo(symbol="HDFCBANK", exchange="NSE", name="HDFC Bank Ltd"),
    SymbolInfo(symbol="INFY", exchange="NSE", name="Infosys Ltd"),
    SymbolInfo(symbol="ICICIBANK", exchange="NSE", name="ICICI Bank Ltd"),
    SymbolInfo(symbol="HINDUNILVR", exchange="NSE", name="Hindustan Unilever Ltd"),
    SymbolInfo(symbol="SBIN", exchange="NSE", name="State Bank of India"),
    SymbolInfo(symbol="BHARTIARTL", exchange="NSE", name="Bharti Airtel Ltd"),
    SymbolInfo(symbol="ITC", exchange="NSE", name="ITC Ltd"),
    SymbolInfo(symbol="KOTAKBANK", exchange="NSE", name="Kotak Mahindra Bank Ltd"),
    SymbolInfo(symbol="LT", exchange="NSE", name="Larsen & Toubro Ltd"),
    SymbolInfo(symbol="AXISBANK", exchange="NSE", name="Axis Bank Ltd"),
    SymbolInfo(symbol="ASIANPAINT", exchange="NSE", name="Asian Paints Ltd"),
    SymbolInfo(symbol="MARUTI", exchange="NSE", name="Maruti Suzuki India Ltd"),
    SymbolInfo(symbol="SUNPHARMA", exchange="NSE", name="Sun Pharmaceutical Industries Ltd"),
    SymbolInfo(symbol="TITAN", exchange="NSE", name="Titan Company Ltd"),
    SymbolInfo(symbol="BAJFINANCE", exchange="NSE", name="Bajaj Finance Ltd"),
    SymbolInfo(symbol="WIPRO", exchange="NSE", name="Wipro Ltd"),
    SymbolInfo(symbol="ULTRACEMCO", exchange="NSE", name="UltraTech Cement Ltd"),
    SymbolInfo(symbol="NESTLEIND", exchange="NSE", name="Nestle India Ltd"),
    SymbolInfo(symbol="TATAMOTORS", exchange="NSE", name="Tata Motors Ltd"),
    SymbolInfo(symbol="TATASTEEL", exchange="NSE", name="Tata Steel Ltd"),
    SymbolInfo(symbol="POWERGRID", exchange="NSE", name="Power Grid Corporation of India Ltd"),
    SymbolInfo(symbol="NTPC", exchange="NSE", name="NTPC Ltd"),
    SymbolInfo(symbol="ONGC", exchange="NSE", name="Oil and Natural Gas Corporation Ltd"),
    SymbolInfo(symbol="HCLTECH", exchange="NSE", name="HCL Technologies Ltd"),
    SymbolInfo(symbol="TECHM", exchange="NSE", name="Tech Mahindra Ltd"),
    SymbolInfo(symbol="ADANIENT", exchange="NSE", name="Adani Enterprises Ltd"),
    SymbolInfo(symbol="ADANIPORTS", exchange="NSE", name="Adani Ports and SEZ Ltd"),
    SymbolInfo(symbol="COALINDIA", exchange="NSE", name="Coal India Ltd"),
]


# ==================== Endpoints ====================


@router.get("/indices", response_model=IndicesResponse)
async def get_market_indices(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current values for all market indices (NIFTY, BANKNIFTY, SENSEX, BANKEX).

    Returns placeholder data if broker is not connected.
    """
    # Check for active broker connection
    result = await db.execute(
        select(BrokerConnection).where(
            BrokerConnection.user_id == current_user.id,
            BrokerConnection.is_active == True,
        )
    )
    connection = result.scalar_one_or_none()

    # Build placeholder response
    indices = [
        IndexValue(
            symbol=key,
            display_name=info["display_name"],
        )
        for key, info in INDEX_SYMBOLS.items()
    ]

    if not connection:
        return IndicesResponse(
            connected=False,
            indices=indices,
            message="No broker connected",
        )

    # Check if token is expired
    if connection.token_expiry and connection.token_expiry < datetime.utcnow():
        return IndicesResponse(
            connected=False,
            indices=indices,
            message="Broker session expired",
        )

    try:
        # Get broker config and create broker instance
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

        # Fetch quotes for all indices
        updated_indices = []
        for key, info in INDEX_SYMBOLS.items():
            try:
                quote = await broker.get_quote(info["symbol"], info["exchange"])

                prev_close = float(quote.close) if quote.close else None
                ltp = float(quote.ltp) if quote.ltp else None
                change = None
                change_percent = None

                if ltp is not None and prev_close is not None and prev_close > 0:
                    change = ltp - prev_close
                    change_percent = (change / prev_close) * 100

                updated_indices.append(IndexValue(
                    symbol=key,
                    display_name=info["display_name"],
                    ltp=ltp,
                    change=round(change, 2) if change is not None else None,
                    change_percent=round(change_percent, 2) if change_percent is not None else None,
                    open=float(quote.open) if quote.open else None,
                    high=float(quote.high) if quote.high else None,
                    low=float(quote.low) if quote.low else None,
                    prev_close=prev_close,
                    timestamp=quote.timestamp.isoformat() if quote.timestamp else None,
                ))
            except Exception as e:
                # If individual quote fails, add placeholder
                updated_indices.append(IndexValue(
                    symbol=key,
                    display_name=info["display_name"],
                ))

        await broker.disconnect()

        return IndicesResponse(
            connected=True,
            indices=updated_indices,
        )

    except Exception as e:
        return IndicesResponse(
            connected=False,
            indices=indices,
            message=f"Broker error: {str(e)}",
        )


@router.get("/historical/{symbol}", response_model=HistoricalDataResponse)
async def get_historical_data(
    symbol: str,
    exchange: str = Query("NSE", pattern="^(NSE|BSE|NFO|MCX|CDS)$"),
    interval: str = Query("1day", pattern="^(1min|5min|15min|30min|1hour|1day)$"),
    from_date: date = Query(..., description="Start date"),
    to_date: date = Query(..., description="End date"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get historical OHLC data for a symbol.

    Intervals: 1min, 5min, 15min, 30min, 1hour, 1day
    """
    # Validate date range
    if to_date <= from_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date must be after start date",
        )

    # Get broker connection
    result = await db.execute(
        select(BrokerConnection).where(
            BrokerConnection.user_id == current_user.id,
            BrokerConnection.is_active == True,
        )
    )
    connection = result.scalar_one_or_none()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active broker connection",
        )

    # Check token expiry
    if connection.token_expiry and connection.token_expiry < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Broker session expired",
        )

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
            symbol=symbol.upper(),
            exchange=exchange.upper(),
            interval=interval,
            from_date=datetime.combine(from_date, datetime.min.time()),
            to_date=datetime.combine(to_date, datetime.max.time()),
        )

        await broker.disconnect()

        if not historical_data:
            return HistoricalDataResponse(
                symbol=symbol.upper(),
                exchange=exchange.upper(),
                interval=interval,
                candles=[],
                message="No data available for the specified period",
            )

        candles = [
            HistoricalCandle(
                timestamp=candle.get("timestamp"),
                open=float(candle.get("open", 0)),
                high=float(candle.get("high", 0)),
                low=float(candle.get("low", 0)),
                close=float(candle.get("close", 0)),
                volume=int(candle.get("volume", 0)),
            )
            for candle in historical_data
        ]

        return HistoricalDataResponse(
            symbol=symbol.upper(),
            exchange=exchange.upper(),
            interval=interval,
            candles=candles,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to fetch historical data: {str(e)}",
        )


def _get_broker_config(broker_name: str) -> dict:
    """Get broker configuration from settings based on broker name."""
    config_mapping = {
        "fyers": {
            "app_id": settings.FYERS_APP_ID,
            "secret_key": settings.FYERS_SECRET_KEY,
            "redirect_uri": settings.FYERS_REDIRECT_URI,
        },
    }
    return config_mapping.get(broker_name, {})


@router.get("/symbols/search", response_model=SymbolSearchResponse)
async def search_symbols(
    query: str = Query(..., min_length=1, description="Search query for symbol"),
    exchange: Optional[str] = Query(None, pattern="^(NSE|BSE|NFO|MCX|CDS)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Search for tradeable symbols.

    Returns symbols matching the query from the user's connected broker
    or from a static list of popular symbols if broker search is not available.
    """
    query_lower = query.lower()

    # First, try to get symbols from broker if connected
    result = await db.execute(
        select(BrokerConnection).where(
            BrokerConnection.user_id == current_user.id,
            BrokerConnection.is_active == True,
        )
    )
    connection = result.scalar_one_or_none()

    if connection and connection.access_token:
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

            # Try broker's search_symbols if available
            if hasattr(broker, 'search_symbols'):
                broker_results = await broker.search_symbols(query, exchange)
                await broker.disconnect()

                if broker_results:
                    return SymbolSearchResponse(
                        symbols=[
                            SymbolInfo(
                                symbol=s.get("symbol", ""),
                                exchange=s.get("exchange", "NSE"),
                                name=s.get("name", s.get("symbol", "")),
                                segment=s.get("segment"),
                            )
                            for s in broker_results
                        ]
                    )

            await broker.disconnect()
        except Exception:
            # Fall back to static search on broker error
            pass

    # Fall back to static symbol search
    matching_symbols = []
    for sym in POPULAR_SYMBOLS:
        if query_lower in sym.symbol.lower() or query_lower in sym.name.lower():
            if exchange is None or sym.exchange == exchange:
                matching_symbols.append(sym)

    return SymbolSearchResponse(symbols=matching_symbols[:20])


@router.get("/symbols/popular", response_model=SymbolSearchResponse)
async def get_popular_symbols(
    exchange: Optional[str] = Query(None, pattern="^(NSE|BSE)$"),
    limit: int = Query(20, ge=1, le=50),
):
    """
    Get list of popular trading symbols.

    Returns a curated list of popular NSE/BSE symbols for quick selection.
    """
    symbols = POPULAR_SYMBOLS

    if exchange:
        symbols = [s for s in symbols if s.exchange == exchange]

    return SymbolSearchResponse(symbols=symbols[:limit])
