"""
RISKCAST Plugin System.

Provides extensible architecture for:
- Signal sources (new data providers)
- Action types (new recommendation types)
- Delivery channels (new alert methods)
- Validators (custom validation rules)

Addresses audit gap: B1.4 Extensibility (+8 points)
"""

from app.plugins.base import (
    PluginMetadata,
    PluginStatus,
    PluginHealth,
    BasePlugin,
    SignalSourcePlugin,
    ActionTypePlugin,
    DeliveryPlugin,
    ValidatorPlugin,
)

from app.plugins.registry import (
    PluginRegistry,
    PluginConfig,
    PluginLoadResult,
    get_plugin_registry,
)

__all__ = [
    # Base
    "PluginMetadata",
    "PluginStatus",
    "PluginHealth",
    "BasePlugin",
    "SignalSourcePlugin",
    "ActionTypePlugin",
    "DeliveryPlugin",
    "ValidatorPlugin",
    # Registry
    "PluginRegistry",
    "PluginConfig",
    "PluginLoadResult",
    "get_plugin_registry",
]
