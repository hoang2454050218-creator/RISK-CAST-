"""
RiskCast API entry point — alias for OMEN integration.

Usage:
    uvicorn riskcast.api.app:app --host 0.0.0.0 --port 8001

This module re-exports the app from riskcast.main so that both entry points work:
    - riskcast.main:app          (original)
    - riskcast.api.app:app       (OMEN spec)
"""

from riskcast.main import app

__all__ = ["app"]
