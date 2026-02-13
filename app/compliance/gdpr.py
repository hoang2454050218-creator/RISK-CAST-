"""
GDPR Compliance Service.

Implements GDPR compliance features including:
- Processing records (Article 30)
- Lawful basis tracking
- Consent management
- Data retention policies

Addresses audit gap: B3.4 Compliance Readiness (+8 points)
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum
import hashlib
import json

from pydantic import BaseModel, Field, EmailStr
import structlog

logger = structlog.get_logger(__name__)


class DataProcessingPurpose(str, Enum):
    """GDPR-compliant processing purposes."""
    SERVICE_DELIVERY = "service_delivery"
    RISK_ANALYSIS = "risk_analysis"
    ALERT_DELIVERY = "alert_delivery"
    ANALYTICS = "analytics"
    MARKETING = "marketing"
    LEGAL_COMPLIANCE = "legal_compliance"
    LEGITIMATE_INTEREST = "legitimate_interest"


class LawfulBasis(str, Enum):
    """GDPR Article 6 lawful bases."""
    CONSENT = "consent"
    CONTRACT = "contract"
    LEGAL_OBLIGATION = "legal_obligation"
    VITAL_INTERESTS = "vital_interests"
    PUBLIC_TASK = "public_task"
    LEGITIMATE_INTERESTS = "legitimate_interests"


class DataCategory(str, Enum):
    """Categories of personal data."""
    IDENTITY = "identity"           # Name, email, phone
    CONTACT = "contact"             # Address, location
    BUSINESS = "business"           # Company, role
    SHIPMENT = "shipment"           # Shipment data
    BEHAVIORAL = "behavioral"       # Usage, preferences
    FINANCIAL = "financial"         # Payment, billing
    TECHNICAL = "technical"         # IP, device info


class ProcessingRecord(BaseModel):
    """
    Record of processing activities (GDPR Article 30).
    
    Documents what data is processed, why, and how.
    """
    record_id: str = Field(description="Unique record identifier")
    activity_name: str = Field(description="Name of processing activity")
    purpose: DataProcessingPurpose = Field(description="Processing purpose")
    lawful_basis: LawfulBasis = Field(description="Legal basis for processing")
    data_categories: List[DataCategory] = Field(description="Categories of data processed")
    data_subjects: List[str] = Field(description="Categories of data subjects")
    recipients: List[str] = Field(default_factory=list, description="Data recipients")
    transfers_outside_eea: bool = Field(default=False)
    transfer_safeguards: Optional[str] = Field(default=None)
    retention_period: str = Field(description="Retention period description")
    retention_days: int = Field(default=365, description="Retention in days")
    security_measures: List[str] = Field(default_factory=list)
    automated_decision_making: bool = Field(default=False)
    profiling: bool = Field(default=False)
    dpia_required: bool = Field(default=False, description="Data Protection Impact Assessment required")
    dpia_completed: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def to_article30_record(self) -> Dict[str, Any]:
        """Export as Article 30 compliant record."""
        return {
            "name_of_processing": self.activity_name,
            "purpose": self.purpose.value,
            "categories_of_data_subjects": self.data_subjects,
            "categories_of_personal_data": [c.value for c in self.data_categories],
            "recipients": self.recipients,
            "transfers_to_third_countries": self.transfers_outside_eea,
            "transfer_safeguards": self.transfer_safeguards,
            "envisaged_retention_period": self.retention_period,
            "technical_and_organisational_measures": self.security_measures,
        }


class ConsentRecord(BaseModel):
    """
    Record of consent given by data subject.
    
    Tracks consent lifecycle for GDPR compliance.
    """
    consent_id: str = Field(description="Unique consent identifier")
    subject_id: str = Field(description="Data subject identifier")
    purpose: DataProcessingPurpose = Field(description="Purpose consent is for")
    version: str = Field(default="1.0", description="Consent form version")
    consent_text: str = Field(description="Text shown to user")
    given: bool = Field(description="Whether consent was given")
    given_at: Optional[datetime] = Field(default=None)
    withdrawn_at: Optional[datetime] = Field(default=None)
    ip_address: Optional[str] = Field(default=None, description="IP when consent given")
    user_agent: Optional[str] = Field(default=None)
    proof_hash: Optional[str] = Field(default=None, description="Hash for proof of consent")
    
    def generate_proof_hash(self) -> str:
        """Generate tamper-evident hash of consent record."""
        data = {
            "consent_id": self.consent_id,
            "subject_id": self.subject_id,
            "purpose": self.purpose.value,
            "version": self.version,
            "given": self.given,
            "given_at": self.given_at.isoformat() if self.given_at else None,
        }
        hash_input = json.dumps(data, sort_keys=True)
        return hashlib.sha256(hash_input.encode()).hexdigest()
    
    @property
    def is_valid(self) -> bool:
        """Check if consent is currently valid."""
        return self.given and self.withdrawn_at is None


class DataRetentionPolicy(BaseModel):
    """Data retention policy definition."""
    policy_id: str
    data_category: DataCategory
    retention_days: int
    justification: str
    exceptions: List[str] = Field(default_factory=list)
    review_date: datetime


class GDPRService:
    """
    GDPR compliance service.
    
    Manages:
    - Processing records (Article 30)
    - Consent tracking
    - Data retention policies
    - Compliance reporting
    """
    
    def __init__(self):
        self._processing_records: Dict[str, ProcessingRecord] = {}
        self._consent_records: Dict[str, List[ConsentRecord]] = {}  # By subject_id
        self._retention_policies: Dict[DataCategory, DataRetentionPolicy] = {}
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize with default RISKCAST processing records."""
        # Register default processing activities
        self._register_default_processing_records()
        self._register_default_retention_policies()
        
        self._initialized = True
        logger.info("gdpr_service_initialized")
    
    def _register_default_processing_records(self) -> None:
        """Register RISKCAST default processing activities."""
        records = [
            ProcessingRecord(
                record_id="proc_service_delivery",
                activity_name="Service Delivery",
                purpose=DataProcessingPurpose.SERVICE_DELIVERY,
                lawful_basis=LawfulBasis.CONTRACT,
                data_categories=[DataCategory.IDENTITY, DataCategory.CONTACT, DataCategory.SHIPMENT],
                data_subjects=["customers", "customer_contacts"],
                recipients=["internal_staff"],
                retention_period="Duration of contract plus 7 years",
                retention_days=365 * 7,
                security_measures=["encryption_at_rest", "encryption_in_transit", "access_control"],
            ),
            ProcessingRecord(
                record_id="proc_risk_analysis",
                activity_name="Risk Analysis",
                purpose=DataProcessingPurpose.RISK_ANALYSIS,
                lawful_basis=LawfulBasis.CONTRACT,
                data_categories=[DataCategory.SHIPMENT, DataCategory.BUSINESS],
                data_subjects=["customers"],
                recipients=["internal_staff", "ai_systems"],
                retention_period="Duration of contract plus 3 years",
                retention_days=365 * 3,
                security_measures=["encryption_at_rest", "encryption_in_transit", "access_control", "audit_logging"],
                automated_decision_making=True,
                profiling=False,
                dpia_required=True,
                dpia_completed=True,
            ),
            ProcessingRecord(
                record_id="proc_alert_delivery",
                activity_name="Alert Delivery",
                purpose=DataProcessingPurpose.ALERT_DELIVERY,
                lawful_basis=LawfulBasis.CONTRACT,
                data_categories=[DataCategory.CONTACT],
                data_subjects=["customer_contacts"],
                recipients=["twilio", "sendgrid"],
                transfers_outside_eea=True,
                transfer_safeguards="Standard Contractual Clauses",
                retention_period="90 days",
                retention_days=90,
                security_measures=["encryption_in_transit", "access_control"],
            ),
            ProcessingRecord(
                record_id="proc_analytics",
                activity_name="Analytics",
                purpose=DataProcessingPurpose.ANALYTICS,
                lawful_basis=LawfulBasis.LEGITIMATE_INTERESTS,
                data_categories=[DataCategory.BEHAVIORAL, DataCategory.TECHNICAL],
                data_subjects=["customers", "website_visitors"],
                recipients=["internal_staff"],
                retention_period="2 years",
                retention_days=365 * 2,
                security_measures=["pseudonymization", "aggregation", "access_control"],
            ),
        ]
        
        for record in records:
            self._processing_records[record.record_id] = record
    
    def _register_default_retention_policies(self) -> None:
        """Register default data retention policies."""
        policies = [
            DataRetentionPolicy(
                policy_id="ret_identity",
                data_category=DataCategory.IDENTITY,
                retention_days=365 * 7,
                justification="Legal requirement for business records",
                review_date=datetime.utcnow() + timedelta(days=365),
            ),
            DataRetentionPolicy(
                policy_id="ret_shipment",
                data_category=DataCategory.SHIPMENT,
                retention_days=365 * 3,
                justification="Business analysis and model improvement",
                exceptions=["Active disputes", "Ongoing contracts"],
                review_date=datetime.utcnow() + timedelta(days=365),
            ),
            DataRetentionPolicy(
                policy_id="ret_behavioral",
                data_category=DataCategory.BEHAVIORAL,
                retention_days=365 * 2,
                justification="Service improvement",
                review_date=datetime.utcnow() + timedelta(days=180),
            ),
            DataRetentionPolicy(
                policy_id="ret_technical",
                data_category=DataCategory.TECHNICAL,
                retention_days=90,
                justification="Security and debugging",
                review_date=datetime.utcnow() + timedelta(days=365),
            ),
        ]
        
        for policy in policies:
            self._retention_policies[policy.data_category] = policy
    
    async def record_consent(
        self,
        subject_id: str,
        purpose: DataProcessingPurpose,
        given: bool,
        consent_text: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> ConsentRecord:
        """Record a consent decision."""
        consent = ConsentRecord(
            consent_id=f"cons_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{subject_id[:8]}",
            subject_id=subject_id,
            purpose=purpose,
            consent_text=consent_text,
            given=given,
            given_at=datetime.utcnow() if given else None,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        consent.proof_hash = consent.generate_proof_hash()
        
        if subject_id not in self._consent_records:
            self._consent_records[subject_id] = []
        
        self._consent_records[subject_id].append(consent)
        
        logger.info(
            "consent_recorded",
            subject_id=subject_id,
            purpose=purpose.value,
            given=given,
            consent_id=consent.consent_id,
        )
        
        return consent
    
    async def withdraw_consent(
        self,
        subject_id: str,
        purpose: DataProcessingPurpose,
    ) -> Optional[ConsentRecord]:
        """Withdraw consent for a purpose."""
        records = self._consent_records.get(subject_id, [])
        
        for record in reversed(records):
            if record.purpose == purpose and record.is_valid:
                record.withdrawn_at = datetime.utcnow()
                
                logger.info(
                    "consent_withdrawn",
                    subject_id=subject_id,
                    purpose=purpose.value,
                    consent_id=record.consent_id,
                )
                
                return record
        
        return None
    
    async def get_consent_status(
        self,
        subject_id: str,
    ) -> Dict[str, Any]:
        """Get current consent status for all purposes."""
        records = self._consent_records.get(subject_id, [])
        
        status = {}
        for purpose in DataProcessingPurpose:
            # Find latest consent for this purpose
            relevant = [r for r in records if r.purpose == purpose]
            if relevant:
                latest = max(relevant, key=lambda r: r.given_at or datetime.min)
                status[purpose.value] = {
                    "consented": latest.is_valid,
                    "consent_id": latest.consent_id,
                    "given_at": latest.given_at.isoformat() if latest.given_at else None,
                    "withdrawn_at": latest.withdrawn_at.isoformat() if latest.withdrawn_at else None,
                }
            else:
                status[purpose.value] = {
                    "consented": False,
                    "consent_id": None,
                    "given_at": None,
                }
        
        return {
            "subject_id": subject_id,
            "consents": status,
            "checked_at": datetime.utcnow().isoformat(),
        }
    
    def get_processing_records(self) -> List[ProcessingRecord]:
        """Get all processing records (Article 30)."""
        return list(self._processing_records.values())
    
    def get_processing_record(self, record_id: str) -> Optional[ProcessingRecord]:
        """Get specific processing record."""
        return self._processing_records.get(record_id)
    
    def get_retention_policy(
        self,
        data_category: DataCategory,
    ) -> Optional[DataRetentionPolicy]:
        """Get retention policy for a data category."""
        return self._retention_policies.get(data_category)
    
    def get_all_retention_policies(self) -> List[DataRetentionPolicy]:
        """Get all retention policies."""
        return list(self._retention_policies.values())
    
    def get_lawful_basis_for_purpose(
        self,
        purpose: DataProcessingPurpose,
    ) -> Optional[LawfulBasis]:
        """Get lawful basis for a processing purpose."""
        for record in self._processing_records.values():
            if record.purpose == purpose:
                return record.lawful_basis
        return None
    
    async def generate_article30_export(self) -> Dict[str, Any]:
        """Generate GDPR Article 30 compliant export."""
        return {
            "controller": {
                "name": "RISKCAST Platform",
                "contact": "dpo@riskcast.io",
            },
            "processing_activities": [
                record.to_article30_record()
                for record in self._processing_records.values()
            ],
            "generated_at": datetime.utcnow().isoformat(),
            "version": "1.0",
        }
    
    async def check_retention_compliance(self) -> Dict[str, Any]:
        """Check data retention compliance status."""
        issues = []
        
        for category, policy in self._retention_policies.items():
            if policy.review_date < datetime.utcnow():
                issues.append({
                    "category": category.value,
                    "issue": "Retention policy review overdue",
                    "review_date": policy.review_date.isoformat(),
                })
        
        return {
            "compliant": len(issues) == 0,
            "issues": issues,
            "policies_count": len(self._retention_policies),
            "checked_at": datetime.utcnow().isoformat(),
        }


# Singleton accessor
_service: Optional[GDPRService] = None


async def get_gdpr_service() -> GDPRService:
    """Get or create the GDPR service singleton."""
    global _service
    if _service is None:
        _service = GDPRService()
        await _service.initialize()
    return _service
