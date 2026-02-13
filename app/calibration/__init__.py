"""
Calibration Module - Persistent calibration data storage and validation.

This module addresses audit gaps A3:
- Calibration data persistence to PostgreSQL (not in-memory)
- CI coverage validation
- Historical accuracy tracking

Components:
- models.py: SQLAlchemy models for calibration data
- persistence.py: PostgreSQL persistence layer
- validation.py: Confidence interval coverage validation
"""

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

__all__ = [
    # Models
    "PredictionRecordModel",
    "CalibrationBucketModel",
    "CalibrationMetricsModel",
    "CICoverageRecordModel",
    # Persistence
    "CalibrationPersistence",
    "PersistentCalibrator",
    "CalibrationResult",
    # Validation
    "CIValidator",
    "CoverageResult",
    "CalibrationReport",
]
