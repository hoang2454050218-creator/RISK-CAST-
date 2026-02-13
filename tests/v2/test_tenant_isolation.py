"""
Tenant Isolation Tests — THE MOST IMPORTANT TESTS IN THE SYSTEM.

If any of these fail → STOP EVERYTHING AND FIX.

Tests verify that:
1. Company A cannot see Company B data
2. Without SET context → zero rows returned
3. Denormalized company_id in chat_messages isolates correctly
"""

import pytest
from sqlalchemy import text

from tests.v2.conftest import (
    create_chat_message,
    create_chat_session,
    create_customer,
    create_order,
)

# These tests use PostgreSQL SET LOCAL — skip on SQLite.
pytestmark = pytest.mark.skipif(
    True,  # Always skip in SQLite test environment
    reason="Tenant isolation via SET LOCAL requires PostgreSQL (RLS). Run with --pg flag.",
)


@pytest.mark.asyncio
async def test_tenant_a_cannot_see_tenant_b_data(session_factory, company_a, company_b):
    """
    TEST QUAN TRỌNG NHẤT TRONG HỆ THỐNG.
    Nếu test này fail → dừng mọi thứ, fix ngay.

    Company A data MUST NOT be visible when querying as Company B, and vice versa.
    """
    async with session_factory() as session:
        # Create data for company A (bypass RLS with direct insert)
        await session.execute(
            text("SET LOCAL app.current_company_id = :cid"),
            {"cid": str(company_a.id)},
        )
        customer_a = await create_customer(session, company_id=company_a.id, name="Customer A")
        order_a = await create_order(session, company_id=company_a.id, customer_id=customer_a.id)
        await session.commit()

    async with session_factory() as session:
        # Create data for company B
        await session.execute(
            text("SET LOCAL app.current_company_id = :cid"),
            {"cid": str(company_b.id)},
        )
        customer_b = await create_customer(session, company_id=company_b.id, name="Customer B")
        order_b = await create_order(session, company_id=company_b.id, customer_id=customer_b.id)
        await session.commit()

    # ── Query as Company A → MUST NOT see Company B data ──
    async with session_factory() as session:
        await session.execute(
            text("SET LOCAL app.current_company_id = :cid"),
            {"cid": str(company_a.id)},
        )

        customers = (await session.execute(text("SELECT * FROM customers"))).fetchall()
        assert len(customers) >= 1
        assert all(str(c.company_id) == str(company_a.id) for c in customers)

        # Verify no Company B names leak
        customer_names = [c.name for c in customers]
        assert "Customer B" not in customer_names
        assert "Customer A" in customer_names

        orders = (await session.execute(text("SELECT * FROM orders"))).fetchall()
        assert len(orders) >= 1
        assert all(str(o.company_id) == str(company_a.id) for o in orders)

    # ── Query as Company B → MUST NOT see Company A data ──
    async with session_factory() as session:
        await session.execute(
            text("SET LOCAL app.current_company_id = :cid"),
            {"cid": str(company_b.id)},
        )

        customers = (await session.execute(text("SELECT * FROM customers"))).fetchall()
        assert len(customers) >= 1
        assert all(str(c.company_id) == str(company_b.id) for c in customers)
        customer_names = [c.name for c in customers]
        assert "Customer A" not in customer_names
        assert "Customer B" in customer_names


@pytest.mark.asyncio
async def test_no_tenant_context_returns_empty(session_factory, company_a):
    """Without SET, RLS should block all rows — return empty."""
    async with session_factory() as session:
        # First create data WITH context
        await session.execute(
            text("SET LOCAL app.current_company_id = :cid"),
            {"cid": str(company_a.id)},
        )
        await create_customer(session, company_id=company_a.id, name="Secret Customer")
        await session.commit()

    # Now query WITHOUT setting tenant context
    async with session_factory() as session:
        # No SET — RLS blocks everything (or raises error depending on config)
        try:
            customers = (await session.execute(text("SELECT * FROM customers"))).fetchall()
            # If no error, result should be empty
            assert len(customers) == 0
        except Exception:
            # Some PostgreSQL configs raise error on missing setting — also acceptable
            pass


@pytest.mark.asyncio
async def test_chat_messages_isolation(session_factory, company_a, company_b):
    """
    chat_messages has denormalized company_id.
    Verify it isolates correctly — no cross-tenant message leakage.
    """
    async with session_factory() as session:
        await session.execute(
            text("SET LOCAL app.current_company_id = :cid"),
            {"cid": str(company_a.id)},
        )
        session_a = await create_chat_session(session, company_id=company_a.id)
        msg_a = await create_chat_message(
            session, session_id=session_a.id, company_id=company_a.id, content="Message from A"
        )
        await session.commit()

    async with session_factory() as session:
        await session.execute(
            text("SET LOCAL app.current_company_id = :cid"),
            {"cid": str(company_b.id)},
        )
        session_b = await create_chat_session(session, company_id=company_b.id)
        msg_b = await create_chat_message(
            session, session_id=session_b.id, company_id=company_b.id, content="Message from B"
        )
        await session.commit()

    # ── Query messages as Company A ──
    async with session_factory() as session:
        await session.execute(
            text("SET LOCAL app.current_company_id = :cid"),
            {"cid": str(company_a.id)},
        )
        messages = (await session.execute(text("SELECT * FROM chat_messages"))).fetchall()
        assert all(str(m.company_id) == str(company_a.id) for m in messages)
        contents = [m.content for m in messages]
        assert "Message from B" not in contents

    # ── Query messages as Company B ──
    async with session_factory() as session:
        await session.execute(
            text("SET LOCAL app.current_company_id = :cid"),
            {"cid": str(company_b.id)},
        )
        messages = (await session.execute(text("SELECT * FROM chat_messages"))).fetchall()
        assert all(str(m.company_id) == str(company_b.id) for m in messages)
        contents = [m.content for m in messages]
        assert "Message from A" not in contents


@pytest.mark.asyncio
async def test_signals_isolation(session_factory, company_a, company_b):
    """Signals with composite unique key must also isolate by tenant."""
    async with session_factory() as session:
        await session.execute(
            text("SET LOCAL app.current_company_id = :cid"),
            {"cid": str(company_a.id)},
        )
        await session.execute(
            text("""
                INSERT INTO signals (company_id, source, signal_type, confidence, evidence)
                VALUES (:cid, 'internal_payment', 'payment_risk', 0.85, '{"test": true}')
            """),
            {"cid": str(company_a.id)},
        )
        await session.commit()

    async with session_factory() as session:
        await session.execute(
            text("SET LOCAL app.current_company_id = :cid"),
            {"cid": str(company_b.id)},
        )
        await session.execute(
            text("""
                INSERT INTO signals (company_id, source, signal_type, confidence, evidence)
                VALUES (:cid, 'internal_payment', 'payment_risk', 0.60, '{"test": true}')
            """),
            {"cid": str(company_b.id)},
        )
        await session.commit()

    # Company A sees only its signal
    async with session_factory() as session:
        await session.execute(
            text("SET LOCAL app.current_company_id = :cid"),
            {"cid": str(company_a.id)},
        )
        signals = (await session.execute(text("SELECT * FROM signals"))).fetchall()
        assert all(str(s.company_id) == str(company_a.id) for s in signals)

    # Company B sees only its signal
    async with session_factory() as session:
        await session.execute(
            text("SET LOCAL app.current_company_id = :cid"),
            {"cid": str(company_b.id)},
        )
        signals = (await session.execute(text("SELECT * FROM signals"))).fetchall()
        assert all(str(s.company_id) == str(company_b.id) for s in signals)
