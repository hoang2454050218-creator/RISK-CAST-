"""
RISKCAST Compliance Module.

Provides compliance features for:
- GDPR data subject rights (access, erasure, portability)
- Data inventory and processing records
- Consent management
- Compliance auditing

Addresses audit gap: B3.4 Compliance Readiness (+8 points)
"""

from app.compliance.gdpr import (
    GDPRService,
    DataProcessingPurpose,
    LawfulBasis,
    ProcessingRecord,
    ConsentRecord,
    get_gdpr_service,
)

from app.compliance.data_subject import (
    DataSubjectRight,
    RequestStatus,
    DataSubjectRequest,
    DataInventoryItem,
    DataSubjectService,
    get_data_subject_service,
)

__all__ = [
    # GDPR
    "GDPRService",
    "DataProcessingPurpose",
    "LawfulBasis",
    "ProcessingRecord",
    "ConsentRecord",
    "get_gdpr_service",
    # Data Subject Rights
    "DataSubjectRight",
    "RequestStatus",
    "DataSubjectRequest",
    "DataInventoryItem",
    "DataSubjectService",
    "get_data_subject_service",
]
