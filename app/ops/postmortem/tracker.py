"""
Post-Mortem Tracking and Enforcement.

Tracks post-mortems and enforces completion to ensure organizational learning.

Rules:
- SEV1/SEV2: Post-mortem required within 48h
- All action items must have owners and due dates
- Incomplete action items escalated weekly

Addresses audit gap: D4.4 Post-Incident (+10 points)
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid

import structlog
from pydantic import BaseModel, Field, computed_field

logger = structlog.get_logger(__name__)


# ============================================================================
# ENUMS
# ============================================================================


class IncidentSeverity(str, Enum):
    """Incident severity levels."""
    SEV1 = "sev1"  # Complete outage, major customer impact
    SEV2 = "sev2"  # Partial outage, significant customer impact
    SEV3 = "sev3"  # Degradation, minor customer impact
    SEV4 = "sev4"  # Minor issue, no customer impact


class ActionItemStatus(str, Enum):
    """Action item status."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    WONT_FIX = "wont_fix"
    BLOCKED = "blocked"


class PostMortemStatus(str, Enum):
    """Post-mortem document status."""
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    PUBLISHED = "published"
    ARCHIVED = "archived"


# ============================================================================
# SCHEMAS
# ============================================================================


class ActionItem(BaseModel):
    """Post-mortem action item."""
    
    item_id: str = Field(default_factory=lambda: f"ai_{uuid.uuid4().hex[:8]}")
    postmortem_id: str
    
    # Content
    description: str = Field(description="What needs to be done")
    category: str = Field(default="improvement", description="bug_fix|improvement|process|monitoring")
    
    # Assignment
    owner: str = Field(description="Person responsible")
    team: Optional[str] = Field(default=None, description="Owning team")
    
    # Timing
    due_date: datetime = Field(description="Due date")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)
    
    # Status
    status: ActionItemStatus = Field(default=ActionItemStatus.OPEN)
    priority: str = Field(default="P1", description="P0|P1|P2|P3")
    
    # Notes
    notes: Optional[str] = Field(default=None)
    blocker: Optional[str] = Field(default=None)
    
    @computed_field
    @property
    def is_overdue(self) -> bool:
        """Whether action item is past due date."""
        if self.status in [ActionItemStatus.COMPLETED, ActionItemStatus.WONT_FIX]:
            return False
        return datetime.utcnow() > self.due_date
    
    @computed_field
    @property
    def days_overdue(self) -> int:
        """Days past due date (0 if not overdue)."""
        if not self.is_overdue:
            return 0
        return (datetime.utcnow() - self.due_date).days


class IncidentTimeline(BaseModel):
    """Timeline entry for incident."""
    timestamp: datetime
    event: str
    description: Optional[str] = None
    actor: Optional[str] = None


class Incident(BaseModel):
    """Incident record."""
    
    incident_id: str = Field(default_factory=lambda: f"inc_{uuid.uuid4().hex[:8]}")
    title: str
    severity: IncidentSeverity
    
    # Timeline
    started_at: datetime
    detected_at: datetime
    acknowledged_at: Optional[datetime] = None
    mitigated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    # Assignment
    incident_commander: Optional[str] = None
    responding_teams: List[str] = Field(default_factory=list)
    
    # Description
    summary: Optional[str] = None
    customer_impact: Optional[str] = None
    
    # Status
    status: str = Field(default="open", description="open|mitigated|resolved")


class PostMortem(BaseModel):
    """Post-mortem document."""
    
    # Identity
    postmortem_id: str = Field(default_factory=lambda: f"pm_{uuid.uuid4().hex[:8]}")
    incident_id: str
    severity: IncidentSeverity
    
    # Timeline metrics
    incident_start: datetime
    incident_detected: datetime
    incident_mitigated: datetime
    incident_resolved: datetime
    
    # Calculated metrics
    time_to_detect_minutes: float = Field(ge=0)
    time_to_mitigate_minutes: float = Field(ge=0)
    time_to_resolve_minutes: float = Field(ge=0)
    customer_impact_minutes: float = Field(ge=0)
    
    # Summary
    title: str
    summary: str = Field(default="")
    
    # Analysis
    timeline: List[IncidentTimeline] = Field(default_factory=list)
    root_causes: List[str] = Field(default_factory=list)
    contributing_factors: List[str] = Field(default_factory=list)
    
    # Impact
    customers_affected: int = Field(default=0, ge=0)
    revenue_impact_usd: float = Field(default=0, ge=0)
    decisions_affected: int = Field(default=0, ge=0)
    slo_impact: Optional[str] = Field(default=None)
    
    # Retrospective
    what_went_well: List[str] = Field(default_factory=list)
    what_went_poorly: List[str] = Field(default_factory=list)
    where_we_got_lucky: List[str] = Field(default_factory=list)
    
    # Actions
    action_items: List[ActionItem] = Field(default_factory=list)
    
    # Metadata
    author: str
    reviewers: List[str] = Field(default_factory=list)
    status: PostMortemStatus = Field(default=PostMortemStatus.DRAFT)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    published_at: Optional[datetime] = Field(default=None)
    
    # Tags
    tags: List[str] = Field(default_factory=list)
    related_postmortems: List[str] = Field(default_factory=list)
    
    @computed_field
    @property
    def requires_postmortem(self) -> bool:
        """Whether this severity requires a post-mortem."""
        return self.severity in [IncidentSeverity.SEV1, IncidentSeverity.SEV2]
    
    @computed_field
    @property
    def postmortem_deadline(self) -> datetime:
        """Deadline for completing post-mortem (48h after resolution)."""
        return self.incident_resolved + timedelta(hours=48)
    
    @computed_field
    @property
    def is_overdue(self) -> bool:
        """Whether post-mortem is past deadline."""
        if self.status == PostMortemStatus.PUBLISHED:
            return False
        return datetime.utcnow() > self.postmortem_deadline
    
    @computed_field
    @property
    def hours_until_deadline(self) -> float:
        """Hours until deadline (negative if overdue)."""
        return (self.postmortem_deadline - datetime.utcnow()).total_seconds() / 3600
    
    @computed_field
    @property
    def action_items_complete(self) -> int:
        """Number of completed action items."""
        return sum(1 for a in self.action_items if a.status == ActionItemStatus.COMPLETED)
    
    @computed_field
    @property
    def action_items_overdue(self) -> int:
        """Number of overdue action items."""
        return sum(1 for a in self.action_items if a.is_overdue)


class PostMortemMetrics(BaseModel):
    """Aggregate post-mortem metrics."""
    
    # Counts
    total_postmortems: int = Field(ge=0)
    postmortems_required: int = Field(ge=0)
    postmortems_completed: int = Field(ge=0)
    postmortems_overdue: int = Field(ge=0)
    
    # Completion
    completion_rate: float = Field(ge=0, le=1)
    avg_days_to_complete: float = Field(ge=0)
    
    # Action items
    total_action_items: int = Field(ge=0)
    action_items_completed: int = Field(ge=0)
    action_items_overdue: int = Field(ge=0)
    action_item_completion_rate: float = Field(ge=0, le=1)
    
    # Quality
    avg_action_items_per_postmortem: float = Field(ge=0)
    avg_root_causes_identified: float = Field(ge=0)
    
    # Timing (minutes)
    avg_time_to_detect: float = Field(ge=0)
    avg_time_to_mitigate: float = Field(ge=0)
    avg_time_to_resolve: float = Field(ge=0)


# ============================================================================
# REPOSITORY
# ============================================================================


class PostMortemRepository:
    """In-memory repository for post-mortems (mock for MVP)."""
    
    def __init__(self):
        self._postmortems: Dict[str, PostMortem] = {}
        self._incidents: Dict[str, Incident] = {}
        self._action_items: Dict[str, ActionItem] = {}
    
    async def save_incident(self, incident: Incident) -> None:
        """Save an incident."""
        self._incidents[incident.incident_id] = incident
    
    async def get_incident(self, incident_id: str) -> Optional[Incident]:
        """Get incident by ID."""
        return self._incidents.get(incident_id)
    
    async def save_postmortem(self, postmortem: PostMortem) -> None:
        """Save a post-mortem."""
        self._postmortems[postmortem.postmortem_id] = postmortem
        
        # Also save action items
        for item in postmortem.action_items:
            self._action_items[item.item_id] = item
    
    async def get_postmortem(self, postmortem_id: str) -> Optional[PostMortem]:
        """Get post-mortem by ID."""
        return self._postmortems.get(postmortem_id)
    
    async def get_postmortem_by_incident(self, incident_id: str) -> Optional[PostMortem]:
        """Get post-mortem for an incident."""
        for pm in self._postmortems.values():
            if pm.incident_id == incident_id:
                return pm
        return None
    
    async def list_postmortems(
        self,
        status: Optional[PostMortemStatus] = None,
        severity: Optional[IncidentSeverity] = None,
        limit: int = 100,
    ) -> List[PostMortem]:
        """List post-mortems with optional filters."""
        results = list(self._postmortems.values())
        
        if status:
            results = [pm for pm in results if pm.status == status]
        
        if severity:
            results = [pm for pm in results if pm.severity == severity]
        
        return sorted(results, key=lambda pm: pm.created_at, reverse=True)[:limit]
    
    async def get_action_item(self, item_id: str) -> Optional[ActionItem]:
        """Get action item by ID."""
        return self._action_items.get(item_id)
    
    async def update_action_item(self, item: ActionItem) -> None:
        """Update an action item."""
        self._action_items[item.item_id] = item
    
    async def list_overdue_action_items(self) -> List[ActionItem]:
        """List all overdue action items."""
        return [
            item for item in self._action_items.values()
            if item.is_overdue
        ]
    
    async def get_incidents_without_postmortem(
        self,
        severities: List[IncidentSeverity],
        before: datetime,
    ) -> List[Incident]:
        """Get incidents that need post-mortems but don't have them."""
        result = []
        
        for incident in self._incidents.values():
            if incident.severity not in severities:
                continue
            if incident.resolved_at is None or incident.resolved_at > before:
                continue
            
            # Check if has post-mortem
            has_pm = await self.get_postmortem_by_incident(incident.incident_id)
            if not has_pm:
                result.append(incident)
        
        return result


# ============================================================================
# POST-MORTEM TRACKER
# ============================================================================


class PostMortemTracker:
    """
    Tracks post-mortems and enforces completion.
    
    Rules:
    - SEV1/SEV2: Post-mortem required within 48h
    - All action items must have owners and due dates
    - Incomplete action items escalated weekly
    """
    
    POSTMORTEM_DEADLINE_HOURS = 48
    ACTION_ITEM_DEFAULT_DAYS = 14
    
    def __init__(self, repository: Optional[PostMortemRepository] = None):
        """Initialize tracker."""
        self._repo = repository or PostMortemRepository()
    
    async def create_incident(
        self,
        title: str,
        severity: IncidentSeverity,
        started_at: datetime,
        detected_at: Optional[datetime] = None,
        summary: Optional[str] = None,
        incident_commander: Optional[str] = None,
    ) -> Incident:
        """Create a new incident."""
        incident = Incident(
            title=title,
            severity=severity,
            started_at=started_at,
            detected_at=detected_at or started_at,
            summary=summary,
            incident_commander=incident_commander,
        )
        
        await self._repo.save_incident(incident)
        
        logger.info(
            "incident_created",
            incident_id=incident.incident_id,
            severity=severity.value,
            title=title,
        )
        
        return incident
    
    async def resolve_incident(
        self,
        incident_id: str,
        mitigated_at: datetime,
        resolved_at: datetime,
    ) -> Optional[Incident]:
        """Mark incident as resolved."""
        incident = await self._repo.get_incident(incident_id)
        if not incident:
            return None
        
        incident.mitigated_at = mitigated_at
        incident.resolved_at = resolved_at
        incident.status = "resolved"
        
        await self._repo.save_incident(incident)
        
        logger.info(
            "incident_resolved",
            incident_id=incident_id,
            severity=incident.severity.value,
            duration_minutes=(resolved_at - incident.started_at).total_seconds() / 60,
        )
        
        return incident
    
    async def create_postmortem(
        self,
        incident_id: str,
        author: str,
    ) -> Optional[PostMortem]:
        """Create a post-mortem from an incident."""
        incident = await self._repo.get_incident(incident_id)
        if not incident:
            logger.error("incident_not_found", incident_id=incident_id)
            return None
        
        if not incident.resolved_at:
            logger.error("incident_not_resolved", incident_id=incident_id)
            return None
        
        # Calculate timing metrics
        ttd = (incident.detected_at - incident.started_at).total_seconds() / 60
        ttm = (incident.mitigated_at - incident.detected_at).total_seconds() / 60 if incident.mitigated_at else 0
        ttr = (incident.resolved_at - (incident.mitigated_at or incident.detected_at)).total_seconds() / 60
        impact = (incident.mitigated_at or incident.resolved_at) - incident.started_at
        
        postmortem = PostMortem(
            incident_id=incident_id,
            severity=incident.severity,
            incident_start=incident.started_at,
            incident_detected=incident.detected_at,
            incident_mitigated=incident.mitigated_at or incident.detected_at,
            incident_resolved=incident.resolved_at,
            time_to_detect_minutes=ttd,
            time_to_mitigate_minutes=ttm,
            time_to_resolve_minutes=ttr,
            customer_impact_minutes=impact.total_seconds() / 60,
            title=incident.title,
            summary=incident.summary or "",
            author=author,
        )
        
        await self._repo.save_postmortem(postmortem)
        
        logger.info(
            "postmortem_created",
            postmortem_id=postmortem.postmortem_id,
            incident_id=incident_id,
            severity=incident.severity.value,
            deadline=postmortem.postmortem_deadline.isoformat(),
        )
        
        return postmortem
    
    async def update_postmortem(
        self,
        postmortem_id: str,
        **updates,
    ) -> Optional[PostMortem]:
        """Update a post-mortem."""
        postmortem = await self._repo.get_postmortem(postmortem_id)
        if not postmortem:
            return None
        
        # Update fields
        for key, value in updates.items():
            if hasattr(postmortem, key):
                setattr(postmortem, key, value)
        
        await self._repo.save_postmortem(postmortem)
        
        return postmortem
    
    async def publish_postmortem(self, postmortem_id: str) -> Optional[PostMortem]:
        """Publish a post-mortem."""
        postmortem = await self._repo.get_postmortem(postmortem_id)
        if not postmortem:
            return None
        
        postmortem.status = PostMortemStatus.PUBLISHED
        postmortem.published_at = datetime.utcnow()
        
        await self._repo.save_postmortem(postmortem)
        
        logger.info(
            "postmortem_published",
            postmortem_id=postmortem_id,
            incident_id=postmortem.incident_id,
            action_items=len(postmortem.action_items),
        )
        
        return postmortem
    
    async def add_action_item(
        self,
        postmortem_id: str,
        description: str,
        owner: str,
        due_date: Optional[datetime] = None,
        priority: str = "P1",
        category: str = "improvement",
    ) -> Optional[ActionItem]:
        """Add an action item to a post-mortem."""
        postmortem = await self._repo.get_postmortem(postmortem_id)
        if not postmortem:
            return None
        
        item = ActionItem(
            postmortem_id=postmortem_id,
            description=description,
            owner=owner,
            due_date=due_date or (datetime.utcnow() + timedelta(days=self.ACTION_ITEM_DEFAULT_DAYS)),
            priority=priority,
            category=category,
        )
        
        postmortem.action_items.append(item)
        await self._repo.save_postmortem(postmortem)
        
        logger.info(
            "action_item_added",
            item_id=item.item_id,
            postmortem_id=postmortem_id,
            owner=owner,
            due_date=item.due_date.isoformat(),
        )
        
        return item
    
    async def complete_action_item(
        self,
        item_id: str,
        notes: Optional[str] = None,
    ) -> Optional[ActionItem]:
        """Mark an action item as completed."""
        item = await self._repo.get_action_item(item_id)
        if not item:
            return None
        
        item.status = ActionItemStatus.COMPLETED
        item.completed_at = datetime.utcnow()
        item.notes = notes
        
        await self._repo.update_action_item(item)
        
        logger.info(
            "action_item_completed",
            item_id=item_id,
            postmortem_id=item.postmortem_id,
            days_to_complete=(item.completed_at - item.created_at).days,
        )
        
        return item
    
    async def get_overdue_postmortems(self) -> List[Dict[str, Any]]:
        """Get incidents that need post-mortems but don't have them."""
        cutoff = datetime.utcnow() - timedelta(hours=self.POSTMORTEM_DEADLINE_HOURS)
        
        incidents = await self._repo.get_incidents_without_postmortem(
            severities=[IncidentSeverity.SEV1, IncidentSeverity.SEV2],
            before=cutoff,
        )
        
        return [
            {
                "incident_id": i.incident_id,
                "title": i.title,
                "severity": i.severity.value,
                "resolved_at": i.resolved_at.isoformat() if i.resolved_at else None,
                "age_hours": (datetime.utcnow() - i.resolved_at).total_seconds() / 3600 if i.resolved_at else 0,
                "hours_overdue": (datetime.utcnow() - i.resolved_at).total_seconds() / 3600 - self.POSTMORTEM_DEADLINE_HOURS if i.resolved_at else 0,
            }
            for i in incidents
        ]
    
    async def get_overdue_action_items(self) -> List[ActionItem]:
        """Get action items past due date."""
        return await self._repo.list_overdue_action_items()
    
    async def get_metrics(self) -> PostMortemMetrics:
        """Get aggregate post-mortem metrics."""
        postmortems = await self._repo.list_postmortems()
        
        if not postmortems:
            return PostMortemMetrics(
                total_postmortems=0,
                postmortems_required=0,
                postmortems_completed=0,
                postmortems_overdue=0,
                completion_rate=0,
                avg_days_to_complete=0,
                total_action_items=0,
                action_items_completed=0,
                action_items_overdue=0,
                action_item_completion_rate=0,
                avg_action_items_per_postmortem=0,
                avg_root_causes_identified=0,
                avg_time_to_detect=0,
                avg_time_to_mitigate=0,
                avg_time_to_resolve=0,
            )
        
        required = [pm for pm in postmortems if pm.requires_postmortem]
        completed = [pm for pm in postmortems if pm.status == PostMortemStatus.PUBLISHED]
        overdue = [pm for pm in postmortems if pm.is_overdue]
        
        all_items = [item for pm in postmortems for item in pm.action_items]
        completed_items = [item for item in all_items if item.status == ActionItemStatus.COMPLETED]
        overdue_items = [item for item in all_items if item.is_overdue]
        
        # Calculate averages
        days_to_complete = []
        for pm in completed:
            if pm.published_at:
                days = (pm.published_at - pm.created_at).days
                days_to_complete.append(days)
        
        return PostMortemMetrics(
            total_postmortems=len(postmortems),
            postmortems_required=len(required),
            postmortems_completed=len(completed),
            postmortems_overdue=len(overdue),
            completion_rate=len(completed) / len(postmortems) if postmortems else 0,
            avg_days_to_complete=sum(days_to_complete) / len(days_to_complete) if days_to_complete else 0,
            total_action_items=len(all_items),
            action_items_completed=len(completed_items),
            action_items_overdue=len(overdue_items),
            action_item_completion_rate=len(completed_items) / len(all_items) if all_items else 0,
            avg_action_items_per_postmortem=len(all_items) / len(postmortems) if postmortems else 0,
            avg_root_causes_identified=sum(len(pm.root_causes) for pm in postmortems) / len(postmortems) if postmortems else 0,
            avg_time_to_detect=sum(pm.time_to_detect_minutes for pm in postmortems) / len(postmortems) if postmortems else 0,
            avg_time_to_mitigate=sum(pm.time_to_mitigate_minutes for pm in postmortems) / len(postmortems) if postmortems else 0,
            avg_time_to_resolve=sum(pm.time_to_resolve_minutes for pm in postmortems) / len(postmortems) if postmortems else 0,
        )


# ============================================================================
# SINGLETON
# ============================================================================


_postmortem_tracker: Optional[PostMortemTracker] = None


def get_postmortem_tracker() -> PostMortemTracker:
    """Get global post-mortem tracker instance."""
    global _postmortem_tracker
    if _postmortem_tracker is None:
        _postmortem_tracker = PostMortemTracker()
    return _postmortem_tracker
