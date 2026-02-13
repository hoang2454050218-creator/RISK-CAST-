"""
Audit Repository - Persistent Storage for Audit Records.

Provides database operations for:
- Audit records (with chain integrity)
- Input snapshots
- Processing records

Uses PostgreSQL for durability and ACID guarantees.
The append-only nature of audit records makes this
suitable for compliance requirements.
"""

from datetime import datetime
from typing import Optional, List
import json

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.audit.schemas import (
    AuditEventType,
    AuditRecord,
    InputSnapshot,
    ProcessingRecord,
)

import structlog

logger = structlog.get_logger(__name__)


class AuditRepository:
    """
    Repository for audit data.
    
    Uses PostgreSQL for:
    - Durability (ACID compliance)
    - Atomic operations
    - Efficient range queries
    
    The audit records are append-only - no updates or deletes
    are performed on audit data.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.
        
        Args:
            session: Async SQLAlchemy session
        """
        self._session = session
    
    # =========================================================================
    # AUDIT RECORD OPERATIONS
    # =========================================================================
    
    async def store_record(self, record: AuditRecord) -> None:
        """
        Store an audit record.
        
        This is append-only - records are never updated or deleted.
        """
        from app.db.models import AuditLogModel
        
        model = AuditLogModel(
            event_id=record.audit_id,
            event_type=record.event_type.value,
            entity_type=record.entity_type,
            entity_id=record.entity_id,
            actor_type=record.actor_type,
            actor_id=record.actor_id,
            payload=record.payload,
            payload_hash=record.payload_hash,
            sequence_number=record.sequence_number,
            previous_hash=record.previous_hash,
            record_hash=record.record_hash,
            created_at=record.timestamp,
        )
        
        self._session.add(model)
        await self._session.commit()
        
        logger.debug(
            "audit_record_stored",
            audit_id=record.audit_id,
            sequence=record.sequence_number,
        )
    
    async def get_last_record(self) -> Optional[AuditRecord]:
        """
        Get the most recent audit record.
        
        Used for chain initialization.
        """
        from app.db.models import AuditLogModel
        
        result = await self._session.execute(
            select(AuditLogModel)
            .order_by(AuditLogModel.sequence_number.desc())
            .limit(1)
        )
        model = result.scalar_one_or_none()
        
        if model:
            return self._model_to_record(model)
        return None
    
    async def get_records_range(
        self,
        start_sequence: int,
        end_sequence: Optional[int] = None,
        limit: int = 10000,
    ) -> List[AuditRecord]:
        """
        Get audit records in a sequence range.
        
        Used for chain verification.
        """
        from app.db.models import AuditLogModel
        
        query = (
            select(AuditLogModel)
            .where(AuditLogModel.sequence_number >= start_sequence)
        )
        
        if end_sequence is not None:
            query = query.where(AuditLogModel.sequence_number <= end_sequence)
        
        query = query.order_by(AuditLogModel.sequence_number).limit(limit)
        
        result = await self._session.execute(query)
        return [self._model_to_record(m) for m in result.scalars().all()]
    
    async def get_records_for_entity(
        self,
        entity_type: str,
        entity_id: str,
        limit: int = 100,
    ) -> List[AuditRecord]:
        """
        Get all audit records for a specific entity.
        
        Used for audit trail retrieval.
        """
        from app.db.models import AuditLogModel
        
        result = await self._session.execute(
            select(AuditLogModel)
            .where(
                and_(
                    AuditLogModel.entity_type == entity_type,
                    AuditLogModel.entity_id == entity_id,
                )
            )
            .order_by(AuditLogModel.sequence_number)
            .limit(limit)
        )
        
        return [self._model_to_record(m) for m in result.scalars().all()]
    
    async def get_records_by_event_type(
        self,
        event_type: AuditEventType,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[AuditRecord]:
        """
        Get audit records by event type within a time range.
        """
        from app.db.models import AuditLogModel
        
        query = select(AuditLogModel).where(
            AuditLogModel.event_type == event_type.value
        )
        
        if start_time:
            query = query.where(AuditLogModel.created_at >= start_time)
        if end_time:
            query = query.where(AuditLogModel.created_at <= end_time)
        
        query = query.order_by(AuditLogModel.created_at.desc()).limit(limit)
        
        result = await self._session.execute(query)
        return [self._model_to_record(m) for m in result.scalars().all()]
    
    async def count_records(
        self,
        entity_type: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
    ) -> int:
        """
        Count audit records with optional filters.
        """
        from app.db.models import AuditLogModel
        
        query = select(func.count(AuditLogModel.id))
        
        if entity_type:
            query = query.where(AuditLogModel.entity_type == entity_type)
        if event_type:
            query = query.where(AuditLogModel.event_type == event_type.value)
        
        result = await self._session.execute(query)
        return result.scalar() or 0
    
    # =========================================================================
    # INPUT SNAPSHOT OPERATIONS
    # =========================================================================
    
    async def store_snapshot(self, snapshot: InputSnapshot) -> None:
        """
        Store an input snapshot.
        
        Snapshots are immutable - stored once, never modified.
        """
        from app.db.models import InputSnapshotModel
        
        model = InputSnapshotModel(
            snapshot_id=snapshot.snapshot_id,
            signal_id=snapshot.signal_id,
            signal_data=snapshot.signal_data,
            signal_hash=snapshot.signal_hash,
            reality_data=snapshot.reality_data,
            reality_hash=snapshot.reality_hash,
            reality_staleness_seconds=snapshot.reality_staleness_seconds,
            customer_id=snapshot.customer_id,
            customer_context_data=snapshot.customer_context_data,
            customer_context_hash=snapshot.customer_context_hash,
            customer_context_version=snapshot.customer_context_version,
            combined_hash=snapshot.combined_hash,
            captured_at=snapshot.captured_at,
        )
        
        self._session.add(model)
        await self._session.commit()
        
        logger.debug(
            "snapshot_stored",
            snapshot_id=snapshot.snapshot_id,
            customer_id=snapshot.customer_id,
        )
    
    async def get_snapshot(self, snapshot_id: str) -> Optional[InputSnapshot]:
        """
        Get an input snapshot by ID.
        """
        from app.db.models import InputSnapshotModel
        
        result = await self._session.execute(
            select(InputSnapshotModel).where(
                InputSnapshotModel.snapshot_id == snapshot_id
            )
        )
        model = result.scalar_one_or_none()
        
        if model:
            return self._model_to_snapshot(model)
        return None
    
    async def get_snapshots_for_customer(
        self,
        customer_id: str,
        limit: int = 100,
    ) -> List[InputSnapshot]:
        """
        Get input snapshots for a customer.
        """
        from app.db.models import InputSnapshotModel
        
        result = await self._session.execute(
            select(InputSnapshotModel)
            .where(InputSnapshotModel.customer_id == customer_id)
            .order_by(InputSnapshotModel.captured_at.desc())
            .limit(limit)
        )
        
        return [self._model_to_snapshot(m) for m in result.scalars().all()]
    
    # =========================================================================
    # PROCESSING RECORD OPERATIONS
    # =========================================================================
    
    async def store_processing_record(self, record: ProcessingRecord) -> None:
        """
        Store a processing record.
        """
        from app.db.models import ProcessingRecordModel
        
        model = ProcessingRecordModel(
            record_id=record.record_id,
            model_version=record.model_version,
            model_hash=record.model_hash,
            config_version=record.config_version,
            config_hash=record.config_hash,
            reasoning_trace_id=record.reasoning_trace_id,
            layers_executed=record.layers_executed,
            computation_time_ms=record.computation_time_ms,
            memory_used_mb=record.memory_used_mb,
            warnings=record.warnings,
            degradation_level=record.degradation_level,
            stale_data_sources=record.stale_data_sources,
            missing_data_sources=record.missing_data_sources,
        )
        
        self._session.add(model)
        await self._session.commit()
    
    async def get_processing_record(self, record_id: str) -> Optional[ProcessingRecord]:
        """
        Get a processing record by ID.
        """
        from app.db.models import ProcessingRecordModel
        
        result = await self._session.execute(
            select(ProcessingRecordModel).where(
                ProcessingRecordModel.record_id == record_id
            )
        )
        model = result.scalar_one_or_none()
        
        if model:
            return self._model_to_processing_record(model)
        return None
    
    # =========================================================================
    # MODEL CONVERSIONS
    # =========================================================================
    
    def _model_to_record(self, model) -> AuditRecord:
        """Convert database model to AuditRecord."""
        return AuditRecord(
            audit_id=model.event_id,
            event_type=AuditEventType(model.event_type),
            timestamp=model.created_at,
            entity_type=model.entity_type,
            entity_id=model.entity_id,
            actor_type=model.actor_type,
            actor_id=model.actor_id,
            payload=model.payload or {},
            payload_hash=model.payload_hash or "",
            sequence_number=model.sequence_number,
            previous_hash=model.previous_hash or "genesis",
            record_hash=model.record_hash or "",
        )
    
    def _model_to_snapshot(self, model) -> InputSnapshot:
        """Convert database model to InputSnapshot."""
        return InputSnapshot(
            snapshot_id=model.snapshot_id,
            captured_at=model.captured_at,
            signal_data=model.signal_data or {},
            signal_hash=model.signal_hash,
            signal_id=model.signal_id,
            reality_data=model.reality_data or {},
            reality_hash=model.reality_hash,
            reality_staleness_seconds=model.reality_staleness_seconds,
            customer_context_data=model.customer_context_data or {},
            customer_context_hash=model.customer_context_hash,
            customer_id=model.customer_id,
            customer_context_version=model.customer_context_version,
            combined_hash=model.combined_hash,
        )
    
    def _model_to_processing_record(self, model) -> ProcessingRecord:
        """Convert database model to ProcessingRecord."""
        return ProcessingRecord(
            record_id=model.record_id,
            model_version=model.model_version,
            model_hash=model.model_hash or "",
            config_version=model.config_version,
            config_hash=model.config_hash or "",
            reasoning_trace_id=model.reasoning_trace_id or "",
            layers_executed=model.layers_executed or [],
            computation_time_ms=model.computation_time_ms,
            memory_used_mb=model.memory_used_mb or 0.0,
            warnings=model.warnings or [],
            degradation_level=model.degradation_level or 0,
            stale_data_sources=model.stale_data_sources or [],
            missing_data_sources=model.missing_data_sources or [],
        )


class InMemoryAuditRepository:
    """
    In-memory audit repository for testing.
    
    NOT FOR PRODUCTION USE - data is lost on restart.
    """
    
    def __init__(self):
        self._records: List[AuditRecord] = []
        self._snapshots: dict[str, InputSnapshot] = {}
        self._processing_records: dict[str, ProcessingRecord] = {}
    
    async def store_record(self, record: AuditRecord) -> None:
        self._records.append(record)
    
    async def get_last_record(self) -> Optional[AuditRecord]:
        if self._records:
            return max(self._records, key=lambda r: r.sequence_number)
        return None
    
    async def get_records_range(
        self,
        start_sequence: int,
        end_sequence: Optional[int] = None,
        limit: int = 10000,
    ) -> List[AuditRecord]:
        records = [r for r in self._records if r.sequence_number >= start_sequence]
        if end_sequence is not None:
            records = [r for r in records if r.sequence_number <= end_sequence]
        records.sort(key=lambda r: r.sequence_number)
        return records[:limit]
    
    async def get_records_for_entity(
        self,
        entity_type: str,
        entity_id: str,
        limit: int = 100,
    ) -> List[AuditRecord]:
        records = [
            r for r in self._records
            if r.entity_type == entity_type and r.entity_id == entity_id
        ]
        records.sort(key=lambda r: r.sequence_number)
        return records[:limit]
    
    async def get_records_by_event_type(
        self,
        event_type: AuditEventType,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[AuditRecord]:
        records = [r for r in self._records if r.event_type == event_type]
        if start_time:
            records = [r for r in records if r.timestamp >= start_time]
        if end_time:
            records = [r for r in records if r.timestamp <= end_time]
        records.sort(key=lambda r: r.timestamp, reverse=True)
        return records[:limit]
    
    async def count_records(
        self,
        entity_type: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
    ) -> int:
        records = self._records
        if entity_type:
            records = [r for r in records if r.entity_type == entity_type]
        if event_type:
            records = [r for r in records if r.event_type == event_type]
        return len(records)
    
    async def store_snapshot(self, snapshot: InputSnapshot) -> None:
        self._snapshots[snapshot.snapshot_id] = snapshot
    
    async def get_snapshot(self, snapshot_id: str) -> Optional[InputSnapshot]:
        return self._snapshots.get(snapshot_id)
    
    async def get_snapshots_for_customer(
        self,
        customer_id: str,
        limit: int = 100,
    ) -> List[InputSnapshot]:
        snapshots = [s for s in self._snapshots.values() if s.customer_id == customer_id]
        snapshots.sort(key=lambda s: s.captured_at, reverse=True)
        return snapshots[:limit]
    
    async def store_processing_record(self, record: ProcessingRecord) -> None:
        self._processing_records[record.record_id] = record
    
    async def get_processing_record(self, record_id: str) -> Optional[ProcessingRecord]:
        return self._processing_records.get(record_id)
