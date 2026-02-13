"""
Migration v1.1.0: Add Calibration Tables for Persistent Confidence Calibration.

This migration addresses audit gap A3 (Accountability & Trust):
- Calibration data persistence to PostgreSQL (not in-memory)
- CI coverage validation
- Historical accuracy tracking

Tables created:
- calibration_predictions: Individual prediction records
- calibration_buckets: Aggregated calibration buckets
- calibration_metrics: Calibration metrics snapshots
- calibration_ci_coverage: CI coverage validation records

Version: 1.1.0
Created: 2026-02-05
Author: RISKCAST Audit Integration
Breaking: No
Downtime: No
"""

from datetime import datetime
from typing import Optional
import structlog

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.schema_versioning import SchemaVersionService, MigrationStatus

logger = structlog.get_logger(__name__)

# Migration metadata
VERSION = "1.1.0"
NAME = "calibration_tables"
DESCRIPTION = "Add calibration tables for persistent confidence calibration (A3)"
IS_BREAKING = False
REQUIRES_DOWNTIME = False


# =============================================================================
# FORWARD MIGRATION SQL
# =============================================================================

FORWARD_SQL = """
-- ============================================================================
-- Calibration Predictions Table
-- Stores individual prediction records for calibration tracking
-- ============================================================================

CREATE TABLE IF NOT EXISTS calibration_predictions (
    id SERIAL PRIMARY KEY,
    
    -- Decision linkage
    decision_id VARCHAR(100) NOT NULL UNIQUE,
    
    -- Prediction data
    predicted_confidence FLOAT NOT NULL CHECK (predicted_confidence >= 0 AND predicted_confidence <= 1),
    actual_outcome FLOAT CHECK (actual_outcome >= 0 AND actual_outcome <= 1),
    
    -- Confidence intervals (90% and 95%)
    predicted_ci_90_low FLOAT,
    predicted_ci_90_high FLOAT,
    predicted_ci_95_low FLOAT,
    predicted_ci_95_high FLOAT,
    
    -- Actual values for CI validation
    actual_value FLOAT,
    actual_within_ci_90 BOOLEAN,
    actual_within_ci_95 BOOLEAN,
    
    -- Context for granular analysis
    chokepoint VARCHAR(50) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    customer_id VARCHAR(100),
    
    -- Financial impact tracking
    predicted_exposure_usd FLOAT,
    actual_exposure_usd FLOAT,
    
    -- Timestamps
    predicted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE,
    
    -- Status
    is_resolved BOOLEAN NOT NULL DEFAULT FALSE,
    resolution_source VARCHAR(100),
    
    -- Indexes for common queries
    CONSTRAINT chk_ci_90_bounds CHECK (predicted_ci_90_low IS NULL OR predicted_ci_90_low <= predicted_ci_90_high),
    CONSTRAINT chk_ci_95_bounds CHECK (predicted_ci_95_low IS NULL OR predicted_ci_95_low <= predicted_ci_95_high)
);

-- Indexes for calibration_predictions
CREATE INDEX IF NOT EXISTS idx_cal_pred_chokepoint ON calibration_predictions(chokepoint);
CREATE INDEX IF NOT EXISTS idx_cal_pred_event_type ON calibration_predictions(event_type);
CREATE INDEX IF NOT EXISTS idx_cal_pred_customer ON calibration_predictions(customer_id);
CREATE INDEX IF NOT EXISTS idx_cal_pred_confidence ON calibration_predictions(predicted_confidence);
CREATE INDEX IF NOT EXISTS idx_cal_pred_resolved ON calibration_predictions(is_resolved);
CREATE INDEX IF NOT EXISTS idx_cal_pred_predicted_at ON calibration_predictions(predicted_at);
CREATE INDEX IF NOT EXISTS idx_cal_pred_chokepoint_event ON calibration_predictions(chokepoint, event_type);


-- ============================================================================
-- Calibration Buckets Table
-- Stores aggregated calibration data by probability bucket
-- ============================================================================

CREATE TABLE IF NOT EXISTS calibration_buckets (
    id SERIAL PRIMARY KEY,
    
    -- Bucket definition
    bucket_lower FLOAT NOT NULL CHECK (bucket_lower >= 0 AND bucket_lower <= 1),
    bucket_upper FLOAT NOT NULL CHECK (bucket_upper >= 0 AND bucket_upper <= 1),
    bucket_center FLOAT NOT NULL CHECK (bucket_center >= 0 AND bucket_center <= 1),
    
    -- Aggregated statistics
    prediction_count INTEGER NOT NULL DEFAULT 0,
    outcome_sum FLOAT NOT NULL DEFAULT 0,
    actual_frequency FLOAT CHECK (actual_frequency >= 0 AND actual_frequency <= 1),
    
    -- Calibration error for this bucket
    calibration_error FLOAT,
    
    -- Granularity
    chokepoint VARCHAR(50),
    event_type VARCHAR(50),
    
    -- Time window
    window_start TIMESTAMP WITH TIME ZONE NOT NULL,
    window_end TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_bucket_bounds CHECK (bucket_lower < bucket_upper),
    CONSTRAINT chk_bucket_center CHECK (bucket_center >= bucket_lower AND bucket_center <= bucket_upper)
);

-- Indexes for calibration_buckets
CREATE INDEX IF NOT EXISTS idx_cal_bucket_center ON calibration_buckets(bucket_center);
CREATE INDEX IF NOT EXISTS idx_cal_bucket_chokepoint ON calibration_buckets(chokepoint);
CREATE INDEX IF NOT EXISTS idx_cal_bucket_window ON calibration_buckets(window_start, window_end);


-- ============================================================================
-- Calibration Metrics Table
-- Stores periodic calibration metric snapshots
-- ============================================================================

CREATE TABLE IF NOT EXISTS calibration_metrics (
    id SERIAL PRIMARY KEY,
    
    -- Metric values
    ece FLOAT NOT NULL CHECK (ece >= 0),  -- Expected Calibration Error
    mce FLOAT CHECK (mce >= 0),  -- Maximum Calibration Error
    brier_score FLOAT CHECK (brier_score >= 0 AND brier_score <= 1),
    log_loss FLOAT CHECK (log_loss >= 0),
    mace FLOAT CHECK (mace >= 0),  -- Mean Absolute Calibration Error
    
    -- CI coverage metrics
    ci_90_coverage FLOAT CHECK (ci_90_coverage >= 0 AND ci_90_coverage <= 1),
    ci_95_coverage FLOAT CHECK (ci_95_coverage >= 0 AND ci_95_coverage <= 1),
    
    -- Sample information
    sample_count INTEGER NOT NULL,
    resolved_count INTEGER NOT NULL,
    
    -- Granularity
    chokepoint VARCHAR(50),
    event_type VARCHAR(50),
    
    -- Time window
    window_start TIMESTAMP WITH TIME ZONE NOT NULL,
    window_end TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Metadata
    computed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Quality assessment
    is_well_calibrated BOOLEAN NOT NULL DEFAULT FALSE,
    calibration_quality VARCHAR(20),  -- EXCELLENT, GOOD, FAIR, POOR
    
    CONSTRAINT chk_counts CHECK (resolved_count <= sample_count)
);

-- Indexes for calibration_metrics
CREATE INDEX IF NOT EXISTS idx_cal_metrics_computed_at ON calibration_metrics(computed_at);
CREATE INDEX IF NOT EXISTS idx_cal_metrics_chokepoint ON calibration_metrics(chokepoint);
CREATE INDEX IF NOT EXISTS idx_cal_metrics_window ON calibration_metrics(window_start, window_end);
CREATE INDEX IF NOT EXISTS idx_cal_metrics_quality ON calibration_metrics(calibration_quality);


-- ============================================================================
-- CI Coverage Records Table
-- Stores CI coverage validation records for detailed analysis
-- ============================================================================

CREATE TABLE IF NOT EXISTS calibration_ci_coverage (
    id SERIAL PRIMARY KEY,
    
    -- Validation period
    validation_period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    validation_period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Coverage statistics
    total_predictions INTEGER NOT NULL,
    resolved_predictions INTEGER NOT NULL,
    
    -- 90% CI coverage
    ci_90_covered INTEGER NOT NULL DEFAULT 0,
    ci_90_coverage_rate FLOAT CHECK (ci_90_coverage_rate >= 0 AND ci_90_coverage_rate <= 1),
    ci_90_expected_rate FLOAT DEFAULT 0.90,
    ci_90_deviation FLOAT,  -- coverage_rate - expected_rate
    ci_90_is_valid BOOLEAN,
    
    -- 95% CI coverage
    ci_95_covered INTEGER NOT NULL DEFAULT 0,
    ci_95_coverage_rate FLOAT CHECK (ci_95_coverage_rate >= 0 AND ci_95_coverage_rate <= 1),
    ci_95_expected_rate FLOAT DEFAULT 0.95,
    ci_95_deviation FLOAT,
    ci_95_is_valid BOOLEAN,
    
    -- Granularity
    chokepoint VARCHAR(50),
    event_type VARCHAR(50),
    
    -- Statistical significance
    p_value_90 FLOAT,
    p_value_95 FLOAT,
    is_statistically_significant BOOLEAN,
    
    -- Metadata
    computed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_ci_coverage_counts CHECK (
        ci_90_covered <= resolved_predictions AND
        ci_95_covered <= resolved_predictions AND
        resolved_predictions <= total_predictions
    )
);

-- Indexes for calibration_ci_coverage
CREATE INDEX IF NOT EXISTS idx_ci_cov_period ON calibration_ci_coverage(validation_period_start, validation_period_end);
CREATE INDEX IF NOT EXISTS idx_ci_cov_chokepoint ON calibration_ci_coverage(chokepoint);
CREATE INDEX IF NOT EXISTS idx_ci_cov_computed ON calibration_ci_coverage(computed_at);
CREATE INDEX IF NOT EXISTS idx_ci_cov_valid ON calibration_ci_coverage(ci_90_is_valid, ci_95_is_valid);
"""


# =============================================================================
# ROLLBACK MIGRATION SQL
# =============================================================================

ROLLBACK_SQL = """
-- Drop tables in reverse order (respecting potential dependencies)
DROP TABLE IF EXISTS calibration_ci_coverage CASCADE;
DROP TABLE IF EXISTS calibration_metrics CASCADE;
DROP TABLE IF EXISTS calibration_buckets CASCADE;
DROP TABLE IF EXISTS calibration_predictions CASCADE;
"""


# =============================================================================
# MIGRATION FUNCTIONS
# =============================================================================


async def apply_migration(session: AsyncSession) -> dict:
    """
    Apply the forward migration.
    
    Returns:
        Migration result with status and details
    """
    started_at = datetime.utcnow()
    
    logger.info(
        "migration_starting",
        version=VERSION,
        name=NAME,
    )
    
    try:
        # Execute migration SQL
        await session.execute(text(FORWARD_SQL))
        await session.commit()
        
        completed_at = datetime.utcnow()
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)
        
        logger.info(
            "migration_completed",
            version=VERSION,
            name=NAME,
            duration_ms=duration_ms,
        )
        
        return {
            "status": "completed",
            "version": VERSION,
            "name": NAME,
            "duration_ms": duration_ms,
            "tables_created": [
                "calibration_predictions",
                "calibration_buckets",
                "calibration_metrics",
                "calibration_ci_coverage",
            ],
        }
        
    except Exception as e:
        await session.rollback()
        
        logger.error(
            "migration_failed",
            version=VERSION,
            name=NAME,
            error=str(e),
        )
        
        return {
            "status": "failed",
            "version": VERSION,
            "name": NAME,
            "error": str(e),
        }


async def rollback_migration(session: AsyncSession) -> dict:
    """
    Roll back the migration.
    
    Returns:
        Rollback result with status and details
    """
    started_at = datetime.utcnow()
    
    logger.info(
        "migration_rollback_starting",
        version=VERSION,
        name=NAME,
    )
    
    try:
        await session.execute(text(ROLLBACK_SQL))
        await session.commit()
        
        completed_at = datetime.utcnow()
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)
        
        logger.info(
            "migration_rollback_completed",
            version=VERSION,
            name=NAME,
            duration_ms=duration_ms,
        )
        
        return {
            "status": "rolled_back",
            "version": VERSION,
            "name": NAME,
            "duration_ms": duration_ms,
        }
        
    except Exception as e:
        await session.rollback()
        
        logger.error(
            "migration_rollback_failed",
            version=VERSION,
            name=NAME,
            error=str(e),
        )
        
        return {
            "status": "rollback_failed",
            "version": VERSION,
            "name": NAME,
            "error": str(e),
        }


async def verify_migration(session: AsyncSession) -> dict:
    """
    Verify the migration was applied correctly.
    
    Returns:
        Verification result with table checks
    """
    tables_to_check = [
        "calibration_predictions",
        "calibration_buckets",
        "calibration_metrics",
        "calibration_ci_coverage",
    ]
    
    results = {}
    
    for table in tables_to_check:
        check_sql = f"""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = '{table}'
            );
        """
        result = await session.execute(text(check_sql))
        exists = result.scalar()
        results[table] = exists
    
    all_exist = all(results.values())
    
    return {
        "verified": all_exist,
        "tables": results,
        "version": VERSION,
    }


# =============================================================================
# CLI HELPERS
# =============================================================================


def get_migration_info() -> dict:
    """Get migration information."""
    return {
        "version": VERSION,
        "name": NAME,
        "description": DESCRIPTION,
        "is_breaking": IS_BREAKING,
        "requires_downtime": REQUIRES_DOWNTIME,
    }
