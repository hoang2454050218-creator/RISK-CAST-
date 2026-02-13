"""
Database query functions for analyzers and services.

These are raw query functions that bypass RLS (used by the scheduler
which runs with direct DB access, not through the API middleware).
All functions require an explicit company_id parameter.
"""

from datetime import date, timedelta
from typing import Any, Optional, Sequence

from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.db.models import (
    ChatMessage,
    ChatSession,
    Company,
    Customer,
    Incident,
    MorningBrief,
    Order,
    Payment,
    RiskAppetiteProfile,
    Route,
    Signal,
)


# ── Company ──────────────────────────────────────────────────────────────


async def get_active_companies(session: AsyncSession) -> Sequence[Company]:
    """Get all active companies (for scheduler iteration)."""
    result = await session.execute(select(Company))
    return result.scalars().all()


async def get_company(session: AsyncSession, company_id: str) -> Optional[Company]:
    result = await session.execute(
        select(Company).where(Company.id == company_id)
    )
    return result.scalar_one_or_none()


# ── Customers + Payments ─────────────────────────────────────────────────


async def get_customers_with_payments(
    session: AsyncSession, company_id: str
) -> Sequence[Customer]:
    """Get customers that have at least one payment record."""
    result = await session.execute(
        select(Customer)
        .where(Customer.company_id == company_id)
        .where(
            Customer.id.in_(
                select(Payment.customer_id)
                .where(Payment.company_id == company_id)
                .where(Payment.customer_id.is_not(None))
                .distinct()
            )
        )
    )
    return result.scalars().all()


async def get_payment_history(
    session: AsyncSession, company_id: str, customer_id: str, days: int = 90
) -> Sequence[Payment]:
    """Get payment history for a customer within the last N days."""
    cutoff = date.today() - timedelta(days=days)
    result = await session.execute(
        select(Payment)
        .where(
            and_(
                Payment.company_id == company_id,
                Payment.customer_id == customer_id,
                Payment.created_at >= cutoff,
            )
        )
        .order_by(Payment.created_at.asc())
    )
    return result.scalars().all()


# ── Routes + Orders ──────────────────────────────────────────────────────


async def get_active_routes(
    session: AsyncSession, company_id: str
) -> Sequence[Route]:
    """Get active routes for a company."""
    result = await session.execute(
        select(Route).where(
            and_(Route.company_id == company_id, Route.is_active == True)  # noqa: E712
        )
    )
    return result.scalars().all()


async def get_route_orders(
    session: AsyncSession, company_id: str, route_id: str, days: int = 14
) -> Sequence[Order]:
    """Get orders on a specific route within the last N days."""
    cutoff = date.today() - timedelta(days=days)
    result = await session.execute(
        select(Order)
        .where(
            and_(
                Order.company_id == company_id,
                Order.route_id == route_id,
                Order.created_at >= cutoff,
            )
        )
        .order_by(Order.created_at.desc())
    )
    return result.scalars().all()


async def get_orders_by_status(
    session: AsyncSession, company_id: str, statuses: list[str]
) -> Sequence[Order]:
    """Get orders matching any of the given statuses."""
    result = await session.execute(
        select(Order).where(
            and_(
                Order.company_id == company_id,
                Order.status.in_(statuses),
            )
        )
    )
    return result.scalars().all()


# ── Signals ──────────────────────────────────────────────────────────────


async def get_active_signals(
    session: AsyncSession, company_id: str, limit: int = 50
) -> Sequence[Signal]:
    """Get active signals for a company."""
    result = await session.execute(
        select(Signal)
        .where(
            and_(Signal.company_id == company_id, Signal.is_active == True)  # noqa: E712
        )
        .order_by(Signal.severity_score.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def get_active_signals_map(
    session: AsyncSession, company_id: str
) -> dict[tuple[str, str], list[Signal]]:
    """
    Get active signals grouped by (entity_type, entity_id).
    Returns a dict for O(1) lookup by analyzers.
    """
    signals = await get_active_signals(session, company_id, limit=500)
    signal_map: dict[tuple[str, str], list[Signal]] = {}
    for s in signals:
        if s.entity_type and s.entity_id:
            key = (s.entity_type, str(s.entity_id))
            signal_map.setdefault(key, []).append(s)
    return signal_map


# ── Risk Appetite ────────────────────────────────────────────────────────


async def get_risk_appetite(
    session: AsyncSession, company_id: str
) -> Optional[dict]:
    """Get risk appetite profile for a company."""
    result = await session.execute(
        select(RiskAppetiteProfile).where(
            RiskAppetiteProfile.company_id == company_id
        )
    )
    row = result.scalar_one_or_none()
    return row.profile if row else None


# ── Counts / Summaries ───────────────────────────────────────────────────


async def count_orders(
    session: AsyncSession, company_id: str, status: Optional[str] = None
) -> int:
    stmt = select(func.count()).select_from(Order).where(Order.company_id == company_id)
    if status:
        stmt = stmt.where(Order.status == status)
    result = await session.execute(stmt)
    return result.scalar_one()


async def count_payments(
    session: AsyncSession, company_id: str, status: Optional[str] = None
) -> int:
    stmt = select(func.count()).select_from(Payment).where(Payment.company_id == company_id)
    if status:
        stmt = stmt.where(Payment.status == status)
    result = await session.execute(stmt)
    return result.scalar_one()


async def sum_overdue_payments(session: AsyncSession, company_id: str) -> float:
    result = await session.execute(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            and_(Payment.company_id == company_id, Payment.status == "overdue")
        )
    )
    return float(result.scalar_one())


async def count_incidents(
    session: AsyncSession, company_id: str, days: int = 7
) -> int:
    cutoff = date.today() - timedelta(days=days)
    result = await session.execute(
        select(func.count())
        .select_from(Incident)
        .where(and_(Incident.company_id == company_id, Incident.created_at >= cutoff))
    )
    return result.scalar_one()


# ── Chat Sessions / Messages ─────────────────────────────────────────────


async def get_or_create_session(
    session: AsyncSession,
    company_id: str,
    user_id: str,
    session_id: Optional[str] = None,
) -> ChatSession:
    """Get existing session or create a new one."""
    if session_id:
        result = await session.execute(
            select(ChatSession).where(
                and_(
                    ChatSession.id == session_id,
                    ChatSession.company_id == company_id,
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

    # Create new session
    new_session = ChatSession(company_id=company_id, user_id=user_id)
    session.add(new_session)
    await session.flush()
    return new_session


async def save_message(
    session: AsyncSession,
    session_id: str,
    company_id: str,
    role: str,
    content: str,
    context_used: Optional[dict] = None,
) -> ChatMessage:
    """Save a chat message."""
    msg = ChatMessage(
        session_id=session_id,
        company_id=company_id,
        role=role,
        content=content,
        context_used=context_used or {},
    )
    session.add(msg)
    await session.flush()
    return msg


async def get_session_messages(
    session: AsyncSession,
    session_id: str,
    limit: int = 50,
) -> Sequence[ChatMessage]:
    """Get messages for a session, ordered by time."""
    result = await session.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .limit(limit)
    )
    return result.scalars().all()


async def get_user_sessions(
    session: AsyncSession,
    company_id: str,
    user_id: str,
    limit: int = 20,
) -> Sequence[ChatSession]:
    """Get chat sessions for a user, newest first."""
    result = await session.execute(
        select(ChatSession)
        .where(
            and_(
                ChatSession.company_id == company_id,
                ChatSession.user_id == user_id,
            )
        )
        .order_by(ChatSession.updated_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


# ── Search / Lookup (for Context Builder) ────────────────────────────────


async def find_order(
    session: AsyncSession, company_id: str, query: str
) -> Optional[dict]:
    """Find an order by order_number (fuzzy)."""
    result = await session.execute(
        select(Order).where(
            and_(
                Order.company_id == company_id,
                Order.order_number.ilike(f"%{query}%"),
            )
        ).limit(1)
    )
    order = result.scalar_one_or_none()
    if not order:
        return None
    return {
        "id": str(order.id),
        "order_number": order.order_number,
        "status": order.status,
        "total_value": float(order.total_value) if order.total_value else 0,
        "currency": order.currency,
        "customer_id": str(order.customer_id) if order.customer_id else None,
        "route_id": str(order.route_id) if order.route_id else None,
        "origin": order.origin,
        "destination": order.destination,
        "expected_date": str(order.expected_date) if order.expected_date else None,
        "actual_date": str(order.actual_date) if order.actual_date else None,
    }


async def find_customer(
    session: AsyncSession, company_id: str, query: str
) -> Optional[dict]:
    """Find a customer by name or code (fuzzy)."""
    result = await session.execute(
        select(Customer).where(
            and_(
                Customer.company_id == company_id,
                (Customer.name.ilike(f"%{query}%")) | (Customer.code.ilike(f"%{query}%")),
            )
        ).limit(1)
    )
    cust = result.scalar_one_or_none()
    if not cust:
        return None
    return {
        "id": str(cust.id),
        "name": cust.name,
        "code": cust.code,
        "tier": cust.tier,
        "payment_terms": cust.payment_terms,
        "contact_email": cust.contact_email,
    }


async def find_route(
    session: AsyncSession, company_id: str, query: str
) -> Optional[dict]:
    """Find a route by name (fuzzy)."""
    result = await session.execute(
        select(Route).where(
            and_(
                Route.company_id == company_id,
                Route.name.ilike(f"%{query}%"),
            )
        ).limit(1)
    )
    route = result.scalar_one_or_none()
    if not route:
        return None
    return {
        "id": str(route.id),
        "name": route.name,
        "origin": route.origin,
        "destination": route.destination,
        "transport_mode": route.transport_mode,
        "avg_duration_days": float(route.avg_duration_days) if route.avg_duration_days else None,
    }


async def get_customer_summary(
    session: AsyncSession, company_id: str, customer_id: str
) -> Optional[dict]:
    """Get a customer summary with order + payment stats."""
    cust = await session.execute(
        select(Customer).where(
            and_(Customer.company_id == company_id, Customer.id == customer_id)
        )
    )
    customer = cust.scalar_one_or_none()
    if not customer:
        return None

    order_count = await session.execute(
        select(func.count()).select_from(Order).where(
            and_(Order.company_id == company_id, Order.customer_id == customer_id)
        )
    )
    payment_stats = await session.execute(
        select(
            func.count().label("total"),
            func.sum(Payment.amount).label("total_amount"),
        )
        .where(and_(Payment.company_id == company_id, Payment.customer_id == customer_id))
    )
    ps = payment_stats.one()

    return {
        "name": customer.name,
        "code": customer.code,
        "tier": customer.tier,
        "total_orders": order_count.scalar_one(),
        "total_payments": ps.total or 0,
        "total_payment_amount": float(ps.total_amount or 0),
    }


async def get_orders_summary(
    session: AsyncSession, company_id: str, days: int = 7
) -> dict:
    """Summary of orders in the last N days."""
    cutoff = date.today() - timedelta(days=days)
    result = await session.execute(
        select(
            Order.status,
            func.count().label("count"),
            func.sum(Order.total_value).label("total_value"),
        )
        .where(and_(Order.company_id == company_id, Order.created_at >= cutoff))
        .group_by(Order.status)
    )
    rows = result.all()
    return {
        "period_days": days,
        "by_status": [
            {"status": r.status, "count": r.count, "total_value": float(r.total_value or 0)}
            for r in rows
        ],
        "total": sum(r.count for r in rows),
    }


async def get_overdue_payments_summary(
    session: AsyncSession, company_id: str
) -> dict:
    """Summary of overdue payments."""
    result = await session.execute(
        select(
            func.count().label("count"),
            func.sum(Payment.amount).label("total"),
        ).where(
            and_(Payment.company_id == company_id, Payment.status == "overdue")
        )
    )
    row = result.one()
    return {"overdue_count": row.count or 0, "overdue_total": float(row.total or 0)}


async def get_incidents_summary(
    session: AsyncSession, company_id: str, days: int = 7
) -> dict:
    """Summary of incidents in the last N days."""
    cutoff = date.today() - timedelta(days=days)
    result = await session.execute(
        select(
            Incident.type,
            Incident.severity,
            func.count().label("count"),
        )
        .where(and_(Incident.company_id == company_id, Incident.created_at >= cutoff))
        .group_by(Incident.type, Incident.severity)
    )
    rows = result.all()
    return {
        "period_days": days,
        "incidents": [
            {"type": r.type, "severity": r.severity, "count": r.count}
            for r in rows
        ],
        "total": sum(r.count for r in rows),
    }


async def get_today_brief(
    session: AsyncSession, company_id: str
) -> Optional[dict]:
    """Get today's morning brief."""
    result = await session.execute(
        select(MorningBrief).where(
            and_(
                MorningBrief.company_id == company_id,
                MorningBrief.brief_date == date.today(),
            )
        )
    )
    brief = result.scalar_one_or_none()
    if not brief:
        return None
    return {
        "id": str(brief.id),
        "brief_date": str(brief.brief_date),
        "content": brief.content,
        "priority_items": brief.priority_items,
    }


async def search_incidents_fulltext(
    session: AsyncSession, company_id: str, query: str, limit: int = 5
) -> list[dict]:
    """Full-text search incidents."""
    result = await session.execute(
        select(Incident)
        .where(
            and_(
                Incident.company_id == company_id,
                (
                    Incident.type.ilike(f"%{query}%")
                    | Incident.description.ilike(f"%{query}%")
                    | Incident.resolution.ilike(f"%{query}%")
                ),
            )
        )
        .order_by(Incident.created_at.desc())
        .limit(limit)
    )
    rows = result.scalars().all()
    return [
        {
            "id": str(i.id),
            "type": i.type,
            "severity": i.severity,
            "description": i.description,
            "resolution": i.resolution,
            "created_at": str(i.created_at),
        }
        for i in rows
    ]
