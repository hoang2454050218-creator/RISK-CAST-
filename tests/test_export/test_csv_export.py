"""
Tests for CSV Export Functionality.

C1 COMPLIANCE: Validates bulk CSV export implementation.

Tests:
- Audit trail CSV export
- Decisions CSV export
- Outcome data export
- Field selection
- Encoding and format options
"""
import pytest
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional, List
import csv
import io

from app.export.csv_exporter import (
    CSVExporter,
    AuditTrailCSVExporter,
    DecisionCSVExporter,
    OutcomeCSVExporter,
    ExportFormat,
    create_csv_exporter,
)


# ============================================================================
# FIXTURES - MOCK DATA
# ============================================================================


@dataclass
class MockAuditRecord:
    """Mock audit record for testing."""
    audit_id: str
    timestamp: datetime
    event_type: str
    entity_type: str
    entity_id: str
    actor_type: str
    actor_id: Optional[str]
    payload_hash: str
    sequence_number: int
    record_hash: str


@dataclass
class MockDecision:
    """Mock decision for testing."""
    decision_id: str
    customer_id: str
    created_at: datetime
    chokepoint: str
    reasoning_trace_id: str
    outcome: Optional["MockOutcome"] = None
    
    @property
    def q5_action(self):
        return MockAction()
    
    @property
    def q6_confidence(self):
        return MockConfidence()
    
    @property
    def q3_severity(self):
        return MockSeverity()
    
    @property
    def q2_when(self):
        return MockWhen()


@dataclass
class MockAction:
    action_type: str = "reroute"
    estimated_cost_usd: float = 5000.0
    deadline: datetime = None
    
    def __post_init__(self):
        if self.deadline is None:
            self.deadline = datetime.utcnow() + timedelta(hours=24)


@dataclass
class MockConfidence:
    calibrated_score: float = 0.85


@dataclass
class MockSeverity:
    total_exposure_usd: float = 100000.0
    expected_delay_days: int = 5


@dataclass
class MockWhen:
    urgency: str = "urgent"


@dataclass
class MockOutcome:
    actual_disruption: bool = True
    actual_delay_days: int = 7
    actual_loss_usd: float = 50000.0
    action_was_correct: bool = True
    recorded_at: datetime = None
    
    def __post_init__(self):
        if self.recorded_at is None:
            self.recorded_at = datetime.utcnow()


@pytest.fixture
def sample_audit_records():
    """Sample audit records for testing."""
    now = datetime.utcnow()
    return [
        MockAuditRecord(
            audit_id=f"AUD-{i:04d}",
            timestamp=now - timedelta(hours=i),
            event_type="decision_created" if i % 2 == 0 else "alert_sent",
            entity_type="decision",
            entity_id=f"DEC-{i:04d}",
            actor_type="system",
            actor_id=None,
            payload_hash=f"hash_{i}",
            sequence_number=i,
            record_hash=f"record_hash_{i}",
        )
        for i in range(10)
    ]


@pytest.fixture
def sample_decisions():
    """Sample decisions for testing."""
    now = datetime.utcnow()
    decisions = []
    
    for i in range(5):
        decision = MockDecision(
            decision_id=f"DEC-{i:04d}",
            customer_id=f"CUST-{i % 3:03d}",
            created_at=now - timedelta(days=i),
            chokepoint="red_sea" if i % 2 == 0 else "suez",
            reasoning_trace_id=f"TRACE-{i:04d}",
        )
        
        # Add outcome to some decisions
        if i % 2 == 0:
            decision.outcome = MockOutcome(
                actual_delay_days=i + 3,
                actual_loss_usd=10000.0 * (i + 1),
            )
        
        decisions.append(decision)
    
    return decisions


# ============================================================================
# AUDIT TRAIL EXPORT TESTS
# ============================================================================


class TestAuditTrailCSVExport:
    """Test audit trail CSV export."""
    
    def test_export_audit_records(self, sample_audit_records):
        """
        C1 COMPLIANCE: Audit trail exports to CSV.
        
        Should export all audit records with correct headers.
        """
        exporter = AuditTrailCSVExporter()
        result = exporter.export_sync(sample_audit_records)
        
        # Parse result
        reader = csv.DictReader(io.StringIO(result.decode('utf-8')))
        rows = list(reader)
        
        assert len(rows) == 10
        assert "audit_id" in reader.fieldnames
        assert "timestamp" in reader.fieldnames
        assert "event_type" in reader.fieldnames
        assert "record_hash" in reader.fieldnames
    
    def test_export_audit_with_field_selection(self, sample_audit_records):
        """Should export only selected fields."""
        exporter = AuditTrailCSVExporter()
        selected_fields = ["audit_id", "timestamp", "event_type"]
        
        result = exporter.export_sync(sample_audit_records, fields=selected_fields)
        
        reader = csv.DictReader(io.StringIO(result.decode('utf-8')))
        rows = list(reader)
        
        assert len(reader.fieldnames) == 3
        assert "audit_id" in reader.fieldnames
        assert "record_hash" not in reader.fieldnames
    
    def test_export_empty_audit_trail(self):
        """Should handle empty audit trail."""
        exporter = AuditTrailCSVExporter()
        result = exporter.export_sync([])
        
        reader = csv.DictReader(io.StringIO(result.decode('utf-8')))
        rows = list(reader)
        
        assert len(rows) == 0
        # Headers should still be present
        assert len(reader.fieldnames) > 0


# ============================================================================
# DECISION EXPORT TESTS
# ============================================================================


class TestDecisionCSVExport:
    """Test decision CSV export."""
    
    def test_export_decisions(self, sample_decisions):
        """
        C1 COMPLIANCE: Decisions export to CSV.
        
        Should export decisions with core fields.
        """
        exporter = DecisionCSVExporter()
        result = exporter.export_sync(sample_decisions, include_outcomes=False)
        
        reader = csv.DictReader(io.StringIO(result.decode('utf-8')))
        rows = list(reader)
        
        assert len(rows) == 5
        assert "decision_id" in reader.fieldnames
        assert "customer_id" in reader.fieldnames
        assert "action_type" in reader.fieldnames
        assert "confidence_score" in reader.fieldnames
    
    def test_export_decisions_with_outcomes(self, sample_decisions):
        """
        C1 COMPLIANCE: Decisions export includes outcomes.
        
        Should include outcome columns when requested.
        """
        exporter = DecisionCSVExporter()
        result = exporter.export_sync(sample_decisions, include_outcomes=True)
        
        reader = csv.DictReader(io.StringIO(result.decode('utf-8')))
        rows = list(reader)
        
        # Check outcome columns exist
        assert "outcome_recorded" in reader.fieldnames
        assert "actual_delay_days" in reader.fieldnames
        assert "action_was_correct" in reader.fieldnames
        
        # Check outcome data
        with_outcome = [r for r in rows if r["outcome_recorded"] == "true"]
        without_outcome = [r for r in rows if r["outcome_recorded"] == "false"]
        
        assert len(with_outcome) > 0
        assert len(without_outcome) > 0
    
    def test_export_decisions_empty(self):
        """Should handle empty decision list."""
        exporter = DecisionCSVExporter()
        result = exporter.export_sync([], include_outcomes=True)
        
        reader = csv.DictReader(io.StringIO(result.decode('utf-8')))
        rows = list(reader)
        
        assert len(rows) == 0


# ============================================================================
# FORMAT TESTS
# ============================================================================


class TestCSVFormats:
    """Test different CSV formats."""
    
    def test_standard_csv_format(self, sample_audit_records):
        """Standard CSV with comma delimiter."""
        exporter = AuditTrailCSVExporter(delimiter=",")
        result = exporter.export_sync(sample_audit_records)
        
        # Should be comma-separated
        first_line = result.decode('utf-8').split('\n')[0]
        assert ',' in first_line
    
    def test_tsv_format(self, sample_audit_records):
        """TSV format with tab delimiter."""
        exporter = AuditTrailCSVExporter(delimiter="\t")
        result = exporter.export_sync(sample_audit_records)
        
        # Should be tab-separated
        first_line = result.decode('utf-8').split('\n')[0]
        assert '\t' in first_line
    
    def test_excel_csv_with_bom(self, sample_audit_records):
        """Excel CSV with BOM for proper encoding."""
        exporter = AuditTrailCSVExporter(include_bom=True)
        result = exporter.export_sync(sample_audit_records)
        
        # Should start with UTF-8 BOM
        assert result.startswith(b'\xef\xbb\xbf')
    
    def test_create_csv_exporter_factory(self):
        """Factory function creates correct exporter."""
        audit_exporter = create_csv_exporter("audit")
        assert isinstance(audit_exporter, AuditTrailCSVExporter)
        
        decision_exporter = create_csv_exporter("decisions")
        assert isinstance(decision_exporter, DecisionCSVExporter)
        
        outcome_exporter = create_csv_exporter("outcomes")
        assert isinstance(outcome_exporter, OutcomeCSVExporter)
    
    def test_factory_with_excel_format(self):
        """Factory should configure Excel format correctly."""
        exporter = create_csv_exporter("audit", format=ExportFormat.EXCEL_CSV)
        
        # Excel format should have BOM
        assert exporter._include_bom is True


# ============================================================================
# DATA FORMATTING TESTS
# ============================================================================


class TestDataFormatting:
    """Test value formatting in exports."""
    
    def test_datetime_formatting(self, sample_audit_records):
        """Datetime values should be ISO formatted."""
        exporter = AuditTrailCSVExporter()
        result = exporter.export_sync(sample_audit_records)
        
        reader = csv.DictReader(io.StringIO(result.decode('utf-8')))
        row = next(reader)
        
        # Timestamp should be ISO format
        timestamp = row["timestamp"]
        assert "T" in timestamp or "-" in timestamp
    
    def test_none_values(self):
        """None values should be empty strings."""
        record = MockAuditRecord(
            audit_id="AUD-001",
            timestamp=datetime.utcnow(),
            event_type="test",
            entity_type="test",
            entity_id="test",
            actor_type="user",
            actor_id=None,  # None value
            payload_hash="hash",
            sequence_number=1,
            record_hash="hash",
        )
        
        exporter = AuditTrailCSVExporter()
        result = exporter.export_sync([record])
        
        reader = csv.DictReader(io.StringIO(result.decode('utf-8')))
        row = next(reader)
        
        assert row["actor_id"] == ""
    
    def test_boolean_formatting(self, sample_decisions):
        """Boolean values should be 'true' or 'false'."""
        exporter = DecisionCSVExporter()
        result = exporter.export_sync(sample_decisions, include_outcomes=True)
        
        reader = csv.DictReader(io.StringIO(result.decode('utf-8')))
        rows = list(reader)
        
        for row in rows:
            if row["outcome_recorded"]:
                assert row["outcome_recorded"] in ["true", "false"]


# ============================================================================
# ENCODING TESTS
# ============================================================================


class TestEncoding:
    """Test encoding handling."""
    
    def test_utf8_encoding(self, sample_audit_records):
        """Default encoding should be UTF-8."""
        exporter = AuditTrailCSVExporter(encoding="utf-8")
        result = exporter.export_sync(sample_audit_records)
        
        # Should be valid UTF-8
        decoded = result.decode('utf-8')
        assert len(decoded) > 0
    
    def test_handles_unicode_characters(self):
        """Should handle Unicode characters in data."""
        record = MockAuditRecord(
            audit_id="AUD-001",
            timestamp=datetime.utcnow(),
            event_type="test_unicode_тест_测试",
            entity_type="test",
            entity_id="test",
            actor_type="user",
            actor_id="用户",
            payload_hash="hash",
            sequence_number=1,
            record_hash="hash",
        )
        
        exporter = AuditTrailCSVExporter()
        result = exporter.export_sync([record])
        
        decoded = result.decode('utf-8')
        assert "тест" in decoded
        assert "测试" in decoded
        assert "用户" in decoded
