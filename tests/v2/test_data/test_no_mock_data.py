"""
CRITICAL TEST: Verify ZERO mock data in production frontend hooks.

Searches for anti-patterns that indicate mock data usage.
Every hook must call a real API endpoint, not a mock generator.
"""

import os
import pytest


FRONTEND_HOOKS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "frontend", "src", "hooks"
)


def _read_hook_files():
    """Read all production .ts files in the hooks directory (exclude test files)."""
    hooks = {}
    if not os.path.isdir(FRONTEND_HOOKS_DIR):
        return hooks
    for fname in os.listdir(FRONTEND_HOOKS_DIR):
        if fname.endswith(".test.ts") or fname.endswith(".test.tsx"):
            continue  # Skip test files — they may reference mock patterns
        if fname.endswith(".ts") or fname.endswith(".tsx"):
            fpath = os.path.join(FRONTEND_HOOKS_DIR, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                hooks[fname] = f.read()
    return hooks


class TestNoMockData:
    """Ensure no mock data patterns exist in production hooks."""

    def test_no_withMockFallback(self):
        """No hook uses the withMockFallback pattern."""
        hooks = _read_hook_files()
        assert len(hooks) > 0, "No hook files found"
        for fname, content in hooks.items():
            assert "withMockFallback" not in content, (
                f"{fname} still uses withMockFallback — must call real API"
            )

    def test_no_throw_not_implemented(self):
        """No hook throws 'Not implemented' (guaranteed-mock pattern)."""
        hooks = _read_hook_files()
        for fname, content in hooks.items():
            assert "Not implemented" not in content, (
                f"{fname} has 'Not implemented' — must call real API"
            )

    def test_no_generate_mock_functions(self):
        """No hook calls generateXxxData() mock generators."""
        hooks = _read_hook_files()
        generate_patterns = [
            "generateDashboardData",
            "generateCustomersList",
            "generateCustomerDetail",
            "generateAnalyticsData",
            "generateAuditTrail",
            "generateRealityData",
        ]
        for fname, content in hooks.items():
            for pattern in generate_patterns:
                assert pattern not in content, (
                    f"{fname} calls {pattern}() — must use real API"
                )

    def test_no_mock_data_import(self):
        """No hook imports from mock-data module."""
        hooks = _read_hook_files()
        for fname, content in hooks.items():
            assert "from '@/lib/mock-data'" not in content, (
                f"{fname} imports from mock-data — must use real API"
            )
            assert "from \"@/lib/mock-data\"" not in content, (
                f"{fname} imports from mock-data — must use real API"
            )

    def test_no_mockSignals_import(self):
        """No hook imports mockSignals."""
        hooks = _read_hook_files()
        for fname, content in hooks.items():
            assert "mockSignals" not in content, (
                f"{fname} uses mockSignals — must use real API"
            )

    def test_critical_hooks_use_v2_api(self):
        """Critical hooks import from api-v2."""
        hooks = _read_hook_files()
        critical = ["useDashboard.ts", "useCustomers.ts", "useAnalytics.ts", "useAuditTrail.ts"]
        for fname in critical:
            if fname in hooks:
                assert "api-v2" in hooks[fname], (
                    f"{fname} does not import from api-v2"
                )
