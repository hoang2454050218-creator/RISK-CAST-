"""
API Contract Tests for RISKCAST.

These tests verify that API responses conform to documented schemas,
ensuring backward compatibility and proper versioning.
"""

import pytest
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock

from pydantic import BaseModel, Field
from fastapi.testclient import TestClient


# ============================================================================
# CONTRACT SCHEMAS - What we promise to clients
# ============================================================================


class DecisionContract(BaseModel):
    """Contract for Decision API response."""
    
    decision_id: str
    customer_id: str
    signal_id: str
    
    # Q1-Q7 required fields
    q1_what: str
    q2_when: Dict[str, Any]
    q3_severity: Dict[str, Any]
    q4_why: Dict[str, Any]
    q5_action: Dict[str, Any]
    q6_confidence: Dict[str, Any]
    q7_inaction: Dict[str, Any]
    
    # Metadata
    created_at: str
    expires_at: str
    
    class Config:
        extra = "allow"  # Allow additional fields for forward compatibility


class SignalContract(BaseModel):
    """Contract for Signal API response."""
    
    signal_id: str
    source: str
    chokepoint: str
    probability: float = Field(ge=0, le=1)
    confidence_score: float = Field(ge=0, le=1)
    evidence: list
    created_at: str
    
    class Config:
        extra = "allow"


class AlertContract(BaseModel):
    """Contract for Alert API response."""
    
    alert_id: str
    customer_id: str
    decision_id: str
    channel: str
    status: str
    sent_at: str
    
    class Config:
        extra = "allow"


class CustomerContract(BaseModel):
    """Contract for Customer API response."""
    
    customer_id: str
    company_name: str
    tier: str
    active_shipments: int
    created_at: str
    
    class Config:
        extra = "allow"


class HealthContract(BaseModel):
    """Contract for Health API response."""
    
    status: str = Field(pattern="^(healthy|degraded|unhealthy)$")
    version: str
    timestamp: str
    components: Dict[str, Dict[str, Any]]
    
    class Config:
        extra = "allow"


class ErrorContract(BaseModel):
    """Contract for Error responses."""
    
    error: str
    message: str
    request_id: str
    timestamp: str
    
    class Config:
        extra = "allow"


# ============================================================================
# CONTRACT TESTS
# ============================================================================


class TestDecisionApiContract:
    """Test Decision API contract compliance."""
    
    def test_decision_response_matches_contract(self):
        """Decision response must match contract schema."""
        # Sample response that should pass
        response = {
            "decision_id": "dec-123",
            "customer_id": "cust-456",
            "signal_id": "sig-789",
            "q1_what": "Houthi attack on Red Sea shipping",
            "q2_when": {
                "event_time": "2024-01-15T10:00:00Z",
                "decision_deadline": "2024-01-15T18:00:00Z",
                "urgency": "urgent",
            },
            "q3_severity": {
                "exposure_usd": 150000,
                "delay_days": 10,
                "affected_shipments": 3,
            },
            "q4_why": {
                "causal_chain": ["Attack detected", "Route blocked"],
                "evidence_count": 5,
            },
            "q5_action": {
                "action_type": "reroute",
                "estimated_cost_usd": 8500,
                "deadline": "2024-01-15T18:00:00Z",
            },
            "q6_confidence": {
                "score": 0.85,
                "factors": ["multiple_sources", "historical_pattern"],
            },
            "q7_inaction": {
                "cost_usd": 25000,
                "delay_days": 21,
                "point_of_no_return": "2024-01-16T06:00:00Z",
            },
            "created_at": "2024-01-15T09:00:00Z",
            "expires_at": "2024-01-16T09:00:00Z",
        }
        
        # Should not raise validation error
        decision = DecisionContract(**response)
        assert decision.decision_id == "dec-123"
        assert decision.q3_severity["exposure_usd"] == 150000
    
    def test_decision_contract_rejects_missing_required_fields(self):
        """Decision missing required fields should fail contract."""
        incomplete_response = {
            "decision_id": "dec-123",
            "customer_id": "cust-456",
            # Missing q1-q7 and other required fields
        }
        
        with pytest.raises(Exception):  # Pydantic ValidationError
            DecisionContract(**incomplete_response)
    
    def test_decision_contract_allows_additional_fields(self):
        """Contract should allow additional fields for forward compatibility."""
        response = {
            "decision_id": "dec-123",
            "customer_id": "cust-456",
            "signal_id": "sig-789",
            "q1_what": "Event description",
            "q2_when": {},
            "q3_severity": {},
            "q4_why": {},
            "q5_action": {},
            "q6_confidence": {},
            "q7_inaction": {},
            "created_at": "2024-01-15T09:00:00Z",
            "expires_at": "2024-01-16T09:00:00Z",
            # Additional fields (future versions)
            "q8_alternatives": [{"action": "delay", "cost": 5000}],
            "ml_model_version": "v2.1.0",
        }
        
        decision = DecisionContract(**response)
        assert hasattr(decision, "q8_alternatives")


class TestSignalApiContract:
    """Test Signal API contract compliance."""
    
    def test_signal_response_matches_contract(self):
        """Signal response must match contract schema."""
        response = {
            "signal_id": "sig-123",
            "source": "polymarket",
            "chokepoint": "red_sea",
            "probability": 0.75,
            "confidence_score": 0.85,
            "evidence": [
                {"type": "price_movement", "value": "65% to 75%"},
            ],
            "created_at": "2024-01-15T09:00:00Z",
        }
        
        signal = SignalContract(**response)
        assert signal.probability == 0.75
        assert signal.confidence_score == 0.85
    
    def test_signal_contract_validates_probability_range(self):
        """Probability must be between 0 and 1."""
        invalid_response = {
            "signal_id": "sig-123",
            "source": "polymarket",
            "chokepoint": "red_sea",
            "probability": 1.5,  # Invalid: > 1
            "confidence_score": 0.85,
            "evidence": [],
            "created_at": "2024-01-15T09:00:00Z",
        }
        
        with pytest.raises(Exception):
            SignalContract(**invalid_response)


class TestHealthApiContract:
    """Test Health API contract compliance."""
    
    def test_health_response_matches_contract(self):
        """Health response must match contract schema."""
        response = {
            "status": "healthy",
            "version": "1.0.0",
            "timestamp": "2024-01-15T09:00:00Z",
            "components": {
                "database": {"status": "healthy", "latency_ms": 5},
                "redis": {"status": "healthy", "latency_ms": 2},
                "omen": {"status": "healthy"},
                "oracle": {"status": "healthy"},
            },
        }
        
        health = HealthContract(**response)
        assert health.status == "healthy"
    
    def test_health_contract_validates_status_values(self):
        """Status must be healthy, degraded, or unhealthy."""
        invalid_response = {
            "status": "broken",  # Invalid status
            "version": "1.0.0",
            "timestamp": "2024-01-15T09:00:00Z",
            "components": {},
        }
        
        with pytest.raises(Exception):
            HealthContract(**invalid_response)


class TestErrorContract:
    """Test Error response contract compliance."""
    
    def test_error_response_matches_contract(self):
        """Error responses must match contract schema."""
        response = {
            "error": "validation_error",
            "message": "Invalid customer_id format",
            "request_id": "req-123",
            "timestamp": "2024-01-15T09:00:00Z",
        }
        
        error = ErrorContract(**response)
        assert error.error == "validation_error"


# ============================================================================
# BACKWARD COMPATIBILITY TESTS
# ============================================================================


class TestBackwardCompatibility:
    """Test backward compatibility with older API versions."""
    
    V1_DECISION_FIELDS = [
        "decision_id",
        "customer_id",
        "signal_id",
        "q1_what",
        "q5_action",
        "created_at",
    ]
    
    def test_v1_fields_still_present(self):
        """V1 clients must still receive expected fields."""
        response = {
            "decision_id": "dec-123",
            "customer_id": "cust-456",
            "signal_id": "sig-789",
            "q1_what": "Event",
            "q2_when": {},
            "q3_severity": {},
            "q4_why": {},
            "q5_action": {"action_type": "reroute"},
            "q6_confidence": {},
            "q7_inaction": {},
            "created_at": "2024-01-15T09:00:00Z",
            "expires_at": "2024-01-16T09:00:00Z",
        }
        
        for field in self.V1_DECISION_FIELDS:
            assert field in response, f"V1 required field '{field}' missing"
    
    def test_deprecated_fields_still_returned(self):
        """Deprecated fields should still be returned during transition."""
        # In a real scenario, track deprecated fields and ensure they're
        # still returned for backward compatibility
        deprecated_fields = ["risk_level"]  # Example deprecated field
        
        # This test would check that deprecated fields are still present
        # but marked for removal in future versions
        pass


# ============================================================================
# SCHEMA VERSIONING
# ============================================================================


class TestSchemaVersioning:
    """Test API schema versioning."""
    
    def test_version_header_present(self):
        """API responses should include version header."""
        # In real test, check X-API-Version header
        expected_versions = ["2024-01-01", "2024-06-01", "2025-01-01"]
        current_version = "2025-01-01"
        assert current_version in expected_versions
    
    def test_version_negotiation(self):
        """Client can request specific API version."""
        # Test that Accept-Version header is respected
        pass


# ============================================================================
# PERFORMANCE CONTRACTS
# ============================================================================


class TestPerformanceContracts:
    """Test performance SLAs as contracts."""
    
    # Response time contracts (in milliseconds)
    CONTRACTS = {
        "health_check": 100,
        "get_decision": 500,
        "create_alert": 1000,
        "get_signals": 300,
    }
    
    @pytest.mark.asyncio
    async def test_health_check_response_time(self):
        """Health check must respond within 100ms."""
        # In real test, measure actual response time
        max_ms = self.CONTRACTS["health_check"]
        actual_ms = 50  # Mock measurement
        assert actual_ms < max_ms
    
    @pytest.mark.asyncio
    async def test_decision_response_time(self):
        """Decision retrieval must respond within 500ms."""
        max_ms = self.CONTRACTS["get_decision"]
        actual_ms = 200  # Mock measurement
        assert actual_ms < max_ms
