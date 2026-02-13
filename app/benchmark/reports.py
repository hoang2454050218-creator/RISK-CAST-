"""
Benchmark Report Generation.

Generates formatted benchmark reports for various audiences:
- Executive summary for leadership
- Detailed analysis for technical teams
- API responses for dashboards
"""

from datetime import datetime
from typing import List, Dict, Any, Optional

import structlog
from pydantic import BaseModel, Field, computed_field

from app.benchmark.framework import BenchmarkReport, BaselineResult, BaselineType

logger = structlog.get_logger(__name__)


# ============================================================================
# REPORT SCHEMAS
# ============================================================================


class BaselineComparison(BaseModel):
    """Comparison between RISKCAST and a single baseline."""
    
    baseline_name: str
    baseline_description: str
    
    # RISKCAST metrics
    riskcast_accuracy: float
    riskcast_value: float
    
    # Baseline metrics
    baseline_accuracy: float
    baseline_value: float
    
    # Comparison
    accuracy_improvement: float  # RISKCAST - baseline
    value_improvement: float     # RISKCAST - baseline
    value_improvement_pct: float # % improvement
    
    # Significance
    p_value: Optional[float] = None
    is_significant: bool = False  # p < 0.05
    
    @computed_field
    @property
    def improvement_summary(self) -> str:
        """Human-readable improvement summary."""
        if self.value_improvement > 0:
            return f"+${self.value_improvement:,.0f} ({self.value_improvement_pct:+.1%})"
        else:
            return f"-${abs(self.value_improvement):,.0f} ({self.value_improvement_pct:+.1%})"


class BenchmarkSummary(BaseModel):
    """Executive summary of benchmark results."""
    
    # Period
    report_period: str
    generated_at: datetime
    
    # Key metrics
    total_decisions: int
    riskcast_accuracy: float
    riskcast_net_value: float
    
    # Headline comparisons
    vs_do_nothing_value: float
    vs_threshold_value: float
    optimal_capture_rate: float  # How close to perfect hindsight
    
    # Status
    beats_all_baselines: bool
    improvement_is_significant: bool
    
    # Headline statements
    key_finding: str
    value_delivered: str
    
    @computed_field
    @property
    def headline(self) -> str:
        """Single-line headline for the report."""
        if self.beats_all_baselines:
            return f"RISKCAST outperforms all baselines, capturing {self.optimal_capture_rate:.0%} of optimal value"
        else:
            return f"RISKCAST accuracy: {self.riskcast_accuracy:.0%}, net value: ${self.riskcast_net_value:,.0f}"


# ============================================================================
# REPORT GENERATOR
# ============================================================================


class BenchmarkReportGenerator:
    """
    Generates formatted benchmark reports.
    
    Outputs:
    - Executive summary (for leadership)
    - Detailed comparison (for technical teams)
    - Markdown report (for documentation)
    - API response (for dashboards)
    """
    
    def generate_summary(self, report: BenchmarkReport) -> BenchmarkSummary:
        """
        Generate executive summary from benchmark report.
        
        Args:
            report: Full benchmark report
            
        Returns:
            BenchmarkSummary with key findings
        """
        # Calculate vs baselines
        do_nothing = report.baseline_results.get(BaselineType.DO_NOTHING.value)
        threshold = report.baseline_results.get(BaselineType.SIMPLE_THRESHOLD.value)
        
        vs_do_nothing = (
            report.riskcast_results.net_value - (do_nothing.net_value if do_nothing else 0)
        )
        vs_threshold = (
            report.riskcast_results.net_value - (threshold.net_value if threshold else 0)
        )
        
        # Generate key finding
        if report.beats_all_baselines:
            key_finding = (
                f"RISKCAST outperformed all baselines in the analysis period, "
                f"achieving {report.riskcast_results.accuracy:.0%} accuracy "
                f"and capturing {report.optimal_capture_rate:.0%} of theoretically optimal value."
            )
        else:
            key_finding = (
                f"RISKCAST achieved {report.riskcast_results.accuracy:.0%} accuracy "
                f"with net value of ${report.riskcast_results.net_value:,.0f}."
            )
        
        # Value delivered statement
        value_delivered = (
            f"RISKCAST delivered ${report.riskcast_results.net_value:,.0f} in net value "
            f"(${vs_do_nothing:,.0f} better than doing nothing)."
        )
        
        return BenchmarkSummary(
            report_period=report.period,
            generated_at=report.generated_at,
            total_decisions=report.total_decisions_analyzed,
            riskcast_accuracy=report.riskcast_results.accuracy,
            riskcast_net_value=report.riskcast_results.net_value,
            vs_do_nothing_value=vs_do_nothing,
            vs_threshold_value=vs_threshold,
            optimal_capture_rate=report.optimal_capture_rate,
            beats_all_baselines=report.beats_all_baselines,
            improvement_is_significant=any(
                p < 0.05 for p in report.significance_vs_baselines.values()
            ),
            key_finding=key_finding,
            value_delivered=value_delivered,
        )
    
    def generate_comparisons(
        self,
        report: BenchmarkReport,
    ) -> List[BaselineComparison]:
        """
        Generate detailed baseline comparisons.
        
        Args:
            report: Full benchmark report
            
        Returns:
            List of BaselineComparison for each baseline
        """
        comparisons = []
        
        baseline_descriptions = {
            BaselineType.DO_NOTHING.value: "Never act - accept all disruptions",
            BaselineType.ALWAYS_REROUTE.value: "Always act - avoid all risk",
            BaselineType.SIMPLE_THRESHOLD.value: "Act if signal > 50%",
            BaselineType.PERFECT_HINDSIGHT.value: "Optimal (theoretical upper bound)",
        }
        
        for baseline_name, baseline_result in report.baseline_results.items():
            accuracy_improvement = (
                report.riskcast_results.accuracy - baseline_result.accuracy
            )
            value_improvement = (
                report.riskcast_results.net_value - baseline_result.net_value
            )
            
            if baseline_result.net_value != 0:
                value_improvement_pct = value_improvement / abs(baseline_result.net_value)
            else:
                value_improvement_pct = 1.0 if value_improvement > 0 else 0
            
            p_value = report.significance_vs_baselines.get(baseline_name)
            
            comparisons.append(BaselineComparison(
                baseline_name=baseline_name,
                baseline_description=baseline_descriptions.get(baseline_name, baseline_name),
                riskcast_accuracy=report.riskcast_results.accuracy,
                riskcast_value=report.riskcast_results.net_value,
                baseline_accuracy=baseline_result.accuracy,
                baseline_value=baseline_result.net_value,
                accuracy_improvement=accuracy_improvement,
                value_improvement=value_improvement,
                value_improvement_pct=value_improvement_pct,
                p_value=p_value,
                is_significant=p_value is not None and p_value < 0.05,
            ))
        
        return comparisons
    
    def generate_markdown_report(self, report: BenchmarkReport) -> str:
        """
        Generate markdown-formatted benchmark report.
        
        Suitable for documentation or sharing.
        """
        summary = self.generate_summary(report)
        comparisons = self.generate_comparisons(report)
        
        md = f"""# RISKCAST Benchmark Report

**Period:** {report.period}  
**Generated:** {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')}  
**Decisions Analyzed:** {report.total_decisions_analyzed}

---

## Executive Summary

{summary.key_finding}

{summary.value_delivered}

### Key Metrics

| Metric | Value |
|--------|-------|
| Accuracy | {summary.riskcast_accuracy:.1%} |
| Net Value | ${summary.riskcast_net_value:,.0f} |
| vs Do-Nothing | +${summary.vs_do_nothing_value:,.0f} |
| Optimal Capture | {summary.optimal_capture_rate:.1%} |

---

## Baseline Comparisons

"""
        # Add comparison table
        md += "| Baseline | Accuracy | Value | vs RISKCAST |\n"
        md += "|----------|----------|-------|-------------|\n"
        md += f"| **RISKCAST** | **{report.riskcast_results.accuracy:.1%}** | **${report.riskcast_results.net_value:,.0f}** | - |\n"
        
        for comp in comparisons:
            md += f"| {comp.baseline_name} | {comp.baseline_accuracy:.1%} | ${comp.baseline_value:,.0f} | {comp.improvement_summary} |\n"
        
        md += """

---

## Detailed Analysis

### RISKCAST Performance

"""
        r = report.riskcast_results
        md += f"""- **True Positives:** {r.true_positives} (correctly recommended action when disruption occurred)
- **False Positives:** {r.false_positives} (recommended action when no disruption)
- **False Negatives:** {r.false_negatives} (did not recommend action when disruption occurred)
- **True Negatives:** {r.true_negatives} (correctly did not recommend action)

**Precision:** {r.precision:.1%} (of recommended actions, how many were needed)  
**Recall:** {r.recall:.1%} (of disruptions, how many did we catch)  
**F1 Score:** {r.f1_score:.2f}

### Value Breakdown

- **Total Savings:** ${r.total_savings_if_followed:,.0f}
- **Total Costs:** ${r.total_cost_if_followed:,.0f}
- **Net Value:** ${r.net_value:,.0f}
- **ROI:** {r.roi:.1f}x

"""
        
        # Statistical significance
        if report.significance_vs_baselines:
            md += """### Statistical Significance

| Baseline | p-value | Significant? |
|----------|---------|--------------|
"""
            for baseline, p_value in report.significance_vs_baselines.items():
                sig = "✅ Yes" if p_value < 0.05 else "❌ No"
                md += f"| {baseline} | {p_value:.4f} | {sig} |\n"
        
        md += """

---

## Methodology

### Baselines

1. **DO_NOTHING**: Never recommend action. Represents lower bound.
2. **ALWAYS_ACT**: Always recommend action. Catches all disruptions but has unnecessary costs.
3. **SIMPLE_THRESHOLD**: Act if signal probability > 50%. Naive approach.
4. **PERFECT_HINDSIGHT**: Optimal decision with full knowledge. Upper bound (theoretical).

### Metrics

- **Accuracy**: (TP + TN) / Total
- **Precision**: TP / (TP + FP) - Of actions recommended, how many were needed
- **Recall**: TP / (TP + FN) - Of disruptions, how many did we catch
- **Net Value**: Total savings - Total costs

---

*Report generated by RISKCAST Benchmark Framework*
"""
        return md
    
    def generate_api_response(self, report: BenchmarkReport) -> Dict[str, Any]:
        """
        Generate API-friendly response for dashboards.
        
        Args:
            report: Full benchmark report
            
        Returns:
            Dict suitable for JSON API response
        """
        summary = self.generate_summary(report)
        comparisons = self.generate_comparisons(report)
        
        return {
            "report_id": report.report_id,
            "period": report.period,
            "generated_at": report.generated_at.isoformat(),
            "summary": {
                "total_decisions": summary.total_decisions,
                "riskcast_accuracy": summary.riskcast_accuracy,
                "riskcast_net_value": summary.riskcast_net_value,
                "vs_do_nothing": summary.vs_do_nothing_value,
                "optimal_capture_rate": summary.optimal_capture_rate,
                "beats_all_baselines": summary.beats_all_baselines,
                "headline": summary.headline,
            },
            "riskcast": {
                "accuracy": report.riskcast_results.accuracy,
                "precision": report.riskcast_results.precision,
                "recall": report.riskcast_results.recall,
                "f1_score": report.riskcast_results.f1_score,
                "net_value": report.riskcast_results.net_value,
                "total_savings": report.riskcast_results.total_savings_if_followed,
                "total_costs": report.riskcast_results.total_cost_if_followed,
                "roi": report.riskcast_results.roi,
            },
            "comparisons": [
                {
                    "baseline": c.baseline_name,
                    "riskcast_value": c.riskcast_value,
                    "baseline_value": c.baseline_value,
                    "improvement": c.value_improvement,
                    "improvement_pct": c.value_improvement_pct,
                    "significant": c.is_significant,
                }
                for c in comparisons
            ],
            "confusion_matrix": {
                "true_positives": report.riskcast_results.true_positives,
                "false_positives": report.riskcast_results.false_positives,
                "false_negatives": report.riskcast_results.false_negatives,
                "true_negatives": report.riskcast_results.true_negatives,
            },
        }
