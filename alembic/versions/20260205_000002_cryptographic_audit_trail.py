"""Add cryptographic audit trail tables.

Revision ID: 20260205_000002
Revises: 20260205_000001
Create Date: 2026-02-05 00:00:02

This migration adds:
1. Cryptographic chain fields to audit_logs (payload_hash, sequence_number, previous_hash, record_hash)
2. input_snapshots table for decision reproducibility
3. processing_records table for computation tracking
4. human_overrides table for override tracking
5. escalations table for escalation management
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260205_000002"
down_revision: Union[str, None] = "20260205_000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add cryptographic audit trail tables and fields."""
    
    # =========================================================================
    # 1. Add cryptographic chain fields to audit_logs
    # =========================================================================
    op.add_column("audit_logs", sa.Column("payload_hash", sa.String(64), nullable=True))
    op.add_column("audit_logs", sa.Column("sequence_number", sa.BigInteger(), nullable=True))
    op.add_column("audit_logs", sa.Column("previous_hash", sa.String(64), nullable=True))
    op.add_column("audit_logs", sa.Column("record_hash", sa.String(64), nullable=True))
    op.add_column("audit_logs", sa.Column("payload", postgresql.JSON(), nullable=True))
    
    # Drop old columns that are being replaced
    op.drop_column("audit_logs", "action")
    op.drop_column("audit_logs", "changes")
    op.drop_column("audit_logs", "metadata")
    op.drop_column("audit_logs", "ip_address")
    op.drop_column("audit_logs", "user_agent")
    op.drop_column("audit_logs", "request_id")
    
    # Alter event_type column to accommodate longer types
    op.alter_column("audit_logs", "event_type", type_=sa.String(100))
    op.alter_column("audit_logs", "entity_type", type_=sa.String(100))
    op.alter_column("audit_logs", "entity_id", type_=sa.String(255))
    op.alter_column("audit_logs", "actor_type", type_=sa.String(50), nullable=False)
    op.alter_column("audit_logs", "actor_id", type_=sa.String(255))
    
    # Add unique constraint on sequence_number and index
    op.create_index("ix_audit_logs_sequence", "audit_logs", ["sequence_number"], unique=True)
    op.create_index("ix_audit_logs_event_time", "audit_logs", ["event_type", "created_at"])
    
    # =========================================================================
    # 2. Create input_snapshots table
    # =========================================================================
    op.create_table(
        "input_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("snapshot_id", sa.String(100), nullable=False),
        
        # Signal data (from OMEN)
        sa.Column("signal_id", sa.String(100), nullable=False),
        sa.Column("signal_data", postgresql.JSON(), nullable=False),
        sa.Column("signal_hash", sa.String(64), nullable=False),
        
        # Reality data (from ORACLE)
        sa.Column("reality_data", postgresql.JSON(), nullable=False),
        sa.Column("reality_hash", sa.String(64), nullable=False),
        sa.Column("reality_staleness_seconds", sa.Integer(), nullable=False),
        
        # Customer context
        sa.Column("customer_id", sa.String(50), nullable=False),
        sa.Column("customer_context_data", postgresql.JSON(), nullable=False),
        sa.Column("customer_context_hash", sa.String(64), nullable=False),
        sa.Column("customer_context_version", sa.Integer(), nullable=False),
        
        # Combined integrity hash
        sa.Column("combined_hash", sa.String(64), nullable=False),
        
        # Timestamps
        sa.Column("captured_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("snapshot_id"),
        sa.UniqueConstraint("combined_hash"),
    )
    op.create_index("ix_input_snapshots_snapshot_id", "input_snapshots", ["snapshot_id"])
    op.create_index("ix_input_snapshots_customer", "input_snapshots", ["customer_id"])
    op.create_index("ix_input_snapshots_signal", "input_snapshots", ["signal_id"])
    op.create_index("ix_input_snapshots_captured", "input_snapshots", ["captured_at"])
    
    # =========================================================================
    # 3. Create processing_records table
    # =========================================================================
    op.create_table(
        "processing_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("record_id", sa.String(100), nullable=False),
        
        # Model information
        sa.Column("model_version", sa.String(50), nullable=False),
        sa.Column("model_hash", sa.String(64), nullable=True),
        
        # Configuration
        sa.Column("config_version", sa.String(50), nullable=False),
        sa.Column("config_hash", sa.String(64), nullable=True),
        
        # Reasoning trace
        sa.Column("reasoning_trace_id", sa.String(100), nullable=True),
        sa.Column("layers_executed", postgresql.JSON(), nullable=False, server_default="[]"),
        
        # Performance metrics
        sa.Column("computation_time_ms", sa.Integer(), nullable=False),
        sa.Column("memory_used_mb", sa.Float(), nullable=True),
        
        # Warnings and flags
        sa.Column("warnings", postgresql.JSON(), nullable=False, server_default="[]"),
        sa.Column("degradation_level", sa.Integer(), nullable=False, server_default="0"),
        
        # Data quality flags
        sa.Column("stale_data_sources", postgresql.JSON(), nullable=False, server_default="[]"),
        sa.Column("missing_data_sources", postgresql.JSON(), nullable=False, server_default="[]"),
        
        # Timestamp
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("record_id"),
    )
    op.create_index("ix_processing_records_record_id", "processing_records", ["record_id"])
    
    # =========================================================================
    # 4. Create human_overrides table
    # =========================================================================
    op.create_table(
        "human_overrides",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("override_id", sa.String(100), nullable=False),
        
        # Decision reference
        sa.Column("decision_id", sa.String(100), nullable=False),
        
        # Override details
        sa.Column("original_action", sa.String(50), nullable=False),
        sa.Column("new_action", sa.String(50), nullable=False),
        sa.Column("new_action_details", postgresql.JSON(), nullable=True),
        
        # Reason
        sa.Column("reason_category", sa.String(50), nullable=False),
        sa.Column("reason_details", sa.Text(), nullable=False),
        
        # Actor
        sa.Column("overridden_by", sa.String(255), nullable=False),
        
        # Timestamp
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("override_id"),
        sa.ForeignKeyConstraint(["decision_id"], ["decisions.decision_id"], ondelete="CASCADE"),
    )
    op.create_index("ix_human_overrides_override_id", "human_overrides", ["override_id"])
    op.create_index("ix_human_overrides_decision", "human_overrides", ["decision_id"])
    op.create_index("ix_human_overrides_user", "human_overrides", ["overridden_by"])
    op.create_index("ix_human_overrides_created", "human_overrides", ["created_at"])
    
    # =========================================================================
    # 5. Create escalations table
    # =========================================================================
    op.create_table(
        "escalations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("escalation_id", sa.String(100), nullable=False),
        
        # Decision reference
        sa.Column("decision_id", sa.String(100), nullable=False),
        sa.Column("customer_id", sa.String(50), nullable=False),
        
        # Escalation details
        sa.Column("trigger", sa.String(50), nullable=False),
        sa.Column("trigger_details", sa.Text(), nullable=False),
        sa.Column("confidence_at_escalation", sa.Float(), nullable=False),
        sa.Column("exposure_usd", sa.Float(), nullable=True),
        
        # System recommendation
        sa.Column("recommended_action", sa.String(50), nullable=False),
        sa.Column("alternative_actions", postgresql.JSON(), nullable=False, server_default="[]"),
        
        # Routing
        sa.Column("escalated_to", postgresql.JSON(), nullable=False, server_default="[]"),
        sa.Column("deadline", sa.DateTime(), nullable=False),
        
        # Resolution
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("resolved_by", sa.String(255), nullable=True),
        sa.Column("resolution", sa.String(20), nullable=True),
        sa.Column("final_action", sa.String(50), nullable=True),
        sa.Column("resolution_reason", sa.Text(), nullable=True),
        
        # Timestamps
        sa.Column("escalated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("escalation_id"),
        sa.ForeignKeyConstraint(["decision_id"], ["decisions.decision_id"], ondelete="CASCADE"),
    )
    op.create_index("ix_escalations_escalation_id", "escalations", ["escalation_id"])
    op.create_index("ix_escalations_decision", "escalations", ["decision_id"])
    op.create_index("ix_escalations_customer", "escalations", ["customer_id"])
    op.create_index("ix_escalations_status", "escalations", ["status"])
    op.create_index("ix_escalations_escalated_at", "escalations", ["escalated_at"])


def downgrade() -> None:
    """Remove cryptographic audit trail tables and fields."""
    
    # Drop new tables
    op.drop_table("escalations")
    op.drop_table("human_overrides")
    op.drop_table("processing_records")
    op.drop_table("input_snapshots")
    
    # Drop new indexes from audit_logs
    op.drop_index("ix_audit_logs_event_time", "audit_logs")
    op.drop_index("ix_audit_logs_sequence", "audit_logs")
    
    # Remove cryptographic chain fields from audit_logs
    op.drop_column("audit_logs", "payload")
    op.drop_column("audit_logs", "record_hash")
    op.drop_column("audit_logs", "previous_hash")
    op.drop_column("audit_logs", "sequence_number")
    op.drop_column("audit_logs", "payload_hash")
    
    # Restore old columns
    op.add_column("audit_logs", sa.Column("action", sa.String(50), nullable=False))
    op.add_column("audit_logs", sa.Column("changes", postgresql.JSON(), nullable=True))
    op.add_column("audit_logs", sa.Column("metadata", postgresql.JSON(), nullable=True))
    op.add_column("audit_logs", sa.Column("ip_address", sa.String(45), nullable=True))
    op.add_column("audit_logs", sa.Column("user_agent", sa.String(500), nullable=True))
    op.add_column("audit_logs", sa.Column("request_id", sa.String(100), nullable=True))
    
    # Restore column types
    op.alter_column("audit_logs", "event_type", type_=sa.String(50))
    op.alter_column("audit_logs", "entity_type", type_=sa.String(50))
    op.alter_column("audit_logs", "entity_id", type_=sa.String(100))
    op.alter_column("audit_logs", "actor_type", type_=sa.String(20), nullable=True)
    op.alter_column("audit_logs", "actor_id", type_=sa.String(100))
