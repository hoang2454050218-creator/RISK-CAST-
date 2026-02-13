"""
Tests for Automated Escalation System.

D4 COMPLIANCE: Validates automated incident escalation.
C2 COMPLIANCE: Validates regulatory response automation.

Tests:
- Alert creation and tracking
- Automatic escalation progression
- Acknowledgment tracking
- Multi-channel notifications
- Regulatory request handling
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from app.ops.escalation.automation import (
    AutomatedEscalation,
    RegulatoryResponseAutomation,
    EscalationLevel,
    EscalationChannel,
    AlertSeverity,
    AlertStatus,
    EscalationPolicy,
    EscalationState,
    Alert,
    RegulatoryFramework,
    RegulatoryRequest,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def escalation_service():
    """Create escalation service for testing."""
    return AutomatedEscalation()


@pytest.fixture
def mock_notification_service():
    """Create mock notification service."""
    service = MagicMock()
    service.send_email = AsyncMock(return_value=True)
    service.send_sms = AsyncMock(return_value=True)
    service.send_slack = AsyncMock(return_value=True)
    service.send_pagerduty = AsyncMock(return_value=True)
    return service


@pytest.fixture
def escalation_with_notifications(mock_notification_service):
    """Escalation service with notification service."""
    return AutomatedEscalation(notification_service=mock_notification_service)


# ============================================================================
# ESCALATION LEVEL TESTS
# ============================================================================


class TestEscalationLevels:
    """Test escalation level definitions."""
    
    def test_all_levels_exist(self):
        """
        D4 COMPLIANCE: All escalation levels defined.
        """
        assert EscalationLevel.L1 is not None
        assert EscalationLevel.L2 is not None
        assert EscalationLevel.L3 is not None
        assert EscalationLevel.L4 is not None
        assert EscalationLevel.L5 is not None
    
    def test_level_values(self):
        """Levels should have correct string values."""
        assert EscalationLevel.L1.value == "l1"
        assert EscalationLevel.L2.value == "l2"
        assert EscalationLevel.L5.value == "l5"


# ============================================================================
# ALERT CREATION TESTS
# ============================================================================


class TestAlertCreation:
    """Test alert creation."""
    
    @pytest.mark.asyncio
    async def test_create_alert(self, escalation_service):
        """
        D4 COMPLIANCE: Alert creation works.
        
        Should create alert with initial escalation state.
        """
        alert_id = await escalation_service.create_alert(
            title="Test Alert",
            description="Test description",
            severity=AlertSeverity.HIGH,
            source="test",
        )
        
        assert alert_id is not None
        assert alert_id.startswith("alert_")
    
    @pytest.mark.asyncio
    async def test_create_alert_with_metadata(self, escalation_service):
        """Should create alert with custom metadata."""
        alert_id = await escalation_service.create_alert(
            title="Test Alert",
            description="Test description",
            severity=AlertSeverity.MEDIUM,
            source="test",
            customer_id="CUST-001",
            decision_id="DEC-001",
            tags=["critical", "supply_chain"],
            metadata={"region": "asia"},
        )
        
        assert alert_id is not None
        
        # Verify alert was stored
        alert = await escalation_service._get_alert(alert_id)
        assert alert is not None
        assert alert.customer_id == "CUST-001"
        assert "critical" in alert.tags
    
    @pytest.mark.asyncio
    async def test_create_alert_initializes_state(self, escalation_service):
        """Alert creation should initialize escalation state."""
        alert_id = await escalation_service.create_alert(
            title="Test Alert",
            description="Test",
            severity=AlertSeverity.HIGH,
            source="test",
        )
        
        state = await escalation_service._get_state(alert_id)
        
        assert state is not None
        assert state.current_level == EscalationLevel.L1
        assert state.acknowledged is False
        assert state.resolved is False
        assert len(state.escalation_history) > 0


# ============================================================================
# ACKNOWLEDGMENT TESTS
# ============================================================================


class TestAcknowledgment:
    """Test alert acknowledgment."""
    
    @pytest.mark.asyncio
    async def test_acknowledge_alert(self, escalation_service):
        """
        D4 COMPLIANCE: Alert acknowledgment works.
        """
        # Create alert
        alert_id = await escalation_service.create_alert(
            title="Test Alert",
            description="Test",
            severity=AlertSeverity.HIGH,
            source="test",
        )
        
        # Acknowledge
        result = await escalation_service.acknowledge(
            alert_id=alert_id,
            user_id="user_123",
            notes="Looking into it",
        )
        
        assert result is True
        
        # Verify state
        state = await escalation_service._get_state(alert_id)
        assert state.acknowledged is True
        assert state.acknowledged_by == "user_123"
        assert state.acknowledged_at is not None
    
    @pytest.mark.asyncio
    async def test_acknowledge_nonexistent_alert(self, escalation_service):
        """Acknowledging nonexistent alert should fail gracefully."""
        result = await escalation_service.acknowledge(
            alert_id="nonexistent_alert",
            user_id="user_123",
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_acknowledgment_updates_alert_status(self, escalation_service):
        """Acknowledgment should update alert status."""
        alert_id = await escalation_service.create_alert(
            title="Test Alert",
            description="Test",
            severity=AlertSeverity.MEDIUM,
            source="test",
        )
        
        await escalation_service.acknowledge(
            alert_id=alert_id,
            user_id="user_123",
        )
        
        alert = await escalation_service._get_alert(alert_id)
        assert alert.status == AlertStatus.ACKNOWLEDGED


# ============================================================================
# RESOLUTION TESTS
# ============================================================================


class TestResolution:
    """Test alert resolution."""
    
    @pytest.mark.asyncio
    async def test_resolve_alert(self, escalation_service):
        """
        D4 COMPLIANCE: Alert resolution works.
        """
        alert_id = await escalation_service.create_alert(
            title="Test Alert",
            description="Test",
            severity=AlertSeverity.HIGH,
            source="test",
        )
        
        # Acknowledge first
        await escalation_service.acknowledge(alert_id, "user_123")
        
        # Resolve
        result = await escalation_service.resolve(
            alert_id=alert_id,
            user_id="user_123",
            resolution_notes="Issue fixed by restarting service",
        )
        
        assert result is True
        
        state = await escalation_service._get_state(alert_id)
        assert state.resolved is True
        assert state.resolved_by == "user_123"
        assert "restarting service" in state.resolution_notes


# ============================================================================
# AUTOMATIC ESCALATION TESTS
# ============================================================================


class TestAutomaticEscalation:
    """Test automatic escalation progression."""
    
    @pytest.mark.asyncio
    async def test_escalation_policy_exists_for_severities(self):
        """
        D4 COMPLIANCE: Escalation policies exist for all severities.
        """
        policies = AutomatedEscalation.DEFAULT_POLICIES
        
        assert AlertSeverity.CRITICAL in policies
        assert AlertSeverity.HIGH in policies
        assert AlertSeverity.MEDIUM in policies
        assert AlertSeverity.LOW in policies
    
    @pytest.mark.asyncio
    async def test_critical_policy_escalates_faster(self):
        """Critical alerts should escalate faster."""
        critical = AutomatedEscalation.DEFAULT_POLICIES[AlertSeverity.CRITICAL]
        high = AutomatedEscalation.DEFAULT_POLICIES[AlertSeverity.HIGH]
        
        assert critical.time_to_ack_minutes < high.time_to_ack_minutes
        assert critical.repeat_notification_minutes < high.repeat_notification_minutes
    
    @pytest.mark.asyncio
    async def test_escalation_chain_progression(self):
        """Escalation should follow the chain."""
        critical = AutomatedEscalation.DEFAULT_POLICIES[AlertSeverity.CRITICAL]
        
        assert critical.initial_level == EscalationLevel.L1
        assert EscalationLevel.L2 in critical.escalation_chain
        assert EscalationLevel.L3 in critical.escalation_chain
    
    @pytest.mark.asyncio
    async def test_should_escalate_after_timeout(self, escalation_service):
        """
        D4 COMPLIANCE: Escalation progresses automatically.
        """
        # Create alert
        alert_id = await escalation_service.create_alert(
            title="Test Alert",
            description="Test",
            severity=AlertSeverity.HIGH,
            source="test",
        )
        
        # Get state and policy
        state = await escalation_service._get_state(alert_id)
        alert = await escalation_service._get_alert(alert_id)
        policy = escalation_service._get_policy(alert.severity)
        
        # Simulate time passing (set escalated_at to past)
        state.escalated_at = datetime.utcnow() - timedelta(minutes=policy.time_to_ack_minutes + 1)
        state.notifications_sent = policy.max_notifications_per_level
        await escalation_service._save_state(state)
        
        # Check if should escalate
        should_escalate = await escalation_service._should_escalate(state, policy)
        
        assert should_escalate is True


# ============================================================================
# NOTIFICATION TESTS
# ============================================================================


class TestNotifications:
    """Test notification sending."""
    
    @pytest.mark.asyncio
    async def test_notification_sent_on_alert_creation(
        self,
        escalation_with_notifications,
        mock_notification_service,
    ):
        """
        D4 COMPLIANCE: Notifications sent on alert creation.
        """
        await escalation_with_notifications.create_alert(
            title="Test Alert",
            description="Test description",
            severity=AlertSeverity.HIGH,
            source="test",
        )
        
        # Notification should have been attempted
        # (May fail if no contacts configured, but attempt should be made)
        # The default contacts have email, so email should be attempted
        assert mock_notification_service.send_email.called or mock_notification_service.send_slack.called
    
    @pytest.mark.asyncio
    async def test_multi_channel_notifications(self):
        """Multiple channels should be used based on policy."""
        policy = AutomatedEscalation.DEFAULT_POLICIES[AlertSeverity.CRITICAL]
        
        # Critical should use multiple channels
        assert len(policy.channels) > 1
        assert EscalationChannel.PAGERDUTY in policy.channels or EscalationChannel.SMS in policy.channels


# ============================================================================
# ESCALATION HISTORY TESTS
# ============================================================================


class TestEscalationHistory:
    """Test escalation history tracking."""
    
    @pytest.mark.asyncio
    async def test_history_recorded_on_creation(self, escalation_service):
        """Creation should be recorded in history."""
        alert_id = await escalation_service.create_alert(
            title="Test Alert",
            description="Test",
            severity=AlertSeverity.MEDIUM,
            source="test",
        )
        
        state = await escalation_service._get_state(alert_id)
        
        assert len(state.escalation_history) >= 1
        assert state.escalation_history[0]["action"] == "created"
    
    @pytest.mark.asyncio
    async def test_history_recorded_on_acknowledgment(self, escalation_service):
        """Acknowledgment should be recorded in history."""
        alert_id = await escalation_service.create_alert(
            title="Test Alert",
            description="Test",
            severity=AlertSeverity.MEDIUM,
            source="test",
        )
        
        await escalation_service.acknowledge(alert_id, "user_123")
        
        state = await escalation_service._get_state(alert_id)
        
        ack_entries = [h for h in state.escalation_history if h["action"] == "acknowledged"]
        assert len(ack_entries) == 1
        assert ack_entries[0]["user"] == "user_123"


# ============================================================================
# SERVICE STATUS TESTS
# ============================================================================


class TestServiceStatus:
    """Test service status reporting."""
    
    @pytest.mark.asyncio
    async def test_get_status(self, escalation_service):
        """Should return service status."""
        status = escalation_service.get_status()
        
        assert "running" in status
        assert "active_alerts" in status
        assert "unacknowledged" in status
        assert "policies_loaded" in status
    
    @pytest.mark.asyncio
    async def test_status_counts_alerts(self, escalation_service):
        """Status should count active alerts."""
        # Create some alerts
        await escalation_service.create_alert(
            title="Alert 1",
            description="Test",
            severity=AlertSeverity.HIGH,
            source="test",
        )
        
        await escalation_service.create_alert(
            title="Alert 2",
            description="Test",
            severity=AlertSeverity.MEDIUM,
            source="test",
        )
        
        status = escalation_service.get_status()
        
        assert status["active_alerts"] == 2
        assert status["unacknowledged"] == 2


# ============================================================================
# REGULATORY RESPONSE TESTS
# ============================================================================


class TestRegulatoryResponseAutomation:
    """
    C2 COMPLIANCE: Test regulatory response automation.
    """
    
    @pytest.fixture
    def regulatory_service(self, escalation_service):
        """Create regulatory service for testing."""
        return RegulatoryResponseAutomation(escalation_service=escalation_service)
    
    @pytest.mark.asyncio
    async def test_create_regulatory_request(self, regulatory_service):
        """
        C2 COMPLIANCE: Regulatory request creation.
        """
        request_id = await regulatory_service.create_request(
            framework=RegulatoryFramework.GDPR,
            request_type="data_export",
            requester_id="user_123",
            requester_email="user@example.com",
        )
        
        assert request_id is not None
        assert request_id.startswith("reg_")
    
    @pytest.mark.asyncio
    async def test_gdpr_deadline_is_30_days(self, regulatory_service):
        """GDPR requests should have 30-day deadline."""
        request_id = await regulatory_service.create_request(
            framework=RegulatoryFramework.GDPR,
            request_type="data_export",
            requester_id="user_123",
            requester_email="user@example.com",
        )
        
        request = regulatory_service._requests[request_id]
        
        days_until_due = (request.due_date - request.received_at).days
        assert days_until_due == 30
    
    @pytest.mark.asyncio
    async def test_complete_regulatory_request(self, regulatory_service):
        """
        C2 COMPLIANCE: Regulatory request completion.
        """
        request_id = await regulatory_service.create_request(
            framework=RegulatoryFramework.GDPR,
            request_type="data_deletion",
            requester_id="user_123",
            requester_email="user@example.com",
        )
        
        result = await regulatory_service.complete_request(
            request_id=request_id,
            completion_notes="All data deleted successfully",
        )
        
        assert result is True
        
        request = regulatory_service._requests[request_id]
        assert request.status == "completed"
        assert request.completed_at is not None
    
    @pytest.mark.asyncio
    async def test_get_pending_requests(self, regulatory_service):
        """Should return pending requests."""
        # Create a request
        await regulatory_service.create_request(
            framework=RegulatoryFramework.GDPR,
            request_type="access",
            requester_id="user_123",
            requester_email="user@example.com",
        )
        
        pending = regulatory_service.get_pending_requests()
        
        assert len(pending) == 1
        assert pending[0].framework == RegulatoryFramework.GDPR
    
    @pytest.mark.asyncio
    async def test_completed_requests_not_in_pending(self, regulatory_service):
        """Completed requests should not appear in pending."""
        request_id = await regulatory_service.create_request(
            framework=RegulatoryFramework.SOX,
            request_type="audit",
            requester_id="auditor",
            requester_email="auditor@example.com",
        )
        
        await regulatory_service.complete_request(request_id, "Completed")
        
        pending = regulatory_service.get_pending_requests()
        
        assert len(pending) == 0
