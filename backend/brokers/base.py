from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Callable, Any, Dict, Type
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


@dataclass
class BrokerCapabilities:
    """Broker capability flags."""
    trading: bool = True
    market_data: bool = True
    historical_data: bool = False
    streaming: bool = False
    options: bool = False
    futures: bool = False
    equity: bool = True
    commodities: bool = False
    currency: bool = False


@dataclass
class BrokerAuthConfig:
    """Authentication configuration for a broker."""
    auth_type: str  # "oauth", "api_key", "totp"
    requires_api_key: bool = True
    requires_api_secret: bool = True
    requires_totp: bool = False
    token_expiry_hours: int = 24
    oauth_auth_url: Optional[str] = None
    oauth_token_url: Optional[str] = None


@dataclass
class BrokerMetadata:
    """Plugin metadata for a broker."""
    name: str
    display_name: str
    version: str
    description: str
    capabilities: BrokerCapabilities
    auth_config: BrokerAuthConfig
    exchanges: List[str]
    symbol_format: str
    logo_url: Optional[str] = None
    config_schema: Dict[str, Any] = field(default_factory=dict)


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

    # ==================== Plugin System Methods ====================

    @classmethod
    def get_metadata(cls) -> BrokerMetadata:
        """
        Return broker plugin metadata.

        This method should be overridden by broker plugins loaded from plugin.json.
        For brokers not using the plugin system, this returns a default metadata.

        Returns:
            BrokerMetadata with broker information
        """
        return BrokerMetadata(
            name=cls.name.lower().replace(" ", "_"),
            display_name=cls.name,
            version="1.0.0",
            description=f"{cls.name} broker integration",
            capabilities=BrokerCapabilities(),
            auth_config=BrokerAuthConfig(auth_type="api_key"),
            exchanges=[],
            symbol_format="{exchange}:{symbol}",
        )

    @classmethod
    def generate_auth_url(cls, config: Dict[str, Any], state: str) -> Optional[str]:
        """
        Generate OAuth authorization URL.

        Override this method for OAuth-based brokers.

        Args:
            config: Broker configuration (app_id, redirect_uri, etc.)
            state: State parameter for OAuth (usually user_id)

        Returns:
            Authorization URL or None if OAuth not supported
        """
        return None

    @classmethod
    async def exchange_auth_code(
        cls, config: Dict[str, Any], auth_code: str
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.

        Override this method for OAuth-based brokers.

        Args:
            config: Broker configuration
            auth_code: Authorization code from OAuth callback

        Returns:
            Dictionary with access_token and optionally refresh_token

        Raises:
            NotImplementedError: If OAuth not supported
        """
        raise NotImplementedError("OAuth not supported for this broker")

    def normalize_symbol(self, broker_symbol: str) -> str:
        """
        Convert broker-specific symbol to normalized format.

        Args:
            broker_symbol: Symbol in broker's format

        Returns:
            Normalized symbol (e.g., "RELIANCE")
        """
        return broker_symbol

    def denormalize_symbol(self, symbol: str, exchange: str) -> str:
        """
        Convert normalized symbol to broker-specific format.

        Args:
            symbol: Normalized symbol
            exchange: Exchange code

        Returns:
            Symbol in broker's format (e.g., "NSE:RELIANCE-EQ")
        """
        return f"{exchange}:{symbol}"
