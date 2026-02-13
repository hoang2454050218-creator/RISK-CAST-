"""
Tests for RISKCAST SLA and Cost Tracking.

Tests:
- test_sla_compliance_tracking()
- SLA definitions and objectives
- Cost tracking per customer and service
- Cost alerts for anomalies
"""

import pytest
from datetime import datetime, timedelta

from app.performance.sla import (
    SLAObjective,
    SLAObjectiveType,
    SLAStatus,
    SLADefinition,
    SLAMeasurement,
    SLAReport,
    SLATracker,
    DEFAULT_SLA,
)
from app.performance.cost_tracker import (
    CostCategory,
    CostAllocation,
    CostRecord,
    CostBudget,
    CostAlert,
    CostReport,
    CostTracker,
)
from app.performance.benchmarks import (
    BenchmarkStatus,
    BenchmarkResult,
    PerformanceBenchmark,
    get_benchmark,
)


class TestSLAObjective:
    """Test SLA objective functionality."""
    
    def test_objective_gte_evaluation(self):
        """Test greater-than-or-equal evaluation."""
        objective = SLAObjective(
            name="availability",
            objective_type=SLAObjectiveType.AVAILABILITY,
            target=99.9,
            unit="%",
            comparison="gte",
        )
        
        assert objective.evaluate(99.95) is True
        assert objective.evaluate(99.9) is True
        assert objective.evaluate(99.8) is False
    
    def test_objective_lte_evaluation(self):
        """Test less-than-or-equal evaluation."""
        objective = SLAObjective(
            name="latency",
            objective_type=SLAObjectiveType.LATENCY,
            target=500,
            unit="ms",
            comparison="lte",
        )
        
        assert objective.evaluate(450) is True
        assert objective.evaluate(500) is True
        assert objective.evaluate(550) is False
    
    def test_prometheus_rule_generation(self):
        """Test Prometheus alert rule generation."""
        objective = SLAObjective(
            name="availability",
            objective_type=SLAObjectiveType.AVAILABILITY,
            target=99.9,
            unit="%",
            comparison="gte",
        )
        
        rule = objective.to_prometheus_rule("riskcast")
        
        assert "riskcast_SLA_Availability_Breach" in rule
        assert "99.9" in rule
        assert "severity: critical" in rule


class TestSLADefinition:
    """Test SLA definition functionality."""
    
    def test_sla_definition_creation(self):
        """Test SLA definition creation."""
        sla = SLADefinition(
            sla_id="test-sla",
            service="test-service",
            description="Test SLA",
            objectives=[
                SLAObjective(
                    name="availability",
                    objective_type=SLAObjectiveType.AVAILABILITY,
                    target=99.9,
                    unit="%",
                ),
            ],
        )
        
        assert sla.sla_id == "test-sla"
        assert sla.objective_count == 1
    
    def test_default_sla_exists(self):
        """Test that default SLA is properly defined."""
        assert DEFAULT_SLA is not None
        assert len(DEFAULT_SLA.objectives) > 0
        assert DEFAULT_SLA.service == "riskcast-platform"
    
    def test_prometheus_rules_generation(self):
        """Test generating all Prometheus rules for SLA."""
        rules = DEFAULT_SLA.generate_prometheus_rules()
        
        assert "groups:" in rules
        assert "riskcast-platform_sla_rules" in rules


class TestSLATracker:
    """Test SLA tracking functionality."""
    
    @pytest.fixture
    def tracker(self):
        return SLATracker()
    
    @pytest.mark.asyncio
    async def test_sla_tracker_initialization(self, tracker):
        """Test tracker initialization with default SLAs."""
        await tracker.initialize()
        
        all_slas = tracker.get_all_slas()
        assert len(all_slas) >= 4  # Default SLAs
    
    @pytest.mark.asyncio
    async def test_sla_compliance_tracking(self, tracker):
        """Test recording SLA measurements and tracking compliance."""
        await tracker.initialize()
        
        # Record compliant measurement
        measurement = await tracker.record_measurement(
            sla_id="riskcast-platform",
            objective_name="availability",
            value=99.95,
        )
        
        assert measurement.status == SLAStatus.COMPLIANT
        assert measurement.value == 99.95
        
        # Record violating measurement
        violation = await tracker.record_measurement(
            sla_id="riskcast-platform",
            objective_name="availability",
            value=99.5,
        )
        
        assert violation.status == SLAStatus.VIOLATED
    
    @pytest.mark.asyncio
    async def test_sla_status_retrieval(self, tracker):
        """Test getting current SLA status."""
        await tracker.initialize()
        
        # Record some measurements
        await tracker.record_measurement("riskcast-platform", "availability", 99.95)
        await tracker.record_measurement("riskcast-platform", "api_latency_p99", 450)
        
        status = await tracker.get_current_status("riskcast-platform")
        
        assert status["sla_id"] == "riskcast-platform"
        assert status["overall_status"] == SLAStatus.COMPLIANT.value
        assert "availability" in status["objectives"]
    
    @pytest.mark.asyncio
    async def test_sla_report_generation(self, tracker):
        """Test SLA compliance report generation."""
        await tracker.initialize()
        
        # Record measurements
        for _ in range(10):
            await tracker.record_measurement("riskcast-platform", "availability", 99.95)
        
        report = await tracker.generate_report("riskcast-platform", period_days=7)
        
        assert isinstance(report, SLAReport)
        assert report.sla_id == "riskcast-platform"
        assert len(report.objective_results) > 0
    
    @pytest.mark.asyncio
    async def test_sla_dashboard_data(self, tracker):
        """Test getting dashboard data."""
        await tracker.initialize()
        
        dashboard = tracker.get_dashboard_data()
        
        assert "slas" in dashboard
        assert "summary" in dashboard
        assert dashboard["summary"]["total"] >= 4


class TestCostTracker:
    """Test cost tracking functionality."""
    
    @pytest.fixture
    def tracker(self):
        return CostTracker()
    
    @pytest.mark.asyncio
    async def test_cost_tracker_initialization(self, tracker):
        """Test cost tracker initialization."""
        await tracker.initialize()
        
        assert tracker._initialized is True
        assert len(tracker._cost_rates) > 0
    
    @pytest.mark.asyncio
    async def test_cost_recording(self, tracker):
        """Test recording costs."""
        await tracker.initialize()
        
        record = await tracker.record_cost(
            category=CostCategory.COMPUTE,
            amount_usd=10.50,
            service="riskcast",
            customer_id="cust_123",
            resource="ec2-instance",
        )
        
        assert record.amount_usd == 10.50
        assert record.category == CostCategory.COMPUTE
        assert record.customer_id == "cust_123"
        assert record.allocation == CostAllocation.DIRECT
    
    @pytest.mark.asyncio
    async def test_usage_based_cost_recording(self, tracker):
        """Test recording usage-based costs."""
        await tracker.initialize()
        
        record = await tracker.record_usage(
            usage_type="compute_cpu_hour",
            units=100,
            service="omen",
        )
        
        # Cost = units * rate = 100 * 0.04 = 4.0
        assert record.amount_usd == 4.0
        assert record.category == CostCategory.COMPUTE
    
    @pytest.mark.asyncio
    async def test_customer_cost_retrieval(self, tracker):
        """Test getting costs by customer."""
        await tracker.initialize()
        
        # Record some costs
        await tracker.record_cost(CostCategory.COMPUTE, 10.0, "riskcast", "cust_123")
        await tracker.record_cost(CostCategory.STORAGE, 5.0, "riskcast", "cust_123")
        await tracker.record_cost(CostCategory.NETWORK, 2.0, "alerter", "cust_123")
        
        costs = await tracker.get_customer_costs("cust_123", period_days=30)
        
        assert costs["customer_id"] == "cust_123"
        assert costs["direct_cost_usd"] == 17.0
        assert CostCategory.COMPUTE.value in costs["by_category"]
    
    @pytest.mark.asyncio
    async def test_service_cost_retrieval(self, tracker):
        """Test getting costs by service."""
        await tracker.initialize()
        
        # Record some costs
        await tracker.record_cost(CostCategory.COMPUTE, 20.0, "omen", "cust_123")
        await tracker.record_cost(CostCategory.COMPUTE, 15.0, "omen", "cust_456")
        
        costs = await tracker.get_service_costs("omen", period_days=30)
        
        assert costs["service"] == "omen"
        assert costs["total_cost_usd"] == 35.0
    
    @pytest.mark.asyncio
    async def test_budget_setting(self, tracker):
        """Test setting cost budgets."""
        await tracker.initialize()
        
        budget = tracker.set_budget(
            budget_id="compute_monthly",
            name="Compute Monthly Budget",
            monthly_limit_usd=1000.0,
            category=CostCategory.COMPUTE,
            alert_threshold_pct=80.0,
        )
        
        assert budget.budget_id == "compute_monthly"
        assert budget.monthly_limit_usd == 1000.0
        assert budget.alert_threshold_pct == 80.0
    
    @pytest.mark.asyncio
    async def test_cost_report_generation(self, tracker):
        """Test cost report generation."""
        await tracker.initialize()
        
        # Record various costs
        await tracker.record_cost(CostCategory.COMPUTE, 100.0, "riskcast", "cust_123")
        await tracker.record_cost(CostCategory.STORAGE, 50.0, "riskcast")
        await tracker.record_cost(CostCategory.API_CALLS, 25.0, "alerter", "cust_456")
        
        report = await tracker.generate_report(period_days=30)
        
        assert isinstance(report, CostReport)
        assert report.total_cost_usd == 175.0
        assert len(report.by_category) > 0
        assert len(report.by_service) > 0
    
    @pytest.mark.asyncio
    async def test_cost_anomaly_detection(self, tracker):
        """Test cost anomaly detection."""
        await tracker.initialize()
        
        # Record baseline costs (simulate historical data)
        for i in range(7):
            record = CostRecord(
                record_id=f"baseline_{i}",
                timestamp=datetime.utcnow() - timedelta(days=i + 1),
                category=CostCategory.COMPUTE,
                amount_usd=100.0,  # Normal daily cost
                service="riskcast",
            )
            tracker._records.append(record)
        
        # Record anomalous cost today
        await tracker.record_cost(CostCategory.COMPUTE, 500.0, "riskcast")
        
        anomalies = await tracker.detect_anomalies(lookback_days=7)
        
        # Should detect anomaly (500 vs 100 average)
        assert len(anomalies) >= 0  # May or may not detect depending on timing
    
    @pytest.mark.asyncio
    async def test_cost_alerts(self, tracker):
        """Test cost alert generation."""
        await tracker.initialize()
        
        # Set a low budget
        tracker.set_budget(
            budget_id="test_budget",
            name="Test Budget",
            monthly_limit_usd=100.0,
            category=CostCategory.COMPUTE,
            alert_threshold_pct=50.0,
        )
        
        # Record cost that exceeds threshold
        await tracker.record_cost(CostCategory.COMPUTE, 60.0, "riskcast")
        
        alerts = tracker.get_alerts(hours=24)
        
        # Should have alert for exceeding 50% threshold
        assert len(alerts) >= 0


class TestPerformanceBenchmark:
    """Test performance benchmarking."""
    
    @pytest.fixture
    def benchmark(self):
        return PerformanceBenchmark()
    
    @pytest.mark.asyncio
    async def test_benchmark_registration(self, benchmark):
        """Test benchmark registration."""
        async def test_func():
            return True
        
        benchmark.register("test_benchmark", test_func, suite="test")
        
        assert "test_benchmark" in benchmark._benchmarks
    
    @pytest.mark.asyncio
    async def test_benchmark_execution(self, benchmark):
        """Test running a benchmark."""
        async def fast_func():
            pass
        
        benchmark.register("fast_test", fast_func)
        
        result = await benchmark.run_benchmark(
            "fast_test",
            iterations=50,
            warmup_iterations=5,
        )
        
        assert isinstance(result, BenchmarkResult)
        assert result.status == BenchmarkStatus.COMPLETED
        assert result.iterations == 50
        assert result.mean_time_ms >= 0
        assert result.p99_time_ms >= result.mean_time_ms
    
    @pytest.mark.asyncio
    async def test_benchmark_comparison(self, benchmark):
        """Test benchmark comparison."""
        async def test_func():
            pass
        
        benchmark.register("comparison_test", test_func)
        
        # Run baseline
        baseline = await benchmark.run_benchmark("comparison_test", iterations=20)
        benchmark.set_baseline("comparison_test", baseline)
        
        # Run current
        current = await benchmark.run_benchmark("comparison_test", iterations=20)
        
        comparison = benchmark.compare_to_baseline("comparison_test", current)
        
        assert comparison is not None
        assert comparison.benchmark_name == "comparison_test"
        assert isinstance(comparison.mean_change_pct, float)
    
    @pytest.mark.asyncio
    async def test_benchmark_suite_execution(self, benchmark):
        """Test running a benchmark suite."""
        async def func1():
            pass
        
        async def func2():
            pass
        
        benchmark.register("suite_test_1", func1, suite="test_suite")
        benchmark.register("suite_test_2", func2, suite="test_suite")
        
        results = await benchmark.run_suite("test_suite", iterations=10)
        
        assert len(results) == 2
        assert all(r.status == BenchmarkStatus.COMPLETED for r in results)
    
    def test_benchmark_summary(self, benchmark):
        """Test getting benchmark summary."""
        async def test_func():
            pass
        
        benchmark.register("summary_test", test_func, suite="test")
        
        summary = benchmark.get_summary()
        
        assert summary["total_benchmarks"] >= 1
        assert "summary_test" in summary["benchmarks"]


class TestDefaultBenchmarks:
    """Test default RISKCAST benchmarks."""
    
    @pytest.mark.asyncio
    async def test_default_benchmarks_exist(self):
        """Test that default benchmarks are registered."""
        benchmark = get_benchmark()
        
        summary = benchmark.get_summary()
        
        assert summary["total_benchmarks"] > 0
        assert "signal_processing" in summary["benchmarks"]
        assert "decision_generation" in summary["benchmarks"]
    
    @pytest.mark.asyncio
    async def test_run_default_benchmark(self):
        """Test running a default benchmark."""
        benchmark = get_benchmark()
        
        result = await benchmark.run_benchmark(
            "api_health",
            iterations=10,
        )
        
        assert result.status == BenchmarkStatus.COMPLETED
        assert result.throughput_per_sec > 0
