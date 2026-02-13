"""
Deterministic Trace ID Generation.

Generates reproducible trace IDs from inputs to ensure
that the same inputs produce the same trace ID.

Addresses audit gap: A1.1 Deterministic Reasoning (+5 points)
"""

import hashlib
import json
from typing import Any, Optional
from datetime import datetime


def generate_deterministic_trace_id(
    signal: Any,
    context: Any,
    reference_timestamp: Optional[str] = None
) -> str:
    """
    Generate reproducible trace ID from inputs.
    
    Same inputs will always produce the same trace ID, enabling:
    - Reproducibility of decisions
    - Deduplication of identical requests
    - Testing determinism
    
    Args:
        signal: Signal data (OmenSignal or dict)
        context: Customer context (CustomerContext or dict)
        reference_timestamp: Fixed timestamp for reproducibility (ISO format)
                           If None, uses signal timestamp or current time
                           
    Returns:
        Deterministic trace ID in format: trace_{hash[:24]}
    """
    # Extract signal data
    if hasattr(signal, "model_dump"):
        signal_data = signal.model_dump(mode="json")
    elif hasattr(signal, "__dict__"):
        signal_data = {k: v for k, v in signal.__dict__.items() if not k.startswith("_")}
    elif isinstance(signal, dict):
        signal_data = signal.copy()
    else:
        signal_data = {"value": str(signal)}
    
    # Extract context data
    if hasattr(context, "model_dump"):
        context_data = context.model_dump(mode="json")
    elif hasattr(context, "__dict__"):
        context_data = {k: v for k, v in context.__dict__.items() if not k.startswith("_")}
    elif isinstance(context, dict):
        context_data = context.copy()
    else:
        context_data = {"value": str(context)}
    
    # Determine reference timestamp
    if reference_timestamp is None:
        # Try to get from signal
        if "timestamp" in signal_data:
            ts = signal_data["timestamp"]
            if isinstance(ts, datetime):
                reference_timestamp = ts.isoformat()
            else:
                reference_timestamp = str(ts)
        elif "created_at" in signal_data:
            ts = signal_data["created_at"]
            if isinstance(ts, datetime):
                reference_timestamp = ts.isoformat()
            else:
                reference_timestamp = str(ts)
        else:
            # Use a fixed epoch for completely deterministic behavior
            reference_timestamp = "2024-01-01T00:00:00Z"
    
    # Remove non-deterministic fields
    fields_to_remove = ["trace_id", "created_at", "updated_at", "id", "_sa_instance_state"]
    for data in [signal_data, context_data]:
        for field in fields_to_remove:
            data.pop(field, None)
    
    # Create canonical representation
    canonical = {
        "signal": signal_data,
        "context": context_data,
        "timestamp": reference_timestamp
    }
    
    # Sort keys and serialize to ensure consistent ordering
    canonical_str = json.dumps(canonical, sort_keys=True, default=str)
    
    # Generate SHA-256 hash
    hash_bytes = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()
    
    return f"trace_{hash_bytes[:24]}"


def generate_decision_id(
    signal_id: str,
    customer_id: str,
    action_type: str,
    timestamp: Optional[str] = None
) -> str:
    """
    Generate deterministic decision ID.
    
    Args:
        signal_id: The signal that triggered the decision
        customer_id: Customer for whom decision was made
        action_type: Type of action recommended
        timestamp: Reference timestamp (ISO format)
        
    Returns:
        Deterministic decision ID
    """
    if timestamp is None:
        timestamp = "2024-01-01T00:00:00Z"
    
    canonical = f"{signal_id}:{customer_id}:{action_type}:{timestamp}"
    hash_bytes = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    
    return f"dec_{hash_bytes[:20]}"


def generate_audit_id(
    decision_id: str,
    event_type: str,
    sequence: int
) -> str:
    """
    Generate deterministic audit record ID.
    
    Args:
        decision_id: The decision being audited
        event_type: Type of audit event
        sequence: Sequence number in the audit chain
        
    Returns:
        Deterministic audit ID
    """
    canonical = f"{decision_id}:{event_type}:{sequence}"
    hash_bytes = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    
    return f"aud_{hash_bytes[:20]}"


def verify_trace_determinism(
    signal1: Any,
    context1: Any,
    signal2: Any,
    context2: Any,
    reference_timestamp: str
) -> bool:
    """
    Verify that two sets of inputs produce the same trace ID.
    
    Useful for testing determinism.
    
    Returns:
        True if both inputs produce the same trace ID
    """
    id1 = generate_deterministic_trace_id(signal1, context1, reference_timestamp)
    id2 = generate_deterministic_trace_id(signal2, context2, reference_timestamp)
    
    return id1 == id2
