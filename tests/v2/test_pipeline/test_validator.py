"""
Tests for OMEN Signal Validator.

Covers:
- Valid signal passes
- Signal ID validation
- Title quality checks
- Category validation
- Confidence consistency
- Temporal validity
- Evidence quality
- Quality score computation
"""

from datetime import datetime, timedelta, timezone

import pytest

from riskcast.pipeline.validator import SignalValidator, ValidationSeverity
from riskcast.schemas.omen_signal import (
    EvidenceItem,
    GeographicInfo,
    OmenSignalPayload,
    SignalEvent,
    TemporalInfo,
)


@pytest.fixture
def validator():
    return SignalValidator()


def _make_signal(
    signal_id: str = "OMEN-TEST-12345",
    title: str = "Major port congestion at Shanghai",
    category: str = "SUPPLY_CHAIN",
    probability: float = 0.75,
    confidence_score: float = 0.85,
    confidence_level: str = "HIGH",
    observed_at: datetime | None = None,
    evidence: list | None = None,
    description: str | None = "Significant delays expected.",
    geographic: GeographicInfo | None = None,
) -> SignalEvent:
    if observed_at is None:
        observed_at = datetime.now(timezone.utc) - timedelta(hours=1)
    if evidence is None:
        evidence = [
            EvidenceItem(source="reuters", source_type="news_article"),
            EvidenceItem(source="ais_data", source_type="vessel_tracking"),
        ]
    return SignalEvent(
        schema_version="1.0.0",
        signal_id=signal_id,
        observed_at=observed_at,
        emitted_at=datetime.now(timezone.utc),
        signal=OmenSignalPayload(
            signal_id=signal_id,
            title=title,
            description=description,
            probability=probability,
            confidence_score=confidence_score,
            confidence_level=confidence_level,
            category=category,
            tags=["port", "congestion"],
            geographic=geographic or GeographicInfo(regions=["Asia"], chokepoints=["Shanghai"]),
            evidence=evidence,
            generated_at=datetime.now(timezone.utc),
        ),
    )


# ── Valid Signal ───────────────────────────────────────────────────────


class TestValidSignal:
    def test_valid_signal_passes(self, validator):
        event = _make_signal()
        result = validator.validate(event)
        assert result.is_valid is True
        assert result.quality_score > 0.8
        assert len(result.errors) == 0

    def test_quality_score_range(self, validator):
        result = validator.validate(_make_signal())
        assert 0.0 <= result.quality_score <= 1.0


# ── Signal ID ──────────────────────────────────────────────────────────


class TestSignalId:
    def test_short_signal_id_error(self, validator):
        event = _make_signal(signal_id="AB")
        # Also update inner signal_id
        event.signal.signal_id = "AB"
        result = validator.validate(event)
        assert not result.is_valid
        assert any(i.field == "signal_id" for i in result.errors)

    def test_mismatched_signal_id_error(self, validator):
        event = _make_signal(signal_id="OMEN-OUTER-123")
        event.signal.signal_id = "OMEN-INNER-456"
        result = validator.validate(event)
        assert not result.is_valid


# ── Title Quality ──────────────────────────────────────────────────────


class TestTitle:
    def test_short_title_warning(self, validator):
        event = _make_signal(title="Short")
        result = validator.validate(event)
        assert any(
            i.field == "signal.title" and i.severity == ValidationSeverity.WARNING
            for i in result.issues
        )

    def test_long_title_warning(self, validator):
        event = _make_signal(title="X" * 501)
        result = validator.validate(event)
        assert any(
            "too long" in i.message for i in result.issues
        )


# ── Category ──────────────────────────────────────────────────────────


class TestCategory:
    def test_valid_category(self, validator):
        for cat in ["GEOPOLITICAL", "ECONOMIC", "WEATHER", "SUPPLY_CHAIN"]:
            event = _make_signal(category=cat)
            result = validator.validate(event)
            assert not any(
                i.field == "signal.category" and i.severity == ValidationSeverity.ERROR
                for i in result.issues
            )

    def test_unknown_category_warning(self, validator):
        event = _make_signal(category="ALIEN_INVASION")
        result = validator.validate(event)
        assert any(
            i.field == "signal.category" for i in result.warnings
        )


# ── Confidence ─────────────────────────────────────────────────────────


class TestConfidence:
    def test_inconsistent_confidence_level_info(self, validator):
        # Score is 0.85 (HIGH) but level says LOW
        event = _make_signal(confidence_score=0.85, confidence_level="LOW")
        result = validator.validate(event)
        assert any("inconsistent" in i.message for i in result.issues)

    def test_zero_probability_high_confidence_warning(self, validator):
        event = _make_signal(probability=0.0, confidence_score=0.9)
        result = validator.validate(event)
        assert any("Probability is 0" in i.message for i in result.issues)


# ── Temporal Validity ──────────────────────────────────────────────────


class TestTemporal:
    def test_old_signal_warning(self, validator):
        old_time = datetime.now(timezone.utc) - timedelta(days=10)
        event = _make_signal(observed_at=old_time)
        result = validator.validate(event)
        assert any("old" in i.message.lower() for i in result.warnings)

    def test_future_signal_error(self, validator):
        future_time = datetime.now(timezone.utc) + timedelta(hours=5)
        event = _make_signal(observed_at=future_time)
        result = validator.validate(event)
        assert any("future" in i.message.lower() for i in result.errors)


# ── Evidence ──────────────────────────────────────────────────────────


class TestEvidence:
    def test_no_evidence_info(self, validator):
        event = _make_signal(evidence=[])
        result = validator.validate(event)
        assert any("No evidence" in i.message for i in result.issues)

    def test_empty_source_warning(self, validator):
        event = _make_signal(evidence=[
            EvidenceItem(source="", source_type="article"),
        ])
        result = validator.validate(event)
        assert any("source is empty" in i.message for i in result.warnings)


# ── Quality Score ──────────────────────────────────────────────────────


class TestQualityScore:
    def test_high_quality_signal(self, validator):
        """Full signal with evidence, description, geographic → high score."""
        event = _make_signal(
            description="Detailed description of the supply chain disruption with significant impact expected",
            geographic=GeographicInfo(regions=["Asia-Pacific"], chokepoints=["Malacca Strait"]),
        )
        result = validator.validate(event)
        assert result.quality_score >= 0.8

    def test_low_quality_signal(self, validator):
        """Bare minimum signal → lower score than a high-quality one."""
        high_q = _make_signal(
            description="Detailed description of supply chain disruption",
            geographic=GeographicInfo(regions=["Asia-Pacific"], chokepoints=["Malacca Strait"]),
        )
        low_q = _make_signal(
            description=None,
            evidence=[],
            geographic=None,
        )
        high_result = validator.validate(high_q)
        low_result = validator.validate(low_q)
        assert low_result.quality_score < high_result.quality_score


# ── Serialization ─────────────────────────────────────────────────────


class TestSerialization:
    def test_to_dict(self, validator):
        result = validator.validate(_make_signal())
        d = result.to_dict()
        assert "signal_id" in d
        assert "is_valid" in d
        assert "quality_score" in d
        assert "issues" in d
