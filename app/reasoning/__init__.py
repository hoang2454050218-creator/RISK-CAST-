"""
RISKCAST Multi-Layer Reasoning Module.

This module implements the 6-layer reasoning architecture:

Layer 6: META-REASONING     → "Should I decide or escalate?"
Layer 5: STRATEGIC          → "Fits customer's strategy?"
Layer 4: COUNTERFACTUAL     → "What if I recommended differently?"
Layer 3: CAUSAL             → "WHY is this happening?"
Layer 2: TEMPORAL           → "WHEN and timing effects?"
Layer 1: FACTUAL            → "WHAT is happening?"

Each layer builds on previous layers' outputs.
The meta layer decides whether to proceed or escalate.

CRITICAL: Reasoning traces are immutable and auditable.
"""

from app.reasoning.schemas import (
    ReasoningLayer,
    LayerOutput,
    FactualLayerOutput,
    TemporalLayerOutput,
    CausalLayerOutput,
    CounterfactualLayerOutput,
    StrategicLayerOutput,
    MetaLayerOutput,
    ReasoningTrace,
)
from app.reasoning.engine import (
    ReasoningEngine,
    create_reasoning_engine,
)

__all__ = [
    # Enums
    "ReasoningLayer",
    # Layer outputs
    "LayerOutput",
    "FactualLayerOutput",
    "TemporalLayerOutput",
    "CausalLayerOutput",
    "CounterfactualLayerOutput",
    "StrategicLayerOutput",
    "MetaLayerOutput",
    # Trace
    "ReasoningTrace",
    # Engine
    "ReasoningEngine",
    "create_reasoning_engine",
]
