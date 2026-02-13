"""
Backtesting Framework for RISKCAST.

Validates decision quality against historical events with known outcomes.

Usage:
    from app.backtest import BacktestFramework, BacktestEvent
    
    # Create framework
    framework = BacktestFramework(decision_engine)
    
    # Load historical events
    events = load_historical_events("2024-01-01", "2024-12-31")
    
    # Run backtest
    summary = await framework.run(events, customer_context)
    
    # Analyze results
    print(f"Accuracy: {summary.accuracy:.0%}")
    print(f"Value captured: ${summary.total_value_captured_usd:,.0f}")
"""

from app.backtest.schemas import (
    BacktestEvent,
    BacktestResult,
    BacktestSummary,
    CalibrationBucket,
    AccuracyByCategory,
)
from app.backtest.framework import (
    BacktestFramework,
    create_backtest_framework,
)

__all__ = [
    # Schemas
    "BacktestEvent",
    "BacktestResult",
    "BacktestSummary",
    "CalibrationBucket",
    "AccuracyByCategory",
    # Framework
    "BacktestFramework",
    "create_backtest_framework",
]
