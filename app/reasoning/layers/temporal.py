"""
Layer 2: Temporal Reasoning.

Responsibilities:
- Construct event timeline
- Calculate decision deadlines
- Determine action deadlines
- Map time-dependent options
- Assess urgency

This layer answers: "WHEN and what are the timing effects?"
"""

from datetime import datetime, timedelta
from typing import Any
import structlog

from app.reasoning.schemas import (
    ReasoningLayer,
    TemporalLayerOutput,
    TimelineEvent,
)

logger = structlog.get_logger(__name__)


class TemporalLayer:
    """
    Layer 2: Temporal Reasoning.
    
    Analyzes timing aspects:
    - When did the signal occur?
    - When will impact materialize?
    - When must decision be made?
    - What options remain at each time?
    
    Outputs timeline with deadlines and urgency.
    """
    
    # Urgency thresholds (hours until deadline)
    URGENCY_IMMEDIATE_HOURS = 6
    URGENCY_URGENT_HOURS = 24
    URGENCY_SOON_HOURS = 72
    
    # Default action lead times (hours)
    ACTION_LEAD_TIMES = {
        "reroute": 48,      # Need 48h to arrange reroute
        "delay": 24,        # Need 24h to coordinate delay
        "insure": 72,       # Need 72h for insurance
        "monitor": 0,       # Can start immediately
        "do_nothing": 0,    # No action needed
    }
    
    async def execute(self, inputs: dict) -> TemporalLayerOutput:
        """
        Execute temporal reasoning layer.
        
        Args:
            inputs: Dict with 'factual', 'context', and optionally 'signal'
        """
        factual = inputs.get("factual")
        context = inputs.get("context")
        signal = inputs.get("signal")
        
        started_at = datetime.utcnow()
        
        # Build event timeline
        event_sequence = self._build_timeline(factual, context, signal)
        
        # Calculate deadlines
        decision_deadline = self._calculate_decision_deadline(factual, context, signal)
        action_deadlines = self._calculate_action_deadlines(decision_deadline)
        
        # Map time-dependent options
        options_by_time = self._map_time_options(action_deadlines, decision_deadline)
        
        # Assess urgency
        urgency_level, urgency_reason = self._assess_urgency(decision_deadline)
        
        # Calculate hours until deadline
        hours_until = (decision_deadline - datetime.utcnow()).total_seconds() / 3600
        
        completed_at = datetime.utcnow()
        
        # Calculate confidence based on timeline certainty
        confidence = self._calculate_confidence(event_sequence, decision_deadline)
        
        # Generate warnings
        warnings = self._generate_warnings(
            urgency_level, hours_until, options_by_time
        )
        
        output = TemporalLayerOutput(
            layer=ReasoningLayer.TEMPORAL,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=int((completed_at - started_at).total_seconds() * 1000),
            inputs={
                "factual_confidence": factual.confidence if factual else 0,
                "shipment_count": len(getattr(context, "active_shipments", [])),
            },
            outputs={
                "urgency": urgency_level,
                "hours_until_deadline": hours_until,
                "event_count": len(event_sequence),
            },
            confidence=confidence,
            depends_on=[ReasoningLayer.FACTUAL],
            event_sequence=event_sequence,
            decision_deadline=decision_deadline,
            action_deadlines=action_deadlines,
            options_by_time=options_by_time,
            urgency_level=urgency_level,
            urgency_reason=urgency_reason,
            hours_until_decision_deadline=max(0, hours_until),
            warnings=warnings,
        )
        
        logger.debug(
            "temporal_layer_complete",
            urgency=urgency_level,
            hours_until_deadline=hours_until,
            event_count=len(event_sequence),
        )
        
        return output
    
    def _build_timeline(
        self,
        factual: Any,
        context: Any,
        signal: Any,
    ) -> list[TimelineEvent]:
        """Build chronological event timeline."""
        events = []
        now = datetime.utcnow()
        
        # Signal creation event
        if signal:
            signal_time = getattr(signal, "created_at", now)
            events.append(TimelineEvent(
                event_type="signal_created",
                timestamp=signal_time,
                description=f"Risk signal detected: {getattr(signal, 'event_type', 'unknown')}",
                is_past=signal_time <= now,
                confidence=0.95,
            ))
        
        # Signal prediction time
        if signal:
            prediction_time = getattr(signal, "prediction_date", None)
            if prediction_time:
                events.append(TimelineEvent(
                    event_type="predicted_event",
                    timestamp=prediction_time,
                    description="Predicted event occurrence",
                    is_past=prediction_time <= now,
                    confidence=getattr(signal, "probability", 0.5),
                ))
        
        # Shipment events
        if context:
            for shipment in getattr(context, "active_shipments", []):
                # ETD
                etd = getattr(shipment, "etd", None)
                if etd:
                    events.append(TimelineEvent(
                        event_type="shipment_departure",
                        timestamp=etd,
                        description=f"Shipment {getattr(shipment, 'shipment_id', '?')} departure",
                        is_past=etd <= now,
                        confidence=0.90,
                    ))
                
                # ETA
                eta = getattr(shipment, "eta", None)
                if eta:
                    events.append(TimelineEvent(
                        event_type="shipment_arrival",
                        timestamp=eta,
                        description=f"Shipment {getattr(shipment, 'shipment_id', '?')} arrival",
                        is_past=eta <= now,
                        confidence=0.80,  # ETAs have more uncertainty
                    ))
                
                # Contract deadline
                deadline = getattr(shipment, "delivery_deadline", None)
                if deadline:
                    events.append(TimelineEvent(
                        event_type="delivery_deadline",
                        timestamp=deadline,
                        description=f"Delivery deadline for {getattr(shipment, 'shipment_id', '?')}",
                        is_past=deadline <= now,
                        confidence=0.99,  # Contract deadlines are firm
                    ))
        
        # Sort by timestamp
        events.sort(key=lambda e: e.timestamp)
        
        return events
    
    def _calculate_decision_deadline(
        self,
        factual: Any,
        context: Any,
        signal: Any,
    ) -> datetime:
        """Calculate when a decision must be made."""
        now = datetime.utcnow()
        
        # Default: 72 hours from now
        deadline = now + timedelta(hours=72)
        
        # If signal has prediction date, decision should be before that
        if signal:
            prediction_time = getattr(signal, "prediction_date", None)
            if prediction_time and isinstance(prediction_time, datetime):
                # Need decision at least 24h before predicted event
                signal_deadline = prediction_time - timedelta(hours=24)
                if signal_deadline < deadline:
                    deadline = signal_deadline
        
        # Consider earliest shipment action deadline
        if context:
            for shipment in getattr(context, "active_shipments", []):
                # If shipment is departing soon, need decision before
                etd = getattr(shipment, "etd", None)
                if etd and isinstance(etd, datetime):
                    shipment_deadline = etd - timedelta(hours=48)  # 48h before ETD
                    if shipment_deadline < deadline and shipment_deadline > now:
                        deadline = shipment_deadline
        
        # Never set deadline in the past
        if deadline < now:
            deadline = now + timedelta(hours=2)  # Minimum 2 hours
        
        return deadline
    
    def _calculate_action_deadlines(
        self,
        decision_deadline: datetime,
    ) -> dict[str, datetime]:
        """Calculate deadline for each action type."""
        deadlines = {}
        
        for action, lead_hours in self.ACTION_LEAD_TIMES.items():
            # Deadline = decision_deadline - lead_time
            action_deadline = decision_deadline - timedelta(hours=lead_hours)
            
            # If deadline is in past, action is no longer available
            if action_deadline < datetime.utcnow():
                action_deadline = datetime.utcnow()  # Past deadline
            
            deadlines[action] = action_deadline
        
        return deadlines
    
    def _map_time_options(
        self,
        action_deadlines: dict[str, datetime],
        decision_deadline: datetime,
    ) -> dict[str, list[str]]:
        """Map available actions at different time horizons."""
        now = datetime.utcnow()
        
        # Time horizons
        horizons = {
            "now": now,
            "6h": now + timedelta(hours=6),
            "24h": now + timedelta(hours=24),
            "48h": now + timedelta(hours=48),
            "72h": now + timedelta(hours=72),
        }
        
        options = {}
        for horizon_name, horizon_time in horizons.items():
            available = []
            for action, deadline in action_deadlines.items():
                if deadline >= horizon_time:
                    available.append(action)
            options[horizon_name] = available
        
        return options
    
    def _assess_urgency(
        self,
        decision_deadline: datetime,
    ) -> tuple[str, str]:
        """Assess urgency level based on deadline."""
        now = datetime.utcnow()
        hours_until = (decision_deadline - now).total_seconds() / 3600
        
        if hours_until <= self.URGENCY_IMMEDIATE_HOURS:
            return "immediate", f"Only {hours_until:.1f} hours until deadline"
        elif hours_until <= self.URGENCY_URGENT_HOURS:
            return "urgent", f"{hours_until:.0f} hours until deadline"
        elif hours_until <= self.URGENCY_SOON_HOURS:
            return "soon", f"{hours_until:.0f} hours until deadline"
        else:
            return "watch", f"Adequate time ({hours_until:.0f} hours)"
    
    def _calculate_confidence(
        self,
        events: list[TimelineEvent],
        deadline: datetime,
    ) -> float:
        """Calculate confidence in temporal analysis."""
        if not events:
            return 0.5
        
        # Average event confidence
        avg_confidence = sum(e.confidence for e in events) / len(events)
        
        # Discount for near-term deadlines (more uncertainty)
        hours_until = (deadline - datetime.utcnow()).total_seconds() / 3600
        if hours_until < 24:
            time_discount = 0.9
        elif hours_until < 72:
            time_discount = 0.95
        else:
            time_discount = 1.0
        
        return avg_confidence * time_discount
    
    def _generate_warnings(
        self,
        urgency: str,
        hours_until: float,
        options: dict[str, list[str]],
    ) -> list[str]:
        """Generate temporal warnings."""
        warnings = []
        
        if urgency == "immediate":
            warnings.append("IMMEDIATE action required - very limited time")
        
        if hours_until < 0:
            warnings.append("Decision deadline has passed!")
        
        # Check if options are narrowing
        now_options = set(options.get("now", []))
        future_options = set(options.get("24h", []))
        lost_options = now_options - future_options
        if lost_options:
            warnings.append(
                f"Options closing soon: {', '.join(lost_options)}"
            )
        
        return warnings
