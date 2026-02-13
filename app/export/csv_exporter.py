"""
CSV bulk export for audit trail and decisions.

C1 COMPLIANCE: "No bulk export functionality (CSV, PDF)" - FIXED

Provides:
- Audit trail CSV export
- Decisions CSV export with outcomes
- Calibration data export
- Configurable field selection
"""
from datetime import datetime
from typing import List, Optional, Dict, Any, Callable, Protocol, TYPE_CHECKING
from enum import Enum
import csv
import io
import structlog

if TYPE_CHECKING:
    from app.audit.schemas import AuditRecord
    from app.riskcast.schemas.decision import DecisionObject

logger = structlog.get_logger(__name__)


# ============================================================================
# PROTOCOLS
# ============================================================================


class AuditRepository(Protocol):
    """Protocol for audit repository."""
    
    async def get_records(
        self,
        start_date: datetime,
        end_date: datetime,
        event_types: Optional[List[str]] = None,
        entity_type: Optional[str] = None,
        limit: int = 10000,
    ) -> List[Any]: ...


class DecisionRepository(Protocol):
    """Protocol for decision repository."""
    
    async def get_decisions(
        self,
        start_date: datetime,
        end_date: datetime,
        customer_id: Optional[str] = None,
        limit: int = 10000,
    ) -> List[Any]: ...


# ============================================================================
# EXPORT FORMATS
# ============================================================================


class ExportFormat(str, Enum):
    """Supported export formats."""
    
    CSV = "csv"
    TSV = "tsv"
    EXCEL_CSV = "excel_csv"  # CSV with BOM for Excel


# ============================================================================
# BASE CSV EXPORTER
# ============================================================================


class CSVExporter:
    """
    Base CSV exporter class.
    
    C1 COMPLIANCE: CSV bulk export functionality.
    
    Features:
    - Configurable field selection
    - Custom field transformers
    - Multiple format support (CSV, TSV, Excel)
    - Progress callbacks for large exports
    """
    
    def __init__(
        self,
        delimiter: str = ",",
        include_bom: bool = False,
        encoding: str = "utf-8",
    ):
        """
        Initialize CSV exporter.
        
        Args:
            delimiter: Field delimiter (comma, tab, etc.)
            include_bom: Include BOM for Excel compatibility
            encoding: Output encoding
        """
        self._delimiter = delimiter
        self._include_bom = include_bom
        self._encoding = encoding
    
    def _create_output(self) -> io.StringIO:
        """Create output buffer."""
        output = io.StringIO()
        if self._include_bom:
            output.write('\ufeff')  # UTF-8 BOM
        return output
    
    def _to_bytes(self, output: io.StringIO) -> bytes:
        """Convert string output to bytes."""
        return output.getvalue().encode(self._encoding)
    
    def _format_value(self, value: Any) -> str:
        """Format a value for CSV output."""
        if value is None:
            return ""
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (list, dict)):
            import json
            return json.dumps(value)
        return str(value)


# ============================================================================
# AUDIT TRAIL EXPORTER
# ============================================================================


class AuditTrailCSVExporter(CSVExporter):
    """
    Export audit trail to CSV.
    
    C1 COMPLIANCE: Audit trail bulk export.
    """
    
    FIELDNAMES = [
        "audit_id",
        "timestamp",
        "event_type",
        "entity_type",
        "entity_id",
        "actor_type",
        "actor_id",
        "action",
        "payload_hash",
        "sequence_number",
        "record_hash",
        "parent_hash",
        "metadata",
    ]
    
    def __init__(
        self,
        audit_repo: Optional[AuditRepository] = None,
        **kwargs,
    ):
        """
        Initialize audit trail exporter.
        
        Args:
            audit_repo: Repository for fetching audit records
        """
        super().__init__(**kwargs)
        self._audit_repo = audit_repo
    
    async def export(
        self,
        start_date: datetime,
        end_date: datetime,
        event_types: Optional[List[str]] = None,
        entity_type: Optional[str] = None,
        fields: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> bytes:
        """
        Export audit trail to CSV.
        
        C1 COMPLIANCE: Audit trail CSV export.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            event_types: Filter by event types
            entity_type: Filter by entity type
            fields: Fields to include (default: all)
            progress_callback: Callback for progress updates
        
        Returns:
            CSV file as bytes
        """
        fieldnames = fields or self.FIELDNAMES
        
        # Fetch records
        if self._audit_repo:
            records = await self._audit_repo.get_records(
                start_date=start_date,
                end_date=end_date,
                event_types=event_types,
                entity_type=entity_type,
            )
        else:
            records = []
        
        total = len(records)
        
        # Create CSV
        output = self._create_output()
        writer = csv.DictWriter(
            output,
            fieldnames=fieldnames,
            delimiter=self._delimiter,
            extrasaction='ignore',
        )
        
        writer.writeheader()
        
        for idx, record in enumerate(records):
            row = self._record_to_row(record)
            writer.writerow({k: self._format_value(row.get(k)) for k in fieldnames})
            
            if progress_callback and idx % 100 == 0:
                progress_callback(idx + 1, total)
        
        logger.info(
            "audit_trail_exported",
            record_count=total,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )
        
        return self._to_bytes(output)
    
    def _record_to_row(self, record: Any) -> Dict[str, Any]:
        """Convert audit record to row dict."""
        if hasattr(record, 'dict'):
            return record.dict()
        if hasattr(record, '__dict__'):
            return record.__dict__
        return dict(record) if isinstance(record, dict) else {}
    
    def export_sync(
        self,
        records: List[Any],
        fields: Optional[List[str]] = None,
    ) -> bytes:
        """
        Synchronous export from provided records.
        
        C1 COMPLIANCE: Sync export for testing.
        """
        fieldnames = fields or self.FIELDNAMES
        
        output = self._create_output()
        writer = csv.DictWriter(
            output,
            fieldnames=fieldnames,
            delimiter=self._delimiter,
            extrasaction='ignore',
        )
        
        writer.writeheader()
        
        for record in records:
            row = self._record_to_row(record)
            writer.writerow({k: self._format_value(row.get(k)) for k in fieldnames})
        
        return self._to_bytes(output)


# ============================================================================
# DECISION EXPORTER
# ============================================================================


class DecisionCSVExporter(CSVExporter):
    """
    Export decisions to CSV.
    
    C1 COMPLIANCE: Decisions bulk export.
    """
    
    FIELDNAMES = [
        "decision_id",
        "customer_id",
        "created_at",
        "action_type",
        "confidence_score",
        "exposure_usd",
        "expected_delay_days",
        "action_cost_usd",
        "chokepoint",
        "reasoning_trace_id",
        "urgency",
        "deadline",
    ]
    
    OUTCOME_FIELDNAMES = [
        "outcome_recorded",
        "actual_disruption",
        "actual_delay_days",
        "actual_loss_usd",
        "action_was_correct",
        "outcome_recorded_at",
    ]
    
    def __init__(
        self,
        decision_repo: Optional[DecisionRepository] = None,
        **kwargs,
    ):
        """Initialize decision exporter."""
        super().__init__(**kwargs)
        self._decision_repo = decision_repo
    
    async def export(
        self,
        start_date: datetime,
        end_date: datetime,
        customer_id: Optional[str] = None,
        include_outcomes: bool = True,
        fields: Optional[List[str]] = None,
    ) -> bytes:
        """
        Export decisions to CSV.
        
        C1 COMPLIANCE: Decisions CSV export with outcomes.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            customer_id: Filter by customer
            include_outcomes: Include outcome data
            fields: Fields to include
        
        Returns:
            CSV file as bytes
        """
        fieldnames = fields or self.FIELDNAMES.copy()
        if include_outcomes:
            fieldnames.extend(self.OUTCOME_FIELDNAMES)
        
        # Fetch decisions
        if self._decision_repo:
            decisions = await self._decision_repo.get_decisions(
                start_date=start_date,
                end_date=end_date,
                customer_id=customer_id,
            )
        else:
            decisions = []
        
        # Create CSV
        output = self._create_output()
        writer = csv.DictWriter(
            output,
            fieldnames=fieldnames,
            delimiter=self._delimiter,
            extrasaction='ignore',
        )
        
        writer.writeheader()
        
        for decision in decisions:
            row = self._decision_to_row(decision, include_outcomes)
            writer.writerow({k: self._format_value(row.get(k)) for k in fieldnames})
        
        logger.info(
            "decisions_exported",
            decision_count=len(decisions),
            customer_id=customer_id,
            include_outcomes=include_outcomes,
        )
        
        return self._to_bytes(output)
    
    def _decision_to_row(self, decision: Any, include_outcomes: bool) -> Dict[str, Any]:
        """Convert decision to row dict."""
        row = {
            "decision_id": getattr(decision, 'decision_id', ''),
            "customer_id": getattr(decision, 'customer_id', ''),
            "created_at": getattr(decision, 'created_at', ''),
            "action_type": getattr(getattr(decision, 'q5_action', None), 'action_type', ''),
            "confidence_score": getattr(getattr(decision, 'q6_confidence', None), 'calibrated_score', ''),
            "exposure_usd": getattr(getattr(decision, 'q3_severity', None), 'total_exposure_usd', ''),
            "expected_delay_days": getattr(getattr(decision, 'q3_severity', None), 'expected_delay_days', ''),
            "action_cost_usd": getattr(getattr(decision, 'q5_action', None), 'estimated_cost_usd', ''),
            "chokepoint": getattr(decision, 'chokepoint', ''),
            "reasoning_trace_id": getattr(decision, 'reasoning_trace_id', ''),
            "urgency": getattr(getattr(decision, 'q2_when', None), 'urgency', ''),
            "deadline": getattr(getattr(decision, 'q5_action', None), 'deadline', ''),
        }
        
        if include_outcomes:
            outcome = getattr(decision, 'outcome', None)
            if outcome:
                row.update({
                    "outcome_recorded": True,
                    "actual_disruption": getattr(outcome, 'actual_disruption', ''),
                    "actual_delay_days": getattr(outcome, 'actual_delay_days', ''),
                    "actual_loss_usd": getattr(outcome, 'actual_loss_usd', ''),
                    "action_was_correct": getattr(outcome, 'action_was_correct', ''),
                    "outcome_recorded_at": getattr(outcome, 'recorded_at', ''),
                })
            else:
                row.update({
                    "outcome_recorded": False,
                    "actual_disruption": "",
                    "actual_delay_days": "",
                    "actual_loss_usd": "",
                    "action_was_correct": "",
                    "outcome_recorded_at": "",
                })
        
        return row
    
    def export_sync(
        self,
        decisions: List[Any],
        include_outcomes: bool = True,
        fields: Optional[List[str]] = None,
    ) -> bytes:
        """Synchronous export from provided decisions."""
        fieldnames = fields or self.FIELDNAMES.copy()
        if include_outcomes:
            fieldnames.extend(self.OUTCOME_FIELDNAMES)
        
        output = self._create_output()
        writer = csv.DictWriter(
            output,
            fieldnames=fieldnames,
            delimiter=self._delimiter,
            extrasaction='ignore',
        )
        
        writer.writeheader()
        
        for decision in decisions:
            row = self._decision_to_row(decision, include_outcomes)
            writer.writerow({k: self._format_value(row.get(k)) for k in fieldnames})
        
        return self._to_bytes(output)


# ============================================================================
# OUTCOME EXPORTER
# ============================================================================


class OutcomeCSVExporter(CSVExporter):
    """
    Export outcomes for calibration analysis.
    
    C1 COMPLIANCE: Outcome data export for calibration.
    """
    
    FIELDNAMES = [
        "outcome_id",
        "decision_id",
        "recorded_at",
        "predicted_probability",
        "actual_outcome",
        "confidence_band",
        "calibration_bucket",
        "prediction_correct",
        "error_magnitude",
    ]
    
    def export_sync(
        self,
        outcomes: List[Any],
        fields: Optional[List[str]] = None,
    ) -> bytes:
        """Export outcomes to CSV."""
        fieldnames = fields or self.FIELDNAMES
        
        output = self._create_output()
        writer = csv.DictWriter(
            output,
            fieldnames=fieldnames,
            delimiter=self._delimiter,
            extrasaction='ignore',
        )
        
        writer.writeheader()
        
        for outcome in outcomes:
            row = self._outcome_to_row(outcome)
            writer.writerow({k: self._format_value(row.get(k)) for k in fieldnames})
        
        return self._to_bytes(output)
    
    def _outcome_to_row(self, outcome: Any) -> Dict[str, Any]:
        """Convert outcome to row dict."""
        if hasattr(outcome, 'dict'):
            return outcome.dict()
        if hasattr(outcome, '__dict__'):
            return outcome.__dict__
        return dict(outcome) if isinstance(outcome, dict) else {}


# ============================================================================
# FACTORY FUNCTION
# ============================================================================


def create_csv_exporter(
    export_type: str,
    format: ExportFormat = ExportFormat.CSV,
    **kwargs,
) -> CSVExporter:
    """
    Create CSV exporter for specified type.
    
    Args:
        export_type: Type of export (audit, decisions, outcomes)
        format: Export format
        **kwargs: Additional arguments for exporter
    
    Returns:
        Configured CSV exporter
    """
    delimiter = "," if format in [ExportFormat.CSV, ExportFormat.EXCEL_CSV] else "\t"
    include_bom = format == ExportFormat.EXCEL_CSV
    
    exporters = {
        "audit": AuditTrailCSVExporter,
        "decisions": DecisionCSVExporter,
        "outcomes": OutcomeCSVExporter,
    }
    
    exporter_class = exporters.get(export_type, CSVExporter)
    return exporter_class(delimiter=delimiter, include_bom=include_bom, **kwargs)
