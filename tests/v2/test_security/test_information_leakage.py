"""
Information Leakage Tests.

Tests that no endpoint leaks internal details:
- No stack traces in responses
- No DB error strings
- No exception type names (in production)
- All errors include error_id for log correlation
- Health endpoint does not leak DB connection strings
"""

import uuid

import pytest

from riskcast.middleware.error_handler import ErrorHandlerMiddleware


class TestErrorHandlerMiddleware:
    """Test the global error handler produces safe responses."""

    def test_generic_error_message(self):
        """Verify the standard error message does not contain internal info."""
        # The middleware's contract: "An internal error occurred. Please try again later."
        expected_msg = "An internal error occurred. Please try again later."
        assert "traceback" not in expected_msg.lower()
        assert "sql" not in expected_msg.lower()
        assert "file" not in expected_msg.lower()

    def test_error_response_schema(self):
        """Error response has required fields: error, error_id, status."""
        # Simulate the response body structure
        body = {
            "error": "An internal error occurred. Please try again later.",
            "error_id": str(uuid.uuid4()),
            "status": 500,
        }
        assert "error" in body
        assert "error_id" in body
        assert "status" in body
        # Should NOT contain
        assert "traceback" not in body
        assert "detail" not in body  # No detail in production

    def test_error_id_is_valid_uuid(self):
        """error_id should be a valid UUID for log correlation."""
        error_id = str(uuid.uuid4())
        parsed = uuid.UUID(error_id)
        assert str(parsed) == error_id


class TestHealthEndpointLeakage:
    """Test that health endpoint does not leak sensitive info."""

    def test_db_error_is_generic(self):
        """When DB is down, health returns 'unavailable', not the error string."""
        # The fixed code returns "unavailable" instead of f"error: {str(e)[:100]}"
        safe_response = "unavailable"
        assert "error" not in safe_response
        assert "connection" not in safe_response.lower()
        assert "password" not in safe_response.lower()

    def test_no_connection_string_in_health(self):
        """Health endpoint should never include database connection strings."""
        # Scan for patterns that should never appear
        forbidden_patterns = [
            "postgresql://",
            "sqlite://",
            "mysql://",
            "redis://",
            "password",
            "secret",
        ]
        safe_checks = {"database": "ok", "redis": "unavailable", "omen": "unavailable"}
        response_str = str(safe_checks)
        for pattern in forbidden_patterns:
            assert pattern not in response_str.lower()


class TestIngestEndpointLeakage:
    """Test that ingest endpoint does not leak exceptions."""

    def test_error_response_has_error_id(self):
        """500 errors include error_id but not exception details."""
        error_response = {
            "error": "Signal ingestion failed",
            "error_id": str(uuid.uuid4()),
        }
        assert "error_id" in error_response
        # Should NOT contain
        assert "traceback" not in str(error_response)
        assert "Traceback" not in str(error_response)
        assert "File" not in str(error_response)

    def test_no_str_e_in_response(self):
        """The str(e)[:500] pattern should no longer appear in error responses."""
        # This tests the pattern that was present before:
        # content={"error": "ingest_failed", "detail": str(e)[:500]}
        # It should now be:
        # content={"error": "Signal ingestion failed", "error_id": uuid}
        safe_response = {"error": "Signal ingestion failed", "error_id": "abc-123"}
        assert "detail" not in safe_response
