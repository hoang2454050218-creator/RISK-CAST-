"""Tests for Calibration Persistence Module.

Tests the persistent calibration system that addresses audit gap A3:
- Calibration data persistence to PostgreSQL
- CI coverage validation
- Historical accuracy tracking
"""

from datetime import datetime, timedelta
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.calibration.models import (
    PredictionRecordModel,
    CalibrationBucketModel,
    CalibrationMetricsModel,
    CICoverageRecordModel,
)
from app.calibration.persistence import (
    CalibrationPersistence,
    PersistentCalibrator,
    CalibrationResult,
)
from app.calibration.validation import (
    CIValidator,
    CoverageResult,
    CalibrationReport,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create mock async session."""
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_session_factory(mock_session) -> MagicMock:
    """Create mock session factory."""
    factory = MagicMock()
    factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    factory.return_value.__aexit__ = AsyncMock()
    return factory


@pytest.fixture
def persistence(mock_session_factory) -> CalibrationPersistence:
    """Create CalibrationPersistence instance."""
    return CalibrationPersistence(mock_session_factory)


@pytest.fixture
def calibrator(mock_session_factory) -> PersistentCalibrator:
    """Create PersistentCalibrator instance."""
    return PersistentCalibrator(mock_session_factory)


@pytest.fixture
def validator(mock_session_factory) -> CIValidator:
    """Create CIValidator instance."""
    return CIValidator(mock_session_factory)


# =============================================================================
# PREDICTION RECORD MODEL TESTS
# =============================================================================


class TestPredictionRecordModel:
    """Tests for PredictionRecordModel."""

    def test_model_creation(self):
        """Test model creation with required fields."""
        record = PredictionRecordModel(
            decision_id="dec_test_001",
            predicted_confidence=0.85,
            chokepoint="red_sea",
            event_type="disruption",
            predicted_at=datetime.utcnow(),
        )

        assert record.decision_id == "dec_test_001"
        assert record.predicted_confidence == 0.85
        assert record.chokepoint == "red_sea"
        assert record.is_resolved is False

    def test_model_with_ci_bounds(self):
        """Test model with CI bounds."""
        record = PredictionRecordModel(
            decision_id="dec_test_002",
            predicted_confidence=0.75,
            chokepoint="suez",
            event_type="congestion",
            predicted_at=datetime.utcnow(),
            predicted_ci_90_low=0.65,
            predicted_ci_90_high=0.85,
            predicted_ci_95_low=0.60,
            predicted_ci_95_high=0.90,
        )

        assert record.predicted_ci_90_low == 0.65
        assert record.predicted_ci_90_high == 0.85

    def test_model_resolution(self):
        """Test resolving a prediction."""
        record = PredictionRecordModel(
            decision_id="dec_test_003",
            predicted_confidence=0.80,
            chokepoint="red_sea",
            event_type="disruption",
            predicted_at=datetime.utcnow(),
        )

        # Resolve the prediction
        record.actual_outcome = 1.0  # Event occurred
        record.is_resolved = True
        record.resolved_at = datetime.utcnow()

        assert record.is_resolved is True
        assert record.actual_outcome == 1.0


# =============================================================================
# CALIBRATION BUCKET MODEL TESTS
# =============================================================================


class TestCalibrationBucketModel:
    """Tests for CalibrationBucketModel."""

    def test_bucket_creation(self):
        """Test bucket creation."""
        bucket = CalibrationBucketModel(
            bucket_lower=0.7,
            bucket_upper=0.8,
            bucket_center=0.75,
            prediction_count=100,
            outcome_sum=72.0,
            actual_frequency=0.72,
            window_start=datetime.utcnow() - timedelta(days=30),
            window_end=datetime.utcnow(),
        )

        assert bucket.bucket_center == 0.75
        assert bucket.prediction_count == 100
        assert bucket.actual_frequency == 0.72

    def test_calibration_error(self):
        """Test calibration error calculation."""
        bucket = CalibrationBucketModel(
            bucket_lower=0.8,
            bucket_upper=0.9,
            bucket_center=0.85,
            prediction_count=50,
            outcome_sum=40.0,
            actual_frequency=0.80,  # Expected ~0.85
            calibration_error=0.05,  # 0.85 - 0.80
            window_start=datetime.utcnow() - timedelta(days=30),
            window_end=datetime.utcnow(),
        )

        assert bucket.calibration_error == 0.05


# =============================================================================
# CALIBRATION METRICS MODEL TESTS
# =============================================================================


class TestCalibrationMetricsModel:
    """Tests for CalibrationMetricsModel."""

    def test_metrics_creation(self):
        """Test metrics snapshot creation."""
        metrics = CalibrationMetricsModel(
            ece=0.05,  # 5% ECE
            brier_score=0.15,
            sample_count=1000,
            resolved_count=950,
            window_start=datetime.utcnow() - timedelta(days=30),
            window_end=datetime.utcnow(),
            computed_at=datetime.utcnow(),
            is_well_calibrated=True,
            calibration_quality="GOOD",
        )

        assert metrics.ece == 0.05
        assert metrics.is_well_calibrated is True
        assert metrics.calibration_quality == "GOOD"

    def test_ci_coverage_metrics(self):
        """Test CI coverage in metrics."""
        metrics = CalibrationMetricsModel(
            ece=0.03,
            brier_score=0.12,
            sample_count=500,
            resolved_count=480,
            ci_90_coverage=0.88,  # Should be ~0.90
            ci_95_coverage=0.93,  # Should be ~0.95
            window_start=datetime.utcnow() - timedelta(days=30),
            window_end=datetime.utcnow(),
            computed_at=datetime.utcnow(),
            is_well_calibrated=False,  # CI coverage slightly off
            calibration_quality="FAIR",
        )

        assert metrics.ci_90_coverage == 0.88
        assert metrics.ci_95_coverage == 0.93


# =============================================================================
# CALIBRATION PERSISTENCE TESTS
# =============================================================================


class TestCalibrationPersistence:
    """Tests for CalibrationPersistence."""

    @pytest.mark.asyncio
    async def test_record_prediction(self, persistence: CalibrationPersistence, mock_session):
        """Test recording a new prediction."""
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        
        result = await persistence.record_prediction(
            decision_id="dec_persist_001",
            predicted_confidence=0.85,
            chokepoint="red_sea",
            event_type="disruption",
            customer_id="cust_001",
            predicted_exposure_usd=150000,
            ci_90=(0.75, 0.95),
            ci_95=(0.70, 0.98),
        )

        assert result is True
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_outcome(self, persistence: CalibrationPersistence, mock_session):
        """Test recording an outcome for a prediction."""
        # Mock existing prediction
        mock_record = MagicMock()
        mock_record.is_resolved = False
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_record
        
        result = await persistence.record_outcome(
            decision_id="dec_persist_001",
            actual_outcome=1.0,  # Event occurred
            actual_value=0.92,
            actual_exposure_usd=180000,
            resolution_source="oracle_confirmation",
        )

        assert result is True
        assert mock_record.is_resolved is True
        assert mock_record.actual_outcome == 1.0


# =============================================================================
# PERSISTENT CALIBRATOR TESTS
# =============================================================================


class TestPersistentCalibrator:
    """Tests for PersistentCalibrator."""

    @pytest.mark.asyncio
    async def test_calibrate_no_history(self, calibrator: PersistentCalibrator, mock_session):
        """Test calibration with no historical data."""
        # Mock no historical data
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        
        result = await calibrator.calibrate_and_persist(
            raw_confidence=0.80,
            chokepoint="red_sea",
            event_type="disruption",
            customer_id="cust_001",
        )

        assert isinstance(result, CalibrationResult)
        # With no history, calibrated should be close to raw
        assert result.calibrated_confidence == 0.80
        assert result.adjustment == 0.0

    @pytest.mark.asyncio
    async def test_calibrate_with_history(self, calibrator: PersistentCalibrator, mock_session):
        """Test calibration with historical data showing overconfidence."""
        # Mock historical data showing the system is overconfident
        # Predictions of 0.80 resulted in only 0.70 actual frequency
        mock_bucket = MagicMock()
        mock_bucket.bucket_center = 0.80
        mock_bucket.actual_frequency = 0.70
        mock_bucket.prediction_count = 100
        mock_session.execute.return_value.scalars.return_value.all.return_value = [mock_bucket]
        
        result = await calibrator.calibrate_and_persist(
            raw_confidence=0.80,
            chokepoint="red_sea",
            event_type="disruption",
            customer_id="cust_001",
        )

        assert isinstance(result, CalibrationResult)
        # Should adjust downward due to overconfidence
        assert result.calibrated_confidence < 0.80
        assert result.adjustment < 0

    @pytest.mark.asyncio
    async def test_record_prediction_persistence(self, calibrator: PersistentCalibrator, mock_session):
        """Test that predictions are persisted."""
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        
        await calibrator.record_prediction(
            decision_id="dec_001",
            predicted_confidence=0.85,
            chokepoint="red_sea",
            event_type="disruption",
            exposure_usd=200000,
        )

        mock_session.add.assert_called()


# =============================================================================
# CI VALIDATOR TESTS
# =============================================================================


class TestCIValidator:
    """Tests for CIValidator."""

    @pytest.mark.asyncio
    async def test_validate_coverage_perfect(self, validator: CIValidator, mock_session):
        """Test CI coverage validation with perfect coverage."""
        # Mock predictions with 90% within 90% CI
        mock_records = []
        for i in range(100):
            record = MagicMock()
            record.is_resolved = True
            record.actual_value = 0.85
            record.predicted_ci_90_low = 0.70 if i < 90 else 0.90  # 90 within CI
            record.predicted_ci_90_high = 0.95 if i < 90 else 0.92
            record.predicted_ci_95_low = 0.65 if i < 95 else 0.90
            record.predicted_ci_95_high = 0.98 if i < 95 else 0.92
            mock_records.append(record)
        
        mock_session.execute.return_value.scalars.return_value.all.return_value = mock_records
        
        result = await validator.validate_coverage(
            start_date=datetime.utcnow() - timedelta(days=30),
            end_date=datetime.utcnow(),
        )

        assert isinstance(result, CoverageResult)
        # Should be approximately 90%
        assert result.ci_90_coverage_rate >= 0.85

    @pytest.mark.asyncio
    async def test_validate_coverage_undercoverage(self, validator: CIValidator, mock_session):
        """Test CI coverage validation with undercoverage."""
        # Mock predictions with only 70% within 90% CI (should be 90%)
        mock_records = []
        for i in range(100):
            record = MagicMock()
            record.is_resolved = True
            record.actual_value = 0.85
            record.predicted_ci_90_low = 0.70 if i < 70 else 0.90  # Only 70 within CI
            record.predicted_ci_90_high = 0.95 if i < 70 else 0.92
            record.predicted_ci_95_low = 0.65 if i < 75 else 0.90
            record.predicted_ci_95_high = 0.98 if i < 75 else 0.92
            mock_records.append(record)
        
        mock_session.execute.return_value.scalars.return_value.all.return_value = mock_records
        
        result = await validator.validate_coverage(
            start_date=datetime.utcnow() - timedelta(days=30),
            end_date=datetime.utcnow(),
        )

        assert isinstance(result, CoverageResult)
        # Should flag as not valid (70% < 90% expected)
        assert result.ci_90_is_valid is False

    @pytest.mark.asyncio
    async def test_generate_calibration_report(self, validator: CIValidator, mock_session):
        """Test calibration report generation."""
        # Mock metrics and coverage data
        mock_metrics = MagicMock()
        mock_metrics.ece = 0.05
        mock_metrics.brier_score = 0.15
        mock_metrics.is_well_calibrated = True
        mock_session.execute.return_value.scalars.return_value.all.return_value = [mock_metrics]
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_metrics
        
        report = await validator.generate_calibration_report(
            start_date=datetime.utcnow() - timedelta(days=30),
            end_date=datetime.utcnow(),
        )

        assert isinstance(report, CalibrationReport)


# =============================================================================
# CALIBRATION RESULT TESTS
# =============================================================================


class TestCalibrationResult:
    """Tests for CalibrationResult schema."""

    def test_result_creation(self):
        """Test CalibrationResult creation."""
        result = CalibrationResult(
            raw_confidence=0.85,
            calibrated_confidence=0.80,
            adjustment=-0.05,
            bucket_used="0.80-0.90",
            sample_count=150,
            method="empirical",
        )

        assert result.raw_confidence == 0.85
        assert result.calibrated_confidence == 0.80
        assert result.adjustment == -0.05
        assert result.was_adjusted is True

    def test_result_no_adjustment(self):
        """Test CalibrationResult with no adjustment."""
        result = CalibrationResult(
            raw_confidence=0.75,
            calibrated_confidence=0.75,
            adjustment=0.0,
            method="no_history",
        )

        assert result.was_adjusted is False


# =============================================================================
# COVERAGE RESULT TESTS
# =============================================================================


class TestCoverageResult:
    """Tests for CoverageResult schema."""

    def test_result_valid_coverage(self):
        """Test CoverageResult with valid coverage."""
        result = CoverageResult(
            total_predictions=1000,
            resolved_predictions=950,
            ci_90_covered=855,
            ci_90_coverage_rate=0.90,
            ci_90_expected_rate=0.90,
            ci_90_deviation=0.0,
            ci_90_is_valid=True,
            ci_95_covered=903,
            ci_95_coverage_rate=0.95,
            ci_95_expected_rate=0.95,
            ci_95_deviation=0.0,
            ci_95_is_valid=True,
            validation_period_start=datetime.utcnow() - timedelta(days=30),
            validation_period_end=datetime.utcnow(),
        )

        assert result.ci_90_is_valid is True
        assert result.ci_95_is_valid is True

    def test_result_invalid_coverage(self):
        """Test CoverageResult with invalid coverage."""
        result = CoverageResult(
            total_predictions=1000,
            resolved_predictions=950,
            ci_90_covered=760,  # Only 80% covered (should be 90%)
            ci_90_coverage_rate=0.80,
            ci_90_expected_rate=0.90,
            ci_90_deviation=-0.10,
            ci_90_is_valid=False,
            ci_95_covered=855,  # Only 90% covered (should be 95%)
            ci_95_coverage_rate=0.90,
            ci_95_expected_rate=0.95,
            ci_95_deviation=-0.05,
            ci_95_is_valid=False,
            validation_period_start=datetime.utcnow() - timedelta(days=30),
            validation_period_end=datetime.utcnow(),
        )

        assert result.ci_90_is_valid is False
        assert result.ci_95_is_valid is False
