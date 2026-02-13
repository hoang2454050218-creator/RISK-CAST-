"""
WhatsApp Message Templates.

Pre-approved templates for WhatsApp Business API.
All templates must be approved by WhatsApp before use in production.

Template Design Principles (Business Decision Language):
1. Lead with MONEY — what's at risk, what it costs, what you save
2. Lead with TIME — deadline, point of no return, escalation timeline
3. Lead with CONTEXT — which shipments, which routes, why
4. Action-oriented — specific steps, not generic advice
5. Mobile-first — scannable on small screens
"""

from typing import Optional
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.riskcast.schemas.decision import DecisionObject
from app.riskcast.constants import Urgency, Severity


# ============================================================================
# TEMPLATE TYPES
# ============================================================================


class TemplateType(str, Enum):
    """WhatsApp template types."""

    # Decision alerts
    DECISION_URGENT = "decision_urgent"
    DECISION_STANDARD = "decision_standard"
    DECISION_WATCH = "decision_watch"

    # Follow-ups
    DEADLINE_REMINDER = "deadline_reminder"
    ESCALATION = "escalation"

    # Confirmations
    ACTION_CONFIRMED = "action_confirmed"
    WELCOME = "welcome"


# ============================================================================
# TEMPLATE CONTENT — BUSINESS DECISION LANGUAGE
# ============================================================================

# WhatsApp template definitions
# In production, these must match exactly with approved templates
TEMPLATES = {
    TemplateType.DECISION_URGENT: {
        "name": "riskcast_decision_urgent",
        "language": "en",
        "components": [
            {
                "type": "header",
                "format": "text",
                "text": "{{1}} — Action Required",
            },
            {
                "type": "body",
                "text": """*Your shipment is at risk.*

{{2}}

*FINANCIAL IMPACT*
Cargo at risk: {{3}}
Potential loss if no action: {{4}}

*RECOMMENDED ACTION: {{5}}*
Cost: {{6}}
You save: {{7}}
Deadline: {{8}}

*IF YOU WAIT*
Cost in 6h: {{9}}
Cost in 24h: {{10}}
Point of no return: {{11}}

*AFFECTED SHIPMENTS*
{{12}}

Confidence: {{13}}

Reply 1 to ACT | 2 for DETAILS | 3 to IGNORE"""
            },
        ],
    },

    TemplateType.DECISION_STANDARD: {
        "name": "riskcast_decision_standard",
        "language": "en",
        "components": [
            {
                "type": "header",
                "format": "text",
                "text": "Shipment Risk Detected",
            },
            {
                "type": "body",
                "text": """*{{1}}*

{{2}} shipment(s) on route {{3}} are affected.

*FINANCIAL SUMMARY*
Total exposure: {{4}}
Recommended: {{5}}
Action cost: {{6}} | You save: {{7}}

Deadline: {{8}}
If no action: {{9}} potential loss

Reply 1 to ACT | 2 for DETAILS"""
            },
        ],
    },

    TemplateType.DECISION_WATCH: {
        "name": "riskcast_decision_watch",
        "language": "en",
        "components": [
            {
                "type": "body",
                "text": """*Monitoring: {{1}}*

Your {{2}} shipment(s) worth {{3}} may be affected.

Current risk: {{4}}%
Potential exposure: {{5}}

No action required yet.
We'll alert you immediately if this escalates.

Reply DETAILS for full analysis"""
            },
        ],
    },

    TemplateType.DEADLINE_REMINDER: {
        "name": "riskcast_deadline_reminder",
        "language": "en",
        "components": [
            {
                "type": "body",
                "text": """*DEADLINE IN {{1}}*

Your decision on {{2}} is expiring.

*RIGHT NOW*: Action costs {{3}}
*IF YOU WAIT*: Cost increases to {{4}}
*Additional delay*: +{{5}} days

Every hour of delay costs you approximately {{6}}.

Reply 1 to ACT NOW"""
            },
        ],
    },

    TemplateType.ESCALATION: {
        "name": "riskcast_escalation",
        "language": "en",
        "components": [
            {
                "type": "header",
                "format": "text",
                "text": "SITUATION WORSENED",
            },
            {
                "type": "body",
                "text": """*{{1}}*

*EXPOSURE INCREASED*
Was: {{2}}
Now: {{3}} (+{{4}})

*Updated recommendation*: {{5}}
New cost: {{6}}
New deadline: {{7}}

{{8}}

Reply 1 to ACT NOW"""
            },
        ],
    },

    TemplateType.ACTION_CONFIRMED: {
        "name": "riskcast_action_confirmed",
        "language": "en",
        "components": [
            {
                "type": "body",
                "text": """*Action Confirmed*

You chose: {{1}}
Shipment: {{2}}
Cost: {{3}}

*What happens next:*
{{4}}

Expected outcome: {{5}}
Estimated savings: {{6}}

We'll track progress and update you."""
            },
        ],
    },

    TemplateType.WELCOME: {
        "name": "riskcast_welcome",
        "language": "en",
        "components": [
            {
                "type": "body",
                "text": """Welcome to RISKCAST

Hi {{1}}, you're now connected to supply chain intelligence.

We monitor {{2}} for disruptions and alert you with:
- Specific financial impact on YOUR shipments
- Clear recommended actions with costs
- Deadlines so you never miss a window

Commands:
STATUS — Check current alerts
HELP — Get assistance

Questions? Reply anytime."""
            },
        ],
    },
}


# ============================================================================
# MESSAGE BUILDER
# ============================================================================


class MessageContent(BaseModel):
    """Formatted message content."""

    template_type: TemplateType
    template_name: str
    language: str = "en"
    parameters: list[str] = Field(default_factory=list)
    preview_text: str = Field(description="Plain text preview")
    header: Optional[str] = None


def build_decision_message(decision: DecisionObject) -> MessageContent:
    """
    Build WhatsApp message from decision.

    Selects template based on urgency and formats parameters
    using BUSINESS DECISION LANGUAGE — money, time, context.
    """
    # Select template based on urgency
    if decision.urgency in [Urgency.IMMEDIATE, Urgency.URGENT]:
        template_type = TemplateType.DECISION_URGENT
    elif decision.urgency == Urgency.SOON:
        template_type = TemplateType.DECISION_STANDARD
    else:
        template_type = TemplateType.DECISION_WATCH

    template = TEMPLATES[template_type]

    # Build parameters based on template type
    if template_type == TemplateType.DECISION_URGENT:
        parameters = _build_urgent_params(decision)
    elif template_type == TemplateType.DECISION_STANDARD:
        parameters = _build_standard_params(decision)
    else:
        parameters = _build_watch_params(decision)

    # Build preview text — business language
    preview = _build_preview(decision)

    return MessageContent(
        template_type=template_type,
        template_name=template["name"],
        language=template["language"],
        parameters=parameters,
        preview_text=preview,
        header=_get_header(template),
    )


def _format_usd(amount: float) -> str:
    """Format USD amount in human-readable form."""
    if amount >= 1_000_000:
        return f"${amount/1_000_000:,.1f}M"
    if amount >= 1_000:
        return f"${amount/1_000:,.0f}K"
    return f"${amount:,.0f}"


def _build_urgent_params(decision: DecisionObject) -> list[str]:
    """Build parameters for urgent template — full business context."""
    action = decision.q5_action.primary_action
    impact = decision.q3_severity
    inaction = decision.q7_inaction

    # Format deadline
    deadline = action.deadline.strftime("%b %d, %I:%M %p UTC") if action.deadline else "ASAP"

    # Format point of no return
    ponr = ""
    if hasattr(inaction, 'point_of_no_return') and inaction.point_of_no_return:
        ponr = inaction.point_of_no_return.strftime("%b %d, %I:%M %p UTC")
    else:
        ponr = "Within 24 hours"

    # Build shipment list
    shipment_ids = decision.affected_shipment_ids[:5]  # Max 5 for readability
    shipment_list = ", ".join(shipment_ids) if shipment_ids else "See details"
    if len(decision.affected_shipment_ids) > 5:
        shipment_list += f" (+{len(decision.affected_shipment_ids) - 5} more)"

    # Calculate savings
    exposure = impact.total_exposure_usd
    action_cost = action.estimated_cost_usd
    savings = max(0, exposure - action_cost)

    # Get escalation costs
    cost_6h = getattr(inaction, 'cost_if_wait_6h', action_cost * 1.3)
    cost_24h = getattr(inaction, 'cost_if_wait_24h', action_cost * 2.0)

    # Severity label for header
    severity_label = "CRITICAL" if impact.severity == Severity.CRITICAL else "URGENT"

    # Confidence
    confidence_pct = int(decision.q6_confidence.score * 100) if hasattr(decision, 'q6_confidence') else 0

    return [
        severity_label,                                     # {{1}} - Severity for header
        decision.q1_what.event_summary,                     # {{2}} - What's happening
        _format_usd(exposure),                              # {{3}} - Cargo at risk
        _format_usd(inaction.expected_loss_if_nothing),     # {{4}} - Potential loss
        action.action_type.value.upper(),                   # {{5}} - Action type
        _format_usd(action_cost),                           # {{6}} - Action cost
        _format_usd(savings),                               # {{7}} - Savings
        deadline,                                           # {{8}} - Deadline
        _format_usd(cost_6h),                               # {{9}} - Cost in 6h
        _format_usd(cost_24h),                              # {{10}} - Cost in 24h
        ponr,                                               # {{11}} - Point of no return
        shipment_list,                                      # {{12}} - Shipment IDs
        f"{confidence_pct}%",                               # {{13}} - Confidence
    ]


def _build_standard_params(decision: DecisionObject) -> list[str]:
    """Build parameters for standard template — financial summary."""
    action = decision.q5_action.primary_action
    impact = decision.q3_severity
    inaction = decision.q7_inaction

    deadline = action.deadline.strftime("%b %d, %I:%M %p UTC") if action.deadline else "ASAP"
    shipment_count = len(decision.affected_shipment_ids)

    # Get affected routes
    routes = ", ".join(decision.q1_what.affected_routes[:2]) if hasattr(decision.q1_what, 'affected_routes') and decision.q1_what.affected_routes else "Multiple routes"

    exposure = impact.total_exposure_usd
    action_cost = action.estimated_cost_usd
    savings = max(0, exposure - action_cost)
    loss_if_nothing = getattr(inaction, 'expected_loss_if_nothing', exposure)

    return [
        decision.q1_what.event_summary,          # {{1}} - What's happening
        str(shipment_count),                      # {{2}} - Shipment count
        routes,                                   # {{3}} - Affected routes
        _format_usd(exposure),                    # {{4}} - Total exposure
        action.action_type.value.upper(),         # {{5}} - Action type
        _format_usd(action_cost),                 # {{6}} - Action cost
        _format_usd(savings),                     # {{7}} - Savings
        deadline,                                 # {{8}} - Deadline
        _format_usd(loss_if_nothing),             # {{9}} - Loss if nothing
    ]


def _build_watch_params(decision: DecisionObject) -> list[str]:
    """Build parameters for watch template — monitoring context."""
    impact = decision.q3_severity
    confidence = decision.q6_confidence
    shipment_count = len(decision.affected_shipment_ids)

    # Calculate total cargo value
    cargo_value = impact.total_exposure_usd * 3  # Rough estimate: exposure is ~30% of cargo

    return [
        decision.q1_what.event_summary,                     # {{1}} - What's happening
        str(shipment_count),                                # {{2}} - Shipment count
        _format_usd(cargo_value),                           # {{3}} - Cargo value
        str(int(confidence.confidence_score * 100)),        # {{4}} - Risk probability %
        _format_usd(impact.total_exposure_usd),             # {{5}} - Potential exposure
    ]


def _build_preview(decision: DecisionObject) -> str:
    """Build plain text preview — business language, scannable."""
    action = decision.q5_action.primary_action
    impact = decision.q3_severity
    inaction = decision.q7_inaction
    shipment_count = len(decision.affected_shipment_ids)

    exposure = impact.total_exposure_usd
    action_cost = action.estimated_cost_usd
    savings = max(0, exposure - action_cost)

    return (
        f"{_format_usd(exposure)} at risk across {shipment_count} shipment(s). "
        f"{action.action_type.value.upper()} for {_format_usd(action_cost)} saves {_format_usd(savings)}."
    )


def _get_header(template: dict) -> Optional[str]:
    """Extract header from template."""
    for component in template.get("components", []):
        if component.get("type") == "header":
            return component.get("text")
    return None


# ============================================================================
# TEMPLATE RENDERING
# ============================================================================


def render_template(template_type: TemplateType, parameters: list[str]) -> str:
    """
    Render template with parameters (for preview/logging).

    In production, WhatsApp renders the template.
    This is for debugging and testing.
    """
    template = TEMPLATES.get(template_type)
    if not template:
        return f"Unknown template: {template_type}"

    result = []

    for component in template.get("components", []):
        text = component.get("text", "")

        # Replace placeholders
        for i, param in enumerate(parameters, 1):
            text = text.replace(f"{{{{{i}}}}}", param)

        result.append(text)

    return "\n\n".join(result)


def get_template_names() -> list[str]:
    """Get list of all template names for WhatsApp Business API."""
    return [t["name"] for t in TEMPLATES.values()]
