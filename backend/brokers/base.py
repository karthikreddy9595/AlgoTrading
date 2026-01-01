from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Callable, Any
from decimal import Decimal
from datetime import datetime
from enum import Enum


class OrderStatus(Enum):
    PENDING = "pending"
    PLACED = "placed"
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class BrokerCredentials:
    """Credentials for broker authentication."""
    api_key: str
    api_secret: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    client_id: Optional[str] = None


@dataclass
class BrokerOrder:
    """Order placed with the broker."""
    order_id: str
    broker_order_id: Optional[str]
    symbol: str
    exchange: str
    transaction_type: str  # BUY, SELL
    quantity: int
    order_type: str  # MARKET, LIMIT, SL, SL-M
    price: Optional[Decimal]
    trigger_price: Optional[Decimal]
    status: OrderStatus
    filled_quantity: int = 0
    filled_price: Optional[Decimal] = None
    message: str = ""
    placed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class BrokerPosition:
    """Position from broker."""
    symbol: str
    exchange: str
    quantity: int
    avg_price: Decimal
    ltp: Decimal
    pnl: Decimal
    product_type: str  # INTRADAY, DELIVERY, etc.


@dataclass
class MarketQuote:
    """Market quote from broker."""
    symbol: str
    exchange: str
    ltp: Decimal
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    bid: Decimal
    ask: Decimal
    bid_qty: int
    ask_qty: int
    timestamp: datetime


class BaseBroker(ABC):
    """
    Abstract base class for all broker implementations.

    All broker integrations must implement this interface to ensure
    consistent behavior across different brokers.
    """

    name: str = "Base Broker"

    def __init__(self):
        self.is_connected = False
        self.credentials: Optional[BrokerCredentials] = None
        self._market_data_callback: Optional[Callable] = None

    @abstractmethod
    async def connect(self, credentials: BrokerCredentials) -> bool:
        """
        Establish connection with broker.

        Args:
            credentials: Broker authentication credentials

        Returns:
            True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close broker connection and cleanup resources."""
        pass

    @abstractmethod
    async def get_profile(self) -> dict:
        """
        Get user profile information.

        Returns:
            Dictionary with user profile data
        """
        pass

    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        exchange: str,
        transaction_type: str,
        quantity: int,
        order_type: str,
        price: Optional[Decimal] = None,
        trigger_price: Optional[Decimal] = None,
        product_type: str = "INTRADAY",
    ) -> BrokerOrder:
        """
        Place an order with the broker.

        Args:
            symbol: Trading symbol
            exchange: Exchange (NSE, BSE, NFO, etc.)
            transaction_type: BUY or SELL
            quantity: Number of units
            order_type: MARKET, LIMIT, SL, SL-M
            price: Limit price (required for LIMIT orders)
            trigger_price: Trigger price (required for SL orders)
            product_type: INTRADAY, DELIVERY, etc.

        Returns:
            BrokerOrder with order details
        """
        pass

    @abstractmethod
    async def modify_order(
        self,
        order_id: str,
        quantity: Optional[int] = None,
        price: Optional[Decimal] = None,
        trigger_price: Optional[Decimal] = None,
    ) -> BrokerOrder:
        """
        Modify an existing order.

        Args:
            order_id: Order ID to modify
            quantity: New quantity (optional)
            price: New price (optional)
            trigger_price: New trigger price (optional)

        Returns:
            Updated BrokerOrder
        """
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel a pending order.

        Args:
            order_id: Order ID to cancel

        Returns:
            True if cancelled successfully
        """
        pass

    @abstractmethod
    async def get_order_status(self, order_id: str) -> BrokerOrder:
        """
        Get status of an order.

        Args:
            order_id: Order ID to query

        Returns:
            BrokerOrder with current status
        """
        pass

    @abstractmethod
    async def get_orders(self) -> List[BrokerOrder]:
        """
        Get all orders for the day.

        Returns:
            List of BrokerOrder
        """
        pass

    @abstractmethod
    async def get_positions(self) -> List[BrokerPosition]:
        """
        Get current positions.

        Returns:
            List of BrokerPosition
        """
        pass

    @abstractmethod
    async def get_quote(self, symbol: str, exchange: str) -> MarketQuote:
        """
        Get current market quote for a symbol.

        Args:
            symbol: Trading symbol
            exchange: Exchange

        Returns:
            MarketQuote with current prices
        """
        pass

    @abstractmethod
    async def subscribe_market_data(
        self,
        symbols: List[str],
        callback: Callable[[MarketQuote], None],
    ) -> None:
        """
        Subscribe to real-time market data.

        Args:
            symbols: List of symbols to subscribe (format: EXCHANGE:SYMBOL)
            callback: Function to call on each tick
        """
        pass

    @abstractmethod
    async def unsubscribe_market_data(self, symbols: List[str]) -> None:
        """
        Unsubscribe from market data.

        Args:
            symbols: List of symbols to unsubscribe
        """
        pass

    async def get_margin(self) -> dict:
        """
        Get available margin/funds.

        Returns:
            Dictionary with margin details
        """
        raise NotImplementedError("get_margin not implemented for this broker")

    async def get_historical_data(
        self,
        symbol: str,
        exchange: str,
        interval: str,
        from_date: datetime,
        to_date: datetime,
    ) -> List[dict]:
        """
        Get historical OHLC data.

        Args:
            symbol: Trading symbol
            exchange: Exchange
            interval: Candle interval (1min, 5min, 15min, 1hour, 1day)
            from_date: Start date
            to_date: End date

        Returns:
            List of OHLC candles
        """
        raise NotImplementedError("get_historical_data not implemented for this broker")
