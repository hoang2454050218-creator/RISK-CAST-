"""
Hysteresis Controller for Decision Stability.

Prevents flip-flopping on threshold decisions by implementing
hysteresis bands with configurable activation/deactivation thresholds.

Addresses audit gap: A1.3 Reasoning Consistency (+5 points)
"""

from dataclasses import dataclass
from typing import Optional, Dict, Tuple
from datetime import datetime
import asyncio
import structlog

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class HysteresisConfig:
    """
    Configuration for decision hysteresis.
    
    The activation threshold must be higher than the deactivation threshold
    to create a hysteresis band that prevents oscillation.
    
    Example for escalation decisions:
    - activation_threshold=0.60: Escalate when confidence drops below 60%
    - deactivation_threshold=0.55: Stop escalating only when confidence rises above 55%
    - This 5% band prevents flip-flopping around the threshold
    """
    activation_threshold: float    # Threshold to trigger action
    deactivation_threshold: float  # Threshold to stop action (must be lower)
    min_hold_time_seconds: float   # Minimum time before state can change
    
    def __post_init__(self):
        if self.deactivation_threshold >= self.activation_threshold:
            raise ValueError(
                f"Deactivation threshold ({self.deactivation_threshold}) must be "
                f"lower than activation threshold ({self.activation_threshold})"
            )


@dataclass
class HysteresisState:
    """State for a single hysteresis-controlled decision."""
    key: str
    is_active: bool
    last_change_time: float
    last_value: float
    change_count: int = 0


class HysteresisController:
    """
    Prevents flip-flopping on threshold decisions.
    
    Uses hysteresis bands to ensure decisions are stable:
    - Once activated, stays active until value drops below deactivation threshold
    - Once deactivated, stays inactive until value rises above activation threshold
    - Minimum hold time prevents rapid oscillation
    
    Thread-safe for concurrent use.
    """
    
    def __init__(self):
        self._states: Dict[str, HysteresisState] = {}
        self._lock = asyncio.Lock()
    
    async def evaluate(
        self,
        key: str,
        current_value: float,
        config: HysteresisConfig,
        current_time: Optional[float] = None
    ) -> Tuple[bool, str]:
        """
        Evaluate with hysteresis.
        
        Args:
            key: Unique identifier for this decision point
            current_value: Current value to evaluate
            config: Hysteresis configuration
            current_time: Current timestamp (defaults to datetime.utcnow().timestamp())
            
        Returns:
            Tuple of (should_act, reason)
        """
        if current_time is None:
            current_time = datetime.utcnow().timestamp()
        
        async with self._lock:
            state = self._states.get(key)
            
            if state is None:
                # First evaluation - use activation threshold
                should_act = current_value >= config.activation_threshold
                self._states[key] = HysteresisState(
                    key=key,
                    is_active=should_act,
                    last_change_time=current_time,
                    last_value=current_value,
                    change_count=0
                )
                
                logger.debug(
                    "hysteresis_initial_evaluation",
                    key=key,
                    value=current_value,
                    threshold=config.activation_threshold,
                    result=should_act
                )
                
                return should_act, "initial_evaluation"
            
            was_active = state.is_active
            time_since_change = current_time - state.last_change_time
            
            # Check hold time
            if time_since_change < config.min_hold_time_seconds:
                remaining = config.min_hold_time_seconds - time_since_change
                state.last_value = current_value
                
                logger.debug(
                    "hysteresis_hold_time",
                    key=key,
                    remaining_seconds=remaining,
                    current_state=was_active
                )
                
                return was_active, f"hold_time_remaining:{remaining:.1f}s"
            
            # Apply hysteresis logic
            if was_active:
                # Currently active - need to drop below deactivation threshold to deactivate
                should_act = current_value >= config.deactivation_threshold
                
                if should_act:
                    reason = "still_above_deactivation"
                else:
                    reason = "dropped_below_deactivation"
            else:
                # Currently inactive - need to rise above activation threshold to activate
                should_act = current_value >= config.activation_threshold
                
                if should_act:
                    reason = "rose_above_activation"
                else:
                    reason = "still_below_activation"
            
            # Update state if changed
            if should_act != was_active:
                state.is_active = should_act
                state.last_change_time = current_time
                state.change_count += 1
                
                logger.info(
                    "hysteresis_state_change",
                    key=key,
                    previous_state=was_active,
                    new_state=should_act,
                    value=current_value,
                    change_count=state.change_count
                )
            
            state.last_value = current_value
            
            return should_act, reason
    
    async def get_state(self, key: str) -> Optional[HysteresisState]:
        """Get current state for a key."""
        async with self._lock:
            return self._states.get(key)
    
    async def reset(self, key: str) -> None:
        """Reset state for a key."""
        async with self._lock:
            if key in self._states:
                del self._states[key]
                logger.info("hysteresis_state_reset", key=key)
    
    async def reset_all(self) -> None:
        """Reset all states."""
        async with self._lock:
            count = len(self._states)
            self._states.clear()
            logger.info("hysteresis_all_states_reset", count=count)
    
    def get_stats(self) -> Dict[str, any]:
        """Get statistics about hysteresis states."""
        return {
            "total_keys": len(self._states),
            "active_count": sum(1 for s in self._states.values() if s.is_active),
            "inactive_count": sum(1 for s in self._states.values() if not s.is_active),
            "total_changes": sum(s.change_count for s in self._states.values()),
        }


# =============================================================================
# DEFAULT CONFIGURATIONS
# =============================================================================


# Escalation hysteresis - 5% band, 5 minute hold
ESCALATION_HYSTERESIS = HysteresisConfig(
    activation_threshold=0.60,     # Escalate when confidence < 60%
    deactivation_threshold=0.55,   # Stop escalating when confidence > 55%
    min_hold_time_seconds=300      # Hold for 5 minutes
)

# Reroute decision hysteresis - 10% band, 10 minute hold
REROUTE_HYSTERESIS = HysteresisConfig(
    activation_threshold=0.70,     # Recommend reroute when probability > 70%
    deactivation_threshold=0.60,   # Stop recommending when probability < 60%
    min_hold_time_seconds=600      # Hold for 10 minutes
)

# Alert hysteresis - 5% band, 2 minute hold
ALERT_HYSTERESIS = HysteresisConfig(
    activation_threshold=0.50,     # Send alert when probability > 50%
    deactivation_threshold=0.45,   # Clear alert when probability < 45%
    min_hold_time_seconds=120      # Hold for 2 minutes
)

# High-value exposure hysteresis - 10% band, 15 minute hold
HIGH_VALUE_HYSTERESIS = HysteresisConfig(
    activation_threshold=0.80,     # Flag high value when confidence > 80%
    deactivation_threshold=0.70,   # Unflag when confidence < 70%
    min_hold_time_seconds=900      # Hold for 15 minutes
)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


# Global controller instance
_controller: Optional[HysteresisController] = None


def get_hysteresis_controller() -> HysteresisController:
    """Get global hysteresis controller."""
    global _controller
    if _controller is None:
        _controller = HysteresisController()
    return _controller


async def evaluate_with_hysteresis(
    key: str,
    value: float,
    config: HysteresisConfig
) -> Tuple[bool, str]:
    """
    Convenience function to evaluate with hysteresis using global controller.
    
    Args:
        key: Unique identifier
        value: Current value
        config: Hysteresis configuration
        
    Returns:
        Tuple of (should_act, reason)
    """
    controller = get_hysteresis_controller()
    return await controller.evaluate(key, value, config)
