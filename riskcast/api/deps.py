"""
FastAPI dependencies for V2 API routes.

Re-exports auth dependencies for convenience.
"""

from riskcast.auth.dependencies import get_company_id, get_db, get_user_id

__all__ = ["get_db", "get_company_id", "get_user_id"]
