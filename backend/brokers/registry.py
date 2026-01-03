"""
Broker Plugin Registry with Auto-Discovery

Scans the plugins directory for broker implementations and loads them dynamically.
"""

import json
import importlib
import logging
from typing import Dict, List, Optional, Type
from pathlib import Path

from brokers.base import (
    BaseBroker,
    BrokerMetadata,
    BrokerCapabilities,
    BrokerAuthConfig,
)

logger = logging.getLogger(__name__)


class BrokerRegistry:
    """
    Registry for broker plugins with auto-discovery.

    Scans the plugins directory on initialization and loads all valid broker plugins.
    """

    _instance: Optional["BrokerRegistry"] = None
    _brokers: Dict[str, Type[BaseBroker]] = {}
    _metadata: Dict[str, BrokerMetadata] = {}
    _plugins_dir: Path = Path(__file__).parent / "plugins"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._brokers = {}
        self._metadata = {}
        self._discover_plugins()

    def _discover_plugins(self) -> None:
        """Scan plugins directory and load all valid broker plugins."""
        if not self._plugins_dir.exists():
            logger.warning(f"Plugins directory not found: {self._plugins_dir}")
            return

        for plugin_dir in self._plugins_dir.iterdir():
            if not plugin_dir.is_dir():
                continue
            if plugin_dir.name.startswith("_"):
                continue

            try:
                self._load_plugin(plugin_dir)
            except Exception as e:
                logger.error(f"Failed to load plugin {plugin_dir.name}: {e}")

    def _load_plugin(self, plugin_dir: Path) -> None:
        """Load a single broker plugin from directory."""
        manifest_path = plugin_dir / "plugin.json"

        if not manifest_path.exists():
            logger.warning(f"No plugin.json found in {plugin_dir}")
            return

        # Load manifest
        with open(manifest_path, "r") as f:
            manifest = json.load(f)

        broker_name = manifest["name"]
        broker_class_path = manifest["broker_class"]

        # Parse metadata from manifest
        metadata = self._parse_metadata(manifest)

        # Import broker class
        # broker_class_path format: "broker.FyersBroker"
        module_path, class_name = broker_class_path.rsplit(".", 1)
        module_name = f"brokers.plugins.{broker_name}.{module_path}"

        module = importlib.import_module(module_name)
        broker_class = getattr(module, class_name)

        # Validate broker class
        if not issubclass(broker_class, BaseBroker):
            raise TypeError(f"{class_name} is not a subclass of BaseBroker")

        # Inject metadata into broker class
        original_get_metadata = broker_class.get_metadata

        @classmethod
        def get_metadata_with_manifest(cls) -> BrokerMetadata:
            return metadata

        broker_class.get_metadata = get_metadata_with_manifest

        # Register
        self._brokers[broker_name] = broker_class
        self._metadata[broker_name] = metadata

        logger.info(f"Loaded broker plugin: {broker_name} v{metadata.version}")

    def _parse_metadata(self, manifest: dict) -> BrokerMetadata:
        """Parse plugin manifest into BrokerMetadata."""
        auth_config = manifest.get("auth", {})
        capabilities_dict = manifest.get("capabilities", {})
        oauth_config = auth_config.get("oauth_config", {})

        return BrokerMetadata(
            name=manifest["name"],
            display_name=manifest["display_name"],
            version=manifest["version"],
            description=manifest.get("description", ""),
            capabilities=BrokerCapabilities(
                trading=capabilities_dict.get("trading", True),
                market_data=capabilities_dict.get("market_data", True),
                historical_data=capabilities_dict.get("historical_data", False),
                streaming=capabilities_dict.get("streaming", False),
                options=capabilities_dict.get("options", False),
                futures=capabilities_dict.get("futures", False),
                equity=capabilities_dict.get("equity", True),
                commodities=capabilities_dict.get("commodities", False),
                currency=capabilities_dict.get("currency", False),
            ),
            auth_config=BrokerAuthConfig(
                auth_type=auth_config.get("type", "api_key"),
                requires_api_key=auth_config.get("requires_api_key", True),
                requires_api_secret=auth_config.get("requires_api_secret", True),
                requires_totp=auth_config.get("requires_totp", False),
                token_expiry_hours=auth_config.get("token_expiry_hours", 24),
                oauth_auth_url=oauth_config.get("auth_url"),
                oauth_token_url=oauth_config.get("token_url"),
            ),
            exchanges=manifest.get("exchanges", []),
            symbol_format=manifest.get("symbol_format", "{symbol}"),
            logo_url=manifest.get("logo_url"),
            config_schema=manifest.get("config_schema", {}),
        )

    def get_broker_class(self, name: str) -> Optional[Type[BaseBroker]]:
        """Get broker class by name."""
        return self._brokers.get(name)

    def get_metadata(self, name: str) -> Optional[BrokerMetadata]:
        """Get broker metadata by name."""
        return self._metadata.get(name)

    def list_brokers(self) -> List[str]:
        """List all registered broker names."""
        return list(self._brokers.keys())

    def list_brokers_with_metadata(self) -> List[BrokerMetadata]:
        """List all registered brokers with their metadata."""
        return list(self._metadata.values())

    def is_registered(self, name: str) -> bool:
        """Check if a broker is registered."""
        return name in self._brokers

    def register_broker(
        self, name: str, broker_class: Type[BaseBroker], metadata: BrokerMetadata
    ) -> None:
        """
        Manually register a broker (for non-plugin brokers like PaperTrading).

        Args:
            name: Broker identifier
            broker_class: Broker class
            metadata: Broker metadata
        """
        self._brokers[name] = broker_class
        self._metadata[name] = metadata
        logger.info(f"Registered broker: {name}")

    def reload_plugins(self) -> None:
        """Reload all plugins from the plugins directory."""
        self._brokers.clear()
        self._metadata.clear()
        self._discover_plugins()


# Global registry instance
broker_registry = BrokerRegistry()
