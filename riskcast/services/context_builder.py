"""
Context Builder — The intelligence pipeline behind every chat message.

Pipeline: Query → Intent (regex→Haiku) → Data + Signals → Compress → Prompt

Intent classification:
- Regex fast path for obvious patterns (free, instant)
- Claude Haiku fallback when regex misses (~$0.0001/req, ~200ms)
"""

import json
import re

import structlog
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.db import queries as db_queries
from riskcast.services.llm_gateway import LLMGateway
from riskcast.services.omen_client import OmenClient

logger = structlog.get_logger(__name__)


class ChatContext(BaseModel):
    """Built context ready for the LLM prompt."""

    system_prompt: str
    data_summary: dict
    signals_summary: list[dict]
    intent: dict
    token_estimate: int


# Regex fast path — obvious patterns
INTENT_PATTERNS = [
    (r"(?:đơn\s*(?:hàng)?|order|ĐH)\s*#?\s*([A-Za-z0-9\-]+)", "order_risk_check"),
    (r"(?:tuần\s*này|weekly|tổng\s*quan|overview)", "weekly_overview"),
    (r"(?:khách\s*(?:hàng)?|customer)\s+(.+?)(?:\s+thế\s+nào|\?|$)", "customer_inquiry"),
    (r"(?:tuyến|route)\s+(.+?)(?:\s+thế\s+nào|\?|$)", "route_inquiry"),
    (r"(?:thanh\s*toán|payment|nợ|overdue)", "payment_overview"),
    (r"(?:nên\s+(?:làm|chú\s*ý|xem)|recommend)", "recommendation"),
    (r"(?:trước\s*đây|lịch\s*sử|giống|similar)", "historical_lookup"),
    (r"(?:brief|tóm\s*tắt\s*sáng|sáng\s*nay)", "morning_brief"),
]

# Intent types that don't require an extracted entity
NO_ENTITY_INTENTS = frozenset({
    "weekly_overview", "payment_overview", "recommendation", "morning_brief",
})


class ContextBuilder:
    """
    Builds LLM context from user query + company data + signals.

    Pipeline: classify intent → retrieve data → enrich with signals → build prompt
    """

    MAX_CONTEXT_TOKENS = 6000

    def __init__(
        self,
        llm: LLMGateway,
        omen_client: OmenClient,
    ):
        self.llm = llm
        self.omen_client = omen_client

    async def build(
        self,
        session: AsyncSession,
        company_id: str,
        user_query: str,
        session_history: list[dict],
    ) -> ChatContext:
        """Build full context for a chat response."""

        # Step 1: Classify intent
        intent = await self._classify_intent(user_query)

        # Step 2: Retrieve relevant data
        data = await self._retrieve_data(session, company_id, intent, user_query)

        # Step 3: Get active signals
        signals = await self._get_signals(session, company_id, intent)

        # Step 4: Company + appetite context
        company = await db_queries.get_company(session, company_id)
        appetite = await db_queries.get_risk_appetite(session, company_id)

        # Step 5: Build system prompt
        prompt = self._build_prompt(
            company, appetite, data, signals, user_query, session_history[-5:]
        )

        return ChatContext(
            system_prompt=prompt,
            data_summary=data,
            signals_summary=[s if isinstance(s, dict) else s.dict() for s in signals[:10]],
            intent=intent,
            token_estimate=len(prompt) // 4,
        )

    # ── Intent Classification ────────────────────────────────────────

    async def _classify_intent(self, query: str) -> dict:
        """
        Regex fast path → Haiku fallback.

        Regex only accepted when match is clear AND entity is extracted.
        Low threshold for fallback — Haiku is cheap (~$0.0001, ~200ms).
        """
        for pattern, intent_type in INTENT_PATTERNS:
            match = re.search(pattern, query, re.IGNORECASE | re.UNICODE)
            if match:
                groups = match.groups()
                entity = groups[0].strip() if groups else ""
                if entity or intent_type in NO_ENTITY_INTENTS:
                    return {
                        "type": intent_type,
                        "entity": entity,
                        "raw": query,
                        "method": "regex",
                    }

        # Fallback: Claude Haiku
        return await self._haiku_classify(query)

    async def _haiku_classify(self, query: str) -> dict:
        """Use Claude Haiku for intent classification when regex misses."""
        try:
            response = await self.llm.generate(
                system=(
                    "Classify user intent. Return JSON only, no markdown.\n"
                    "Types: order_risk_check, weekly_overview, customer_inquiry, "
                    "route_inquiry, payment_overview, recommendation, "
                    "historical_lookup, morning_brief, general\n"
                    'Format: {"type":"...","entity":"extracted entity name/id or empty",'
                    '"raw":"original query"}'
                ),
                user_message=query,
                model="claude-haiku-4-5-20251001",
                max_tokens=100,
            )
            cleaned = response.strip().strip("`").replace("json\n", "")
            result = json.loads(cleaned)
            result["method"] = "haiku"
            return result
        except Exception as e:
            logger.warning("haiku_classify_failed", error=str(e))
            return {"type": "general", "entity": "", "raw": query, "method": "fallback"}

    # ── Data Retrieval ───────────────────────────────────────────────

    async def _retrieve_data(
        self, session: AsyncSession, company_id: str, intent: dict, query: str
    ) -> dict:
        """Retrieve data relevant to the classified intent."""
        data: dict = {"_intent_method": intent.get("method", "unknown")}
        t = intent["type"]
        entity = intent.get("entity", "")

        if t == "order_risk_check" and entity:
            data["order"] = await db_queries.find_order(session, company_id, entity)
            if data["order"] and data["order"].get("customer_id"):
                data["customer_summary"] = await db_queries.get_customer_summary(
                    session, company_id, data["order"]["customer_id"]
                )

        elif t in ("weekly_overview", "recommendation"):
            data["orders_7d"] = await db_queries.get_orders_summary(session, company_id, days=7)
            data["payments_overdue"] = await db_queries.get_overdue_payments_summary(session, company_id)
            data["incidents_7d"] = await db_queries.get_incidents_summary(session, company_id, days=7)

        elif t == "customer_inquiry" and entity:
            data["customer"] = await db_queries.find_customer(session, company_id, entity)
            if data["customer"]:
                cid = data["customer"]["id"]
                data["customer_summary"] = await db_queries.get_customer_summary(
                    session, company_id, cid
                )

        elif t == "route_inquiry" and entity:
            data["route"] = await db_queries.find_route(session, company_id, entity)

        elif t == "payment_overview":
            data["overdue"] = await db_queries.get_overdue_payments_summary(session, company_id)

        elif t == "historical_lookup":
            data["similar_incidents"] = await db_queries.search_incidents_fulltext(
                session, company_id, query, limit=5
            )

        elif t == "morning_brief":
            data["brief"] = await db_queries.get_today_brief(session, company_id)

        return data

    # ── Signals ──────────────────────────────────────────────────────

    async def _get_signals(
        self, session: AsyncSession, company_id: str, intent: dict
    ) -> list:
        """Get active signals, enriched with OMEN market data."""
        signals_raw = await db_queries.get_active_signals(session, company_id, limit=10)
        signals = [
            {
                "signal_type": s.signal_type,
                "severity_score": float(s.severity_score) if s.severity_score else 0,
                "confidence": float(s.confidence),
                "evidence": s.evidence,
                "context": s.context,
            }
            for s in signals_raw
        ]

        # OMEN market signals (graceful)
        omen_signals = await self.omen_client.get_signals(min_confidence=0.5, limit=5)
        for os_ in omen_signals:
            signals.append({
                "signal_type": os_.signal_type,
                "severity_score": os_.severity_score,
                "confidence": os_.confidence,
                "evidence": os_.evidence,
                "source": "omen",
            })

        return signals

    # ── Prompt Builder ───────────────────────────────────────────────

    def _build_prompt(
        self, company, appetite, data, signals, user_query, history
    ) -> str:
        company_name = company.name if company else "N/A"
        company_industry = company.industry if company else "N/A"
        company_tz = company.timezone if company else "Asia/Ho_Chi_Minh"

        return f"""Bạn là RiskCast AI — chuyên viên phân tích rủi ro của {company_name}.
Tiếng Việt, chuyên nghiệp, súc tích, data-driven. Phong cách Bloomberg analyst.

## Công ty
- Tên: {company_name} | Ngành: {company_industry} | TZ: {company_tz}

## Risk Appetite
{json.dumps(appetite or {}, ensure_ascii=False, indent=2)}

## Signals
{self._fmt_signals(signals)}

## Dữ liệu
{self._fmt_data(data)}

## Lịch sử chat
{self._fmt_history(history)}

## Quy tắc
1. Trích dẫn số liệu cụ thể khi nhận định
2. Giải thích TẠI SAO dựa trên evidence khi gợi ý hành động
3. KHÔNG BAO GIỜ bịa số liệu — nếu thiếu data thì nói rõ
4. Tôn trọng risk appetite khi khuyến nghị
5. Ghi rõ khi confidence < 0.6
6. Đoạn văn ngắn gọn, không bullet trừ khi liệt kê > 3 items
7. Khi đề xuất hành động, format:
   [SUGGESTION:type] nội dung [/SUGGESTION]
   Types: cancel_order, require_prepayment, split_shipment, delay_shipment, increase_monitoring, contact_customer"""

    def _fmt_signals(self, signals: list) -> str:
        if not signals:
            return "Không có signal."
        lines = []
        for s in signals[:8]:
            d = s if isinstance(s, dict) else vars(s)
            ev = json.dumps(d.get("evidence", {}), ensure_ascii=False)[:200]
            lines.append(
                f"- [{d.get('signal_type')}] sev={d.get('severity_score','?')}, "
                f"conf={d.get('confidence','?')}, evidence: {ev}"
            )
        return "\n".join(lines)

    def _fmt_data(self, data: dict) -> str:
        if not data:
            return "Không có dữ liệu."
        # Remove internal keys
        clean = {k: v for k, v in data.items() if not k.startswith("_")}
        return json.dumps(clean, ensure_ascii=False, default=str)[:3000]

    def _fmt_history(self, history: list[dict]) -> str:
        if not history:
            return "Tin nhắn đầu tiên."
        return "\n".join(
            f"{'User' if m.get('role') == 'user' else 'AI'}: {str(m.get('content', ''))[:200]}"
            for m in history
        )
