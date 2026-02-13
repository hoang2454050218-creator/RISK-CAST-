"""
Signal Scheduler — Runs in a separate container (riskcast-scheduler).

NOT inside the API process. Prevents background jobs from blocking API requests.

Jobs:
1. Full signal scan (every 6 hours) — runs all analyzers per company
2. Expire stale signals (every 1 hour) — deactivate expired signals
"""

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from riskcast.analyzers.order_risk import OrderRiskScorer
from riskcast.analyzers.payment_risk import PaymentRiskAnalyzer
from riskcast.analyzers.route_disruption import RouteDisruptionAnalyzer
from riskcast.db import queries as db_queries
from riskcast.services.llm_gateway import LLMGateway
from riskcast.services.morning_brief import MorningBriefGenerator
from riskcast.services.omen_client import OmenClient
from riskcast.services.signal_service import SignalService

logger = structlog.get_logger(__name__)


class AnalyzerDbAdapter:
    """
    Adapter that wraps db.queries functions with a bound session.

    Analyzers call self.db.get_customers_with_payments(company_id).
    This adapter provides that interface backed by the queries module.
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_customers_with_payments(self, company_id: str):
        return await db_queries.get_customers_with_payments(self._session, company_id)

    async def get_payment_history(self, company_id: str, customer_id: str, days: int = 90):
        return await db_queries.get_payment_history(self._session, company_id, customer_id, days)

    async def get_active_routes(self, company_id: str):
        return await db_queries.get_active_routes(self._session, company_id)

    async def get_route_orders(self, company_id: str, route_id: str, days: int = 14):
        return await db_queries.get_route_orders(self._session, company_id, route_id, days)

    async def get_orders_by_status(self, company_id: str, statuses: list[str]):
        return await db_queries.get_orders_by_status(self._session, company_id, statuses)

    async def get_active_signals_map(self, company_id: str):
        return await db_queries.get_active_signals_map(self._session, company_id)

    async def get_risk_appetite(self, company_id: str):
        return await db_queries.get_risk_appetite(self._session, company_id)


class SignalScheduler:
    """
    Background scheduler for signal scanning.

    Runs in container riskcast-scheduler, NOT in the API process.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker,
        omen_client: OmenClient,
        llm: LLMGateway | None = None,
    ):
        self.session_factory = session_factory
        self.omen_client = omen_client
        self.signal_service = SignalService()
        self.brief_generator = MorningBriefGenerator(llm=llm or LLMGateway())
        self.scheduler = AsyncIOScheduler()

    def start(self):
        """Register and start all scheduled jobs."""
        self.scheduler.add_job(
            self.run_full_scan,
            IntervalTrigger(hours=6),
            id="full_scan",
            max_instances=1,
            replace_existing=True,
        )
        self.scheduler.add_job(
            self.generate_all_briefs,
            CronTrigger(hour=6, minute=0),
            id="morning_brief",
            max_instances=1,
            replace_existing=True,
        )
        self.scheduler.add_job(
            self.expire_signals,
            IntervalTrigger(hours=1),
            id="expire_signals",
            replace_existing=True,
        )
        self.scheduler.start()
        logger.info("signal_scheduler_started")

    def stop(self):
        """Gracefully stop the scheduler."""
        self.scheduler.shutdown(wait=True)
        logger.info("signal_scheduler_stopped")

    async def run_full_scan(self):
        """Scan all companies, run all analyzers, upsert signals."""
        logger.info("full_scan_started")
        async with self.session_factory() as session:
            companies = await db_queries.get_active_companies(session)

        for company in companies:
            try:
                await self._scan_company(str(company.id))
            except Exception as e:
                logger.error(
                    "scan_failed",
                    company_id=str(company.id),
                    error=str(e),
                )

        logger.info("full_scan_completed", companies=len(companies))

    async def _scan_company(self, company_id: str):
        """
        Run all analyzers for a single company.

        Error isolation: if one analyzer fails, others still run.
        Upsert pattern: old signals stay if an analyzer crashes.
        """
        async with self.session_factory() as session:
            db_adapter = AnalyzerDbAdapter(session)

            analyzers = [
                PaymentRiskAnalyzer(db_adapter),
                RouteDisruptionAnalyzer(db_adapter, self.omen_client),
                OrderRiskScorer(db_adapter),
            ]

            all_signals = []

            for analyzer in analyzers:
                try:
                    signals = await analyzer.analyze(company_id)
                    all_signals.extend(signals)
                except Exception as e:
                    logger.error(
                        "analyzer_failed",
                        analyzer=type(analyzer).__name__,
                        company_id=company_id,
                        error=str(e),
                    )
                    # DO NOT stop — continue with next analyzer

            # Upsert all collected signals in one transaction
            upserted = await self.signal_service.upsert_signals(
                session, company_id, all_signals
            )
            await session.commit()

            # ── Auto-trigger scan summary alert ────────────────────
            try:
                critical = sum(1 for s in all_signals if s.severity_score >= 75)
                high = sum(1 for s in all_signals if 50 <= s.severity_score < 75)
                if critical > 0 or high > 0:
                    from riskcast.alerting.auto_trigger import on_scan_completed
                    await on_scan_completed(company_id, upserted, critical, high)
            except Exception as alert_err:
                logger.debug("scan_alert_skip", error=str(alert_err))

            logger.info(
                "company_scan_completed",
                company_id=company_id,
                signals_upserted=upserted,
            )

    async def generate_all_briefs(self):
        """Generate morning briefs for all companies (6AM daily)."""
        logger.info("morning_brief_generation_started")
        async with self.session_factory() as session:
            companies = await db_queries.get_active_companies(session)

        for company in companies:
            try:
                async with self.session_factory() as session:
                    await self.brief_generator.generate(session, str(company.id))
                    await session.commit()
            except Exception as e:
                logger.error(
                    "brief_generation_failed",
                    company_id=str(company.id),
                    error=str(e),
                )

        logger.info("morning_brief_generation_completed", companies=len(companies))

    async def expire_signals(self):
        """Deactivate expired signals across all companies."""
        async with self.session_factory() as session:
            count = await self.signal_service.expire_stale_signals(session)
            await session.commit()
            if count:
                logger.info("stale_signals_expired", count=count)
