"""
RBAC Tests — Role-Based Access Control.

Tests every role × permission combination to ensure correct enforcement.
"""

import pytest

from riskcast.auth.rbac import (
    Permission,
    Role,
    ROLE_PERMISSIONS,
    check_permission,
    check_role,
    has_permission,
    has_role,
)
from fastapi import HTTPException


# ── Role Hierarchy Tests ─────────────────────────────────────────────────


class TestRoleHierarchy:
    """Test that role ordering and from_str work correctly."""

    def test_role_ordering(self):
        """Roles are ordered: VIEWER < ANALYST < MANAGER < ADMIN < OWNER."""
        assert Role.VIEWER < Role.ANALYST < Role.MANAGER < Role.ADMIN < Role.OWNER

    def test_role_from_str_known(self):
        """Known role strings map correctly."""
        assert Role.from_str("viewer") == Role.VIEWER
        assert Role.from_str("analyst") == Role.ANALYST
        assert Role.from_str("manager") == Role.MANAGER
        assert Role.from_str("admin") == Role.ADMIN
        assert Role.from_str("owner") == Role.OWNER

    def test_role_from_str_case_insensitive(self):
        """Role parsing is case-insensitive."""
        assert Role.from_str("ADMIN") == Role.ADMIN
        assert Role.from_str("Admin") == Role.ADMIN
        assert Role.from_str("aDmIn") == Role.ADMIN

    def test_role_from_str_legacy_member(self):
        """Legacy 'member' role maps to VIEWER."""
        assert Role.from_str("member") == Role.VIEWER

    def test_role_from_str_unknown(self):
        """Unknown role strings default to VIEWER (least privilege)."""
        assert Role.from_str("superuser") == Role.VIEWER
        assert Role.from_str("") == Role.VIEWER
        assert Role.from_str("root") == Role.VIEWER


# ── Permission Mapping Tests ─────────────────────────────────────────────


class TestPermissionMapping:
    """Test that each role has the correct permissions."""

    def test_viewer_can_read(self):
        """Viewers can read signals, orders, customers, etc."""
        assert has_permission(Role.VIEWER, Permission.SIGNALS_READ)
        assert has_permission(Role.VIEWER, Permission.ORDERS_READ)
        assert has_permission(Role.VIEWER, Permission.CUSTOMERS_READ)
        assert has_permission(Role.VIEWER, Permission.DECISIONS_READ)

    def test_viewer_cannot_write(self):
        """Viewers cannot write or modify data."""
        assert not has_permission(Role.VIEWER, Permission.ORDERS_WRITE)
        assert not has_permission(Role.VIEWER, Permission.CUSTOMERS_WRITE)
        assert not has_permission(Role.VIEWER, Permission.SETTINGS_WRITE)

    def test_viewer_cannot_manage(self):
        """Viewers cannot manage users, API keys, or settings."""
        assert not has_permission(Role.VIEWER, Permission.USERS_MANAGE)
        assert not has_permission(Role.VIEWER, Permission.API_KEYS_MANAGE)
        assert not has_permission(Role.VIEWER, Permission.RECONCILE_RUN)

    def test_analyst_can_write(self):
        """Analysts can write orders, export data, and use chat."""
        assert has_permission(Role.ANALYST, Permission.ORDERS_WRITE)
        assert has_permission(Role.ANALYST, Permission.EXPORT_DATA)
        assert has_permission(Role.ANALYST, Permission.CHAT_USE)
        assert has_permission(Role.ANALYST, Permission.AUDIT_READ)

    def test_analyst_cannot_approve(self):
        """Analysts cannot approve decisions or manage settings."""
        assert not has_permission(Role.ANALYST, Permission.DECISIONS_APPROVE)
        assert not has_permission(Role.ANALYST, Permission.SETTINGS_WRITE)

    def test_manager_can_approve(self):
        """Managers can approve decisions and read settings."""
        assert has_permission(Role.MANAGER, Permission.DECISIONS_APPROVE)
        assert has_permission(Role.MANAGER, Permission.SETTINGS_READ)

    def test_manager_cannot_manage_users(self):
        """Managers cannot manage users or API keys."""
        assert not has_permission(Role.MANAGER, Permission.USERS_MANAGE)
        assert not has_permission(Role.MANAGER, Permission.API_KEYS_MANAGE)

    def test_admin_can_manage(self):
        """Admins can manage users, API keys, reconcile, and settings."""
        assert has_permission(Role.ADMIN, Permission.USERS_MANAGE)
        assert has_permission(Role.ADMIN, Permission.API_KEYS_MANAGE)
        assert has_permission(Role.ADMIN, Permission.RECONCILE_RUN)
        assert has_permission(Role.ADMIN, Permission.SETTINGS_WRITE)

    def test_owner_has_all_permissions(self):
        """Owners have every defined permission."""
        for perm in Permission:
            assert has_permission(Role.OWNER, perm), f"Owner missing: {perm.value}"

    def test_permission_inheritance(self):
        """Higher roles inherit all permissions from lower roles."""
        viewer_perms = ROLE_PERMISSIONS[Role.VIEWER]
        analyst_perms = ROLE_PERMISSIONS[Role.ANALYST]
        manager_perms = ROLE_PERMISSIONS[Role.MANAGER]
        admin_perms = ROLE_PERMISSIONS[Role.ADMIN]
        owner_perms = ROLE_PERMISSIONS[Role.OWNER]

        assert viewer_perms.issubset(analyst_perms)
        assert analyst_perms.issubset(manager_perms)
        assert manager_perms.issubset(admin_perms)
        assert admin_perms.issubset(owner_perms)


# ── has_role Tests ──────────────────────────────────────────────────────


class TestHasRole:
    """Test the has_role function."""

    def test_same_role_passes(self):
        assert has_role(Role.ADMIN, Role.ADMIN)

    def test_higher_role_passes(self):
        assert has_role(Role.OWNER, Role.ADMIN)
        assert has_role(Role.ADMIN, Role.VIEWER)

    def test_lower_role_fails(self):
        assert not has_role(Role.VIEWER, Role.ADMIN)
        assert not has_role(Role.ANALYST, Role.MANAGER)


# ── check_permission / check_role with Request mock ─────────────────────


class _FakeState:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class _FakeRequest:
    def __init__(self, role: str, user_id: str = "test-uid"):
        self.state = _FakeState(user_role=role, user_id=user_id)
        self.url = type("URL", (), {"path": "/test"})()


class TestCheckPermission:
    """Test the check_permission function raises 403 on denial."""

    def test_allowed(self):
        """No exception when permission is granted."""
        req = _FakeRequest(role="admin")
        check_permission(req, Permission.USERS_MANAGE)  # Should not raise

    def test_denied(self):
        """HTTPException 403 when permission is denied."""
        req = _FakeRequest(role="viewer")
        with pytest.raises(HTTPException) as exc_info:
            check_permission(req, Permission.USERS_MANAGE)
        assert exc_info.value.status_code == 403

    def test_denied_detail_contains_required(self):
        """403 response includes the required permission name."""
        req = _FakeRequest(role="viewer")
        with pytest.raises(HTTPException) as exc_info:
            check_permission(req, Permission.SETTINGS_WRITE)
        detail = exc_info.value.detail
        assert detail["required"] == "settings:write"
        assert detail["your_role"] == "viewer"


class TestCheckRole:
    """Test the check_role function."""

    def test_allowed(self):
        req = _FakeRequest(role="admin")
        check_role(req, Role.MANAGER)  # Should not raise

    def test_denied(self):
        req = _FakeRequest(role="viewer")
        with pytest.raises(HTTPException) as exc_info:
            check_role(req, Role.ADMIN)
        assert exc_info.value.status_code == 403
