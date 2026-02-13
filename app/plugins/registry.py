"""
Plugin Registry - Central management for all plugins.

Handles:
- Plugin registration and discovery
- Dynamic loading from directories
- Lifecycle management (init/shutdown)
- Health monitoring
- Configuration management
"""

from datetime import datetime
from typing import Dict, Optional, List, Type, Any
from pathlib import Path
import importlib.util
import asyncio

import structlog
from pydantic import BaseModel, Field

from app.plugins.base import (
    BasePlugin,
    PluginMetadata,
    PluginStatus,
    PluginHealth,
    PluginType,
    SignalSourcePlugin,
    ActionTypePlugin,
    DeliveryPlugin,
    ValidatorPlugin,
)

logger = structlog.get_logger(__name__)


# ============================================================================
# SCHEMAS
# ============================================================================


class PluginConfig(BaseModel):
    """Configuration for a plugin."""
    plugin_id: str
    enabled: bool = True
    config: Dict[str, Any] = Field(default_factory=dict)


class PluginLoadResult(BaseModel):
    """Result of loading a plugin."""
    plugin_id: str
    success: bool
    error: Optional[str] = None
    loaded_at: datetime = Field(default_factory=datetime.utcnow)


class RegistryStats(BaseModel):
    """Plugin registry statistics."""
    total_plugins: int
    active_plugins: int
    plugins_by_type: Dict[str, int]
    failed_plugins: int
    last_scan: Optional[datetime] = None


# ============================================================================
# PLUGIN REGISTRY
# ============================================================================


class PluginRegistry:
    """
    Central registry for all RISKCAST plugins.
    
    Usage:
        registry = PluginRegistry()
        
        # Register plugins
        registry.register(MySignalPlugin())
        
        # Load plugins from directory
        await registry.load_plugins_from_directory("/plugins")
        
        # Initialize all plugins
        await registry.initialize_all(configs)
        
        # Get plugins
        signal_plugins = registry.get_plugins_by_type(PluginType.SIGNAL_SOURCE)
        
        # Shutdown
        await registry.shutdown_all()
    """
    
    def __init__(self):
        self._plugins: Dict[str, BasePlugin] = {}
        self._by_type: Dict[PluginType, List[str]] = {t: [] for t in PluginType}
        self._configs: Dict[str, PluginConfig] = {}
        self._load_results: List[PluginLoadResult] = []
        self._last_scan: Optional[datetime] = None
    
    # ========================================================================
    # REGISTRATION
    # ========================================================================
    
    def register(self, plugin: BasePlugin) -> bool:
        """
        Register a plugin.
        
        Args:
            plugin: Plugin instance to register
            
        Returns:
            True if registered successfully
        """
        try:
            metadata = plugin.metadata
            plugin_id = metadata.plugin_id
            
            # Check for duplicates
            if plugin_id in self._plugins:
                logger.warning(
                    "plugin_already_registered",
                    plugin_id=plugin_id,
                )
                return False
            
            # Validate metadata
            if not self._validate_metadata(metadata):
                logger.error(
                    "invalid_plugin_metadata",
                    plugin_id=plugin_id,
                )
                return False
            
            # Register
            self._plugins[plugin_id] = plugin
            self._by_type[metadata.plugin_type].append(plugin_id)
            
            logger.info(
                "plugin_registered",
                plugin_id=plugin_id,
                type=metadata.plugin_type.value,
                version=metadata.version,
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "plugin_registration_failed",
                error=str(e),
            )
            return False
    
    def unregister(self, plugin_id: str) -> bool:
        """
        Unregister a plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            True if unregistered successfully
        """
        if plugin_id not in self._plugins:
            return False
        
        plugin = self._plugins[plugin_id]
        plugin_type = plugin.metadata.plugin_type
        
        del self._plugins[plugin_id]
        self._by_type[plugin_type].remove(plugin_id)
        
        logger.info("plugin_unregistered", plugin_id=plugin_id)
        
        return True
    
    def _validate_metadata(self, metadata: PluginMetadata) -> bool:
        """Validate plugin metadata."""
        if not metadata.name:
            return False
        if not metadata.version:
            return False
        return True
    
    # ========================================================================
    # RETRIEVAL
    # ========================================================================
    
    def get_plugin(self, plugin_id: str) -> Optional[BasePlugin]:
        """
        Get a plugin by ID.
        
        Args:
            plugin_id: Plugin identifier (type:name)
            
        Returns:
            Plugin instance or None
        """
        return self._plugins.get(plugin_id)
    
    def get_plugin_by_name(
        self,
        plugin_type: PluginType,
        name: str,
    ) -> Optional[BasePlugin]:
        """
        Get a plugin by type and name.
        
        Args:
            plugin_type: Plugin type
            name: Plugin name
            
        Returns:
            Plugin instance or None
        """
        plugin_id = f"{plugin_type.value}:{name}"
        return self._plugins.get(plugin_id)
    
    def get_plugins_by_type(self, plugin_type: PluginType) -> List[BasePlugin]:
        """
        Get all plugins of a type.
        
        Args:
            plugin_type: Type of plugins to get
            
        Returns:
            List of plugin instances
        """
        plugin_ids = self._by_type.get(plugin_type, [])
        return [self._plugins[pid] for pid in plugin_ids if pid in self._plugins]
    
    def get_all_plugins(self) -> List[BasePlugin]:
        """Get all registered plugins."""
        return list(self._plugins.values())
    
    def list_plugins(self) -> List[PluginMetadata]:
        """List metadata for all plugins."""
        return [p.metadata for p in self._plugins.values()]
    
    def get_signal_sources(self) -> List[SignalSourcePlugin]:
        """Get all signal source plugins."""
        plugins = self.get_plugins_by_type(PluginType.SIGNAL_SOURCE)
        return [p for p in plugins if isinstance(p, SignalSourcePlugin)]
    
    def get_action_types(self) -> List[ActionTypePlugin]:
        """Get all action type plugins."""
        plugins = self.get_plugins_by_type(PluginType.ACTION_TYPE)
        return [p for p in plugins if isinstance(p, ActionTypePlugin)]
    
    def get_delivery_channels(self) -> List[DeliveryPlugin]:
        """Get all delivery plugins."""
        plugins = self.get_plugins_by_type(PluginType.DELIVERY)
        return [p for p in plugins if isinstance(p, DeliveryPlugin)]
    
    def get_validators(self) -> List[ValidatorPlugin]:
        """Get all validator plugins."""
        plugins = self.get_plugins_by_type(PluginType.VALIDATOR)
        return [p for p in plugins if isinstance(p, ValidatorPlugin)]
    
    # ========================================================================
    # DYNAMIC LOADING
    # ========================================================================
    
    async def load_plugins_from_directory(
        self,
        directory: str,
        recursive: bool = True,
    ) -> List[PluginLoadResult]:
        """
        Load plugins from a directory.
        
        Plugins should be Python files with a `Plugin` class.
        
        Args:
            directory: Directory path
            recursive: Search subdirectories
            
        Returns:
            List of load results
        """
        path = Path(directory)
        results = []
        
        if not path.exists():
            logger.warning(
                "plugin_directory_not_found",
                directory=directory,
            )
            return results
        
        # Find plugin files
        pattern = "**/*.py" if recursive else "*.py"
        
        for plugin_file in path.glob(pattern):
            if plugin_file.name.startswith("_"):
                continue
            
            result = await self._load_plugin_file(plugin_file)
            results.append(result)
            self._load_results.append(result)
        
        self._last_scan = datetime.utcnow()
        
        logger.info(
            "plugins_loaded_from_directory",
            directory=directory,
            total=len(results),
            successful=sum(1 for r in results if r.success),
        )
        
        return results
    
    async def _load_plugin_file(self, plugin_file: Path) -> PluginLoadResult:
        """Load a single plugin file."""
        module_name = plugin_file.stem
        
        try:
            # Load module
            spec = importlib.util.spec_from_file_location(
                module_name,
                plugin_file,
            )
            if spec is None or spec.loader is None:
                raise ImportError(f"Cannot load spec for {plugin_file}")
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Look for Plugin class
            if not hasattr(module, "Plugin"):
                return PluginLoadResult(
                    plugin_id=module_name,
                    success=False,
                    error="No Plugin class found",
                )
            
            # Instantiate and register
            plugin_class = getattr(module, "Plugin")
            plugin = plugin_class()
            
            if not isinstance(plugin, BasePlugin):
                return PluginLoadResult(
                    plugin_id=module_name,
                    success=False,
                    error="Plugin class must inherit from BasePlugin",
                )
            
            success = self.register(plugin)
            
            return PluginLoadResult(
                plugin_id=plugin.metadata.plugin_id,
                success=success,
                error=None if success else "Registration failed",
            )
            
        except Exception as e:
            logger.error(
                "plugin_load_failed",
                file=str(plugin_file),
                error=str(e),
            )
            return PluginLoadResult(
                plugin_id=module_name,
                success=False,
                error=str(e),
            )
    
    # ========================================================================
    # LIFECYCLE MANAGEMENT
    # ========================================================================
    
    async def initialize_all(
        self,
        configs: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, bool]:
        """
        Initialize all registered plugins.
        
        Args:
            configs: Configuration dict by plugin_id
            
        Returns:
            Dict of plugin_id -> success
        """
        configs = configs or {}
        results = {}
        
        for plugin_id, plugin in self._plugins.items():
            config = configs.get(plugin_id, {})
            
            try:
                plugin._set_status(PluginStatus.INITIALIZING)
                await plugin.initialize(config)
                plugin._set_status(PluginStatus.ACTIVE)
                plugin._config = config
                results[plugin_id] = True
                
                logger.info(
                    "plugin_initialized",
                    plugin_id=plugin_id,
                )
                
            except Exception as e:
                plugin._set_status(PluginStatus.ERROR, str(e))
                results[plugin_id] = False
                
                logger.error(
                    "plugin_init_failed",
                    plugin_id=plugin_id,
                    error=str(e),
                )
        
        return results
    
    async def initialize_plugin(
        self,
        plugin_id: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Initialize a single plugin."""
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return False
        
        config = config or {}
        
        try:
            plugin._set_status(PluginStatus.INITIALIZING)
            await plugin.initialize(config)
            plugin._set_status(PluginStatus.ACTIVE)
            plugin._config = config
            return True
        except Exception as e:
            plugin._set_status(PluginStatus.ERROR, str(e))
            return False
    
    async def shutdown_all(self) -> Dict[str, bool]:
        """
        Shutdown all plugins.
        
        Returns:
            Dict of plugin_id -> success
        """
        results = {}
        
        for plugin_id, plugin in self._plugins.items():
            try:
                await plugin.shutdown()
                plugin._set_status(PluginStatus.SHUTDOWN)
                results[plugin_id] = True
                
            except Exception as e:
                logger.error(
                    "plugin_shutdown_failed",
                    plugin_id=plugin_id,
                    error=str(e),
                )
                results[plugin_id] = False
        
        return results
    
    async def shutdown_plugin(self, plugin_id: str) -> bool:
        """Shutdown a single plugin."""
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return False
        
        try:
            await plugin.shutdown()
            plugin._set_status(PluginStatus.SHUTDOWN)
            return True
        except Exception:
            return False
    
    # ========================================================================
    # HEALTH & STATUS
    # ========================================================================
    
    async def get_health(self) -> Dict[str, PluginHealth]:
        """
        Get health status for all plugins.
        
        Returns:
            Dict of plugin_id -> health
        """
        health = {}
        
        for plugin_id, plugin in self._plugins.items():
            try:
                health[plugin_id] = await plugin.health_check()
            except Exception as e:
                health[plugin_id] = PluginHealth(
                    plugin_id=plugin_id,
                    status=PluginStatus.ERROR,
                    healthy=False,
                    message=str(e),
                )
        
        return health
    
    async def get_plugin_health(self, plugin_id: str) -> Optional[PluginHealth]:
        """Get health for a specific plugin."""
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return None
        
        try:
            return await plugin.health_check()
        except Exception as e:
            return PluginHealth(
                plugin_id=plugin_id,
                status=PluginStatus.ERROR,
                healthy=False,
                message=str(e),
            )
    
    def get_stats(self) -> RegistryStats:
        """Get registry statistics."""
        active = sum(
            1 for p in self._plugins.values()
            if p.status == PluginStatus.ACTIVE
        )
        failed = sum(
            1 for p in self._plugins.values()
            if p.status == PluginStatus.ERROR
        )
        
        by_type = {
            t.value: len(self._by_type[t])
            for t in PluginType
        }
        
        return RegistryStats(
            total_plugins=len(self._plugins),
            active_plugins=active,
            plugins_by_type=by_type,
            failed_plugins=failed,
            last_scan=self._last_scan,
        )
    
    # ========================================================================
    # CONFIGURATION
    # ========================================================================
    
    def set_plugin_config(
        self,
        plugin_id: str,
        config: Dict[str, Any],
    ) -> bool:
        """
        Update plugin configuration.
        
        Note: Plugin may need reinitialization for config to take effect.
        """
        if plugin_id not in self._plugins:
            return False
        
        self._configs[plugin_id] = PluginConfig(
            plugin_id=plugin_id,
            config=config,
        )
        
        return True
    
    def get_plugin_config(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """Get plugin configuration."""
        config = self._configs.get(plugin_id)
        if config:
            return config.config
        
        plugin = self._plugins.get(plugin_id)
        if plugin:
            return plugin.config
        
        return None
    
    def enable_plugin(self, plugin_id: str) -> bool:
        """Enable a plugin."""
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return False
        
        # Re-enable requires reinitializing
        # For now, just update metadata
        return True
    
    def disable_plugin(self, plugin_id: str) -> bool:
        """Disable a plugin."""
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return False
        
        plugin._set_status(PluginStatus.DISABLED)
        return True


# ============================================================================
# SINGLETON
# ============================================================================


_plugin_registry: Optional[PluginRegistry] = None


def get_plugin_registry() -> PluginRegistry:
    """Get global plugin registry instance."""
    global _plugin_registry
    if _plugin_registry is None:
        _plugin_registry = PluginRegistry()
    return _plugin_registry
