"""
Tests for RISKCAST GDPR Compliance.

Tests:
- test_gdpr_access_request()
- test_gdpr_erasure_request()
- Data portability
- Consent management
"""

import pytest
from datetime import datetime, timedelta

from app.compliance.gdpr import (
    GDPRService,
    DataProcessingPurpose,
    LawfulBasis,
    DataCategory,
    ProcessingRecord,
    ConsentRecord,
    DataRetentionPolicy,
)
from app.compliance.data_subject import (
    DataSubjectRight,
    RequestStatus,
    DataSubjectRequest,
    DataInventoryItem,
    PortabilityExport,
    DataSubjectService,
)


class TestGDPRService:
    """Test GDPR compliance service."""
    
    @pytest.fixture
    def gdpr_service(self):
        return GDPRService()
    
    @pytest.mark.asyncio
    async def test_gdpr_service_initialization(self, gdpr_service):
        """Test GDPR service initialization."""
        await gdpr_service.initialize()
        
        records = gdpr_service.get_processing_records()
        assert len(records) >= 4  # Default processing records
    
    @pytest.mark.asyncio
    async def test_processing_records_article30(self, gdpr_service):
        """Test Article 30 compliant processing records."""
        await gdpr_service.initialize()
        
        records = gdpr_service.get_processing_records()
        
        for record in records:
            # Every record must have required Article 30 fields
            assert record.activity_name is not None
            assert record.purpose is not None
            assert record.lawful_basis is not None
            assert len(record.data_categories) > 0
            assert record.retention_period is not None
            
            # Check Article 30 export format
            export = record.to_article30_record()
            assert "name_of_processing" in export
            assert "purpose" in export
            assert "categories_of_personal_data" in export
    
    @pytest.mark.asyncio
    async def test_consent_recording(self, gdpr_service):
        """Test consent recording."""
        await gdpr_service.initialize()
        
        consent = await gdpr_service.record_consent(
            subject_id="user_123",
            purpose=DataProcessingPurpose.MARKETING,
            given=True,
            consent_text="I agree to receive marketing communications",
            ip_address="192.168.1.1",
        )
        
        assert consent.consent_id is not None
        assert consent.subject_id == "user_123"
        assert consent.given is True
        assert consent.is_valid is True
        assert consent.proof_hash is not None
    
    @pytest.mark.asyncio
    async def test_consent_withdrawal(self, gdpr_service):
        """Test consent withdrawal."""
        await gdpr_service.initialize()
        
        # First give consent
        await gdpr_service.record_consent(
            subject_id="user_456",
            purpose=DataProcessingPurpose.ANALYTICS,
            given=True,
            consent_text="I agree to analytics",
        )
        
        # Then withdraw
        withdrawn = await gdpr_service.withdraw_consent(
            subject_id="user_456",
            purpose=DataProcessingPurpose.ANALYTICS,
        )
        
        assert withdrawn is not None
        assert withdrawn.withdrawn_at is not None
        assert withdrawn.is_valid is False
    
    @pytest.mark.asyncio
    async def test_consent_status(self, gdpr_service):
        """Test getting consent status."""
        await gdpr_service.initialize()
        
        # Record some consents
        await gdpr_service.record_consent(
            subject_id="user_789",
            purpose=DataProcessingPurpose.MARKETING,
            given=True,
            consent_text="Marketing consent",
        )
        
        await gdpr_service.record_consent(
            subject_id="user_789",
            purpose=DataProcessingPurpose.ANALYTICS,
            given=False,
            consent_text="Analytics consent",
        )
        
        status = await gdpr_service.get_consent_status("user_789")
        
        assert status["subject_id"] == "user_789"
        assert status["consents"]["marketing"]["consented"] is True
        assert status["consents"]["analytics"]["consented"] is False
    
    @pytest.mark.asyncio
    async def test_retention_policies(self, gdpr_service):
        """Test data retention policies."""
        await gdpr_service.initialize()
        
        policies = gdpr_service.get_all_retention_policies()
        assert len(policies) > 0
        
        identity_policy = gdpr_service.get_retention_policy(DataCategory.IDENTITY)
        assert identity_policy is not None
        assert identity_policy.retention_days > 0
    
    @pytest.mark.asyncio
    async def test_article30_export(self, gdpr_service):
        """Test Article 30 export generation."""
        await gdpr_service.initialize()
        
        export = await gdpr_service.generate_article30_export()
        
        assert "controller" in export
        assert "processing_activities" in export
        assert len(export["processing_activities"]) >= 4
    
    @pytest.mark.asyncio
    async def test_retention_compliance_check(self, gdpr_service):
        """Test retention compliance check."""
        await gdpr_service.initialize()
        
        compliance = await gdpr_service.check_retention_compliance()
        
        assert "compliant" in compliance
        assert "issues" in compliance
        assert "policies_count" in compliance


class TestDataSubjectService:
    """Test data subject rights service."""
    
    @pytest.fixture
    def dsr_service(self):
        return DataSubjectService()
    
    @pytest.mark.asyncio
    async def test_dsr_service_initialization(self, dsr_service):
        """Test DSR service initialization."""
        await dsr_service.initialize()
        assert dsr_service._initialized is True
    
    @pytest.mark.asyncio
    async def test_submit_access_request(self, dsr_service):
        """Test submitting an access request."""
        await dsr_service.initialize()
        
        request = await dsr_service.submit_request(
            subject_id="user_123",
            subject_email="user@example.com",
            right=DataSubjectRight.ACCESS,
        )
        
        assert request.request_id is not None
        assert request.subject_id == "user_123"
        assert request.right == DataSubjectRight.ACCESS
        assert request.status == RequestStatus.PENDING
        assert len(request.audit_trail) == 1  # Submitted entry
    
    @pytest.mark.asyncio
    async def test_gdpr_access_request(self, dsr_service):
        """Test complete access request workflow."""
        await dsr_service.initialize()
        
        # Submit request
        request = await dsr_service.submit_request(
            subject_id="user_access_test",
            subject_email="access@example.com",
            right=DataSubjectRight.ACCESS,
        )
        
        # Verify identity
        verified = await dsr_service.verify_identity(request.request_id)
        assert verified is True
        
        # Process request
        response = await dsr_service.process_access_request(request.request_id)
        
        assert response is not None
        assert response["subject_id"] == "user_access_test"
        assert "data" in response
        assert len(response["data"]) > 0
        
        # Check request is completed
        updated_request = dsr_service.get_request(request.request_id)
        assert updated_request.status == RequestStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_gdpr_erasure_request(self, dsr_service):
        """Test complete erasure request workflow."""
        await dsr_service.initialize()
        
        # Submit request
        request = await dsr_service.submit_request(
            subject_id="user_erasure_test",
            subject_email="erasure@example.com",
            right=DataSubjectRight.ERASURE,
        )
        
        # Verify identity
        verified = await dsr_service.verify_identity(request.request_id)
        assert verified is True
        
        # Process erasure
        response = await dsr_service.process_erasure_request(request.request_id)
        
        assert response is not None
        assert response["success"] is True
        assert "sources_erased" in response
        
        # Check request is completed
        updated_request = dsr_service.get_request(request.request_id)
        assert updated_request.status == RequestStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_gdpr_portability_request(self, dsr_service):
        """Test data portability request."""
        await dsr_service.initialize()
        
        # Submit request
        request = await dsr_service.submit_request(
            subject_id="user_portability_test",
            subject_email="portability@example.com",
            right=DataSubjectRight.PORTABILITY,
        )
        
        # Verify and process
        await dsr_service.verify_identity(request.request_id)
        export = await dsr_service.process_portability_request(request.request_id)
        
        assert isinstance(export, PortabilityExport)
        assert export.subject_id == "user_portability_test"
        assert export.file_size_bytes > 0
        assert export.checksum is not None
    
    @pytest.mark.asyncio
    async def test_request_deadline(self, dsr_service):
        """Test request deadline calculation."""
        await dsr_service.initialize()
        
        request = await dsr_service.submit_request(
            subject_id="deadline_test",
            subject_email="deadline@example.com",
            right=DataSubjectRight.ACCESS,
        )
        
        # Deadline should be 30 days from submission
        expected_deadline = request.submitted_at + timedelta(days=30)
        assert abs((request.deadline - expected_deadline).total_seconds()) < 60
        assert request.days_until_deadline <= 30
    
    @pytest.mark.asyncio
    async def test_deadline_extension(self, dsr_service):
        """Test extending request deadline."""
        await dsr_service.initialize()
        
        request = await dsr_service.submit_request(
            subject_id="extension_test",
            subject_email="extension@example.com",
            right=DataSubjectRight.ACCESS,
        )
        
        original_deadline = request.deadline
        
        updated = await dsr_service.extend_deadline(
            request.request_id,
            days=30,
            reason="Complex request",
        )
        
        assert updated.extended_deadline is not None
        assert updated.extended_deadline > original_deadline
        assert updated.extension_reason == "Complex request"
    
    @pytest.mark.asyncio
    async def test_request_rejection(self, dsr_service):
        """Test request rejection."""
        await dsr_service.initialize()
        
        request = await dsr_service.submit_request(
            subject_id="reject_test",
            subject_email="reject@example.com",
            right=DataSubjectRight.ERASURE,
        )
        
        rejected = await dsr_service.reject_request(
            request.request_id,
            reason="Legal hold prevents erasure",
        )
        
        assert rejected.status == RequestStatus.REJECTED
        assert rejected.rejection_reason == "Legal hold prevents erasure"
    
    @pytest.mark.asyncio
    async def test_get_pending_requests(self, dsr_service):
        """Test getting pending requests."""
        await dsr_service.initialize()
        
        # Submit multiple requests
        await dsr_service.submit_request("user1", "u1@example.com", DataSubjectRight.ACCESS)
        await dsr_service.submit_request("user2", "u2@example.com", DataSubjectRight.ERASURE)
        
        pending = dsr_service.get_pending_requests()
        
        assert len(pending) >= 2
        assert all(r.status in [RequestStatus.PENDING, RequestStatus.VERIFYING, RequestStatus.PROCESSING] for r in pending)
    
    @pytest.mark.asyncio
    async def test_service_metrics(self, dsr_service):
        """Test getting service metrics."""
        await dsr_service.initialize()
        
        # Submit and process some requests
        request = await dsr_service.submit_request("metrics_user", "metrics@example.com", DataSubjectRight.ACCESS)
        await dsr_service.verify_identity(request.request_id)
        await dsr_service.process_access_request(request.request_id)
        
        metrics = dsr_service.get_metrics()
        
        assert metrics["total_requests"] >= 1
        assert "by_status" in metrics
        assert "by_right" in metrics


class TestDataInventory:
    """Test data inventory functionality."""
    
    def test_data_inventory_item_creation(self):
        """Test creating data inventory items."""
        item = DataInventoryItem(
            category="identity",
            description="Customer profile",
            source="customer_database",
            collected_at=datetime(2024, 1, 1),
            data={"name": "Test User", "email": "test@example.com"},
        )
        
        assert item.category == "identity"
        assert item.can_rectify is True
        assert item.can_erase is True
    
    def test_data_inventory_with_restrictions(self):
        """Test inventory item with erasure restrictions."""
        item = DataInventoryItem(
            category="financial",
            description="Transaction records",
            source="finance_database",
            data={"transactions": 100},
            can_erase=False,
            erasure_restrictions="Required for tax compliance (7 years)",
        )
        
        assert item.can_erase is False
        assert item.erasure_restrictions is not None


class TestProcessingRecord:
    """Test processing record functionality."""
    
    def test_processing_record_creation(self):
        """Test creating a processing record."""
        record = ProcessingRecord(
            record_id="proc_test",
            activity_name="Test Processing",
            purpose=DataProcessingPurpose.SERVICE_DELIVERY,
            lawful_basis=LawfulBasis.CONTRACT,
            data_categories=[DataCategory.IDENTITY, DataCategory.CONTACT],
            data_subjects=["customers"],
            retention_period="5 years",
            retention_days=365 * 5,
        )
        
        assert record.record_id == "proc_test"
        assert record.purpose == DataProcessingPurpose.SERVICE_DELIVERY
        assert record.lawful_basis == LawfulBasis.CONTRACT
    
    def test_dpia_requirements(self):
        """Test DPIA requirement tracking."""
        record = ProcessingRecord(
            record_id="proc_dpia",
            activity_name="Automated Decision Making",
            purpose=DataProcessingPurpose.RISK_ANALYSIS,
            lawful_basis=LawfulBasis.CONTRACT,
            data_categories=[DataCategory.SHIPMENT],
            data_subjects=["customers"],
            retention_period="3 years",
            automated_decision_making=True,
            profiling=True,
            dpia_required=True,
            dpia_completed=True,
        )
        
        assert record.dpia_required is True
        assert record.dpia_completed is True


class TestConsentRecord:
    """Test consent record functionality."""
    
    def test_consent_proof_hash(self):
        """Test consent proof hash generation."""
        consent = ConsentRecord(
            consent_id="cons_123",
            subject_id="user_123",
            purpose=DataProcessingPurpose.MARKETING,
            consent_text="I agree to marketing",
            given=True,
            given_at=datetime(2024, 1, 15, 10, 30, 0),
        )
        
        hash1 = consent.generate_proof_hash()
        hash2 = consent.generate_proof_hash()
        
        # Hash should be deterministic
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex
    
    def test_consent_validity(self):
        """Test consent validity checking."""
        valid_consent = ConsentRecord(
            consent_id="valid",
            subject_id="user",
            purpose=DataProcessingPurpose.MARKETING,
            consent_text="Agree",
            given=True,
            given_at=datetime.utcnow(),
        )
        
        invalid_consent = ConsentRecord(
            consent_id="invalid",
            subject_id="user",
            purpose=DataProcessingPurpose.MARKETING,
            consent_text="Agree",
            given=True,
            given_at=datetime.utcnow(),
            withdrawn_at=datetime.utcnow(),
        )
        
        not_given = ConsentRecord(
            consent_id="not_given",
            subject_id="user",
            purpose=DataProcessingPurpose.MARKETING,
            consent_text="Agree",
            given=False,
        )
        
        assert valid_consent.is_valid is True
        assert invalid_consent.is_valid is False
        assert not_given.is_valid is False
