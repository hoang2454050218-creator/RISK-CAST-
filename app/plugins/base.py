"""
Plugin Base Classes.

Defines the interface for all plugin types in RISKCAST.

Plugin Types:
- SignalSourcePlugin: Add new data sources (e.g., news APIs, weather)
- ActionTypePlugin: Add new action recommendations (e.g., hedge, swap)
- DeliveryPlugin: Add new alert channels (e.g., SMS, Teams)
- ValidatorPlugin: Add custom validation rules
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


# ============================================================================
# ENUMS
# ============================================================================


class PluginType(str, Enum):
    """Types of plugins."""
    SIGNAL_SOURCE = "signal_source"
    ACTION_TYPE = "action_type"
    DELIVERY = "delivery"
    VALIDATOR = "validator"


class PluginStatus(str, Enum):
    """Plugin lifecycle status."""
    REGISTERED = "registered"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    DISABLED = "disabled"
    ERROR = "error"
    SHUTDOWN = "shutdown"


# ============================================================================
# SCHEMAS
# ============================================================================


class PluginMetadata(BaseModel):
    """Plugin metadata and configuration."""
    
    # Identity
    name: str = Field(description="Unique plugin name")
    version: str = Field(description="Semantic version (e.g., 1.0.0)")
    plugin_type: PluginType = Field(description="Type of plugin")
    
    # Info
    author: str = Field(default="RISKCAST", description="Plugin author")
    description: str = Field(default="", description="Plugin description")
    homepage: Optional[str] = Field(default=None, description="Plugin homepage URL")
    
    # Configuration
    config_schema: Optional[Dict[str, Any]] = Field(
        default=None,
        description="JSON Schema for plugin configuration"
    )
    required_permissions: List[str] = Field(
        default_factory=list,
        description="Required permissions"
    )
    
    # Status
    enabled: bool = Field(default=True, description="Whether plugin is enabled")
    
    # Dependencies
    dependencies: List[str] = Field(
        default_factory=list,
        description="Other plugins this depends on"
    )
    
    @property
    def plugin_id(self) -> str:
        """Unique plugin identifier."""
        return f"{self.plugin_type.value}:{self.name}"


class PluginHealth(BaseModel):
    """Plugin health status."""
    
    plugin_id: str
    status: PluginStatus
    healthy: bool
    last_check: datetime = Field(default_factory=datetime.utcnow)
    
    # Metrics
    uptime_seconds: float = Field(default=0)
    requests_handled: int = Field(default=0)
    errors_count: int = Field(default=0)
    
    # Details
    message: Optional[str] = Field(default=None)
    details: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# BASE PLUGIN
# ============================================================================


class BasePlugin(ABC):
    """
    Base class for all RISKCAST plugins.
    
    Lifecycle:
    1. Plugin registered with registry
    2. initialize() called with configuration
    3. Plugin becomes active
    4. shutdown() called on cleanup
    
    All plugins must implement:
    - metadata property
    - initialize() method
    - shutdown() method
    """
    
    def __init__(self):
        self._status = PluginStatus.REGISTERED
        self._initialized_at: Optional[datetime] = None
        self._config: Dict[str, Any] = {}
        self._error: Optional[str] = None
    
    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """
        Return plugin metadata.
        
        Must be implemented by all plugins.
        """
        pass
    
    @property
    def status(self) -> PluginStatus:
        """Current plugin status."""
        return self._status
    
    @property
    def config(self) -> Dict[str, Any]:
        """Plugin configuration."""
        return self._config
    
    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> None:
        """
        Initialize the plugin with configuration.
        
        Called once when plugin is loaded. Should:
        - Validate configuration
        - Establish connections
        - Load resources
        
        Raises:
            Exception: If initialization fails
        """
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """
        Cleanup on shutdown.
        
        Should:
        - Close connections
        - Release resources
        - Flush buffers
        """
        pass
    
    async def health_check(self) -> PluginHealth:
        """
        Check plugin health.
        
        Override for custom health checks.
        
        Returns:
            PluginHealth with current status
        """
        return PluginHealth(
            plugin_id=self.metadata.plugin_id,
            status=self._status,
            healthy=self._status == PluginStatus.ACTIVE,
            uptime_seconds=(
                (datetime.utcnow() - self._initialized_at).total_seconds()
                if self._initialized_at else 0
            ),
            message=self._error,
        )
    
    def _set_status(self, status: PluginStatus, error: Optional[str] = None) -> None:
        """Update plugin status."""
        self._status = status
        self._error = error
        
        if status == PluginStatus.ACTIVE:
            self._initialized_at = datetime.utcnow()
        
        logger.info(
            "plugin_status_changed",
            plugin_id=self.metadata.plugin_id,
            status=status.value,
            error=error,
        )


# ============================================================================
# SIGNAL SOURCE PLUGIN
# ============================================================================


class SignalSourcePlugin(BasePlugin):
    """
    Plugin for signal data sources.
    
    Add new data providers to OMEN signal pipeline.
    
    Examples:
    - News API integration
    - Weather data feeds
    - Social media sentiment
    - Custom market data
    """
    
    @abstractmethod
    async def fetch_signals(
        self,
        query: Dict[str, Any],
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Fetch signals from this source.
        
        Args:
            query: Query parameters (source-specific)
            limit: Maximum signals to return
            
        Returns:
            List of signal dicts with:
            - signal_id: Unique identifier
            - source: Source name
            - event_type: Type of event
            - probability: Event probability (0-1)
            - confidence: Data confidence (0-1)
            - timestamp: Signal timestamp
            - data: Source-specific data
        """
        pass
    
    @abstractmethod
    async def get_signal_by_id(
        self,
        signal_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific signal by ID.
        
        Args:
            signal_id: Signal identifier
            
        Returns:
            Signal dict or None if not found
        """
        pass
    
    async def validate_signal(
        self,
        signal: Dict[str, Any],
    ) -> bool:
        """
        Validate a signal from this source.
        
        Override for custom validation.
        
        Args:
            signal: Signal to validate
            
        Returns:
            True if valid
        """
        required = ["signal_id", "source", "event_type", "probability"]
        return all(key in signal for key in required)
    
    async def get_source_status(self) -> Dict[str, Any]:
        """
        Get data source status.
        
        Returns:
            Status dict with availability, latency, etc.
        """
        return {
            "source": self.metadata.name,
            "available": self._status == PluginStatus.ACTIVE,
            "last_fetch": None,
            "signals_fetched": 0,
        }


# ============================================================================
# ACTION TYPE PLUGIN
# ============================================================================


class ActionTypePlugin(BasePlugin):
    """
    Plugin for action recommendation types.
    
    Add new types of actions RISKCAST can recommend.
    
    Examples:
    - Hedge recommendation
    - Swap carrier
    - Split shipment
    - Pre-position inventory
    """
    
    @property
    @abstractmethod
    def action_type_name(self) -> str:
        """Unique action type name (e.g., 'hedge', 'swap_carrier')."""
        pass
    
    @abstractmethod
    async def evaluate_feasibility(
        self,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Evaluate if this action is feasible given context.
        
        Args:
            context: Decision context including:
            - customer_id: Customer identifier
            - shipment: Shipment details
            - exposure: Exposure amount
            - signal: Triggering signal
            
        Returns:
            Feasibility result:
            - feasible: bool
            - reason: Why (not) feasible
            - confidence: Feasibility confidence
            - prerequisites: What's needed
        """
        pass
    
    @abstractmethod
    async def estimate_cost(
        self,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Estimate the cost of this action.
        
        Args:
            context: Decision context
            
        Returns:
            Cost estimate:
            - total_cost_usd: Total cost
            - breakdown: Cost breakdown
            - confidence: Cost confidence
            - valid_until: Estimate validity
        """
        pass
    
    @abstractmethod
    async def generate_steps(
        self,
        context: Dict[str, Any],
    ) -> List[str]:
        """
        Generate execution steps for this action.
        
        Args:
            context: Decision context
            
        Returns:
            List of steps to execute action
        """
        pass
    
    async def estimate_time(
        self,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Estimate time to execute action.
        
        Override for custom estimates.
        
        Returns:
            Time estimate:
            - min_hours: Minimum hours
            - max_hours: Maximum hours
            - expected_hours: Expected hours
        """
        return {
            "min_hours": 1,
            "max_hours": 24,
            "expected_hours": 4,
        }


# ============================================================================
# DELIVERY PLUGIN
# ============================================================================


class DeliveryPlugin(BasePlugin):
    """
    Plugin for alert delivery channels.
    
    Add new ways to deliver alerts to customers.
    
    Examples:
    - SMS via Twilio
    - Microsoft Teams
    - Slack webhook
    - Email
    - Push notifications
    """
    
    @property
    @abstractmethod
    def channel_name(self) -> str:
        """Unique channel name (e.g., 'sms', 'teams')."""
        pass
    
    @abstractmethod
    async def deliver(
        self,
        message: Dict[str, Any],
        recipient: str,
    ) -> Dict[str, Any]:
        """
        Deliver an alert via this channel.
        
        Args:
            message: Message content:
            - title: Alert title
            - body: Alert body
            - urgency: Urgency level
            - action_url: Optional action URL
            recipient: Recipient identifier (phone, email, etc.)
            
        Returns:
            Delivery result:
            - delivery_id: Unique delivery ID
            - status: pending/sent/delivered/failed
            - timestamp: Delivery timestamp
            - error: Error message if failed
        """
        pass
    
    @abstractmethod
    async def check_delivery_status(
        self,
        delivery_id: str,
    ) -> Dict[str, Any]:
        """
        Check delivery status.
        
        Args:
            delivery_id: Delivery identifier
            
        Returns:
            Status:
            - status: Current status
            - delivered_at: Delivery timestamp
            - read_at: Read timestamp (if available)
        """
        pass
    
    async def validate_recipient(
        self,
        recipient: str,
    ) -> bool:
        """
        Validate recipient format.
        
        Override for channel-specific validation.
        
        Args:
            recipient: Recipient identifier
            
        Returns:
            True if valid format
        """
        return bool(recipient)
    
    async def get_channel_status(self) -> Dict[str, Any]:
        """
        Get delivery channel status.
        
        Returns:
            Status including availability, rate limits, etc.
        """
        return {
            "channel": self.channel_name,
            "available": self._status == PluginStatus.ACTIVE,
            "rate_limit_remaining": None,
        }


# ============================================================================
# VALIDATOR PLUGIN
# ============================================================================


class ValidatorPlugin(BasePlugin):
    """
    Plugin for custom validation rules.
    
    Add custom validation logic for decisions.
    
    Examples:
    - Compliance validators
    - Business rule validators
    - Risk limit validators
    """
    
    @property
    @abstractmethod
    def validator_name(self) -> str:
        """Unique validator name."""
        pass
    
    @property
    @abstractmethod
    def validation_stage(self) -> str:
        """
        When to run validation.
        
        Options:
        - 'pre_decision': Before decision is made
        - 'post_decision': After decision, before delivery
        - 'pre_delivery': Just before alert delivery
        """
        pass
    
    @abstractmethod
    async def validate(
        self,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Run validation.
        
        Args:
            data: Data to validate (stage-dependent)
            
        Returns:
            Validation result:
            - valid: bool
            - errors: List of error messages
            - warnings: List of warnings
            - modified_data: Optionally modified data
        """
        pass
    
    async def get_validation_rules(self) -> List[Dict[str, Any]]:
        """
        Get list of validation rules.
        
        Returns:
            List of rules with name, description, severity
        """
        return []
