"""
Role-Based Access Control — Full Enforcement.

Defines:
- Role hierarchy (VIEWER < ANALYST < MANAGER < ADMIN < OWNER)
- Fine-grained permissions per role
- require_role / require_permission decorators for endpoint-level checks
"""

from enum import IntEnum, Enum
from functools import wraps
from typing import Callable, Optional

import structlog
from fastapi import HTTPException, Request

logger = structlog.get_logger(__name__)


class Role(IntEnum):
    """Ordered role hierarchy — higher value = more permissions."""

    VIEWER = 10
    ANALYST = 20
    MANAGER = 30
    ADMIN = 40
    OWNER = 50

    @classmethod
    def from_str(cls, value: str) -> "Role":
        """Convert string role name to Role enum, case-insensitive."""
        mapping = {
            "viewer": cls.VIEWER,
            "analyst": cls.ANALYST,
            "manager": cls.MANAGER,
            "admin": cls.ADMIN,
            "owner": cls.OWNER,
            # Legacy mapping
            "member": cls.VIEWER,
        }
        return mapping.get(value.lower(), cls.VIEWER)


class Permission(str, Enum):
    """Fine-grained permissions beyond role hierarchy."""

    SIGNALS_READ = "signals:read"
    SIGNALS_INGEST = "signals:ingest"
    ORDERS_READ = "orders:read"
    ORDERS_WRITE = "orders:write"
    CUSTOMERS_READ = "customers:read"
    CUSTOMERS_WRITE = "customers:write"
    PAYMENTS_READ = "payments:read"
    PAYMENTS_WRITE = "payments:write"
    ROUTES_READ = "routes:read"
    ROUTES_WRITE = "routes:write"
    INCIDENTS_READ = "incidents:read"
    INCIDENTS_WRITE = "incidents:write"
    DECISIONS_READ = "decisions:read"
    DECISIONS_APPROVE = "decisions:approve"
    SETTINGS_READ = "settings:read"
    SETTINGS_WRITE = "settings:write"
    USERS_MANAGE = "users:manage"
    API_KEYS_MANAGE = "api_keys:manage"
    RECONCILE_RUN = "reconcile:run"
    EXPORT_DATA = "data:export"
    AUDIT_READ = "audit:read"
    CHAT_USE = "chat:use"
    BRIEFS_READ = "briefs:read"
    ANALYTICS_READ = "analytics:read"


# ── Role → Permission Mapping ─────────────────────────────────────────────

_VIEWER_PERMS = frozenset({
    Permission.SIGNALS_READ,
    Permission.ORDERS_READ,
    Permission.CUSTOMERS_READ,
    Permission.PAYMENTS_READ,
    Permission.ROUTES_READ,
    Permission.INCIDENTS_READ,
    Permission.DECISIONS_READ,
    Permission.BRIEFS_READ,
    Permission.ANALYTICS_READ,
})

_ANALYST_PERMS = _VIEWER_PERMS | frozenset({
    Permission.ORDERS_WRITE,
    Permission.CUSTOMERS_WRITE,
    Permission.PAYMENTS_WRITE,
    Permission.ROUTES_WRITE,
    Permission.INCIDENTS_WRITE,
    Permission.EXPORT_DATA,
    Permission.AUDIT_READ,
    Permission.CHAT_USE,
})

_MANAGER_PERMS = _ANALYST_PERMS | frozenset({
    Permission.DECISIONS_APPROVE,
    Permission.SETTINGS_READ,
})

_ADMIN_PERMS = _MANAGER_PERMS | frozenset({
    Permission.SETTINGS_WRITE,
    Permission.USERS_MANAGE,
    Permission.RECONCILE_RUN,
    Permission.API_KEYS_MANAGE,
    Permission.SIGNALS_INGEST,
})

_OWNER_PERMS = frozenset(Permission)  # All permissions

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.VIEWER: _VIEWER_PERMS,
    Role.ANALYST: _ANALYST_PERMS,
    Role.MANAGER: _MANAGER_PERMS,
    Role.ADMIN: _ADMIN_PERMS,
    Role.OWNER: _OWNER_PERMS,
}


def _extract_role_from_request(request: Request) -> Role:
    """Extract Role from request.state (set by TenantMiddleware)."""
    role_str = getattr(request.state, "user_role", "viewer")
    return Role.from_str(role_str)


def has_permission(role: Role, permission: Permission) -> bool:
    """Check if a role has a specific permission."""
    return permission in ROLE_PERMISSIONS.get(role, frozenset())


def has_role(current_role: Role, minimum_role: Role) -> bool:
    """Check if current role meets or exceeds minimum role level."""
    return current_role >= minimum_role


def check_permission(request: Request, permission: Permission) -> None:
    """
    Check that the current request has the required permission.

    Raises HTTPException 403 if denied.
    """
    role = _extract_role_from_request(request)
    if not has_permission(role, permission):
        user_id = getattr(request.state, "user_id", "unknown")
        logger.warning(
            "permission_denied",
            user_id=user_id,
            role=role.name,
            required_permission=permission.value,
            path=request.url.path,
        )
        raise HTTPException(
            status_code=403,
            detail={
                "error": "insufficient_permissions",
                "required": permission.value,
                "your_role": role.name.lower(),
            },
        )


def check_role(request: Request, minimum_role: Role) -> None:
    """
    Check that the current request meets the minimum role level.

    Raises HTTPException 403 if denied.
    """
    role = _extract_role_from_request(request)
    if not has_role(role, minimum_role):
        user_id = getattr(request.state, "user_id", "unknown")
        logger.warning(
            "role_denied",
            user_id=user_id,
            role=role.name,
            required_role=minimum_role.name,
            path=request.url.path,
        )
        raise HTTPException(
            status_code=403,
            detail={
                "error": "insufficient_role",
                "required_role": minimum_role.name.lower(),
                "your_role": role.name.lower(),
            },
        )
