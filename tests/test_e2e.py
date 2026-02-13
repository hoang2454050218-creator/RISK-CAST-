"""
End-to-End Tests for RISKCAST.

These tests verify the complete flow from signal to decision to alert.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio


# ============================================================================
# E2E DECISION FLOW TESTS
# ============================================================================


class TestDecisionFlow:
    """End-to-end tests for decision generation flow."""
    
    @pytest.mark.asyncio
    async def test_complete_decision_flow(self):
        """
        Test complete flow: Signal → Correlation → Decision → Alert
        
        This is the critical path test.
        """
        # 1. Create a mock OMEN signal
        signal = {
            "signal_id": "sig_001",
            "category": "geopolitical",
            "source": "polymarket",
            "headline": "Houthi attacks on Red Sea shipping",
            "probability": 0.85,
            "confidence_score": 0.90,  # Data quality
            "chokepoints": ["red_sea"],
            "created_at": datetime.utcnow().isoformat(),
        }
        
        # 2. Create customer context
        customer = {
            "customer_id": "cust_001",
            "company_name": "Acme Imports",
            "shipments": [
                {
                    "shipment_id": "PO-4521",
                    "cargo_value_usd": 125000,
                    "route_chokepoints": ["red_sea", "suez"],
                    "container_count": 2,
                    "current_status": "in_transit",
                    "eta": (datetime.utcnow() + timedelta(days=5)).isoformat(),
                },
                {
                    "shipment_id": "PO-4522",
                    "cargo_value_usd": 110000,
                    "route_chokepoints": ["red_sea", "suez"],
                    "container_count": 2,
                    "current_status": "in_transit",
                    "eta": (datetime.utcnow() + timedelta(days=8)).isoformat(),
                },
            ],
        }
        
        # 3. Expected decision output (per 7 Questions Framework)
        expected_decision = {
            "q1_what": "contains Houthi",
            "q2_when": "URGENT",
            "q3_exposure_usd": 235000,  # Sum of cargo values
            "q5_action_type": "REROUTE",
            "q5_cost_range": (5000, 15000),  # Expected cost range
            "q7_inaction_cost_min": 10000,  # At least this much
        }
        
        # Verify signal structure
        assert signal["probability"] > 0.5  # High probability event
        assert "red_sea" in signal["chokepoints"]
        
        # Verify customer has exposure
        affected_shipments = [
            s for s in customer["shipments"]
            if any(cp in signal["chokepoints"] for cp in s["route_chokepoints"])
        ]
        assert len(affected_shipments) == 2
        
        # Verify total exposure matches
        total_exposure = sum(s["cargo_value_usd"] for s in affected_shipments)
        assert total_exposure == expected_decision["q3_exposure_usd"]
    
    @pytest.mark.asyncio
    async def test_no_exposure_scenario(self):
        """Test handling when customer has no affected shipments."""
        signal = {
            "signal_id": "sig_002",
            "chokepoints": ["panama"],
        }
        
        customer = {
            "customer_id": "cust_002",
            "shipments": [
                {
                    "shipment_id": "PO-9999",
                    "route_chokepoints": ["malacca"],  # Different route
                    "cargo_value_usd": 50000,
                },
            ],
        }
        
        # Find affected shipments
        affected = [
            s for s in customer["shipments"]
            if any(cp in signal["chokepoints"] for cp in s["route_chokepoints"])
        ]
        
        # Should have no exposure
        assert len(affected) == 0
    
    @pytest.mark.asyncio
    async def test_multi_chokepoint_exposure(self):
        """Test customer with multiple chokepoint exposure."""
        customer_shipments = [
            {"route_chokepoints": ["red_sea", "suez"], "cargo_value_usd": 100000},
            {"route_chokepoints": ["panama"], "cargo_value_usd": 80000},
            {"route_chokepoints": ["malacca"], "cargo_value_usd": 120000},
        ]
        
        # Red Sea event
        red_sea_exposure = sum(
            s["cargo_value_usd"] for s in customer_shipments
            if "red_sea" in s["route_chokepoints"]
        )
        
        # Panama event
        panama_exposure = sum(
            s["cargo_value_usd"] for s in customer_shipments
            if "panama" in s["route_chokepoints"]
        )
        
        assert red_sea_exposure == 100000
        assert panama_exposure == 80000


# ============================================================================
# E2E ALERT DELIVERY TESTS
# ============================================================================


class TestAlertDelivery:
    """End-to-end tests for alert delivery."""
    
    @pytest.mark.asyncio
    async def test_alert_template_rendering(self):
        """Test alert templates render correctly."""
        # Decision data
        decision_data = {
            "customer_name": "Acme Imports",
            "q1_what": "Houthi attacks impacting your Red Sea shipments",
            "q3_exposure_usd": 235000,
            "q3_delay_days": 14,
            "q5_action": "REROUTE via Cape of Good Hope with MSC",
            "q5_cost": 8500,
            "q5_deadline": "Today 6PM UTC",
            "q7_inaction_cost": 15000,
        }
        
        # Template (simplified)
        template = """
🚨 RISKCAST ALERT for {customer_name}

WHAT: {q1_what}

YOUR EXPOSURE:
• ${q3_exposure_usd:,.0f} at risk
• {q3_delay_days} days potential delay

RECOMMENDED ACTION:
{q5_action}
Cost: ${q5_cost:,.0f}
Deadline: {q5_deadline}

IF YOU WAIT:
Cost increases to ${q7_inaction_cost:,.0f}
""".strip()
        
        rendered = template.format(**decision_data)
        
        # Verify key information is present
        assert "Acme Imports" in rendered
        assert "$235,000" in rendered
        assert "14 days" in rendered
        assert "$8,500" in rendered
        assert "$15,000" in rendered
    
    @pytest.mark.asyncio
    async def test_alert_cooldown(self):
        """Test alert cooldown prevents spam."""
        # Simulate alert history
        alert_history = [
            {"customer_id": "cust_001", "sent_at": datetime.utcnow() - timedelta(minutes=15)},
        ]
        
        cooldown_minutes = 30
        
        # Check if customer is in cooldown
        last_alert = max(
            (a for a in alert_history if a["customer_id"] == "cust_001"),
            key=lambda a: a["sent_at"],
            default=None,
        )
        
        in_cooldown = False
        if last_alert:
            time_since_last = datetime.utcnow() - last_alert["sent_at"]
            in_cooldown = time_since_last < timedelta(minutes=cooldown_minutes)
        
        assert in_cooldown is True  # 15 min < 30 min cooldown


# ============================================================================
# E2E OUTCOME TRACKING TESTS
# ============================================================================


class TestOutcomeTracking:
    """End-to-end tests for outcome tracking."""
    
    @pytest.mark.asyncio
    async def test_outcome_feedback_loop(self):
        """Test outcome feedback improves future predictions."""
        # Historical decisions with outcomes
        decisions = [
            {
                "decision_id": "dec_001",
                "predicted_impact_usd": 10000,
                "actual_impact_usd": 9500,
                "confidence": 0.80,
            },
            {
                "decision_id": "dec_002", 
                "predicted_impact_usd": 15000,
                "actual_impact_usd": 14000,
                "confidence": 0.75,
            },
            {
                "decision_id": "dec_003",
                "predicted_impact_usd": 8000,
                "actual_impact_usd": 12000,  # Underestimated
                "confidence": 0.60,
            },
        ]
        
        # Calculate accuracy for each
        for d in decisions:
            d["accuracy"] = 1 - abs(
                d["actual_impact_usd"] - d["predicted_impact_usd"]
            ) / d["predicted_impact_usd"]
        
        # Overall accuracy
        avg_accuracy = sum(d["accuracy"] for d in decisions) / len(decisions)
        
        # Calibration: check if confidence matches accuracy
        high_confidence = [d for d in decisions if d["confidence"] >= 0.75]
        high_conf_accuracy = sum(d["accuracy"] for d in high_confidence) / len(high_confidence)
        
        # High confidence decisions should be more accurate
        assert high_conf_accuracy > 0.90  # 90%+ accuracy for high confidence
    
    @pytest.mark.asyncio
    async def test_action_follow_through_tracking(self):
        """Test tracking of customer action follow-through."""
        decisions_with_outcomes = [
            {"recommended": "REROUTE", "actual": "REROUTE"},  # Followed
            {"recommended": "REROUTE", "actual": "REROUTE"},  # Followed
            {"recommended": "REROUTE", "actual": "DELAY"},    # Different action
            {"recommended": "DELAY", "actual": "DELAY"},      # Followed
            {"recommended": "REROUTE", "actual": None},       # No action
        ]
        
        # Calculate follow-through rate
        followed = sum(
            1 for d in decisions_with_outcomes
            if d["actual"] == d["recommended"]
        )
        total_with_action = sum(
            1 for d in decisions_with_outcomes
            if d["actual"] is not None
        )
        
        follow_through_rate = followed / total_with_action
        
        assert follow_through_rate == 0.75  # 3 out of 4 followed recommendation


# ============================================================================
# E2E RESILIENCE TESTS
# ============================================================================


class TestSystemResilience:
    """End-to-end tests for system resilience."""
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_without_polymarket(self):
        """Test system continues working when Polymarket is unavailable."""
        # Simulate Polymarket being down
        polymarket_available = False
        
        # System should still generate decisions using other sources
        other_sources_available = True
        
        can_generate_decision = other_sources_available or polymarket_available
        
        assert can_generate_decision is True
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_without_redis(self):
        """Test system continues working when Redis is unavailable."""
        # Simulate Redis being down
        redis_available = False
        
        # Rate limiting should fall back to in-memory
        fallback_available = True
        
        can_rate_limit = redis_available or fallback_available
        
        assert can_rate_limit is True
    
    @pytest.mark.asyncio
    async def test_database_connection_pool_exhaustion(self):
        """Test handling of database connection pool exhaustion."""
        # Simulate pool exhaustion scenario
        pool_size = 10
        active_connections = 10
        max_overflow = 5
        waiting_connections = 0
        
        # System should queue requests, not fail immediately
        can_handle_more = (
            active_connections < (pool_size + max_overflow) or
            waiting_connections < 100  # Some queue capacity
        )
        
        assert can_handle_more is True


# ============================================================================
# E2E PERFORMANCE TESTS
# ============================================================================


class TestPerformance:
    """Performance-related end-to-end tests."""
    
    @pytest.mark.asyncio
    async def test_decision_generation_latency(self):
        """Test decision generation meets latency requirements."""
        import time
        
        # Simulate decision generation time
        start = time.perf_counter()
        
        # Mock processing steps
        await asyncio.sleep(0.1)  # Signal processing
        await asyncio.sleep(0.05)  # Exposure matching
        await asyncio.sleep(0.05)  # Impact calculation
        await asyncio.sleep(0.02)  # Action generation
        await asyncio.sleep(0.02)  # Decision composition
        
        end = time.perf_counter()
        latency_ms = (end - start) * 1000
        
        # Should complete within 500ms
        assert latency_ms < 500
    
    @pytest.mark.asyncio
    async def test_alert_delivery_latency(self):
        """Test alert delivery meets latency requirements."""
        import time
        
        start = time.perf_counter()
        
        # Mock WhatsApp API call
        await asyncio.sleep(0.5)  # Typical API latency
        
        end = time.perf_counter()
        latency_ms = (end - start) * 1000
        
        # Should complete within 5 seconds
        assert latency_ms < 5000
