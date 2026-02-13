"""
Feedback Loop System for RISKCAST.

Collects, processes, and analyzes feedback to improve decision quality.

This is THE COMPETITIVE MOAT - learning from every decision to get better.

Components:
- schemas: Feedback data models (user feedback, outcome records, improvement signals)
- service: FeedbackService for collecting and processing feedback
- analyzer: FeedbackAnalyzer for continuous accuracy measurement
- api: REST endpoints for feedback collection

The Feedback Loop:
    1. Decision Generated → Record prediction
    2. Customer Feedback → Capture what they did
    3. Outcome Observed → Record what actually happened
    4. Accuracy Analysis → Measure prediction quality
    5. Calibration Update → Improve confidence scores
    6. Model Feedback → Signal for future improvements

Usage:
    from app.feedback import FeedbackService, FeedbackAnalyzer
    
    # Record customer feedback
    feedback = await service.record_feedback(
        decision_id="dec_123",
        action_taken="REROUTE",
        satisfaction=4,
        notes="Great timing, avoided major delays"
    )
    
    # Get improvement insights
    insights = await analyzer.get_improvement_insights(days=30)
"""

from app.feedback.schemas import (
    # Feedback types
    FeedbackType,
    FeedbackSource,
    SatisfactionLevel,
    # Customer feedback
    CustomerFeedback,
    CustomerFeedbackCreate,
    # Outcome records
    OutcomeRecord,
    OutcomeRecordCreate,
    # Improvement signals
    ImprovementSignal,
    ImprovementArea,
    # Accuracy reports
    AccuracyReport,
    CalibrationReport,
    TrendAnalysis,
)
from app.feedback.service import (
    FeedbackService,
    create_feedback_service,
)
from app.feedback.analyzer import (
    FeedbackAnalyzer,
    create_feedback_analyzer,
)

__all__ = [
    # Schemas
    "FeedbackType",
    "FeedbackSource",
    "SatisfactionLevel",
    "CustomerFeedback",
    "CustomerFeedbackCreate",
    "OutcomeRecord",
    "OutcomeRecordCreate",
    "ImprovementSignal",
    "ImprovementArea",
    "AccuracyReport",
    "CalibrationReport",
    "TrendAnalysis",
    # Service
    "FeedbackService",
    "create_feedback_service",
    # Analyzer
    "FeedbackAnalyzer",
    "create_feedback_analyzer",
]
