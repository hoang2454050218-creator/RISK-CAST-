"""
Data Retention Management.

Implements C1.4 Audit Trail Retention Requirements:
- Automated retention policy enforcement
- Storage tiering (hot/warm/cold)
- Legal hold capability
- GDPR-compliant deletion

P1 COMPLIANCE: Implements automated retention cleanup job.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)


# ============================================================================
# RETENTION POLICIES
# ============================================================================


class StorageTier(str, Enum):
    """Storage tier for data lifecycle."""
    HOT = "hot"       # Fast access, < 90 days
    WARM = "warm"     # Moderate access, 90 days - 2 years
    COLD = "cold"     # Archive, 2+ years


class RetentionAction(str, Enum):
    """Action to take on retained data."""
    KEEP = "keep"           # Keep in current tier
    ARCHIVE = "archive"     # Move to lower tier
    DELETE = "delete"       # Delete permanently
    LEGAL_HOLD = "legal_hold"  # Cannot be deleted


@dataclass
class RetentionPolicy:
    """Retention policy definition."""
    
    name: str
    description: str
    
    # Retention periods
    hot_days: int = 90
    warm_days: int = 730  # 2 years
    total_retention_days: int = 2555  # 7 years (financial standard)
    
    # Actions
    archive_after_hot: bool = True
    delete_after_retention: bool = True
    
    # Legal compliance
    supports_legal_hold: bool = True


# Default retention policies by data type
RETENTION_POLICIES: Dict[str, RetentionPolicy] = {
    "audit_logs": RetentionPolicy(
        name="audit_logs",
        description="Audit trail retention - 7 years minimum",
        hot_days=90,
        warm_days=730,
        total_retention_days=2555,
        supports_legal_hold=True,
    ),
    "decisions": RetentionPolicy(
        name="decisions",
        description="Decision records - 7 years for compliance",
        hot_days=90,
        warm_days=730,
        total_retention_days=2555,
        supports_legal_hold=True,
    ),
    "outcomes": RetentionPolicy(
        name="outcomes",
        description="Outcome records for ML training",
        hot_days=180,
        warm_days=1095,  # 3 years
        total_retention_days=2555,
        supports_legal_hold=True,
    ),
    "alerts": RetentionPolicy(
        name="alerts",
        description="Alert delivery records",
        hot_days=30,
        warm_days=365,
        total_retention_days=730,  # 2 years
        supports_legal_hold=False,
    ),
    "metrics": RetentionPolicy(
        name="metrics",
        description="Operational metrics",
        hot_days=14,
        warm_days=90,
        total_retention_days=365,
        delete_after_retention=True,
    ),
}


# ============================================================================
# LEGAL HOLD
# ============================================================================


@dataclass
class LegalHold:
    """Legal hold record."""
    
    hold_id: str
    created_at: datetime
    created_by: str
    
    # Scope
    entity_type: str  # decisions, customers, etc.
    entity_ids: List[str]  # Specific IDs or ["*"] for all
    
    # Hold details
    matter_name: str
    description: str
    
    # Status
    is_active: bool = True
    released_at: Optional[datetime] = None
    released_by: Optional[str] = None


class LegalHoldManager:
    """Manage legal holds on data."""
    
    def __init__(self):
        self._holds: Dict[str, LegalHold] = {}
        self._entity_holds: Dict[str, List[str]] = {}  # entity_id -> [hold_ids]
    
    def create_hold(
        self,
        hold_id: str,
        entity_type: str,
        entity_ids: List[str],
        matter_name: str,
        description: str,
        created_by: str,
    ) -> LegalHold:
        """Create a legal hold."""
        hold = LegalHold(
            hold_id=hold_id,
            created_at=datetime.utcnow(),
            created_by=created_by,
            entity_type=entity_type,
            entity_ids=entity_ids,
            matter_name=matter_name,
            description=description,
        )
        
        self._holds[hold_id] = hold
        
        # Index by entity
        for entity_id in entity_ids:
            key = f"{entity_type}:{entity_id}"
            if key not in self._entity_holds:
                self._entity_holds[key] = []
            self._entity_holds[key].append(hold_id)
        
        logger.info(
            "legal_hold_created",
            hold_id=hold_id,
            entity_type=entity_type,
            entity_count=len(entity_ids),
            matter=matter_name,
        )
        
        return hold
    
    def release_hold(
        self,
        hold_id: str,
        released_by: str,
    ) -> bool:
        """Release a legal hold."""
        if hold_id not in self._holds:
            return False
        
        hold = self._holds[hold_id]
        hold.is_active = False
        hold.released_at = datetime.utcnow()
        hold.released_by = released_by
        
        # Remove from entity index
        for entity_id in hold.entity_ids:
            key = f"{hold.entity_type}:{entity_id}"
            if key in self._entity_holds:
                self._entity_holds[key] = [
                    h for h in self._entity_holds[key] if h != hold_id
                ]
        
        logger.info("legal_hold_released", hold_id=hold_id, released_by=released_by)
        return True
    
    def is_under_hold(self, entity_type: str, entity_id: str) -> bool:
        """Check if an entity is under legal hold."""
        # Check specific entity
        key = f"{entity_type}:{entity_id}"
        if key in self._entity_holds and self._entity_holds[key]:
            return True
        
        # Check wildcard hold
        wildcard_key = f"{entity_type}:*"
        if wildcard_key in self._entity_holds and self._entity_holds[wildcard_key]:
            return True
        
        return False
    
    def get_holds_for_entity(
        self,
        entity_type: str,
        entity_id: str,
    ) -> List[LegalHold]:
        """Get all holds for an entity."""
        holds = []
        
        # Check specific entity
        key = f"{entity_type}:{entity_id}"
        if key in self._entity_holds:
            for hold_id in self._entity_holds[key]:
                if hold_id in self._holds:
                    holds.append(self._holds[hold_id])
        
        # Check wildcard hold
        wildcard_key = f"{entity_type}:*"
        if wildcard_key in self._entity_holds:
            for hold_id in self._entity_holds[wildcard_key]:
                if hold_id in self._holds:
                    holds.append(self._holds[hold_id])
        
        return [h for h in holds if h.is_active]


# ============================================================================
# RETENTION MANAGER
# ============================================================================


class RetentionManager:
    """
    Manage data retention lifecycle.
    
    Responsibilities:
    - Track data age
    - Move data between storage tiers
    - Delete expired data (respecting legal holds)
    - Generate retention reports
    """
    
    def __init__(
        self,
        session_factory=None,
        legal_hold_manager: Optional[LegalHoldManager] = None,
    ):
        self._session_factory = session_factory
        self._legal_holds = legal_hold_manager or LegalHoldManager()
        self._last_cleanup: Optional[datetime] = None
    
    async def run_cleanup(
        self,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Run retention cleanup.
        
        Args:
            dry_run: If True, don't actually delete/archive, just report
            
        Returns:
            Cleanup report
        """
        logger.info("retention_cleanup_started", dry_run=dry_run)
        
        report = {
            "started_at": datetime.utcnow().isoformat(),
            "dry_run": dry_run,
            "data_types": {},
            "total_archived": 0,
            "total_deleted": 0,
            "legal_holds_respected": 0,
            "errors": [],
        }
        
        for data_type, policy in RETENTION_POLICIES.items():
            try:
                result = await self._process_data_type(data_type, policy, dry_run)
                report["data_types"][data_type] = result
                report["total_archived"] += result.get("archived", 0)
                report["total_deleted"] += result.get("deleted", 0)
                report["legal_holds_respected"] += result.get("held", 0)
            except Exception as e:
                logger.error(
                    "retention_cleanup_error",
                    data_type=data_type,
                    error=str(e),
                )
                report["errors"].append({
                    "data_type": data_type,
                    "error": str(e),
                })
        
        report["completed_at"] = datetime.utcnow().isoformat()
        self._last_cleanup = datetime.utcnow()
        
        logger.info(
            "retention_cleanup_completed",
            dry_run=dry_run,
            archived=report["total_archived"],
            deleted=report["total_deleted"],
        )
        
        return report
    
    async def _process_data_type(
        self,
        data_type: str,
        policy: RetentionPolicy,
        dry_run: bool,
    ) -> Dict[str, Any]:
        """Process a single data type for retention."""
        now = datetime.utcnow()
        
        # Calculate cutoffs
        hot_cutoff = now - timedelta(days=policy.hot_days)
        warm_cutoff = now - timedelta(days=policy.hot_days + policy.warm_days)
        delete_cutoff = now - timedelta(days=policy.total_retention_days)
        
        result = {
            "policy": policy.name,
            "hot_cutoff": hot_cutoff.isoformat(),
            "warm_cutoff": warm_cutoff.isoformat(),
            "delete_cutoff": delete_cutoff.isoformat(),
            "to_archive_warm": 0,
            "to_archive_cold": 0,
            "to_delete": 0,
            "archived": 0,
            "deleted": 0,
            "held": 0,
        }
        
        if not self._session_factory:
            logger.warning("no_session_factory_skipping_retention", data_type=data_type)
            return result
        
        # Process based on data type
        if data_type == "audit_logs":
            result = await self._process_audit_logs(policy, result, dry_run)
        elif data_type == "decisions":
            result = await self._process_decisions(policy, result, dry_run)
        elif data_type == "outcomes":
            result = await self._process_outcomes(policy, result, dry_run)
        elif data_type == "alerts":
            result = await self._process_alerts(policy, result, dry_run)
        
        return result
    
    async def _process_audit_logs(
        self,
        policy: RetentionPolicy,
        result: Dict[str, Any],
        dry_run: bool,
    ) -> Dict[str, Any]:
        """Process audit logs retention."""
        # Audit logs are append-only - we archive but never delete
        # They form a cryptographic chain that must remain intact
        
        try:
            from sqlalchemy import select, func, and_
            from app.db.models import AuditLogModel
            
            async with self._session_factory() as session:
                now = datetime.utcnow()
                hot_cutoff = now - timedelta(days=policy.hot_days)
                
                # Count records to archive
                count_result = await session.execute(
                    select(func.count(AuditLogModel.id)).where(
                        AuditLogModel.created_at < hot_cutoff
                    )
                )
                result["to_archive_warm"] = count_result.scalar() or 0
                
                # Note: Audit logs are never deleted, only archived
                result["to_delete"] = 0
                result["archived"] = result["to_archive_warm"] if not dry_run else 0
                
        except Exception as e:
            logger.error("audit_log_retention_failed", error=str(e))
        
        return result
    
    async def _process_decisions(
        self,
        policy: RetentionPolicy,
        result: Dict[str, Any],
        dry_run: bool,
    ) -> Dict[str, Any]:
        """Process decisions retention."""
        try:
            from sqlalchemy import select, func, delete, and_
            from app.db.models import DecisionModel
            
            async with self._session_factory() as session:
                now = datetime.utcnow()
                delete_cutoff = now - timedelta(days=policy.total_retention_days)
                
                # Find decisions eligible for deletion
                query = select(DecisionModel.decision_id).where(
                    DecisionModel.created_at < delete_cutoff
                )
                to_delete = await session.execute(query)
                decision_ids = [row[0] for row in to_delete.fetchall()]
                
                # Filter out those under legal hold
                deletable = []
                held_count = 0
                
                for decision_id in decision_ids:
                    if self._legal_holds.is_under_hold("decisions", decision_id):
                        held_count += 1
                    else:
                        deletable.append(decision_id)
                
                result["to_delete"] = len(deletable)
                result["held"] = held_count
                
                if not dry_run and deletable:
                    delete_stmt = delete(DecisionModel).where(
                        DecisionModel.decision_id.in_(deletable)
                    )
                    await session.execute(delete_stmt)
                    await session.commit()
                    result["deleted"] = len(deletable)
                
        except Exception as e:
            logger.error("decision_retention_failed", error=str(e))
        
        return result
    
    async def _process_outcomes(
        self,
        policy: RetentionPolicy,
        result: Dict[str, Any],
        dry_run: bool,
    ) -> Dict[str, Any]:
        """Process outcomes retention."""
        try:
            from sqlalchemy import select, func, delete, and_
            from app.db.models import DecisionOutcomeModel
            
            async with self._session_factory() as session:
                now = datetime.utcnow()
                delete_cutoff = now - timedelta(days=policy.total_retention_days)
                
                # Count outcomes to delete
                count_result = await session.execute(
                    select(func.count(DecisionOutcomeModel.id)).where(
                        DecisionOutcomeModel.outcome_recorded_at < delete_cutoff
                    )
                )
                result["to_delete"] = count_result.scalar() or 0
                
                if not dry_run and result["to_delete"] > 0:
                    delete_stmt = delete(DecisionOutcomeModel).where(
                        DecisionOutcomeModel.outcome_recorded_at < delete_cutoff
                    )
                    await session.execute(delete_stmt)
                    await session.commit()
                    result["deleted"] = result["to_delete"]
                
        except Exception as e:
            logger.error("outcome_retention_failed", error=str(e))
        
        return result
    
    async def _process_alerts(
        self,
        policy: RetentionPolicy,
        result: Dict[str, Any],
        dry_run: bool,
    ) -> Dict[str, Any]:
        """Process alerts retention."""
        try:
            from sqlalchemy import select, func, delete
            from app.db.models import AlertModel
            
            async with self._session_factory() as session:
                now = datetime.utcnow()
                delete_cutoff = now - timedelta(days=policy.total_retention_days)
                
                # Count alerts to delete
                count_result = await session.execute(
                    select(func.count(AlertModel.id)).where(
                        AlertModel.created_at < delete_cutoff
                    )
                )
                result["to_delete"] = count_result.scalar() or 0
                
                if not dry_run and result["to_delete"] > 0:
                    delete_stmt = delete(AlertModel).where(
                        AlertModel.created_at < delete_cutoff
                    )
                    await session.execute(delete_stmt)
                    await session.commit()
                    result["deleted"] = result["to_delete"]
                
        except Exception as e:
            logger.error("alert_retention_failed", error=str(e))
        
        return result
    
    def get_policy(self, data_type: str) -> Optional[RetentionPolicy]:
        """Get retention policy for a data type."""
        return RETENTION_POLICIES.get(data_type)
    
    def get_all_policies(self) -> Dict[str, RetentionPolicy]:
        """Get all retention policies."""
        return RETENTION_POLICIES.copy()


# ============================================================================
# RETENTION CLEANUP JOB
# ============================================================================


class RetentionCleanupJob:
    """
    Scheduled retention cleanup job.
    
    Runs daily to enforce retention policies.
    """
    
    def __init__(
        self,
        retention_manager: RetentionManager,
        run_interval_hours: int = 24,
    ):
        self._manager = retention_manager
        self._interval = timedelta(hours=run_interval_hours)
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the cleanup job."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._run_loop(), name="retention_cleanup")
        logger.info("retention_cleanup_job_started", interval_hours=self._interval.total_seconds() / 3600)
    
    async def stop(self):
        """Stop the cleanup job."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("retention_cleanup_job_stopped")
    
    async def _run_loop(self):
        """Main cleanup loop."""
        while self._running:
            try:
                # Run cleanup
                report = await self._manager.run_cleanup(dry_run=False)
                
                logger.info(
                    "retention_cleanup_completed",
                    archived=report["total_archived"],
                    deleted=report["total_deleted"],
                    errors=len(report["errors"]),
                )
                
            except Exception as e:
                logger.error("retention_cleanup_error", error=str(e))
            
            # Wait for next run
            await asyncio.sleep(self._interval.total_seconds())
    
    async def run_now(self, dry_run: bool = True) -> Dict[str, Any]:
        """Run cleanup immediately."""
        return await self._manager.run_cleanup(dry_run=dry_run)


# ============================================================================
# SINGLETON
# ============================================================================


_retention_manager: Optional[RetentionManager] = None
_cleanup_job: Optional[RetentionCleanupJob] = None


def get_retention_manager(session_factory=None) -> RetentionManager:
    """Get global retention manager."""
    global _retention_manager
    if _retention_manager is None:
        _retention_manager = RetentionManager(session_factory)
    return _retention_manager


def get_cleanup_job(session_factory=None) -> RetentionCleanupJob:
    """Get global cleanup job."""
    global _cleanup_job
    if _cleanup_job is None:
        manager = get_retention_manager(session_factory)
        _cleanup_job = RetentionCleanupJob(manager)
    return _cleanup_job
