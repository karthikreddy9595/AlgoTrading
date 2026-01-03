"""
Broker Factory

Provides unified interface for creating and managing broker instances.
"""

from typing import Dict, Any, Optional

from brokers.base import BaseBroker, BrokerCredentials
from brokers.registry import broker_registry


class BrokerFactory:
    """Factory for creating broker instances."""

    @staticmethod
    def create(broker_name: str) -> BaseBroker:
        """
        Create a broker instance by name.

        Args:
            broker_name: Name of the broker (e.g., 'fyers', 'zerodha', 'paper')

        Returns:
            Unconnected broker instance

        Raises:
            ValueError: If broker is not registered
        """
        # Special case for paper trading (not a plugin)
        if broker_name == "paper":
            from brokers.paper import PaperTradingBroker

            return PaperTradingBroker()


        broker_class = broker_registry.get_broker_class(broker_name)
        if not broker_class:
            raise ValueError(f"Unknown broker: {broker_name}")

        return broker_class()

    @staticmethod
    async def create_and_connect(
        broker_name: str,
        credentials: Dict[str, Any],
    ) -> BaseBroker:
        """
        Create and connect to a broker.

        Args:
            broker_name: Name of the broker
            credentials: Dictionary with api_key, api_secret, access_token, etc.

        Returns:
            Connected broker instance

        Raises:
            ValueError: If broker is not registered
            ConnectionError: If connection fails
        """
        broker = BrokerFactory.create(broker_name)

        creds = BrokerCredentials(
            api_key=credentials.get("api_key", ""),
            api_secret=credentials.get("api_secret", ""),
            access_token=credentials.get("access_token"),
            refresh_token=credentials.get("refresh_token"),
            client_id=credentials.get("client_id"),
        )

        connected = await broker.connect(creds)
        if not connected:
            raise ConnectionError(f"Failed to connect to {broker_name}")

        return broker

    @staticmethod
    def get_auth_url(
        broker_name: str, config: Dict[str, Any], state: str
    ) -> Optional[str]:
        """
        Generate OAuth URL for a broker.

        Args:
            broker_name: Name of the broker
            config: Broker configuration (app_id, redirect_uri, etc.)
            state: State parameter for OAuth

        Returns:
            Authorization URL or None if OAuth not supported

        Raises:
            ValueError: If broker is not registered
        """
        broker_class = broker_registry.get_broker_class(broker_name)
        if not broker_class:
            raise ValueError(f"Unknown broker: {broker_name}")

        return broker_class.generate_auth_url(config, state)

    @staticmethod
    async def exchange_token(
        broker_name: str,
        config: Dict[str, Any],
        auth_code: str,
    ) -> Dict[str, Any]:
        """
        Exchange OAuth code for access token.

        Args:
            broker_name: Name of the broker
            config: Broker configuration
            auth_code: Authorization code from OAuth callback

        Returns:
            Dictionary with access_token and optionally other token data

        Raises:
            ValueError: If broker is not registered
            NotImplementedError: If broker doesn't support OAuth
        """
        broker_class = broker_registry.get_broker_class(broker_name)
        if not broker_class:
            raise ValueError(f"Unknown broker: {broker_name}")

        return await broker_class.exchange_auth_code(config, auth_code)

    @staticmethod
    def get_available_brokers() -> list:
        """
        Get list of all available brokers.

        Returns:
            List of broker names
        """
        brokers = broker_registry.list_brokers()
        # Always include paper trading
        if "paper" not in brokers:
            brokers.append("paper")
        return brokers
