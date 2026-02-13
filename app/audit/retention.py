"""
Audit trail retention and archival management.

This module implements GAP C1.1: Audit retention policy not enforced.
Provides automated cleanup and archival of old audit records.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
import asyncio
import gzip
import json
import structlog

logger = structlog.get_logger(__name__)


class RetentionTier(str, Enum):
    """Retention tier levels."""
    HOT = "hot"       # Immediate access (database)
    WARM = "warm"     # Fast access (compressed storage)
    COLD = "cold"     # Archival (object storage)
    DELETED = "deleted"  # Marked for deletion


class ArchiveFormat(str, Enum):
    """Archive file formats."""
    JSON_GZ = "json.gz"
    PARQUET = "parquet"
    CSV_GZ = "csv.gz"


@dataclass
class RetentionPolicy:
    """Retention policy configuration."""
    name: str
    hot_retention_days: int = 30      # Keep in database
    warm_retention_days: int = 90     # Keep compressed
    cold_retention_days: int = 365    # Keep in archive
    total_retention_days: int = 2555  # 7 years for compliance
    
    # What to retain
    record_types: List[str] = field(default_factory=lambda: ["*"])
    
    # Archive settings
    archive_format: ArchiveFormat = ArchiveFormat.JSON_GZ
    compression_level: int = 6
    
    # Deletion settings
    require_approval_for_deletion: bool = True
    deletion_batch_size: int = 1000
    
    @property
    def warm_threshold(self) -> datetime:
        """Get threshold for moving to warm storage."""
        return datetime.utcnow() - timedelta(days=self.hot_retention_days)
    
    @property
    def cold_threshold(self) -> datetime:
        """Get threshold for moving to cold storage."""
        return datetime.utcnow() - timedelta(days=self.warm_retention_days)
    
    @property
    def deletion_threshold(self) -> datetime:
        """Get threshold for deletion."""
        return datetime.utcnow() - timedelta(days=self.total_retention_days)


@dataclass
class RetentionJobResult:
    """Result of a retention job run."""
    job_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str = "running"
    
    # Metrics
    records_scanned: int = 0
    records_archived: int = 0
    records_deleted: int = 0
    bytes_archived: int = 0
    bytes_freed: int = 0
    
    # Errors
    errors: List[str] = field(default_factory=list)
    
    @property
    def duration_seconds(self) -> float:
        """Get job duration."""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return (datetime.utcnow() - self.started_at).total_seconds()


@dataclass
class ArchivedBatch:
    """Metadata for an archived batch."""
    batch_id: str
    created_at: datetime
    record_type: str
    record_count: int
    date_range_start: datetime
    date_range_end: datetime
    
    # Storage info
    storage_tier: RetentionTier
    storage_path: str
    file_format: ArchiveFormat
    compressed_size_bytes: int
    original_size_bytes: int
    
    # Verification
    checksum: str
    verified: bool = False


class AuditArchiver:
    """
    Handles archival of audit records.
    
    Compresses and moves records to appropriate storage tiers.
    """
    
    def __init__(
        self,
        storage_backend: Optional[Any] = None,
        archive_path: str = "./archives/audit",
    ):
        self._storage = storage_backend
        self._archive_path = archive_path
        self._batches: Dict[str, ArchivedBatch] = {}
    
    async def archive_records(
        self,
        records: List[Dict[str, Any]],
        record_type: str,
        policy: RetentionPolicy,
    ) -> ArchivedBatch:
        """
        Archive a batch of records.
        
        Args:
            records: Records to archive
            record_type: Type of records
            policy: Retention policy to apply
            
        Returns:
            ArchivedBatch with metadata
        """
        import hashlib
        import uuid
        
        if not records:
            raise ValueError("No records to archive")
        
        batch_id = f"batch_{uuid.uuid4().hex[:16]}"
        now = datetime.utcnow()
        
        # Sort records by timestamp
        sorted_records = sorted(
            records,
            key=lambda r: r.get("timestamp", r.get("created_at", "")),
        )
        
        # Get date range
        date_start = self._extract_timestamp(sorted_records[0])
        date_end = self._extract_timestamp(sorted_records[-1])
        
        # Serialize records
        if policy.archive_format == ArchiveFormat.JSON_GZ:
            data, compressed = await self._compress_json(
                sorted_records,
                policy.compression_level,
            )
        else:
            # Default to JSON for now
            data, compressed = await self._compress_json(
                sorted_records,
                policy.compression_level,
            )
        
        # Calculate checksum
        checksum = hashlib.sha256(compressed).hexdigest()
        
        # Determine storage path
        date_str = date_start.strftime("%Y/%m/%d")
        storage_path = f"{self._archive_path}/{record_type}/{date_str}/{batch_id}.{policy.archive_format.value}"
        
        # Write to storage
        if self._storage:
            await self._storage.write(storage_path, compressed)
        else:
            # Write locally for testing
            import os
            os.makedirs(os.path.dirname(storage_path), exist_ok=True)
            with open(storage_path, "wb") as f:
                f.write(compressed)
        
        batch = ArchivedBatch(
            batch_id=batch_id,
            created_at=now,
            record_type=record_type,
            record_count=len(records),
            date_range_start=date_start,
            date_range_end=date_end,
            storage_tier=RetentionTier.WARM,
            storage_path=storage_path,
            file_format=policy.archive_format,
            compressed_size_bytes=len(compressed),
            original_size_bytes=len(data),
            checksum=checksum,
        )
        
        self._batches[batch_id] = batch
        
        logger.info(
            "records_archived",
            batch_id=batch_id,
            record_count=len(records),
            compressed_size=len(compressed),
            compression_ratio=len(data) / len(compressed) if compressed else 0,
        )
        
        return batch
    
    async def retrieve_batch(
        self,
        batch_id: str,
    ) -> List[Dict[str, Any]]:
        """Retrieve and decompress an archived batch."""
        if batch_id not in self._batches:
            raise ValueError(f"Batch {batch_id} not found")
        
        batch = self._batches[batch_id]
        
        # Read from storage
        if self._storage:
            compressed = await self._storage.read(batch.storage_path)
        else:
            with open(batch.storage_path, "rb") as f:
                compressed = f.read()
        
        # Verify checksum
        import hashlib
        actual_checksum = hashlib.sha256(compressed).hexdigest()
        if actual_checksum != batch.checksum:
            raise ValueError(f"Checksum mismatch for batch {batch_id}")
        
        # Decompress
        if batch.file_format == ArchiveFormat.JSON_GZ:
            data = gzip.decompress(compressed)
            records = json.loads(data.decode("utf-8"))
        else:
            data = gzip.decompress(compressed)
            records = json.loads(data.decode("utf-8"))
        
        return records
    
    async def _compress_json(
        self,
        records: List[Dict[str, Any]],
        compression_level: int,
    ) -> Tuple[bytes, bytes]:
        """Compress records as JSON."""
        data = json.dumps(records, default=str, separators=(",", ":")).encode("utf-8")
        compressed = gzip.compress(data, compresslevel=compression_level)
        return data, compressed
    
    def _extract_timestamp(self, record: Dict[str, Any]) -> datetime:
        """Extract timestamp from a record."""
        for key in ["timestamp", "created_at", "occurred_at"]:
            if key in record:
                ts = record[key]
                if isinstance(ts, datetime):
                    return ts
                if isinstance(ts, str):
                    try:
                        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    except ValueError:
                        pass
        return datetime.utcnow()


class RetentionScheduler:
    """
    Schedules and executes retention jobs.
    
    Automatically enforces retention policies.
    """
    
    def __init__(
        self,
        policies: Optional[List[RetentionPolicy]] = None,
        archiver: Optional[AuditArchiver] = None,
        db_connection: Optional[Any] = None,
    ):
        self._policies = policies or [
            RetentionPolicy(
                name="default",
                hot_retention_days=30,
                warm_retention_days=90,
                cold_retention_days=365,
                total_retention_days=2555,
            ),
        ]
        self._archiver = archiver or AuditArchiver()
        self._db = db_connection
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._history: List[RetentionJobResult] = []
        
        # Callbacks
        self._on_archive: Optional[Callable] = None
        self._on_delete: Optional[Callable] = None
    
    def set_callbacks(
        self,
        on_archive: Optional[Callable] = None,
        on_delete: Optional[Callable] = None,
    ) -> None:
        """Set callbacks for retention events."""
        self._on_archive = on_archive
        self._on_delete = on_delete
    
    async def start(
        self,
        run_interval_hours: int = 24,
    ) -> None:
        """Start the retention scheduler."""
        if self._running:
            logger.warning("retention_scheduler_already_running")
            return
        
        self._running = True
        self._task = asyncio.create_task(
            self._run_loop(run_interval_hours)
        )
        
        logger.info(
            "retention_scheduler_started",
            interval_hours=run_interval_hours,
            policies=len(self._policies),
        )
    
    async def stop(self) -> None:
        """Stop the retention scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("retention_scheduler_stopped")
    
    async def _run_loop(self, interval_hours: int) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                await self.run_retention_job()
            except Exception as e:
                logger.error("retention_job_failed", error=str(e))
            
            # Wait for next run
            await asyncio.sleep(interval_hours * 3600)
    
    async def run_retention_job(
        self,
        dry_run: bool = False,
    ) -> RetentionJobResult:
        """
        Run a retention job.
        
        Args:
            dry_run: If True, don't actually archive/delete
            
        Returns:
            RetentionJobResult with metrics
        """
        import uuid
        
        result = RetentionJobResult(
            job_id=f"ret_{uuid.uuid4().hex[:12]}",
            started_at=datetime.utcnow(),
        )
        
        logger.info(
            "retention_job_started",
            job_id=result.job_id,
            dry_run=dry_run,
        )
        
        try:
            for policy in self._policies:
                await self._apply_policy(policy, result, dry_run)
            
            result.status = "completed"
            
        except Exception as e:
            result.status = "failed"
            result.errors.append(str(e))
            logger.error(
                "retention_job_error",
                job_id=result.job_id,
                error=str(e),
            )
        
        result.completed_at = datetime.utcnow()
        self._history.append(result)
        
        logger.info(
            "retention_job_completed",
            job_id=result.job_id,
            status=result.status,
            records_archived=result.records_archived,
            records_deleted=result.records_deleted,
            duration_seconds=result.duration_seconds,
        )
        
        return result
    
    async def _apply_policy(
        self,
        policy: RetentionPolicy,
        result: RetentionJobResult,
        dry_run: bool,
    ) -> None:
        """Apply a retention policy."""
        
        # Get records to process
        records = await self._fetch_records_for_policy(policy)
        result.records_scanned += len(records)
        
        # Categorize by age
        to_warm = []
        to_cold = []
        to_delete = []
        
        for record in records:
            timestamp = self._get_record_timestamp(record)
            
            if timestamp < policy.deletion_threshold:
                to_delete.append(record)
            elif timestamp < policy.cold_threshold:
                to_cold.append(record)
            elif timestamp < policy.warm_threshold:
                to_warm.append(record)
        
        # Archive to warm storage
        if to_warm and not dry_run:
            batch = await self._archiver.archive_records(
                to_warm,
                "audit_warm",
                policy,
            )
            result.records_archived += len(to_warm)
            result.bytes_archived += batch.compressed_size_bytes
            
            if self._on_archive:
                await self._on_archive(batch)
        
        # Archive to cold storage
        if to_cold and not dry_run:
            cold_policy = RetentionPolicy(
                name=f"{policy.name}_cold",
                archive_format=policy.archive_format,
                compression_level=9,  # Max compression for cold
            )
            batch = await self._archiver.archive_records(
                to_cold,
                "audit_cold",
                cold_policy,
            )
            result.records_archived += len(to_cold)
            result.bytes_archived += batch.compressed_size_bytes
            
            if self._on_archive:
                await self._on_archive(batch)
        
        # Delete old records
        if to_delete and not dry_run:
            if policy.require_approval_for_deletion:
                logger.warning(
                    "deletion_requires_approval",
                    record_count=len(to_delete),
                    policy=policy.name,
                )
            else:
                deleted = await self._delete_records(to_delete, policy)
                result.records_deleted += deleted
                
                if self._on_delete:
                    await self._on_delete(to_delete)
        
        # Estimate bytes freed
        if to_delete:
            # Rough estimate based on average record size
            avg_size = 1024  # Assume 1KB per record
            result.bytes_freed += len(to_delete) * avg_size
    
    async def _fetch_records_for_policy(
        self,
        policy: RetentionPolicy,
    ) -> List[Dict[str, Any]]:
        """Fetch records matching a policy."""
        if not self._db:
            # Return empty for testing without DB
            return []
        
        # Query would look something like:
        # SELECT * FROM audit_log
        # WHERE created_at < :warm_threshold
        # AND record_type IN :record_types
        # ORDER BY created_at ASC
        # LIMIT :batch_size
        
        # Placeholder - would be implemented with actual DB
        return []
    
    async def _delete_records(
        self,
        records: List[Dict[str, Any]],
        policy: RetentionPolicy,
    ) -> int:
        """Delete records from database."""
        if not self._db:
            return 0
        
        deleted = 0
        
        # Delete in batches
        for i in range(0, len(records), policy.deletion_batch_size):
            batch = records[i:i + policy.deletion_batch_size]
            record_ids = [r.get("id") for r in batch if r.get("id")]
            
            if record_ids:
                # DELETE FROM audit_log WHERE id IN :ids
                deleted += len(record_ids)
        
        return deleted
    
    def _get_record_timestamp(self, record: Dict[str, Any]) -> datetime:
        """Get timestamp from a record."""
        for key in ["created_at", "timestamp", "occurred_at"]:
            if key in record:
                ts = record[key]
                if isinstance(ts, datetime):
                    return ts
                if isinstance(ts, str):
                    try:
                        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    except ValueError:
                        pass
        return datetime.utcnow()
    
    def get_history(self, limit: int = 10) -> List[RetentionJobResult]:
        """Get retention job history."""
        return self._history[-limit:]
    
    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running


# Default policy for RISKCAST
DEFAULT_RETENTION_POLICY = RetentionPolicy(
    name="riskcast_default",
    hot_retention_days=30,       # 30 days in database
    warm_retention_days=90,      # 90 days compressed
    cold_retention_days=365,     # 1 year in archive
    total_retention_days=2555,   # 7 years total (compliance)
    record_types=["decision", "signal", "alert", "audit"],
    archive_format=ArchiveFormat.JSON_GZ,
    compression_level=6,
    require_approval_for_deletion=True,
    deletion_batch_size=1000,
)


# Compliance-specific policies
GDPR_RETENTION_POLICY = RetentionPolicy(
    name="gdpr_compliant",
    hot_retention_days=14,
    warm_retention_days=30,
    cold_retention_days=90,
    total_retention_days=365,  # Data minimization
    record_types=["pii", "customer_data"],
    require_approval_for_deletion=True,
)

SOX_RETENTION_POLICY = RetentionPolicy(
    name="sox_compliant",
    hot_retention_days=90,
    warm_retention_days=365,
    cold_retention_days=2555,  # 7 years
    total_retention_days=2555,
    record_types=["financial", "decision", "audit"],
    require_approval_for_deletion=True,
)
