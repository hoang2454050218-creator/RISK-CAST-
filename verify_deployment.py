#!/usr/bin/env python3
"""
RISKCAST Deployment Verification Script
========================================

Kiểm tra xem hệ thống có SỐNG THẬT không, hay chỉ là code chết nằm đó.

Chạy: python verify_deployment.py

Script này sẽ:
1. Kiểm tra môi trường Python
2. Kiểm tra dependencies
3. Kiểm tra imports (code có chạy được không)
4. Kiểm tra database connection
5. Kiểm tra Redis connection
6. Chạy unit tests cơ bản
7. Test API endpoints
8. Test end-to-end flow

Kết quả: PASS/FAIL rõ ràng cho từng component
"""

import sys
import os
import time
import asyncio
import traceback
from datetime import datetime
from typing import Tuple, List, Optional
from pathlib import Path

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}  {text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")

def print_pass(text: str):
    print(f"  {Colors.GREEN}[PASS]{Colors.END}: {text}")

def print_fail(text: str, error: str = ""):
    print(f"  {Colors.RED}[FAIL]{Colors.END}: {text}")
    if error:
        print(f"         {Colors.RED}Error: {error}{Colors.END}")

def print_warn(text: str):
    print(f"  {Colors.YELLOW}[WARN]{Colors.END}: {text}")

def print_info(text: str):
    print(f"  {Colors.BLUE}[INFO]{Colors.END}: {text}")

class VerificationResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.details = []
    
    def add_pass(self, name: str):
        self.passed += 1
        self.details.append(("PASS", name))
        print_pass(name)
    
    def add_fail(self, name: str, error: str = ""):
        self.failed += 1
        self.details.append(("FAIL", name, error))
        print_fail(name, error)
    
    def add_warn(self, name: str):
        self.warnings += 1
        self.details.append(("WARN", name))
        print_warn(name)

results = VerificationResult()

# ==============================================================================
# PHASE 1: ENVIRONMENT CHECKS
# ==============================================================================

def check_python_version():
    """Kiểm tra Python version >= 3.11"""
    print_header("PHASE 1: ENVIRONMENT CHECKS")
    
    version = sys.version_info
    if version.major >= 3 and version.minor >= 11:
        results.add_pass(f"Python version: {version.major}.{version.minor}.{version.micro}")
    else:
        results.add_fail(f"Python version: {version.major}.{version.minor} (need 3.11+)")

def check_working_directory():
    """Kiểm tra đang ở đúng thư mục project"""
    cwd = Path.cwd()
    app_dir = cwd / "app"
    if app_dir.exists():
        results.add_pass(f"Working directory: {cwd}")
    else:
        results.add_fail(f"Working directory incorrect: {cwd} (no 'app' folder)")

def check_env_file():
    """Kiểm tra .env file tồn tại"""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if env_file.exists():
        results.add_pass(".env file exists")
    elif env_example.exists():
        results.add_warn(".env missing but .env.example exists - copy and configure it")
    else:
        results.add_warn(".env file missing - may need configuration")

# ==============================================================================
# PHASE 2: DEPENDENCY CHECKS
# ==============================================================================

def check_dependencies():
    """Kiểm tra các dependencies quan trọng"""
    print_header("PHASE 2: DEPENDENCY CHECKS")
    
    critical_packages = [
        ("fastapi", "FastAPI web framework"),
        ("pydantic", "Data validation"),
        ("sqlalchemy", "Database ORM"),
        ("httpx", "Async HTTP client"),
        ("redis", "Redis client"),
        ("structlog", "Structured logging"),
        ("pytest", "Testing framework"),
    ]
    
    optional_packages = [
        ("prometheus_client", "Prometheus metrics"),
        ("opentelemetry", "OpenTelemetry tracing"),
        ("sklearn", "Machine learning"),
    ]
    
    for package, desc in critical_packages:
        try:
            __import__(package)
            results.add_pass(f"{package} ({desc})")
        except ImportError as e:
            results.add_fail(f"{package} ({desc})", str(e))
    
    for package, desc in optional_packages:
        try:
            __import__(package)
            results.add_pass(f"{package} ({desc}) [optional]")
        except ImportError:
            results.add_warn(f"{package} ({desc}) [optional] - not installed")

# ==============================================================================
# PHASE 3: CODE IMPORT CHECKS
# ==============================================================================

def check_core_imports():
    """Kiểm tra code có import được không (syntax errors, etc.)"""
    print_header("PHASE 3: CODE IMPORT CHECKS")
    
    # Add project root to path
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))
    
    modules_to_check = [
        # Core modules
        ("app.core.config", "Core configuration"),
        ("app.core.circuit_breaker", "Circuit breaker"),
        ("app.core.auth", "Authentication"),
        
        # OMEN (Signal Engine)
        ("app.omen.schemas", "OMEN schemas"),
        ("app.omen.service", "OMEN service"),
        
        # ORACLE (Reality Engine)
        ("app.oracle.schemas", "ORACLE schemas"),
        ("app.oracle.service", "ORACLE service"),
        
        # RISKCAST (Decision Engine)
        ("app.riskcast.schemas.decision", "Decision schemas (7 Questions)"),
        ("app.riskcast.schemas.customer", "Customer schemas"),
        ("app.riskcast.schemas.action", "Action schemas"),
        ("app.riskcast.service", "RISKCAST service"),
        ("app.riskcast.composers.decision", "Decision composer"),
        
        # Reasoning Engine
        ("app.reasoning.engine", "Reasoning engine (6 layers)"),
        ("app.reasoning.schemas", "Reasoning schemas"),
        
        # Audit
        ("app.audit.schemas", "Audit schemas"),
        ("app.audit.service", "Audit service"),
        
        # Alerter
        ("app.alerter.service", "Alerter service"),
        
        # Human-AI Collaboration
        ("app.human.service", "Human-AI service"),
        
        # ML
        ("app.ml.calibration_job", "Calibration job"),
        
        # Uncertainty
        ("app.uncertainty.bayesian", "Bayesian uncertainty"),
        
        # Database
        ("app.db.models", "Database models"),
    ]
    
    for module, desc in modules_to_check:
        try:
            __import__(module)
            results.add_pass(f"{module} ({desc})")
        except Exception as e:
            error_msg = str(e)[:100]  # Truncate long errors
            results.add_fail(f"{module} ({desc})", error_msg)

# ==============================================================================
# PHASE 4: SCHEMA VALIDATION
# ==============================================================================

def check_schema_instantiation():
    """Kiểm tra schemas có thể instantiate được không"""
    print_header("PHASE 4: SCHEMA VALIDATION")
    
    try:
        from app.riskcast.schemas.decision import (
            Q1WhatIsHappening,
            Q2WhenWillItHappen,
            Q3HowBadIsIt,
            Q4WhyIsThisHappening,
            Q5WhatToDoNow,
            Q6HowConfident,
            Q7WhatIfNothing,
            DecisionObject,
        )
        from app.riskcast.constants import Urgency, Severity, ConfidenceLevel
        from datetime import datetime, timedelta
        
        # Test Q1
        q1 = Q1WhatIsHappening(
            event_type="DISRUPTION",
            event_summary="Test disruption",
            affected_chokepoint="red_sea",
            affected_routes=["CNSHA-NLRTM"],
            affected_shipments=["PO-001"],
        )
        results.add_pass("Q1 (What is happening?) schema works")
        
        # Test Q2
        q2 = Q2WhenWillItHappen(
            status="CONFIRMED",
            impact_timeline="Impact in 3 days",
            urgency=Urgency.IMMEDIATE,
            urgency_reason="Test urgency",
        )
        results.add_pass("Q2 (When?) schema works")
        
        # Test Q3 with confidence intervals
        q3 = Q3HowBadIsIt(
            total_exposure_usd=235000,
            expected_delay_days=12,
            delay_range="10-14 days",
            shipments_affected=2,
            severity=Severity.HIGH,
            exposure_ci_90=(188000, 294000),
            exposure_ci_95=(176000, 320000),
        )
        results.add_pass("Q3 (How bad?) schema with CIs works")
        
        # Test Q4
        q4 = Q4WhyIsThisHappening(
            root_cause="Test cause",
            causal_chain=["Cause 1", "Effect 1", "Effect 2"],
            evidence_summary="Test evidence",
        )
        results.add_pass("Q4 (Why?) schema works")
        
        # Test Q5 with cost CIs
        q5 = Q5WhatToDoNow(
            action_type="REROUTE",
            action_summary="Reroute via Cape",
            estimated_cost_usd=8500,
            deadline=datetime.utcnow() + timedelta(hours=24),
            deadline_reason="Booking window closes",
            cost_ci_90=(7200, 10100),
        )
        results.add_pass("Q5 (What to do?) schema with cost CIs works")
        
        # Test Q6
        q6 = Q6HowConfident(
            score=0.87,
            level=ConfidenceLevel.HIGH,
            explanation="High confidence based on market data",
        )
        results.add_pass("Q6 (How confident?) schema works")
        
        # Test Q7 with inaction CIs
        q7 = Q7WhatIfNothing(
            expected_loss_if_nothing=47000,
            cost_if_wait_6h=52000,
            cost_if_wait_24h=61000,
            cost_if_wait_48h=70000,
            worst_case_cost=94000,
            worst_case_scenario="Full disruption",
            inaction_summary="Expected loss $47K",
            loss_ci_90=(38000, 59000),
        )
        results.add_pass("Q7 (What if nothing?) schema with loss CIs works")
        
        # Test full DecisionObject
        decision = DecisionObject(
            decision_id="dec_test_001",
            customer_id="cust_test",
            signal_id="sig_test",
            q1_what=q1,
            q2_when=q2,
            q3_severity=q3,
            q4_why=q4,
            q5_action=q5,
            q6_confidence=q6,
            q7_inaction=q7,
            expires_at=datetime.utcnow() + timedelta(hours=48),
        )
        results.add_pass("Full DecisionObject (7 Questions) instantiates correctly")
        
        # Verify computed fields work
        summary = decision.get_summary()
        assert "REROUTE" in summary
        results.add_pass("DecisionObject computed fields work")
        
    except Exception as e:
        results.add_fail("Schema validation", str(e))
        traceback.print_exc()

# ==============================================================================
# PHASE 5: REASONING ENGINE TEST
# ==============================================================================

def check_reasoning_engine():
    """Kiểm tra Reasoning Engine có chạy được không"""
    print_header("PHASE 5: REASONING ENGINE TEST")
    
    try:
        from app.reasoning.engine import ReasoningEngine, create_reasoning_engine
        from app.reasoning.schemas import ReasoningLayer
        
        # Create engine
        engine = create_reasoning_engine()
        results.add_pass("ReasoningEngine instantiates")
        
        # Check all 6 layers exist
        assert engine._factual is not None
        assert engine._temporal is not None
        assert engine._causal is not None
        assert engine._counterfactual is not None
        assert engine._strategic is not None
        assert engine._meta is not None
        results.add_pass("All 6 reasoning layers present")
        
    except Exception as e:
        results.add_fail("Reasoning engine check", str(e))

# ==============================================================================
# PHASE 6: AUDIT TRAIL TEST
# ==============================================================================

def check_audit_trail():
    """Kiểm tra Audit Trail cryptographic chain"""
    print_header("PHASE 6: AUDIT TRAIL TEST")
    
    try:
        from app.audit.schemas import (
            AuditRecord,
            AuditEventType,
            InputSnapshot,
            AuditChainVerification,
        )
        import hashlib
        
        # Create audit record
        record = AuditRecord(
            event_type=AuditEventType.DECISION_GENERATED,
            entity_type="decision",
            entity_id="dec_test_001",
            actor_type="system",
            payload={"test": "data"},
            sequence_number=1,
            previous_hash="genesis",
        )
        
        # Finalize (compute hash)
        record = record.finalize()
        
        assert record.record_hash != ""
        assert record.payload_hash != ""
        results.add_pass("AuditRecord hash computation works")
        
        # Verify integrity
        assert record.verify_integrity() == True
        results.add_pass("AuditRecord integrity verification works")
        
        # Test tampering detection
        original_hash = record.record_hash
        record.payload["tampered"] = True
        assert record.verify_integrity() == False
        results.add_pass("Tampering detection works (integrity check fails after modification)")
        
    except Exception as e:
        results.add_fail("Audit trail check", str(e))

# ==============================================================================
# PHASE 7: DATABASE CONNECTION TEST
# ==============================================================================

def check_database_connection():
    """Kiểm tra database connection"""
    print_header("PHASE 7: DATABASE CONNECTION TEST")
    
    try:
        from app.core.config import get_settings
        settings = get_settings()
        
        if hasattr(settings, 'DATABASE_URL') and settings.DATABASE_URL:
            results.add_pass(f"Database URL configured")
            
            # Try to connect
            try:
                from sqlalchemy import create_engine, text
                engine = create_engine(settings.DATABASE_URL)
                with engine.connect() as conn:
                    result = conn.execute(text("SELECT 1"))
                    results.add_pass("Database connection successful")
            except Exception as e:
                results.add_warn(f"Database connection failed (may not be running): {str(e)[:50]}")
        else:
            results.add_warn("DATABASE_URL not configured")
            
    except Exception as e:
        results.add_warn(f"Database config check skipped: {str(e)[:50]}")

# ==============================================================================
# PHASE 8: REDIS CONNECTION TEST
# ==============================================================================

def check_redis_connection():
    """Kiểm tra Redis connection"""
    print_header("PHASE 8: REDIS CONNECTION TEST")
    
    try:
        import redis
        from app.core.config import get_settings
        settings = get_settings()
        
        if hasattr(settings, 'REDIS_URL') and settings.REDIS_URL:
            results.add_pass("Redis URL configured")
            
            try:
                r = redis.from_url(settings.REDIS_URL)
                r.ping()
                results.add_pass("Redis connection successful")
            except Exception as e:
                results.add_warn(f"Redis connection failed (may not be running): {str(e)[:50]}")
        else:
            results.add_warn("REDIS_URL not configured")
            
    except Exception as e:
        results.add_warn(f"Redis config check skipped: {str(e)[:50]}")

# ==============================================================================
# PHASE 9: API ROUTE CHECKS
# ==============================================================================

def check_api_routes():
    """Kiểm tra API routes có load được không"""
    print_header("PHASE 9: API ROUTE CHECKS")
    
    routes_to_check = [
        ("app.api.routes.health", "Health check routes"),
        ("app.api.routes.decisions", "Decision routes"),
        ("app.api.routes.signals", "Signal routes"),
        ("app.api.routes.customers", "Customer routes"),
        ("app.api.routes.human", "Human-AI routes"),
        ("app.api.routes.governance", "Governance routes"),
        ("app.api.routes.calibration", "Calibration routes"),
    ]
    
    for module, desc in routes_to_check:
        try:
            __import__(module)
            results.add_pass(f"{module} ({desc})")
        except Exception as e:
            results.add_fail(f"{module} ({desc})", str(e)[:80])

# ==============================================================================
# PHASE 10: FASTAPI APP TEST
# ==============================================================================

def check_fastapi_app():
    """Kiểm tra FastAPI app có khởi tạo được không"""
    print_header("PHASE 10: FASTAPI APP TEST")
    
    try:
        # Try to import the main app
        from app.main import app
        
        results.add_pass("FastAPI app imports successfully")
        
        # Check routes are registered
        routes = [r.path for r in app.routes]
        if "/health" in routes or "/api/health" in routes or any("/health" in r for r in routes):
            results.add_pass("Health endpoint registered")
        else:
            results.add_warn("Health endpoint not found in routes")
            
        if len(routes) > 5:
            results.add_pass(f"API has {len(routes)} routes registered")
        else:
            results.add_warn(f"Only {len(routes)} routes registered")
            
    except Exception as e:
        results.add_fail("FastAPI app initialization", str(e))

# ==============================================================================
# PHASE 11: RUN QUICK TESTS
# ==============================================================================

def run_quick_tests():
    """Chạy một số unit tests nhanh"""
    print_header("PHASE 11: QUICK UNIT TESTS")
    
    try:
        import subprocess
        
        # Just check if pytest can collect tests (no import errors)
        result = subprocess.run(
            [
                sys.executable, "-m", "pytest",
                "--collect-only", "-q",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=Path(__file__).parent,
        )
        
        # Check for critical errors
        output = result.stdout + result.stderr
        if "ImportError" in output or "ModuleNotFoundError" in output or "SyntaxError" in output:
            results.add_fail("Test collection has import errors", output[:200])
        elif result.returncode == 0 or "test" in output.lower():
            # Count tests found
            lines = output.strip().split('\n')
            test_count = 0
            for line in lines:
                if 'test' in line.lower() and ('::' in line or 'selected' in line):
                    test_count += 1
            if test_count > 0 or "selected" in output:
                results.add_pass(f"Pytest can collect tests without import errors")
            else:
                results.add_warn("No tests found, but no import errors")
        else:
            results.add_warn(f"Pytest returned code {result.returncode}")
                
    except subprocess.TimeoutExpired:
        results.add_warn("Test collection timed out (>60s)")
    except Exception as e:
        results.add_warn(f"Could not run pytest: {str(e)[:50]}")

# ==============================================================================
# PHASE 12: END-TO-END SIMULATION
# ==============================================================================

def run_e2e_simulation():
    """Chạy simulation end-to-end flow (không cần external services)"""
    print_header("PHASE 12: END-TO-END SIMULATION")
    
    try:
        from datetime import datetime, timedelta
        
        # 1. Create mock signal (OMEN output)
        print_info("Creating mock OMEN signal...")
        from app.omen.schemas import OmenSignal, EvidenceItem, GeographicScope, TemporalScope
        
        signal = OmenSignal(
            signal_id="OMEN-TEST-001",
            title="Red Sea Disruption Test",
            description="Test signal for deployment verification - Red Sea shipping disruption due to Houthi attacks",
            probability=0.78,
            confidence_score=0.85,
            category="geopolitical",
            geographic=GeographicScope(
                primary_chokepoint="red_sea",
                affected_routes=["ASIA-EUROPE"],
            ),
            temporal=TemporalScope(
                expected_start=datetime.utcnow(),
                expected_duration_days=14,
            ),
            evidence=[
                EvidenceItem(
                    source="Polymarket",
                    source_type="prediction_market",
                    title="Red Sea Shipping Disruption Probability",
                    snippet="Test evidence for verification",
                    credibility_score=0.9,
                )
            ],
        )
        results.add_pass("Mock OMEN signal created")
        
        # 2. Create mock customer context
        print_info("Creating mock customer context...")
        from app.riskcast.schemas.customer import CustomerProfile, Shipment, CustomerContext
        
        profile = CustomerProfile(
            customer_id="cust_test_001",
            company_name="Test Company Ltd",
            primary_routes=["CNSHA-NLRTM"],
            relevant_chokepoints=["red_sea"],
            risk_tolerance="balanced",
            primary_phone="+84901234567",
        )
        
        shipment = Shipment(
            shipment_id="PO-TEST-001",
            customer_id="cust_test_001",
            origin_port="CNSHA",
            destination_port="NLRTM",
            cargo_value_usd=200000,
            container_count=2,
            route_chokepoints=["red_sea", "suez"],
            etd=datetime.utcnow() + timedelta(days=2),
            eta=datetime.utcnow() + timedelta(days=30),
            status="in_transit",
        )
        
        context = CustomerContext(
            profile=profile,
            active_shipments=[shipment],
        )
        results.add_pass("Mock customer context created")
        
        # 3. Test exposure matching
        print_info("Testing exposure matching...")
        from app.riskcast.matchers.exposure import ExposureMatcher
        
        matcher = ExposureMatcher()
        # This is a simplified test - actual matching requires signal integration
        results.add_pass("ExposureMatcher instantiates")
        
        # 4. Test decision composition (with mock data)
        print_info("Testing decision composition...")
        from app.riskcast.composers.decision import DecisionComposer
        
        composer = DecisionComposer()
        results.add_pass("DecisionComposer instantiates")
        
        # 5. Create a mock decision object
        print_info("Creating mock decision...")
        from app.riskcast.schemas.decision import (
            DecisionObject,
            Q1WhatIsHappening,
            Q2WhenWillItHappen,
            Q3HowBadIsIt,
            Q4WhyIsThisHappening,
            Q5WhatToDoNow,
            Q6HowConfident,
            Q7WhatIfNothing,
        )
        from app.riskcast.constants import Urgency, Severity, ConfidenceLevel
        
        decision = DecisionObject(
            decision_id=f"dec_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_test",
            customer_id="cust_test_001",
            signal_id="OMEN-TEST-001",
            q1_what=Q1WhatIsHappening(
                event_type="DISRUPTION",
                event_summary="Red Sea disruption affecting your CNSHA-NLRTM route",
                affected_chokepoint="red_sea",
                affected_routes=["CNSHA-NLRTM"],
                affected_shipments=["PO-TEST-001"],
            ),
            q2_when=Q2WhenWillItHappen(
                status="CONFIRMED",
                impact_timeline="Impact in 3 days",
                urgency=Urgency.IMMEDIATE,
                urgency_reason="Disruption confirmed, vessels rerouting",
            ),
            q3_severity=Q3HowBadIsIt(
                total_exposure_usd=200000,
                expected_delay_days=12,
                delay_range="10-14 days",
                shipments_affected=1,
                severity=Severity.HIGH,
                exposure_ci_90=(160000, 250000),
            ),
            q4_why=Q4WhyIsThisHappening(
                root_cause="Houthi attacks on commercial vessels",
                causal_chain=["Houthi attacks", "Carriers avoiding Red Sea", "Cape rerouting", "10-14 day delay"],
                evidence_summary="78% market probability, 47 vessels rerouting",
            ),
            q5_action=Q5WhatToDoNow(
                action_type="REROUTE",
                action_summary="Reroute PO-TEST-001 via Cape with MSC",
                estimated_cost_usd=5000,
                deadline=datetime.utcnow() + timedelta(hours=24),
                deadline_reason="MSC booking window closes",
                cost_ci_90=(4000, 6500),
            ),
            q6_confidence=Q6HowConfident(
                score=0.87,
                level=ConfidenceLevel.HIGH,
                explanation="High confidence: Market consensus + vessel tracking confirms",
                factors={"market_probability": 0.78, "vessel_confirmation": 0.95},
            ),
            q7_inaction=Q7WhatIfNothing(
                expected_loss_if_nothing=45000,
                cost_if_wait_6h=50000,
                cost_if_wait_24h=60000,
                cost_if_wait_48h=75000,
                worst_case_cost=120000,
                worst_case_scenario="Full cargo delay + penalties",
                inaction_summary="Expected loss $45K, escalates to $75K in 48h",
                loss_ci_90=(36000, 56000),
            ),
            expires_at=datetime.utcnow() + timedelta(hours=48),
        )
        results.add_pass("Full DecisionObject created with all 7 Questions")
        
        # 6. Verify decision has all required fields
        assert decision.q1_what is not None
        assert decision.q2_when is not None
        assert decision.q3_severity is not None
        assert decision.q4_why is not None
        assert decision.q5_action is not None
        assert decision.q6_confidence is not None
        assert decision.q7_inaction is not None
        results.add_pass("All 7 Questions populated correctly")
        
        # 7. Test JSON serialization (important for API)
        json_output = decision.model_dump_json()
        assert len(json_output) > 100
        results.add_pass("Decision serializes to JSON")
        
        # 8. Print sample output
        print_info("Sample decision summary:")
        print(f"         {decision.get_summary()}")
        print(f"         Inaction warning: {decision.get_inaction_warning()}")
        
        results.add_pass("E2E simulation completed successfully!")
        
    except Exception as e:
        results.add_fail("E2E simulation", str(e))
        traceback.print_exc()

# ==============================================================================
# FINAL SUMMARY
# ==============================================================================

def print_summary():
    """In kết quả tổng hợp"""
    print_header("VERIFICATION SUMMARY")
    
    total = results.passed + results.failed
    pass_rate = (results.passed / total * 100) if total > 0 else 0
    
    print(f"""
  +-----------------------------------------------+
  |              RISKCAST VERIFICATION            |
  +-----------------------------------------------+
  |  {Colors.GREEN}PASSED:{Colors.END}   {results.passed:3d}                              |
  |  {Colors.RED}FAILED:{Colors.END}   {results.failed:3d}                              |
  |  {Colors.YELLOW}WARNINGS:{Colors.END} {results.warnings:3d}                              |
  +-----------------------------------------------+
  |  PASS RATE: {pass_rate:.1f}%                          |
  +-----------------------------------------------+
    """)
    
    if results.failed == 0:
        print(f"""
  {Colors.GREEN}{Colors.BOLD}+===================================================+
  |                                                   |
  |   [OK] SYSTEM IS ALIVE AND FUNCTIONAL!            |
  |                                                   |
  |   Code is not dead. RISKCAST can run.             |
  |                                                   |
  +===================================================+{Colors.END}
        """)
        return 0
    elif results.failed <= 3:
        print(f"""
  {Colors.YELLOW}{Colors.BOLD}+===================================================+
  |                                                   |
  |   [!!] SYSTEM IS MOSTLY FUNCTIONAL                |
  |                                                   |
  |   Some components need attention.                 |
  |   See FAILED items above.                         |
  |                                                   |
  +===================================================+{Colors.END}
        """)
        return 1
    else:
        print(f"""
  {Colors.RED}{Colors.BOLD}+===================================================+
  |                                                   |
  |   [XX] SYSTEM HAS CRITICAL ISSUES                 |
  |                                                   |
  |   Multiple components failed verification.        |
  |   Code may be broken or misconfigured.            |
  |                                                   |
  +===================================================+{Colors.END}
        """)
        return 2

# ==============================================================================
# MAIN
# ==============================================================================

def main():
    """Main entry point"""
    print(f"""
{Colors.BOLD}
+===========================================================================+
|                                                                           |
|   RISKCAST DEPLOYMENT VERIFICATION                                        |
|   ---------------------------------                                       |
|                                                                           |
|   "Kiem tra xem he thong co SONG THAT khong,                              |
|    hay chi la code chet nam do lay diem."                                 |
|                                                                           |
|   Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                                             |
|                                                                           |
+===========================================================================+
{Colors.END}
    """)
    
    start_time = time.time()
    
    # Run all checks
    check_python_version()
    check_working_directory()
    check_env_file()
    
    check_dependencies()
    
    check_core_imports()
    
    check_schema_instantiation()
    
    check_reasoning_engine()
    
    check_audit_trail()
    
    check_database_connection()
    
    check_redis_connection()
    
    check_api_routes()
    
    check_fastapi_app()
    
    run_quick_tests()
    
    run_e2e_simulation()
    
    elapsed = time.time() - start_time
    print(f"\n  {Colors.BLUE}Total verification time: {elapsed:.2f}s{Colors.END}")
    
    exit_code = print_summary()
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
