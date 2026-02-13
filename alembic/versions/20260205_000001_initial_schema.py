"""Initial schema with all tables.

Revision ID: 20260205_000001
Revises: 
Create Date: 2026-02-05 00:00:01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260205_000001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all initial tables."""
    # Customers table
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("customer_id", sa.String(50), nullable=False),
        sa.Column("company_name", sa.String(200), nullable=False),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("primary_phone", sa.String(20), nullable=False),
        sa.Column("secondary_phone", sa.String(20), nullable=True),
        sa.Column("email", sa.String(100), nullable=True),
        sa.Column("risk_tolerance", sa.String(20), nullable=False, server_default="balanced"),
        sa.Column("max_reroute_premium_pct", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("notification_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("whatsapp_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("email_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("primary_routes", postgresql.JSON(), nullable=False, server_default="[]"),
        sa.Column("relevant_chokepoints", postgresql.JSON(), nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("tier", sa.String(20), nullable=False, server_default="standard"),
        sa.Column("language", sa.String(10), nullable=False, server_default="en"),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="UTC"),
        sa.Column("onboarding_complete", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", sa.String(100), nullable=True),
        sa.Column("updated_by", sa.String(100), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("customer_id"),
    )
    op.create_index("ix_customers_customer_id", "customers", ["customer_id"])
    op.create_index("ix_customers_phone", "customers", ["primary_phone"])
    op.create_index("ix_customers_active", "customers", ["is_active"])

    # Shipments table
    op.create_table(
        "shipments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("shipment_id", sa.String(100), nullable=False),
        sa.Column("customer_id", sa.String(50), nullable=False),
        sa.Column("origin_port", sa.String(10), nullable=False),
        sa.Column("destination_port", sa.String(10), nullable=False),
        sa.Column("route_code", sa.String(50), nullable=True),
        sa.Column("route_chokepoints", postgresql.JSON(), nullable=False, server_default="[]"),
        sa.Column("cargo_value_usd", sa.Float(), nullable=False),
        sa.Column("cargo_description", sa.Text(), nullable=True),
        sa.Column("container_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("container_type", sa.String(10), nullable=False, server_default="40HC"),
        sa.Column("hs_code", sa.String(20), nullable=True),
        sa.Column("carrier_code", sa.String(10), nullable=True),
        sa.Column("carrier_name", sa.String(100), nullable=True),
        sa.Column("booking_reference", sa.String(50), nullable=True),
        sa.Column("bill_of_lading", sa.String(50), nullable=True),
        sa.Column("etd", sa.DateTime(), nullable=True),
        sa.Column("eta", sa.DateTime(), nullable=True),
        sa.Column("actual_departure", sa.DateTime(), nullable=True),
        sa.Column("actual_arrival", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="booked"),
        sa.Column("has_delay_penalty", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("delay_penalty_per_day_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("penalty_free_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_insured", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("insurance_value_usd", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.customer_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shipment_id"),
    )
    op.create_index("ix_shipments_shipment_id", "shipments", ["shipment_id"])
    op.create_index("ix_shipments_customer", "shipments", ["customer_id"])
    op.create_index("ix_shipments_status", "shipments", ["status"])
    op.create_index("ix_shipments_etd", "shipments", ["etd"])
    op.create_index("ix_shipments_route", "shipments", ["origin_port", "destination_port"])

    # Decisions table
    op.create_table(
        "decisions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("decision_id", sa.String(100), nullable=False),
        sa.Column("customer_id", sa.String(50), nullable=False),
        sa.Column("signal_id", sa.String(100), nullable=True),
        sa.Column("chokepoint", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("urgency", sa.String(20), nullable=False),
        sa.Column("q1_what", postgresql.JSON(), nullable=False),
        sa.Column("q2_when", postgresql.JSON(), nullable=False),
        sa.Column("q3_severity", postgresql.JSON(), nullable=False),
        sa.Column("q4_why", postgresql.JSON(), nullable=False),
        sa.Column("q5_action", postgresql.JSON(), nullable=False),
        sa.Column("q6_confidence", postgresql.JSON(), nullable=False),
        sa.Column("q7_inaction", postgresql.JSON(), nullable=False),
        sa.Column("exposure_usd", sa.Float(), nullable=False),
        sa.Column("potential_loss_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("potential_delay_days", sa.Float(), nullable=False, server_default="0"),
        sa.Column("recommended_action", sa.String(50), nullable=False),
        sa.Column("action_cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("action_deadline", sa.DateTime(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("alternative_actions", postgresql.JSON(), nullable=False, server_default="[]"),
        sa.Column("is_delivered", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_acknowledged", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_acted_upon", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("customer_action", sa.String(50), nullable=True),
        sa.Column("user_feedback", sa.Text(), nullable=True),
        sa.Column("valid_until", sa.DateTime(), nullable=False),
        sa.Column("is_expired", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.customer_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("decision_id"),
    )
    op.create_index("ix_decisions_decision_id", "decisions", ["decision_id"])
    op.create_index("ix_decisions_customer", "decisions", ["customer_id"])
    op.create_index("ix_decisions_signal", "decisions", ["signal_id"])
    op.create_index("ix_decisions_created", "decisions", ["created_at"])
    op.create_index("ix_decisions_chokepoint", "decisions", ["chokepoint"])
    op.create_index("ix_decisions_validity", "decisions", ["valid_until", "is_expired"])

    # Alerts table
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("alert_id", sa.String(100), nullable=False),
        sa.Column("customer_id", sa.String(50), nullable=False),
        sa.Column("decision_id", sa.String(100), nullable=True),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("recipient", sa.String(100), nullable=False),
        sa.Column("template_name", sa.String(100), nullable=False),
        sa.Column("message_content", sa.Text(), nullable=True),
        sa.Column("message_hash", sa.String(64), nullable=True),
        sa.Column("external_message_id", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.customer_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["decision_id"], ["decisions.decision_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("alert_id"),
        sa.UniqueConstraint("customer_id", "message_hash", name="uq_alerts_dedup"),
    )
    op.create_index("ix_alerts_alert_id", "alerts", ["alert_id"])
    op.create_index("ix_alerts_customer", "alerts", ["customer_id"])
    op.create_index("ix_alerts_status", "alerts", ["status"])
    op.create_index("ix_alerts_created", "alerts", ["created_at"])

    # API Keys table
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("key_id", sa.String(50), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False),
        sa.Column("owner_id", sa.String(50), nullable=False),
        sa.Column("owner_type", sa.String(20), nullable=False, server_default="customer"),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("scopes", postgresql.JSON(), nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("rate_limit_per_minute", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("metadata", postgresql.JSON(), nullable=False, server_default="{}"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_id"),
    )
    op.create_index("ix_api_keys_key_id", "api_keys", ["key_id"])
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"])
    op.create_index("ix_api_keys_owner", "api_keys", ["owner_id"])

    # Outcome Tracking table
    op.create_table(
        "decision_outcomes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("decision_id", sa.String(100), nullable=False),
        sa.Column("customer_id", sa.String(50), nullable=False),
        sa.Column("predicted_event_occurred", sa.Boolean(), nullable=True),
        sa.Column("predicted_impact_usd", sa.Float(), nullable=True),
        sa.Column("predicted_delay_days", sa.Integer(), nullable=True),
        sa.Column("predicted_confidence", sa.Float(), nullable=True),
        sa.Column("recommended_action", sa.String(50), nullable=True),
        sa.Column("event_actually_occurred", sa.Boolean(), nullable=True),
        sa.Column("actual_impact_usd", sa.Float(), nullable=True),
        sa.Column("actual_delay_days", sa.Integer(), nullable=True),
        sa.Column("action_outcome", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("actual_action_taken", sa.String(50), nullable=True),
        sa.Column("event_accuracy", sa.String(20), nullable=False, server_default="na"),
        sa.Column("impact_accuracy", sa.String(20), nullable=False, server_default="na"),
        sa.Column("delay_accuracy", sa.String(20), nullable=False, server_default="na"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("confidence_bucket", sa.String(20), nullable=True),
        sa.Column("observation_source", sa.String(50), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("observed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["decision_id"], ["decisions.decision_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.customer_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_outcomes_decision", "decision_outcomes", ["decision_id"])
    op.create_index("ix_outcomes_customer", "decision_outcomes", ["customer_id"])
    op.create_index("ix_outcomes_status", "decision_outcomes", ["status"])
    op.create_index("ix_outcomes_bucket", "decision_outcomes", ["confidence_bucket"])

    # Audit Log table
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.String(100), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.String(100), nullable=False),
        sa.Column("actor_id", sa.String(100), nullable=True),
        sa.Column("actor_type", sa.String(20), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("changes", postgresql.JSON(), nullable=True),
        sa.Column("metadata", postgresql.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("request_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_event_id", "audit_logs", ["event_id"])
    op.create_index("ix_audit_entity", "audit_logs", ["entity_type", "entity_id"])
    op.create_index("ix_audit_actor", "audit_logs", ["actor_id"])
    op.create_index("ix_audit_created", "audit_logs", ["created_at"])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table("audit_logs")
    op.drop_table("decision_outcomes")
    op.drop_table("api_keys")
    op.drop_table("alerts")
    op.drop_table("decisions")
    op.drop_table("shipments")
    op.drop_table("customers")
