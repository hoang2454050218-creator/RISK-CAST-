"""V2 foundation schema — multi-tenant with RLS.

Creates all 12 V2 tables, RLS policies, GIN indexes for full-text search.
This migration is independent of V1 tables.

Revision ID: v2_foundation_001
Revises: 20260205_000002
Create Date: 2026-02-07
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "v2_foundation_001"
down_revision = "20260205_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ──────────────────────────────────────────────────────────────────────
    # 1.1 Tenant & Auth
    # ──────────────────────────────────────────────────────────────────────
    op.execute("""
    CREATE TABLE IF NOT EXISTS companies (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name            VARCHAR(255) NOT NULL,
        slug            VARCHAR(100) UNIQUE NOT NULL,
        industry        VARCHAR(100),
        timezone        VARCHAR(50) DEFAULT 'Asia/Ho_Chi_Minh',
        plan            VARCHAR(50) DEFAULT 'starter',
        settings        JSONB DEFAULT '{}',
        created_at      TIMESTAMPTZ DEFAULT NOW(),
        updated_at      TIMESTAMPTZ DEFAULT NOW()
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        company_id      UUID NOT NULL REFERENCES companies(id),
        email           VARCHAR(255) UNIQUE NOT NULL,
        password_hash   VARCHAR(255) NOT NULL,
        name            VARCHAR(255) NOT NULL,
        role            VARCHAR(50) DEFAULT 'member',
        preferences     JSONB DEFAULT '{}',
        last_login_at   TIMESTAMPTZ,
        created_at      TIMESTAMPTZ DEFAULT NOW()
    )
    """)

    # ──────────────────────────────────────────────────────────────────────
    # 1.2 Company Operational Data
    # ──────────────────────────────────────────────────────────────────────
    op.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        company_id      UUID NOT NULL REFERENCES companies(id),
        name            VARCHAR(255) NOT NULL,
        code            VARCHAR(50),
        tier            VARCHAR(50) DEFAULT 'standard',
        contact_email   VARCHAR(255),
        contact_phone   VARCHAR(50),
        payment_terms   INTEGER DEFAULT 30,
        metadata        JSONB DEFAULT '{}',
        created_at      TIMESTAMPTZ DEFAULT NOW(),
        updated_at      TIMESTAMPTZ DEFAULT NOW()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_v2_customers_company ON customers(company_id)")
    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_v2_customers_search ON customers
        USING GIN (to_tsvector('simple', name || ' ' || COALESCE(code, '')))
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS routes (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        company_id      UUID NOT NULL REFERENCES companies(id),
        name            VARCHAR(255) NOT NULL,
        origin          VARCHAR(255) NOT NULL,
        destination     VARCHAR(255) NOT NULL,
        transport_mode  VARCHAR(50),
        avg_duration_days DECIMAL(5,1),
        is_active       BOOLEAN DEFAULT true,
        metadata        JSONB DEFAULT '{}',
        created_at      TIMESTAMPTZ DEFAULT NOW()
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        company_id      UUID NOT NULL REFERENCES companies(id),
        customer_id     UUID REFERENCES customers(id),
        route_id        UUID REFERENCES routes(id),
        order_number    VARCHAR(100) NOT NULL,
        status          VARCHAR(50) NOT NULL,
        total_value     DECIMAL(15,2),
        currency        VARCHAR(3) DEFAULT 'VND',
        origin          VARCHAR(255),
        destination     VARCHAR(255),
        expected_date   DATE,
        actual_date     DATE,
        metadata        JSONB DEFAULT '{}',
        created_at      TIMESTAMPTZ DEFAULT NOW(),
        updated_at      TIMESTAMPTZ DEFAULT NOW()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_v2_orders_company_status ON orders(company_id, status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_v2_orders_company_date ON orders(company_id, created_at DESC)")

    op.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        company_id      UUID NOT NULL REFERENCES companies(id),
        order_id        UUID REFERENCES orders(id),
        customer_id     UUID REFERENCES customers(id),
        amount          DECIMAL(15,2) NOT NULL,
        currency        VARCHAR(3) DEFAULT 'VND',
        status          VARCHAR(50) NOT NULL,
        due_date        DATE NOT NULL,
        paid_date       DATE,
        days_overdue    INTEGER GENERATED ALWAYS AS (
                            CASE WHEN paid_date IS NULL AND due_date < CURRENT_DATE
                            THEN CURRENT_DATE - due_date ELSE 0 END
                        ) STORED,
        metadata        JSONB DEFAULT '{}',
        created_at      TIMESTAMPTZ DEFAULT NOW()
    )
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_v2_payments_overdue ON payments(company_id, status)
        WHERE status = 'overdue'
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS incidents (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        company_id      UUID NOT NULL REFERENCES companies(id),
        order_id        UUID REFERENCES orders(id),
        route_id        UUID REFERENCES routes(id),
        customer_id     UUID REFERENCES customers(id),
        type            VARCHAR(100) NOT NULL,
        severity        VARCHAR(20) NOT NULL,
        description     TEXT,
        resolution      TEXT,
        resolved_at     TIMESTAMPTZ,
        metadata        JSONB DEFAULT '{}',
        created_at      TIMESTAMPTZ DEFAULT NOW()
    )
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_v2_incidents_search ON incidents
        USING GIN (to_tsvector('simple',
            type || ' ' || COALESCE(description, '') || ' ' || COALESCE(resolution, '')
        ))
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_v2_incidents_company_type
        ON incidents(company_id, type, created_at DESC)
    """)

    # ──────────────────────────────────────────────────────────────────────
    # 1.3 Signals
    # ──────────────────────────────────────────────────────────────────────
    op.execute("""
    CREATE TABLE IF NOT EXISTS signals (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        company_id      UUID NOT NULL REFERENCES companies(id),
        source          VARCHAR(100) NOT NULL,
        signal_type     VARCHAR(100) NOT NULL,
        entity_type     VARCHAR(50),
        entity_id       UUID,
        confidence      DECIMAL(3,2) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
        severity_score  DECIMAL(5,2) CHECK (severity_score BETWEEN 0 AND 100),
        evidence        JSONB NOT NULL,
        context         JSONB DEFAULT '{}',
        is_active       BOOLEAN DEFAULT true,
        expires_at      TIMESTAMPTZ,
        created_at      TIMESTAMPTZ DEFAULT NOW(),
        updated_at      TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE(company_id, source, signal_type, entity_type, entity_id)
    )
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_v2_signals_active ON signals(company_id, created_at DESC)
        WHERE is_active = true
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_v2_signals_entity ON signals(company_id, entity_type, entity_id)
        WHERE is_active = true
    """)

    # ──────────────────────────────────────────────────────────────────────
    # 1.4 AI Interaction
    # ──────────────────────────────────────────────────────────────────────
    op.execute("""
    CREATE TABLE IF NOT EXISTS chat_sessions (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        company_id      UUID NOT NULL REFERENCES companies(id),
        user_id         UUID NOT NULL REFERENCES users(id),
        title           VARCHAR(255),
        created_at      TIMESTAMPTZ DEFAULT NOW(),
        updated_at      TIMESTAMPTZ DEFAULT NOW()
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        session_id      UUID NOT NULL REFERENCES chat_sessions(id),
        company_id      UUID NOT NULL REFERENCES companies(id),
        role            VARCHAR(20) NOT NULL,
        content         TEXT NOT NULL,
        context_used    JSONB DEFAULT '{}',
        created_at      TIMESTAMPTZ DEFAULT NOW()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_v2_messages_session ON chat_messages(session_id, created_at)")

    op.execute("""
    CREATE TABLE IF NOT EXISTS morning_briefs (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        company_id      UUID NOT NULL REFERENCES companies(id),
        brief_date      DATE NOT NULL,
        content         TEXT NOT NULL,
        signals_used    JSONB NOT NULL,
        priority_items  JSONB NOT NULL,
        read_by         UUID[] DEFAULT '{}',
        created_at      TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE(company_id, brief_date)
    )
    """)

    # ──────────────────────────────────────────────────────────────────────
    # 1.5 Feedback Loop
    # ──────────────────────────────────────────────────────────────────────
    op.execute("""
    CREATE TABLE IF NOT EXISTS ai_suggestions (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        company_id      UUID NOT NULL REFERENCES companies(id),
        message_id      UUID REFERENCES chat_messages(id),
        signal_id       UUID REFERENCES signals(id),
        suggestion_type VARCHAR(100) NOT NULL,
        suggestion_text TEXT NOT NULL,
        entity_type     VARCHAR(50),
        entity_id       UUID,
        created_at      TIMESTAMPTZ DEFAULT NOW()
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS suggestion_feedback (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        suggestion_id   UUID NOT NULL REFERENCES ai_suggestions(id),
        user_id         UUID NOT NULL REFERENCES users(id),
        company_id      UUID NOT NULL REFERENCES companies(id),
        decision        VARCHAR(20) NOT NULL,
        reason_code     VARCHAR(100),
        reason_text     TEXT,
        outcome         VARCHAR(50),
        outcome_date    TIMESTAMPTZ,
        created_at      TIMESTAMPTZ DEFAULT NOW()
    )
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_v2_feedback_company
        ON suggestion_feedback(company_id, created_at DESC)
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS risk_appetite_profiles (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        company_id      UUID UNIQUE NOT NULL REFERENCES companies(id),
        profile         JSONB NOT NULL DEFAULT '{
            "payment_risk_tolerance": "medium",
            "route_risk_tolerance": "medium",
            "new_customer_policy": "cautious",
            "vip_override_enabled": true,
            "auto_alert_threshold": 0.7,
            "learned_rules": []
        }',
        updated_at      TIMESTAMPTZ DEFAULT NOW()
    )
    """)

    # ──────────────────────────────────────────────────────────────────────
    # 1.6 Row-Level Security
    # ──────────────────────────────────────────────────────────────────────

    rls_tables = [
        "customers", "routes", "orders", "payments", "incidents",
        "signals", "chat_sessions", "chat_messages", "morning_briefs",
        "ai_suggestions", "suggestion_feedback", "risk_appetite_profiles",
    ]

    for tbl in rls_tables:
        op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation_{tbl} ON {tbl} "
            f"USING (company_id = current_setting('app.current_company_id')::UUID)"
        )

    # Allow the riskcast DB user to bypass RLS (owner role) so app works
    # The RLS is enforced via SET LOCAL in middleware
    op.execute("ALTER TABLE customers FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE routes FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE orders FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE payments FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE incidents FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE signals FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE chat_sessions FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE chat_messages FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE morning_briefs FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE ai_suggestions FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE suggestion_feedback FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE risk_appetite_profiles FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    rls_tables = [
        "risk_appetite_profiles", "suggestion_feedback", "ai_suggestions",
        "morning_briefs", "chat_messages", "chat_sessions",
        "signals", "incidents", "payments", "orders", "routes", "customers",
    ]

    for tbl in rls_tables:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{tbl} ON {tbl}")
        op.execute(f"ALTER TABLE {tbl} DISABLE ROW LEVEL SECURITY")

    drop_order = [
        "risk_appetite_profiles", "suggestion_feedback", "ai_suggestions",
        "morning_briefs", "chat_messages", "chat_sessions",
        "signals", "incidents", "payments", "orders", "routes", "customers",
        "users", "companies",
    ]
    for tbl in drop_order:
        op.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")
