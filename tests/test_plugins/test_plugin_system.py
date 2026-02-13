"""
Tests for the RISKCAST plugin system.

Tests:
- test_plugin_registration()
- test_plugin_dynamic_load()
- Plugin lifecycle
- Plugin health checks
"""

import pytest
from datetime import datetime
from typing import Dict, Any, List, Optional

from app.plugins.base import (
    PluginMetadata,
    PluginType,
    PluginStatus,
    PluginHealth,
    BasePlugin,
    SignalSourcePlugin,
    ActionTypePlugin,
)
from app.plugins.registry import (
    PluginRegistry,
    PluginConfig,
    PluginLoadResult,
    get_plugin_registry,
)


# Test Plugin Implementations

class TestSignalPlugin(SignalSourcePlugin):
    """Test signal source plugin."""
    
    def __init__(self):
        super().__init__()
        self._signals_fetched = 0
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="test_signal",
            version="1.0.0",
            plugin_type=PluginType.SIGNAL_SOURCE,
            author="Test",
            description="Test signal source plugin",
        )
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        self._config = config
    
    async def shutdown(self) -> None:
        pass
    
    async def fetch_signals(
        self,
        query: Dict[str, Any],
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        self._signals_fetched += 1
        return [
            {
                "signal_id": "test_1",
                "source": "test",
                "probability": 0.5,
                "confidence": 0.8,
            }
        ]
    
    async def get_signal_by_id(self, signal_id: str) -> Optional[Dict[str, Any]]:
        return {"signal_id": signal_id, "source": "test"}
    
    async def get_source_status(self) -> Dict[str, Any]:
        return {"source": "test", "available": True}


class TestActionPlugin(ActionTypePlugin):
    """Test action type plugin."""
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="test_action",
            version="1.0.0",
            plugin_type=PluginType.ACTION_TYPE,
            author="Test",
            description="Test action type plugin",
        )
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        self._config = config
    
    async def shutdown(self) -> None:
        pass
    
    async def generate_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action_type": "test",
            "summary": "Test action",
            "estimated_cost_usd": 100.0,
        }
    
    async def validate_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        return {"valid": True, "errors": [], "warnings": []}
    
    async def estimate_cost(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action_type": "test",
            "cost_estimate_usd": {"min": 50, "max": 150, "expected": 100},
        }


class TestPluginRegistration:
    """Test plugin registration functionality."""
    
    @pytest.fixture
    def registry(self):
        """Create a fresh registry for each test."""
        return PluginRegistry()
    
    @pytest.fixture
    def signal_plugin(self):
        """Create a test signal plugin."""
        return TestSignalPlugin()
    
    @pytest.fixture
    def action_plugin(self):
        """Create a test action plugin."""
        return TestActionPlugin()
    
    def test_plugin_registration(self, registry, signal_plugin):
        """Test basic plugin registration."""
        # Register plugin
        result = registry.register(signal_plugin)
        
        assert result is True
        assert registry.get_plugin("test_signal") is signal_plugin
        assert signal_plugin.status == PluginStatus.REGISTERED
    
    def test_plugin_registration_duplicate_rejected(self, registry, signal_plugin):
        """Test that duplicate plugins are rejected."""
        registry.register(signal_plugin)
        
        # Create another plugin with same name
        duplicate = TestSignalPlugin()
        result = registry.register(duplicate)
        
        assert result is False  # Should be rejected
    
    def test_plugin_unregistration(self, registry, signal_plugin):
        """Test plugin unregistration."""
        registry.register(signal_plugin)
        assert registry.get_plugin("test_signal") is not None
        
        result = registry.unregister("test_signal")
        
        assert result is True
        assert registry.get_plugin("test_signal") is None
    
    def test_get_plugins_by_type(self, registry, signal_plugin, action_plugin):
        """Test getting plugins by type."""
        registry.register(signal_plugin)
        registry.register(action_plugin)
        
        signal_sources = registry.get_plugins_by_type(PluginType.SIGNAL_SOURCE)
        action_types = registry.get_plugins_by_type(PluginType.ACTION_TYPE)
        
        assert len(signal_sources) == 1
        assert len(action_types) == 1
        assert signal_sources[0].metadata.name == "test_signal"
        assert action_types[0].metadata.name == "test_action"
    
    def test_get_signal_sources(self, registry, signal_plugin, action_plugin):
        """Test convenience method for getting signal sources."""
        registry.register(signal_plugin)
        registry.register(action_plugin)
        
        signal_sources = registry.get_signal_sources()
        
        assert len(signal_sources) == 1
        assert isinstance(signal_sources[0], SignalSourcePlugin)
    
    def test_get_action_types(self, registry, signal_plugin, action_plugin):
        """Test convenience method for getting action types."""
        registry.register(signal_plugin)
        registry.register(action_plugin)
        
        action_types = registry.get_action_types()
        
        assert len(action_types) == 1
        assert isinstance(action_types[0], ActionTypePlugin)


class TestPluginLifecycle:
    """Test plugin lifecycle management."""
    
    @pytest.fixture
    def registry(self):
        return PluginRegistry()
    
    @pytest.fixture
    def signal_plugin(self):
        return TestSignalPlugin()
    
    @pytest.mark.asyncio
    async def test_plugin_initialization(self, registry, signal_plugin):
        """Test plugin initialization."""
        registry.register(signal_plugin)
        
        config = {"test_key": "test_value"}
        registry.set_plugin_config("test_signal", config)
        
        await registry.initialize_all()
        
        assert signal_plugin.status == PluginStatus.ACTIVE
        assert signal_plugin.config.get("test_key") == "test_value"
    
    @pytest.mark.asyncio
    async def test_plugin_shutdown(self, registry, signal_plugin):
        """Test plugin shutdown."""
        registry.register(signal_plugin)
        await registry.initialize_all()
        
        assert signal_plugin.status == PluginStatus.ACTIVE
        
        await registry.shutdown_all()
        
        assert signal_plugin.status == PluginStatus.STOPPED


class TestPluginHealth:
    """Test plugin health checking."""
    
    @pytest.fixture
    def registry(self):
        return PluginRegistry()
    
    @pytest.fixture
    def signal_plugin(self):
        return TestSignalPlugin()
    
    @pytest.mark.asyncio
    async def test_plugin_health_check(self, registry, signal_plugin):
        """Test plugin health check."""
        registry.register(signal_plugin)
        await registry.initialize_all()
        
        health = await signal_plugin.health_check()
        
        assert isinstance(health, PluginHealth)
        assert health.healthy is True
        assert health.status == PluginStatus.ACTIVE
    
    @pytest.mark.asyncio
    async def test_registry_health(self, registry, signal_plugin):
        """Test registry-level health check."""
        registry.register(signal_plugin)
        await registry.initialize_all()
        
        health = await registry.get_health()
        
        assert "test_signal" in health
        assert health["test_signal"]["healthy"] is True


class TestPluginDynamicLoading:
    """Test dynamic plugin loading."""
    
    @pytest.fixture
    def registry(self):
        return PluginRegistry()
    
    @pytest.mark.asyncio
    async def test_plugin_dynamic_load(self, registry, tmp_path):
        """Test loading plugins from directory."""
        # Create a test plugin file
        plugin_code = '''
from app.plugins.base import SignalSourcePlugin, PluginMetadata, PluginType
from typing import Dict, Any, List, Optional

class Plugin(SignalSourcePlugin):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="dynamic_test",
            version="1.0.0",
            plugin_type=PluginType.SIGNAL_SOURCE,
            author="Test",
            description="Dynamically loaded plugin",
        )
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        pass
    
    async def shutdown(self) -> None:
        pass
    
    async def fetch_signals(self, query: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        return []
    
    async def get_signal_by_id(self, signal_id: str) -> Optional[Dict[str, Any]]:
        return None
    
    async def get_source_status(self) -> Dict[str, Any]:
        return {"available": True}
'''
        
        # Write plugin file
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        plugin_file = plugin_dir / "test_dynamic.py"
        plugin_file.write_text(plugin_code)
        
        # Load plugins
        results = await registry.load_plugins_from_directory(str(plugin_dir))
        
        # Verify loading
        assert len(results) == 1
        assert results[0].success is True
        assert results[0].plugin_name == "dynamic_test"
        
        # Verify plugin is registered
        plugin = registry.get_plugin("dynamic_test")
        assert plugin is not None
        assert plugin.metadata.name == "dynamic_test"


class TestPluginConfiguration:
    """Test plugin configuration management."""
    
    @pytest.fixture
    def registry(self):
        return PluginRegistry()
    
    @pytest.fixture
    def signal_plugin(self):
        return TestSignalPlugin()
    
    def test_set_plugin_config(self, registry, signal_plugin):
        """Test setting plugin configuration."""
        registry.register(signal_plugin)
        
        config = {"api_key": "test123", "timeout": 30}
        registry.set_plugin_config("test_signal", config)
        
        stored_config = registry.get_plugin_config("test_signal")
        assert stored_config == config
    
    def test_get_plugin_config_default(self, registry, signal_plugin):
        """Test getting default config for unconfigured plugin."""
        registry.register(signal_plugin)
        
        config = registry.get_plugin_config("test_signal")
        assert config == {}


class TestRegistryStatistics:
    """Test registry statistics."""
    
    @pytest.fixture
    def registry(self):
        return PluginRegistry()
    
    @pytest.fixture
    def plugins(self):
        return [TestSignalPlugin(), TestActionPlugin()]
    
    @pytest.mark.asyncio
    async def test_registry_stats(self, registry, plugins):
        """Test getting registry statistics."""
        for plugin in plugins:
            registry.register(plugin)
        
        await registry.initialize_all()
        
        stats = registry.get_stats()
        
        assert stats.total_plugins == 2
        assert stats.by_type[PluginType.SIGNAL_SOURCE] == 1
        assert stats.by_type[PluginType.ACTION_TYPE] == 1
        assert stats.by_status[PluginStatus.ACTIVE] == 2


class TestPluginMetadata:
    """Test plugin metadata handling."""
    
    def test_metadata_creation(self):
        """Test plugin metadata creation."""
        metadata = PluginMetadata(
            name="test",
            version="1.0.0",
            plugin_type=PluginType.SIGNAL_SOURCE,
            author="Test Author",
            description="Test description",
            config_schema={"type": "object"},
            required_permissions=["read", "write"],
        )
        
        assert metadata.name == "test"
        assert metadata.version == "1.0.0"
        assert metadata.plugin_type == PluginType.SIGNAL_SOURCE
        assert len(metadata.required_permissions) == 2
    
    def test_metadata_validation(self):
        """Test metadata validation."""
        plugin = TestSignalPlugin()
        metadata = plugin.metadata
        
        assert metadata.name is not None
        assert metadata.version is not None
        assert metadata.plugin_type == PluginType.SIGNAL_SOURCE


class TestBuiltinPlugins:
    """Test built-in plugins."""
    
    @pytest.mark.asyncio
    async def test_polymarket_plugin(self):
        """Test Polymarket signal source plugin."""
        from app.plugins.builtin.signal_sources.polymarket import PolymarketSignalPlugin
        
        plugin = PolymarketSignalPlugin()
        
        assert plugin.metadata.name == "polymarket"
        assert plugin.metadata.plugin_type == PluginType.SIGNAL_SOURCE
        
        # Initialize
        await plugin.initialize({"categories": ["geopolitics"]})
        
        # Fetch signals
        signals = await plugin.fetch_signals({"keywords": ["red sea"]})
        
        assert len(signals) > 0
        assert "signal_id" in signals[0]
        assert "probability" in signals[0]
        
        await plugin.shutdown()
    
    @pytest.mark.asyncio
    async def test_reroute_action_plugin(self):
        """Test reroute action type plugin."""
        from app.plugins.builtin.action_types.reroute import RerouteActionPlugin
        
        plugin = RerouteActionPlugin()
        
        assert plugin.metadata.name == "reroute"
        assert plugin.metadata.plugin_type == PluginType.ACTION_TYPE
        
        # Initialize
        await plugin.initialize({"carriers": ["MSC", "Maersk"]})
        
        # Generate action
        context = {
            "chokepoint": "red_sea",
            "shipment": {
                "shipment_id": "TEST-001",
                "teu_count": 2,
                "cargo_value_usd": 100000,
            },
            "severity": "high",
        }
        
        action = await plugin.generate_action(context)
        
        assert action["action_type"] == "reroute"
        assert "estimated_cost_usd" in action
        assert action["estimated_cost_usd"] > 0
        assert "deadline" in action
        
        await plugin.shutdown()
