"""
Morning Brief Generator — ORM-based for cross-database compatibility.
"""

import json
import uuid
from datetime import date

import structlog
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.db import queries as db_queries
from riskcast.db.models import MorningBrief
from riskcast.services.llm_gateway import LLMGateway

logger = structlog.get_logger(__name__)


class MorningBriefGenerator:
    def __init__(self, llm: LLMGateway, sse_manager=None):
        self.llm = llm
        self.sse_manager = sse_manager

    async def generate(self, session: AsyncSession, company_id: str) -> dict | None:
        cid = uuid.UUID(company_id) if isinstance(company_id, str) else company_id

        # Check existing
        existing = await db_queries.get_today_brief(session, str(cid))
        if existing:
            return existing

        # Collect signals
        all_signals = await db_queries.get_active_signals(session, str(cid), limit=20)
        actionable = sorted(
            [s for s in all_signals if (s.severity_score or 0) >= 40 and float(s.confidence) >= 0.5],
            key=lambda s: float(s.severity_score or 0) * float(s.confidence),
            reverse=True,
        )[:5]

        # Metrics
        metrics = {
            "orders_pending": await db_queries.count_orders(session, str(cid), status="pending"),
            "orders_in_transit": await db_queries.count_orders(session, str(cid), status="in_transit"),
            "payments_overdue_count": await db_queries.count_payments(session, str(cid), status="overdue"),
            "payments_overdue_value": await db_queries.sum_overdue_payments(session, str(cid)),
            "incidents_7d": await db_queries.count_incidents(session, str(cid), days=7),
        }

        # LLM or fallback
        brief_text = await self.llm.generate(
            system="Bạn là RiskCast AI. Viết morning brief ngắn gọn, data-driven.",
            user_message=(
                "Tạo bản tóm tắt rủi ro sáng nay. Tiếng Việt, chuyên nghiệp.\n"
                f"Metrics: {json.dumps(metrics, ensure_ascii=False)}\n"
                f"Signals: {len(actionable)} signals found"
            ),
            model="claude-sonnet-4-20250514",
            max_tokens=500,
        )

        if not brief_text:
            brief_text = self._fallback_brief(metrics, actionable)

        priority_items = [
            {
                "signal_id": str(s.id),
                "signal_type": s.signal_type,
                "severity_score": float(s.severity_score or 0),
                "confidence": float(s.confidence),
                "summary": f"{s.signal_type}: severity {float(s.severity_score or 0):.0f}",
            }
            for s in actionable
        ]

        # Save
        brief = MorningBrief(
            company_id=cid,
            brief_date=date.today(),
            content=brief_text,
            signals_used=priority_items,
            priority_items=priority_items,
        )
        session.add(brief)
        await session.flush()

        result = {
            "id": str(brief.id),
            "brief_date": str(date.today()),
            "content": brief_text,
            "priority_items": priority_items,
        }

        if self.sse_manager:
            await self.sse_manager.broadcast(str(cid), {
                "type": "morning_brief",
                "brief_id": str(brief.id),
                "preview": brief_text[:150],
            })

        return result

    def _fallback_brief(self, metrics, signals):
        today = date.today().strftime("%d/%m/%Y")
        parts = [f"Báo cáo rủi ro ngày {today}."]
        parts.append(f"{metrics['orders_pending']} đơn chờ xử lý, {metrics['orders_in_transit']} đang vận chuyển.")
        if metrics["payments_overdue_count"] > 0:
            parts.append(f"{metrics['payments_overdue_count']} khoản quá hạn.")
        if signals:
            parts.append(f"{len(signals)} cảnh báo cần chú ý.")
        return " ".join(parts)
