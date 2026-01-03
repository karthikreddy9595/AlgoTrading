"""
Fyers Broker Plugin

Provides integration with Fyers trading API for:
- OAuth authentication
- Order placement and management
- Real-time market data via WebSocket
- Position and order tracking
"""

from brokers.plugins.fyers.broker import FyersBroker

__all__ = ["FyersBroker"]
