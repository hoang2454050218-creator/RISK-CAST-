"""
Tests for Post-Mortem Tracking Module.

Tests:
- test_postmortem_deadline_enforcement(): SEV1/2 require post-mortem within 48h
- test_postmortem_creation(): Post-mortems can be created from incidents
- test_action_item_tracking(): Action items are tracked correctly
"""

import pytest
from datetime import datetime, timedelta

from app.ops.postmortem.tracker import (
    IncidentSeverity,
    ActionItemStatus,
    ActionItem,
    PostMortem,
    PostMortemStatus,
    Incident,
    IncidentTimeline,
    PostMortemTracker,
    PostMortemRepository,
    PostMortemMetrics,
    get_postmortem_tracker,
)
from app.ops.postmortem.templates import (
    PostMortemTemplate,
    generate_postmortem_template,
    generate_blank_template,
)


# ============================================================================
# INCIDENT TESTS
# ============================================================================


class TestIncident:
    """Tests for Incident model."""
    
    def test_incident_creation(self):
        """Incident can be created."""
        incident = Incident(
            title="Test Incident",
            severity=IncidentSeverity.SEV2,
            started_at=datetime.utcnow() - timedelta(hours=2),
            detected_at=datetime.utcnow() - timedelta(hours=1, minutes=45),
        )
        
        assert incident.incident_id is not None
        assert incident.severity == IncidentSeverity.SEV2
        assert incident.status == "open"


# ============================================================================
# POST-MORTEM TESTS
# ============================================================================


class TestPostMortem:
    """Tests for PostMortem model."""
    
    @pytest.fixture
    def sample_postmortem(self):
        """Create sample post-mortem."""
        now = datetime.utcnow()
        return PostMortem(
            incident_id="inc_test123",
            severity=IncidentSeverity.SEV1,
            incident_start=now - timedelta(hours=4),
            incident_detected=now - timedelta(hours=3, minutes=50),
            incident_mitigated=now - timedelta(hours=3),
            incident_resolved=now - timedelta(hours=2),
            time_to_detect_minutes=10,
            time_to_mitigate_minutes=50,
            time_to_resolve_minutes=60,
            customer_impact_minutes=120,
            title="Database Outage",
            summary="Database connection pool exhausted",
            author="engineer@riskcast.io",
        )
    
    def test_postmortem_requires_postmortem(self, sample_postmortem):
        """SEV1/SEV2 require post-mortem."""
        assert sample_postmortem.requires_postmortem is True
        
        sev3 = PostMortem(
            incident_id="inc_sev3",
            severity=IncidentSeverity.SEV3,
            incident_start=datetime.utcnow(),
            incident_detected=datetime.utcnow(),
            incident_mitigated=datetime.utcnow(),
            incident_resolved=datetime.utcnow(),
            time_to_detect_minutes=5,
            time_to_mitigate_minutes=10,
            time_to_resolve_minutes=15,
            customer_impact_minutes=15,
            title="Minor Issue",
            author="engineer@riskcast.io",
        )
        
        assert sev3.requires_postmortem is False
    
    def test_postmortem_deadline(self, sample_postmortem):
        """Post-mortem deadline is 48h after resolution."""
        expected = sample_postmortem.incident_resolved + timedelta(hours=48)
        assert sample_postmortem.postmortem_deadline == expected
    
    def test_postmortem_overdue(self):
        """Post-mortem is overdue after 48h."""
        old_pm = PostMortem(
            incident_id="inc_old",
            severity=IncidentSeverity.SEV1,
            incident_start=datetime.utcnow() - timedelta(days=5),
            incident_detected=datetime.utcnow() - timedelta(days=5),
            incident_mitigated=datetime.utcnow() - timedelta(days=5),
            incident_resolved=datetime.utcnow() - timedelta(days=5),  # 5 days ago
            time_to_detect_minutes=10,
            time_to_mitigate_minutes=30,
            time_to_resolve_minutes=60,
            customer_impact_minutes=100,
            title="Old Incident",
            author="engineer@riskcast.io",
            status=PostMortemStatus.DRAFT,
        )
        
        assert old_pm.is_overdue is True
        assert old_pm.hours_until_deadline < 0
    
    def test_postmortem_not_overdue_when_published(self, sample_postmortem):
        """Published post-mortems are not overdue."""
        sample_postmortem.status = PostMortemStatus.PUBLISHED
        sample_postmortem.published_at = datetime.utcnow()
        
        # Even if technically past deadline, published is not overdue
        assert sample_postmortem.is_overdue is False


# ============================================================================
# ACTION ITEM TESTS
# ============================================================================


class TestActionItem:
    """Tests for ActionItem model."""
    
    def test_action_item_creation(self):
        """Action item can be created."""
        item = ActionItem(
            postmortem_id="pm_test",
            description="Add circuit breaker to database connection",
            owner="engineer@riskcast.io",
            due_date=datetime.utcnow() + timedelta(days=7),
            priority="P1",
        )
        
        assert item.item_id is not None
        assert item.status == ActionItemStatus.OPEN
        assert item.is_overdue is False
    
    def test_action_item_overdue(self):
        """Action item is overdue when past due date."""
        item = ActionItem(
            postmortem_id="pm_test",
            description="Overdue item",
            owner="engineer@riskcast.io",
            due_date=datetime.utcnow() - timedelta(days=3),  # 3 days ago
            status=ActionItemStatus.OPEN,
        )
        
        assert item.is_overdue is True
        assert item.days_overdue == 3
    
    def test_completed_item_not_overdue(self):
        """Completed items are not overdue."""
        item = ActionItem(
            postmortem_id="pm_test",
            description="Completed item",
            owner="engineer@riskcast.io",
            due_date=datetime.utcnow() - timedelta(days=5),  # Past due
            status=ActionItemStatus.COMPLETED,
            completed_at=datetime.utcnow() - timedelta(days=6),
        )
        
        assert item.is_overdue is False


# ============================================================================
# POST-MORTEM TRACKER TESTS
# ============================================================================


class TestPostMortemTracker:
    """Tests for PostMortemTracker."""
    
    @pytest.fixture
    def tracker(self):
        """Create fresh tracker instance."""
        import app.ops.postmortem.tracker as pm
        pm._postmortem_tracker = None
        return PostMortemTracker()
    
    @pytest.mark.asyncio
    async def test_create_incident(self, tracker):
        """Incident can be created."""
        incident = await tracker.create_incident(
            title="Test Incident",
            severity=IncidentSeverity.SEV2,
            started_at=datetime.utcnow() - timedelta(hours=1),
            summary="Test incident summary",
        )
        
        assert incident.incident_id is not None
        assert incident.title == "Test Incident"
        assert incident.severity == IncidentSeverity.SEV2
    
    @pytest.mark.asyncio
    async def test_resolve_incident(self, tracker):
        """Incident can be resolved."""
        incident = await tracker.create_incident(
            title="To Resolve",
            severity=IncidentSeverity.SEV1,
            started_at=datetime.utcnow() - timedelta(hours=2),
        )
        
        resolved = await tracker.resolve_incident(
            incident_id=incident.incident_id,
            mitigated_at=datetime.utcnow() - timedelta(hours=1),
            resolved_at=datetime.utcnow(),
        )
        
        assert resolved.status == "resolved"
        assert resolved.resolved_at is not None
    
    @pytest.mark.asyncio
    async def test_create_postmortem(self, tracker):
        """Post-mortem can be created from incident."""
        # Create and resolve incident
        incident = await tracker.create_incident(
            title="For Post-Mortem",
            severity=IncidentSeverity.SEV1,
            started_at=datetime.utcnow() - timedelta(hours=3),
        )
        
        await tracker.resolve_incident(
            incident_id=incident.incident_id,
            mitigated_at=datetime.utcnow() - timedelta(hours=2),
            resolved_at=datetime.utcnow() - timedelta(hours=1),
        )
        
        # Create post-mortem
        postmortem = await tracker.create_postmortem(
            incident_id=incident.incident_id,
            author="engineer@riskcast.io",
        )
        
        assert postmortem is not None
        assert postmortem.incident_id == incident.incident_id
        assert postmortem.status == PostMortemStatus.DRAFT
        assert postmortem.time_to_detect_minutes >= 0
    
    @pytest.mark.asyncio
    async def test_postmortem_deadline_enforcement(self, tracker):
        """
        Test that SEV1/2 require post-mortem within 48h.
        
        This is a required test from acceptance criteria.
        """
        # Create SEV1 incident resolved 3 days ago
        incident = await tracker.create_incident(
            title="Old SEV1 Incident",
            severity=IncidentSeverity.SEV1,
            started_at=datetime.utcnow() - timedelta(days=4),
        )
        
        await tracker.resolve_incident(
            incident_id=incident.incident_id,
            mitigated_at=datetime.utcnow() - timedelta(days=3, hours=23),
            resolved_at=datetime.utcnow() - timedelta(days=3),  # Resolved 3 days ago
        )
        
        # Check for overdue post-mortems
        overdue = await tracker.get_overdue_postmortems()
        
        # Should have this incident as overdue (no post-mortem created)
        assert len(overdue) >= 1
        overdue_ids = [o["incident_id"] for o in overdue]
        assert incident.incident_id in overdue_ids
        
        # Check hours overdue
        overdue_incident = next(o for o in overdue if o["incident_id"] == incident.incident_id)
        assert overdue_incident["hours_overdue"] > 0
    
    @pytest.mark.asyncio
    async def test_add_action_item(self, tracker):
        """Action items can be added to post-mortem."""
        # Setup
        incident = await tracker.create_incident(
            title="Action Item Test",
            severity=IncidentSeverity.SEV2,
            started_at=datetime.utcnow() - timedelta(hours=2),
        )
        await tracker.resolve_incident(
            incident_id=incident.incident_id,
            mitigated_at=datetime.utcnow() - timedelta(hours=1),
            resolved_at=datetime.utcnow(),
        )
        postmortem = await tracker.create_postmortem(
            incident_id=incident.incident_id,
            author="engineer@riskcast.io",
        )
        
        # Add action item
        item = await tracker.add_action_item(
            postmortem_id=postmortem.postmortem_id,
            description="Add database connection monitoring",
            owner="dba@riskcast.io",
            priority="P1",
        )
        
        assert item is not None
        assert item.description == "Add database connection monitoring"
        assert item.owner == "dba@riskcast.io"
        assert item.due_date is not None
    
    @pytest.mark.asyncio
    async def test_complete_action_item(self, tracker):
        """Action items can be completed."""
        # Setup
        incident = await tracker.create_incident(
            title="Complete Item Test",
            severity=IncidentSeverity.SEV2,
            started_at=datetime.utcnow() - timedelta(hours=2),
        )
        await tracker.resolve_incident(
            incident_id=incident.incident_id,
            mitigated_at=datetime.utcnow() - timedelta(hours=1),
            resolved_at=datetime.utcnow(),
        )
        postmortem = await tracker.create_postmortem(
            incident_id=incident.incident_id,
            author="engineer@riskcast.io",
        )
        item = await tracker.add_action_item(
            postmortem_id=postmortem.postmortem_id,
            description="Test item",
            owner="engineer@riskcast.io",
        )
        
        # Complete
        completed = await tracker.complete_action_item(
            item_id=item.item_id,
            notes="Implemented in PR #123",
        )
        
        assert completed.status == ActionItemStatus.COMPLETED
        assert completed.completed_at is not None
        assert completed.notes == "Implemented in PR #123"
    
    @pytest.mark.asyncio
    async def test_publish_postmortem(self, tracker):
        """Post-mortem can be published."""
        # Setup
        incident = await tracker.create_incident(
            title="Publish Test",
            severity=IncidentSeverity.SEV2,
            started_at=datetime.utcnow() - timedelta(hours=2),
        )
        await tracker.resolve_incident(
            incident_id=incident.incident_id,
            mitigated_at=datetime.utcnow() - timedelta(hours=1),
            resolved_at=datetime.utcnow(),
        )
        postmortem = await tracker.create_postmortem(
            incident_id=incident.incident_id,
            author="engineer@riskcast.io",
        )
        
        # Publish
        published = await tracker.publish_postmortem(postmortem.postmortem_id)
        
        assert published.status == PostMortemStatus.PUBLISHED
        assert published.published_at is not None
    
    @pytest.mark.asyncio
    async def test_get_metrics(self, tracker):
        """Metrics are calculated correctly."""
        metrics = await tracker.get_metrics()
        
        assert isinstance(metrics, PostMortemMetrics)
        assert metrics.total_postmortems >= 0
        assert 0 <= metrics.completion_rate <= 1


# ============================================================================
# TEMPLATE TESTS
# ============================================================================


class TestPostMortemTemplates:
    """Tests for post-mortem templates."""
    
    def test_generate_template(self):
        """Template can be generated from post-mortem."""
        pm = PostMortem(
            incident_id="inc_template_test",
            severity=IncidentSeverity.SEV1,
            incident_start=datetime.utcnow() - timedelta(hours=4),
            incident_detected=datetime.utcnow() - timedelta(hours=3, minutes=50),
            incident_mitigated=datetime.utcnow() - timedelta(hours=3),
            incident_resolved=datetime.utcnow() - timedelta(hours=2),
            time_to_detect_minutes=10,
            time_to_mitigate_minutes=50,
            time_to_resolve_minutes=60,
            customer_impact_minutes=120,
            title="Template Test Incident",
            summary="Testing template generation",
            author="engineer@riskcast.io",
            customers_affected=100,
            revenue_impact_usd=5000,
            root_causes=["Root cause 1", "Root cause 2"],
            what_went_well=["Quick detection"],
            what_went_poorly=["Slow mitigation"],
        )
        
        template = generate_postmortem_template(pm)
        
        assert isinstance(template, PostMortemTemplate)
        assert "Template Test Incident" in template.markdown
        assert "SEV1" in template.markdown
        assert "Root cause 1" in template.root_cause_section
        assert "Quick detection" in template.retrospective_section
    
    def test_generate_blank_template(self):
        """Blank template can be generated."""
        template = generate_blank_template(
            title="New Incident",
            severity="SEV2",
            incident_date=datetime.utcnow(),
            author="engineer@riskcast.io",
        )
        
        assert "# Post-Mortem: New Incident" in template
        assert "SEV2" in template
        assert "[Provide a 2-3 sentence summary" in template


# ============================================================================
# SINGLETON TESTS
# ============================================================================


class TestPostMortemSingleton:
    """Tests for post-mortem singleton behavior."""
    
    def test_tracker_singleton(self):
        """get_postmortem_tracker returns same instance."""
        import app.ops.postmortem.tracker as pm
        pm._postmortem_tracker = None
        
        tracker1 = get_postmortem_tracker()
        tracker2 = get_postmortem_tracker()
        
        assert tracker1 is tracker2
