"""
OMEN Signal Validator — Deep validation beyond Pydantic schema.

Validates:
1. Schema compliance (beyond basic Pydantic)
2. Content quality (title length, evidence count, description)
3. Temporal validity (not too old, not in the future)
4. Cross-reference checks (signal_id format, category values)
5. Confidence/probability bounds and consistency

Returns a ValidationResult with pass/fail, quality score, and issues list.
"""

from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Optional

import structlog

from riskcast.schemas.omen_signal import SignalEvent

logger = structlog.get_logger(__name__)

# Validation config
MAX_SIGNAL_AGE_HOURS: int = 168       # 7 days
MIN_TITLE_LENGTH: int = 10
MAX_TITLE_LENGTH: int = 500
MIN_EVIDENCE_ITEMS: int = 0            # 0 = don't require evidence
VALID_CATEGORIES: set[str] = {
    "GEOPOLITICAL", "ECONOMIC", "WEATHER", "SUPPLY_CHAIN",
    "REGULATORY", "LABOR", "INFRASTRUCTURE", "SECURITY",
    "MARKET", "HEALTH", "ENVIRONMENTAL", "TECHNOLOGY",
}
VALID_CONFIDENCE_LEVELS: set[str] = {"HIGH", "MEDIUM", "LOW"}


class ValidationSeverity(StrEnum):
    ERROR = "error"         # Signal should be rejected
    WARNING = "warning"     # Signal accepted but flagged
    INFO = "info"           # Informational note


class ValidationIssue:
    """A single validation issue found in a signal."""

    def __init__(self, field: str, message: str, severity: ValidationSeverity):
        self.field = field
        self.message = message
        self.severity = severity

    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "message": self.message,
            "severity": self.severity.value,
        }


class ValidationResult:
    """Result of signal validation."""

    def __init__(
        self,
        signal_id: str,
        is_valid: bool,
        quality_score: float,
        issues: list[ValidationIssue],
    ):
        self.signal_id = signal_id
        self.is_valid = is_valid
        self.quality_score = quality_score
        self.issues = issues

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]

    def to_dict(self) -> dict:
        return {
            "signal_id": self.signal_id,
            "is_valid": self.is_valid,
            "quality_score": round(self.quality_score, 4),
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "issues": [i.to_dict() for i in self.issues],
        }


class SignalValidator:
    """
    Deep validator for OMEN signals.

    Goes beyond Pydantic schema validation to check content quality,
    temporal validity, and cross-reference consistency.
    """

    def validate(self, event: SignalEvent) -> ValidationResult:
        """
        Validate a SignalEvent.

        Returns ValidationResult with quality score and issues.
        """
        issues: list[ValidationIssue] = []
        sig = event.signal

        # ── 1. Signal ID format ───────────────────────────────────────
        if not event.signal_id or len(event.signal_id) < 5:
            issues.append(ValidationIssue(
                "signal_id", "Signal ID is too short (min 5 chars)",
                ValidationSeverity.ERROR,
            ))

        if event.signal_id != sig.signal_id:
            issues.append(ValidationIssue(
                "signal_id",
                f"Envelope signal_id ({event.signal_id}) != payload signal_id ({sig.signal_id})",
                ValidationSeverity.ERROR,
            ))

        # ── 2. Title quality ──────────────────────────────────────────
        if len(sig.title) < MIN_TITLE_LENGTH:
            issues.append(ValidationIssue(
                "signal.title",
                f"Title too short ({len(sig.title)} chars, min {MIN_TITLE_LENGTH})",
                ValidationSeverity.WARNING,
            ))
        if len(sig.title) > MAX_TITLE_LENGTH:
            issues.append(ValidationIssue(
                "signal.title",
                f"Title too long ({len(sig.title)} chars, max {MAX_TITLE_LENGTH})",
                ValidationSeverity.WARNING,
            ))

        # ── 3. Category validation ────────────────────────────────────
        if sig.category.upper() not in VALID_CATEGORIES:
            issues.append(ValidationIssue(
                "signal.category",
                f"Unknown category '{sig.category}'. Valid: {sorted(VALID_CATEGORIES)}",
                ValidationSeverity.WARNING,
            ))

        # ── 4. Confidence level consistency ───────────────────────────
        if sig.confidence_level:
            if sig.confidence_level.upper() not in VALID_CONFIDENCE_LEVELS:
                issues.append(ValidationIssue(
                    "signal.confidence_level",
                    f"Unknown confidence_level '{sig.confidence_level}'",
                    ValidationSeverity.WARNING,
                ))
            # Check consistency with confidence_score
            expected_level = self._score_to_level(sig.confidence_score)
            if sig.confidence_level.upper() != expected_level:
                issues.append(ValidationIssue(
                    "signal.confidence_level",
                    f"confidence_level '{sig.confidence_level}' inconsistent "
                    f"with score {sig.confidence_score:.2f} (expected '{expected_level}')",
                    ValidationSeverity.INFO,
                ))

        # ── 5. Probability + confidence bounds ────────────────────────
        if sig.probability == 0.0 and sig.confidence_score > 0.5:
            issues.append(ValidationIssue(
                "signal.probability",
                "Probability is 0 but confidence is high — suspicious",
                ValidationSeverity.WARNING,
            ))

        # ── 6. Temporal validity ──────────────────────────────────────
        now = datetime.utcnow()
        if event.observed_at:
            observed = event.observed_at.replace(tzinfo=timezone.utc) if event.observed_at.tzinfo is None else event.observed_at
            age_hours = (now - observed).total_seconds() / 3600
            if age_hours > MAX_SIGNAL_AGE_HOURS:
                issues.append(ValidationIssue(
                    "observed_at",
                    f"Signal is {age_hours:.0f}h old (max {MAX_SIGNAL_AGE_HOURS}h)",
                    ValidationSeverity.WARNING,
                ))
            if age_hours < -1:  # Allow 1 hour clock skew
                issues.append(ValidationIssue(
                    "observed_at",
                    f"Signal observed_at is in the future",
                    ValidationSeverity.ERROR,
                ))

        # ── 7. Evidence quality ───────────────────────────────────────
        if len(sig.evidence) == 0:
            issues.append(ValidationIssue(
                "signal.evidence",
                "No evidence items provided",
                ValidationSeverity.INFO,
            ))
        for i, ev in enumerate(sig.evidence):
            if not ev.source:
                issues.append(ValidationIssue(
                    f"signal.evidence[{i}].source",
                    "Evidence source is empty",
                    ValidationSeverity.WARNING,
                ))

        # ── 8. Schema version ─────────────────────────────────────────
        if event.schema_version not in ("1.0.0", "1.1.0", "2.0.0"):
            issues.append(ValidationIssue(
                "schema_version",
                f"Unexpected schema_version '{event.schema_version}'",
                ValidationSeverity.INFO,
            ))

        # ── Compute quality score ─────────────────────────────────────
        quality_score = self._compute_quality(sig, issues)
        is_valid = len([i for i in issues if i.severity == ValidationSeverity.ERROR]) == 0

        result = ValidationResult(
            signal_id=event.signal_id,
            is_valid=is_valid,
            quality_score=quality_score,
            issues=issues,
        )

        if not is_valid:
            logger.warning(
                "signal_validation_failed",
                signal_id=event.signal_id,
                errors=len(result.errors),
            )
        else:
            logger.debug(
                "signal_validated",
                signal_id=event.signal_id,
                quality=round(quality_score, 2),
                warnings=len(result.warnings),
            )

        return result

    def _compute_quality(self, sig, issues: list[ValidationIssue]) -> float:
        """Compute a quality score from 0 to 1 based on signal completeness."""
        # Start with a base score and add for completeness
        score = 0.5

        # Deduct for errors
        error_count = sum(1 for i in issues if i.severity == ValidationSeverity.ERROR)
        score -= error_count * 0.2

        # Deduct for warnings
        warning_count = sum(1 for i in issues if i.severity == ValidationSeverity.WARNING)
        score -= warning_count * 0.03

        # Evidence quality (0 to 0.15)
        if len(sig.evidence) >= 1:
            score += 0.05
        if len(sig.evidence) >= 2:
            score += 0.05
        if len(sig.evidence) >= 5:
            score += 0.05

        # Description quality (0 to 0.1)
        if sig.description and len(sig.description) > 10:
            score += 0.05
        if sig.description and len(sig.description) > 50:
            score += 0.05

        # Geographic info (0 to 0.1)
        if sig.geographic and sig.geographic.regions:
            score += 0.05
        if sig.geographic and sig.geographic.chokepoints:
            score += 0.05

        # Temporal info (0 to 0.05)
        if sig.temporal and sig.temporal.event_horizon:
            score += 0.05

        # Tags (0 to 0.05)
        if len(sig.tags) >= 2:
            score += 0.05

        return max(0.0, min(1.0, score))

    def _score_to_level(self, score: float) -> str:
        """Convert numeric confidence score to level."""
        if score >= 0.7:
            return "HIGH"
        elif score >= 0.4:
            return "MEDIUM"
        else:
            return "LOW"
