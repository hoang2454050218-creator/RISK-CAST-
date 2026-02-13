"""
Audit Trail API Schemas.
"""

from typing import Optional

from pydantic import BaseModel, Field


class AuditEventResponse(BaseModel):
    """A single audit event."""
    id: str
    timestamp: str
    action: str
    status: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    user_id: Optional[str] = None
    api_key_prefix: Optional[str] = None
    ip_address: Optional[str] = None
    request_method: Optional[str] = None
    request_path: Optional[str] = None
    details: Optional[dict] = None


class AuditTrailResponse(BaseModel):
    """Paginated audit trail."""
    events: list[AuditEventResponse] = Field(default_factory=list)
    total: int = 0
    has_more: bool = False
    cursor: Optional[str] = None


class AuditIntegrityResponse(BaseModel):
    """Hash chain integrity check result."""
    status: str
    total_entries: int
    chain_intact: bool
    breaks_found: int = 0
