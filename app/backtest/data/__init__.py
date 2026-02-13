"""
Backtest Data Module.

Contains historical event data for backtesting RISKCAST decisions.

Components:
- seed.py: Historical event seeding and annotated disruption data
"""

from app.backtest.data.seed import (
    HistoricalEvent,
    HISTORICAL_EVENTS,
    BacktestSeeder,
    get_historical_events,
)

__all__ = [
    "HistoricalEvent",
    "HISTORICAL_EVENTS",
    "BacktestSeeder",
    "get_historical_events",
]
