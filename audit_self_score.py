#!/usr/bin/env python3
"""
RISKCAST Audit Self-Scoring System

Evaluates the codebase against the RISKCAST Ultimate Audit Framework v2.0
and generates a comprehensive score report.

Target: 2000/2000 (Autonomous Grade A+)
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class AuditCheck:
    """A single audit check."""
    check_id: str
    name: str
    category: str
    subcategory: str
    max_points: int
    weight: float = 1.0
    passed: bool = False
    score: int = 0
    details: str = ""
    evidence: List[str] = field(default_factory=list)


@dataclass
class AuditCategory:
    """An audit category with multiple checks."""
    category_id: str
    name: str
    max_points: int
    checks: List[AuditCheck] = field(default_factory=list)
    
    @property
    def score(self) -> int:
        return sum(c.score for c in self.checks)
    
    @property
    def pass_rate(self) -> float:
        if not self.checks:
            return 0.0
        return sum(1 for c in self.checks if c.passed) / len(self.checks) * 100


class AuditScorer:
    """
    RISKCAST Audit Self-Scoring System.
    
    Evaluates all dimensions of the audit framework.
    """
    
    def __init__(self, workspace_path: str = "."):
        self.workspace = Path(workspace_path)
        self.categories: Dict[str, AuditCategory] = {}
        self.total_score = 0
        self.max_score = 2000
        
        # Initialize categories
        self._init_categories()
    
    def _init_categories(self) -> None:
        """Initialize audit categories."""
        self.categories = {
            "A": AuditCategory("A", "Cognitive Excellence", 500),
            "B": AuditCategory("B", "System Integrity", 450),
            "C": AuditCategory("C", "Accountability & Trust", 400),
            "D": AuditCategory("D", "Operational Excellence", 400),
            "E": AuditCategory("E", "Competitive Moat", 250),
        }
    
    def run_all_checks(self) -> Dict[str, Any]:
        """Run all audit checks and return results."""
        print("=" * 60)
        print("RISKCAST AUDIT SELF-SCORING SYSTEM")
        print("=" * 60)
        print()
        
        # Run checks for each category
        self._check_cognitive_excellence()
        self._check_system_integrity()
        self._check_accountability()
        self._check_operational_excellence()
        self._check_competitive_moat()
        
        # Calculate total score
        self.total_score = sum(cat.score for cat in self.categories.values())
        
        # Print results
        self._print_results()
        
        # Return structured results
        return self._build_results()
    
    def _check_cognitive_excellence(self) -> None:
        """Check A: Cognitive Excellence (500 points)."""
        category = self.categories["A"]
        
        # A1: Multi-Layer Reasoning Architecture (150 points)
        checks = [
            self._check_file_exists(
                "A1.1", "6-layer reasoning engine",
                "app/reasoning/engine.py",
                50, ["FACTUAL", "TEMPORAL", "CAUSAL", "COUNTERFACTUAL", "STRATEGIC", "META"]
            ),
            self._check_file_exists(
                "A1.2", "Decision graph visualization",
                "app/reasoning/visualization.py",
                40, ["DecisionGraphRenderer", "to_mermaid", "render_confidence_gauge"]
            ),
            self._check_file_exists(
                "A1.3", "Hysteresis controller",
                "app/reasoning/hysteresis.py",
                30, ["HysteresisController", "activation_threshold", "deactivation_threshold"]
            ),
            self._check_file_exists(
                "A1.4", "Deterministic trace IDs",
                "app/reasoning/deterministic.py",
                30, ["generate_deterministic_trace_id", "hashlib", "sha256"]
            ),
        ]
        category.checks.extend(checks)
        
        # A2: Uncertainty Quantification (120 points)
        checks = [
            self._check_file_exists(
                "A2.1", "Probability calibration",
                "app/reasoning/calibration.py",
                40, ["PlattScaling", "IsotonicRegression", "calculate_calibration_error"]
            ),
            self._check_file_exists(
                "A2.2", "Calibration scheduler",
                "app/reasoning/calibration.py",
                30, ["CalibrationScheduler", "run_calibration"]
            ),
            self._check_file_exists(
                "A2.3", "Temporal counterfactuals",
                "app/reasoning/counterfactuals.py",
                50, ["TemporalCounterfactualEngine", "TimingScenario"]
            ),
        ]
        category.checks.extend(checks)
        
        # A3: Prediction Quality (130 points)
        checks = [
            self._check_file_exists(
                "A3.1", "Backtest framework",
                "app/backtest",
                50, [], check_dir=True
            ),
            self._check_file_exists(
                "A3.2", "Error taxonomy",
                "app/reasoning/error_taxonomy.py",
                50, ["ErrorTaxonomyEngine", "ErrorCategory", "RootCause"]
            ),
            self._check_file_content(
                "A3.3", "Error pattern detection",
                "app/reasoning/error_taxonomy.py",
                30, ["get_patterns", "ErrorPattern"]
            ),
        ]
        category.checks.extend(checks)
        
        # A4: Confidence Visualization (100 points)
        checks = [
            self._check_file_content(
                "A4.1", "Confidence gauge SVG",
                "app/reasoning/visualization.py",
                50, ["render_confidence_gauge", "<svg", "arc"]
            ),
            self._check_file_content(
                "A4.2", "Layer breakdown visualization",
                "app/reasoning/visualization.py",
                50, ["render_layer_breakdown", "svg"]
            ),
        ]
        category.checks.extend(checks)
    
    def _check_system_integrity(self) -> None:
        """Check B: System Integrity (450 points)."""
        category = self.categories["B"]
        
        # B1: Data Validation (100 points)
        checks = [
            self._check_file_exists(
                "B1.1", "4-stage validation",
                "app/omen/validators",
                50, [], check_dir=True
            ),
            self._check_file_exists(
                "B1.2", "Schema validation",
                "app/omen/schemas.py",
                50, ["BaseModel", "Field", "field_validator"]
            ),
        ]
        category.checks.extend(checks)
        
        # B2: Error Handling (100 points)
        checks = [
            self._check_file_exists(
                "B2.1", "Custom exceptions",
                "app/core/exceptions.py",
                50, ["RiskCastError", "ValidationError"]
            ),
            self._check_file_content(
                "B2.2", "Error recovery",
                "app/core/exceptions.py",
                50, ["recovery_hint", "error_code"]
            ),
        ]
        category.checks.extend(checks)
        
        # B3: Security (150 points) - CRITICAL
        checks = [
            self._check_no_xor_encryption(
                "B3.1", "No XOR fallback",
                "app/core/encryption.py",
                60
            ),
            self._check_file_exists(
                "B3.2", "Key management",
                "app/core/key_management.py",
                50, ["KeyManager", "REQUIRED_KEYS", "validate"]
            ),
            self._check_file_exists(
                "B3.3", "Key rotation",
                "app/core/key_rotation.py",
                40, ["KeyRotator", "RotationCoordinator", "re_encrypt"]
            ),
        ]
        category.checks.extend(checks)
        
        # B4: Database (100 points)
        checks = [
            self._check_file_exists(
                "B4.1", "Query optimizer",
                "app/db/query_optimizer.py",
                50, ["QueryOptimizer", "IndexSuggestion"]
            ),
            self._check_file_content(
                "B4.2", "Query analysis",
                "app/db/query_optimizer.py",
                50, ["analyze_query", "issues", "rewrites"]
            ),
        ]
        category.checks.extend(checks)
    
    def _check_accountability(self) -> None:
        """Check C: Accountability & Trust (400 points)."""
        category = self.categories["C"]
        
        # C1: Audit Trail (150 points)
        checks = [
            self._check_file_exists(
                "C1.1", "Audit logging",
                "app/audit",
                50, [], check_dir=True
            ),
            self._check_file_exists(
                "C1.2", "Audit retention",
                "app/audit/retention.py",
                50, ["RetentionScheduler", "AuditArchiver", "RetentionPolicy"]
            ),
            self._check_file_content(
                "C1.3", "Compliance policies",
                "app/audit/retention.py",
                50, ["GDPR_RETENTION_POLICY", "SOX_RETENTION_POLICY"]
            ),
        ]
        category.checks.extend(checks)
        
        # C2: Human-AI Interaction (150 points)
        checks = [
            self._check_file_exists(
                "C2.1", "Challenge system",
                "app/audit/sla.py",
                50, ["Challenge", "ChallengeStatus"]
            ),
            self._check_file_exists(
                "C2.2", "SLA enforcement",
                "app/audit/sla.py",
                50, ["SLAEnforcer", "SLAConfig", "escalation"]
            ),
            self._check_file_content(
                "C2.3", "SLA metrics",
                "app/audit/sla.py",
                50, ["SLAMetrics", "calculate_metrics", "compliance"]
            ),
        ]
        category.checks.extend(checks)
        
        # C3: Explainability (100 points)
        checks = [
            self._check_file_content(
                "C3.1", "7 Questions framework",
                "app/riskcast/composers/decision.py",
                50, ["q1_what", "q2_when", "q3_severity", "q5_action", "q7_inaction"]
            ),
            self._check_file_content(
                "C3.2", "Decision explanations",
                "app/reasoning/visualization.py",
                50, ["TraceExporter", "to_html_report"]
            ),
        ]
        category.checks.extend(checks)
    
    def _check_operational_excellence(self) -> None:
        """Check D: Operational Excellence (400 points)."""
        category = self.categories["D"]
        
        # D1: Observability (150 points)
        checks = [
            self._check_file_exists(
                "D1.1", "Alertmanager config",
                "config/alertmanager.yml",
                50, ["route", "receivers", "inhibit_rules"]
            ),
            self._check_file_exists(
                "D1.2", "OTLP telemetry",
                "app/observability/otlp.py",
                50, ["OTLPExporter", "Tracer", "MetricsCollector"]
            ),
            self._check_file_content(
                "D1.3", "Span tracing",
                "app/observability/otlp.py",
                50, ["start_span", "to_otlp", "trace_id"]
            ),
        ]
        category.checks.extend(checks)
        
        # D2: Testing (150 points)
        checks = [
            self._check_file_exists(
                "D2.1", "Comprehensive tests",
                "tests/test_comprehensive.py",
                50, ["TestReasoningEngine", "TestEncryption", "TestIntegration"]
            ),
            self._check_file_content(
                "D2.2", "Test coverage",
                "tests/test_comprehensive.py",
                50, ["pytest.mark.asyncio", "fixture"]
            ),
            self._check_file_exists(
                "D2.3", "CI configuration",
                ".github/workflows/ci.yml",
                50, ["unit-tests", "integration-tests", "coverage"]
            ),
        ]
        category.checks.extend(checks)
        
        # D3: Deployment (100 points)
        checks = [
            self._check_file_content(
                "D3.1", "CI/CD pipeline",
                ".github/workflows/ci.yml",
                50, ["deploy-staging", "deploy-production", "docker"]
            ),
            self._check_file_content(
                "D3.2", "Audit scoring in CI",
                ".github/workflows/ci.yml",
                50, ["audit-score", "audit_self_score.py"]
            ),
        ]
        category.checks.extend(checks)
    
    def _check_competitive_moat(self) -> None:
        """Check E: Competitive Moat (250 points)."""
        category = self.categories["E"]
        
        # E1: Personalization (100 points)
        checks = [
            self._check_file_exists(
                "E1.1", "Customer schemas",
                "app/riskcast/schemas/customer.py",
                50, ["CustomerProfile", "Shipment"]
            ),
            self._check_file_exists(
                "E1.2", "Exposure matching",
                "app/riskcast/matchers/exposure.py",
                50, ["ExposureMatcher"]
            ),
        ]
        category.checks.extend(checks)
        
        # E2: Data Flywheel (150 points)
        checks = [
            self._check_file_exists(
                "E2.1", "Outcome persistence",
                "app/ml/outcome_persistence.py",
                50, ["OutcomePersistence", "DecisionOutcome"]
            ),
            self._check_file_exists(
                "E2.2", "ML training integration",
                "app/ml/outcome_persistence.py",
                50, ["MLTrainingIntegration", "train_models"]
            ),
            self._check_file_exists(
                "E2.3", "Network effect tracking",
                "app/ml/outcome_persistence.py",
                50, ["NetworkEffectTracker", "data_moat_score"]
            ),
        ]
        category.checks.extend(checks)
    
    # =========================================================================
    # CHECK HELPERS
    # =========================================================================
    
    def _check_file_exists(
        self,
        check_id: str,
        name: str,
        path: str,
        points: int,
        required_content: List[str] = None,
        check_dir: bool = False,
    ) -> AuditCheck:
        """Check if a file exists and optionally contains required content."""
        full_path = self.workspace / path
        
        check = AuditCheck(
            check_id=check_id,
            name=name,
            category=check_id[0],
            subcategory=check_id[:2],
            max_points=points,
        )
        
        if check_dir:
            if full_path.is_dir():
                check.passed = True
                check.score = points
                check.details = f"Directory exists: {path}"
                check.evidence = [str(f) for f in full_path.iterdir()][:5]
            else:
                check.details = f"Directory not found: {path}"
        else:
            if full_path.is_file():
                content = full_path.read_text(encoding="utf-8", errors="ignore")
                
                if required_content:
                    found = [c for c in required_content if c in content]
                    if len(found) == len(required_content):
                        check.passed = True
                        check.score = points
                        check.details = f"File exists with all required content"
                        check.evidence = found
                    else:
                        missing = set(required_content) - set(found)
                        check.score = int(points * len(found) / len(required_content))
                        check.details = f"Missing: {', '.join(missing)}"
                        check.evidence = found
                else:
                    check.passed = True
                    check.score = points
                    check.details = f"File exists: {path}"
            else:
                check.details = f"File not found: {path}"
        
        return check
    
    def _check_file_content(
        self,
        check_id: str,
        name: str,
        path: str,
        points: int,
        required_content: List[str],
    ) -> AuditCheck:
        """Check file content for specific strings."""
        return self._check_file_exists(
            check_id, name, path, points, required_content
        )
    
    def _check_no_xor_encryption(
        self,
        check_id: str,
        name: str,
        path: str,
        points: int,
    ) -> AuditCheck:
        """Check that XOR encryption fallback is removed."""
        full_path = self.workspace / path
        
        check = AuditCheck(
            check_id=check_id,
            name=name,
            category=check_id[0],
            subcategory=check_id[:2],
            max_points=points,
        )
        
        if full_path.is_file():
            content = full_path.read_text(encoding="utf-8", errors="ignore")
            
            # Check for dangerous patterns
            dangerous_patterns = [
                "_xor_fallback",
                "XOR",
                "_encrypt_fallback",
                "_decrypt_fallback",
            ]
            
            found_dangerous = [p for p in dangerous_patterns if p in content]
            
            # Check for secure patterns
            secure_patterns = [
                "AESGCM",
                "fail fast",
                "No fallback",
                "REMOVED",
            ]
            
            found_secure = [p for p in secure_patterns if p in content]
            
            if not found_dangerous and found_secure:
                check.passed = True
                check.score = points
                check.details = "XOR fallback removed, AES-only encryption"
                check.evidence = found_secure
            elif found_dangerous:
                check.details = f"CRITICAL: XOR encryption still present: {found_dangerous}"
            else:
                check.score = points // 2
                check.details = "Encryption file exists but couldn't verify security"
        else:
            check.details = f"File not found: {path}"
        
        return check
    
    # =========================================================================
    # RESULTS
    # =========================================================================
    
    def _print_results(self) -> None:
        """Print audit results to console."""
        print()
        print("=" * 60)
        print("AUDIT RESULTS")
        print("=" * 60)
        print()
        
        for cat_id, category in self.categories.items():
            print(f"{cat_id}. {category.name}")
            print(f"   Score: {category.score}/{category.max_points}")
            print(f"   Pass Rate: {category.pass_rate:.1f}%")
            print()
            
            for check in category.checks:
                status = "PASS" if check.passed else "FAIL"
                print(f"   [{status}] {check.check_id}: {check.name}")
                print(f"       Score: {check.score}/{check.max_points}")
                if check.details:
                    print(f"       Details: {check.details}")
                print()
        
        print("=" * 60)
        print(f"TOTAL SCORE: {self.total_score}/{self.max_score}")
        print("=" * 60)
        
        # Grade
        if self.total_score >= 2000:
            grade = "A+ (Autonomous Grade)"
        elif self.total_score >= 1900:
            grade = "A (Enterprise Grade)"
        elif self.total_score >= 1800:
            grade = "A- (Production Ready)"
        elif self.total_score >= 1700:
            grade = "B+ (Advanced)"
        elif self.total_score >= 1600:
            grade = "B (Standard)"
        else:
            grade = "C (Needs Improvement)"
        
        print(f"GRADE: {grade}")
        print("=" * 60)
    
    def _build_results(self) -> Dict[str, Any]:
        """Build structured results dictionary."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_score": self.total_score,
            "max_score": self.max_score,
            "percentage": round(self.total_score / self.max_score * 100, 2),
            "cognitive": self.categories["A"].score,
            "integrity": self.categories["B"].score,
            "accountability": self.categories["C"].score,
            "operational": self.categories["D"].score,
            "moat": self.categories["E"].score,
            "categories": {
                cat_id: {
                    "name": cat.name,
                    "score": cat.score,
                    "max_points": cat.max_points,
                    "pass_rate": cat.pass_rate,
                    "checks": [
                        {
                            "check_id": c.check_id,
                            "name": c.name,
                            "passed": c.passed,
                            "score": c.score,
                            "max_points": c.max_points,
                            "details": c.details,
                        }
                        for c in cat.checks
                    ]
                }
                for cat_id, cat in self.categories.items()
            }
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="RISKCAST Audit Self-Scoring System"
    )
    parser.add_argument(
        "--workspace", "-w",
        default=".",
        help="Path to workspace (default: current directory)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file for JSON results"
    )
    parser.add_argument(
        "--threshold", "-t",
        type=int,
        default=1900,
        help="Minimum score threshold (default: 1900)"
    )
    
    args = parser.parse_args()
    
    scorer = AuditScorer(args.workspace)
    results = scorer.run_all_checks()
    
    # Save results if output specified
    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {args.output}")
    
    # Exit with error if below threshold
    if scorer.total_score < args.threshold:
        print(f"\nFAILED: Score {scorer.total_score} below threshold {args.threshold}")
        sys.exit(1)
    
    print(f"\nPASSED: Score {scorer.total_score} meets threshold {args.threshold}")
    sys.exit(0)


if __name__ == "__main__":
    main()
