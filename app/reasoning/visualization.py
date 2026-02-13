"""
Decision Graph Visualization.

Renders reasoning traces as interactive graphs in multiple formats:
- Mermaid diagrams
- D3.js JSON structures
- SVG confidence gauges

Addresses audit gap: A1.2 Reasoning Transparency (+12 points)
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import math

from app.reasoning.schemas import ReasoningTrace, ReasoningLayer


class DecisionGraphRenderer:
    """Renders reasoning trace as interactive graph."""
    
    def render_confidence_gauge(self, confidence: float, width: int = 200, height: int = 120) -> str:
        """
        Render a confidence gauge as SVG.
        
        Args:
            confidence: Confidence value between 0 and 1
            width: SVG width in pixels
            height: SVG height in pixels
            
        Returns:
            SVG string
        """
        # Clamp confidence to valid range
        confidence = max(0.0, min(1.0, confidence))
        
        # Calculate arc parameters
        cx, cy = width / 2, height - 20
        radius = min(width, height) - 40
        
        # Arc spans from -150 to -30 degrees (180 degree sweep)
        start_angle = -150
        end_angle = -30
        sweep = end_angle - start_angle
        
        # Current value angle
        value_angle = start_angle + (sweep * confidence)
        
        # Convert to radians for calculations
        def to_radians(deg):
            return deg * 3.14159 / 180
        
        # Calculate arc endpoints
        start_x = cx + radius * math.cos(to_radians(start_angle))
        start_y = cy + radius * math.sin(to_radians(start_angle))
        end_x = cx + radius * math.cos(to_radians(end_angle))
        end_y = cy + radius * math.sin(to_radians(end_angle))
        
        # Calculate current value point
        value_x = cx + radius * math.cos(to_radians(value_angle))
        value_y = cy + radius * math.sin(to_radians(value_angle))
        
        # Determine color based on confidence
        if confidence >= 0.8:
            color = "#22c55e"  # Green
        elif confidence >= 0.6:
            color = "#eab308"  # Yellow
        elif confidence >= 0.4:
            color = "#f97316"  # Orange
        else:
            color = "#ef4444"  # Red
        
        # Build SVG
        svg = f'''<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#ef4444"/>
      <stop offset="50%" style="stop-color:#eab308"/>
      <stop offset="100%" style="stop-color:#22c55e"/>
    </linearGradient>
  </defs>
  
  <!-- Background arc -->
  <path d="M {start_x} {start_y} A {radius} {radius} 0 0 1 {end_x} {end_y}"
        stroke="#e5e7eb" stroke-width="12" fill="none" stroke-linecap="round"/>
  
  <!-- Value arc -->
  <path d="M {start_x} {start_y} A {radius} {radius} 0 0 1 {value_x} {value_y}"
        stroke="{color}" stroke-width="12" fill="none" stroke-linecap="round"/>
  
  <!-- Center text -->
  <text x="{cx}" y="{cy - 10}" text-anchor="middle" font-size="24" font-weight="bold" fill="{color}">
    {int(confidence * 100)}%
  </text>
  <text x="{cx}" y="{cy + 15}" text-anchor="middle" font-size="12" fill="#6b7280">
    Confidence
  </text>
  
  <!-- Needle indicator -->
  <circle cx="{value_x}" cy="{value_y}" r="6" fill="{color}"/>
</svg>'''
        
        return svg
    
    def render_layer_breakdown(self, trace: ReasoningTrace, width: int = 400, height: int = 250) -> str:
        """
        Render layer breakdown as SVG bar chart.
        
        Args:
            trace: Reasoning trace with layer results
            width: SVG width
            height: SVG height
            
        Returns:
            SVG string
        """
        layers = trace.layers
        if not layers:
            return f'<svg width="{width}" height="{height}"><text x="50%" y="50%" text-anchor="middle">No layers</text></svg>'
        
        # Chart dimensions
        margin = {"top": 20, "right": 20, "bottom": 40, "left": 120}
        chart_width = width - margin["left"] - margin["right"]
        chart_height = height - margin["top"] - margin["bottom"]
        
        bar_height = chart_height / len(layers) - 5
        
        # Colors for each layer
        layer_colors = {
            "FACTUAL": "#3b82f6",
            "TEMPORAL": "#8b5cf6",
            "CAUSAL": "#ec4899",
            "COUNTERFACTUAL": "#f97316",
            "STRATEGIC": "#22c55e",
            "META": "#06b6d4",
        }
        
        bars_svg = []
        for i, layer in enumerate(layers):
            y = margin["top"] + i * (bar_height + 5)
            confidence = layer.confidence if hasattr(layer, 'confidence') else 0.5
            bar_width = confidence * chart_width
            
            layer_name = layer.layer.value if hasattr(layer.layer, 'value') else str(layer.layer)
            color = layer_colors.get(layer_name, "#6b7280")
            
            bars_svg.append(f'''
  <!-- {layer_name} -->
  <text x="{margin["left"] - 10}" y="{y + bar_height/2 + 4}" text-anchor="end" font-size="11" fill="#374151">{layer_name}</text>
  <rect x="{margin["left"]}" y="{y}" width="{bar_width}" height="{bar_height}" fill="{color}" rx="3"/>
  <text x="{margin["left"] + bar_width + 5}" y="{y + bar_height/2 + 4}" font-size="10" fill="#6b7280">{confidence:.0%}</text>
''')
        
        svg = f'''<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
  <style>
    .title {{ font-size: 14px; font-weight: bold; fill: #111827; }}
  </style>
  
  <!-- Title -->
  <text x="{width/2}" y="15" text-anchor="middle" class="title">Layer Confidence Breakdown</text>
  
  <!-- Bars -->
  {"".join(bars_svg)}
  
  <!-- X-axis -->
  <line x1="{margin["left"]}" y1="{height - margin["bottom"]}" x2="{width - margin["right"]}" y2="{height - margin["bottom"]}" stroke="#d1d5db"/>
  <text x="{margin["left"]}" y="{height - 10}" font-size="10" fill="#6b7280">0%</text>
  <text x="{width - margin["right"]}" y="{height - 10}" font-size="10" fill="#6b7280" text-anchor="end">100%</text>
</svg>'''
        
        return svg
    
    def to_mermaid(self, trace: ReasoningTrace) -> str:
        """
        Generate Mermaid diagram from reasoning trace.
        
        Returns:
            Mermaid diagram string that can be rendered by any Mermaid-compatible viewer.
        """
        lines = ["graph TD"]
        lines.append("    classDef input fill:#e0f2fe,stroke:#0284c7")
        lines.append("    classDef layer fill:#f0fdf4,stroke:#22c55e")
        lines.append("    classDef output fill:#fef3c7,stroke:#f59e0b")
        lines.append("    classDef escalate fill:#fee2e2,stroke:#dc2626")
        lines.append("")
        
        # Input node
        signal_type = "Unknown"
        if trace.factual:
            for fact in trace.factual.verified_facts:
                if fact.fact_type == "signal_type":
                    signal_type = str(fact.value)
                    break
        
        lines.append(f'    INPUT["🎯 Signal: {signal_type}"]:::input')
        
        # Layer nodes with metrics
        if trace.factual:
            quality = trace.factual.data_quality_score
            fact_count = len(trace.factual.verified_facts)
            lines.append(f'    L1["📊 Factual Layer<br/>Quality: {quality:.0%}<br/>Facts: {fact_count}"]:::layer')
        
        if trace.temporal:
            urgency = trace.temporal.urgency_level
            deadline = trace.temporal.hours_until_decision_deadline
            lines.append(f'    L2["⏱️ Temporal Layer<br/>Urgency: {urgency}<br/>Deadline: {deadline:.1f}h"]:::layer')
        
        if trace.causal:
            causes = len(trace.causal.root_causes)
            interventions = len(trace.causal.intervention_points)
            lines.append(f'    L3["🔗 Causal Layer<br/>Root Causes: {causes}<br/>Interventions: {interventions}"]:::layer')
        
        if trace.counterfactual:
            scenarios = len(trace.counterfactual.scenarios)
            robustness = trace.counterfactual.robustness_score
            lines.append(f'    L4["🎭 Counterfactual<br/>Scenarios: {scenarios}<br/>Robustness: {robustness:.0%}"]:::layer')
        
        if trace.strategic:
            alignment = trace.strategic.risk_tolerance_alignment
            impact = trace.strategic.long_term_impact
            lines.append(f'    L5["♟️ Strategic Layer<br/>Alignment: {alignment:.0%}<br/>Impact: {impact}"]:::layer')
        
        if trace.meta:
            should_decide = trace.meta.should_decide
            confidence = trace.meta.reasoning_confidence
            decision_text = "PROCEED" if should_decide else "ESCALATE"
            lines.append(f'    L6["🧠 Meta Layer<br/>Decision: {decision_text}<br/>Confidence: {confidence:.0%}"]:::layer')
        
        # Output node
        if trace.escalated:
            reason = trace.escalation_reason or "Quality threshold not met"
            # Escape special characters for Mermaid
            reason = reason.replace('"', "'").replace('<', '').replace('>', '')[:50]
            lines.append(f'    OUTPUT["⚠️ ESCALATE TO HUMAN<br/>Reason: {reason}"]:::escalate')
        else:
            decision = trace.final_decision or "MONITOR"
            confidence = trace.final_confidence
            lines.append(f'    OUTPUT["✅ Decision: {decision}<br/>Confidence: {confidence:.0%}"]:::output')
        
        # Add edges
        lines.append("")
        lines.append("    INPUT --> L1")
        lines.append("    L1 --> L2")
        lines.append("    L2 --> L3")
        lines.append("    L3 --> L4")
        lines.append("    L4 --> L5")
        lines.append("    L5 --> L6")
        lines.append("    L6 --> OUTPUT")
        
        # Add warning annotations
        warnings = trace.get_all_warnings()
        if warnings:
            lines.append("")
            lines.append("    subgraph Warnings")
            for i, warning in enumerate(warnings[:5]):  # Max 5 warnings
                warning_clean = warning.replace('"', "'")[:60]
                lines.append(f'        W{i}["⚠️ {warning_clean}"]')
            lines.append("    end")
        
        return "\n".join(lines)
    
    def to_d3_json(self, trace: ReasoningTrace) -> dict:
        """
        Generate D3-compatible JSON structure.
        
        Returns:
            Dictionary with nodes and links for D3.js force-directed graph.
        """
        nodes = []
        links = []
        
        # Input node
        nodes.append({
            "id": "input",
            "label": "Signal Input",
            "type": "input",
            "x": 0,
            "y": 0,
            "metrics": {}
        })
        
        # Layer nodes
        layer_configs = [
            ("factual", "Factual", trace.factual),
            ("temporal", "Temporal", trace.temporal),
            ("causal", "Causal", trace.causal),
            ("counterfactual", "Counterfactual", trace.counterfactual),
            ("strategic", "Strategic", trace.strategic),
            ("meta", "Meta", trace.meta),
        ]
        
        for i, (layer_id, label, layer_output) in enumerate(layer_configs):
            metrics = {}
            if layer_output:
                metrics = {
                    "confidence": layer_output.confidence,
                    "duration_ms": layer_output.duration_ms,
                    "warnings": len(layer_output.warnings),
                }
            
            nodes.append({
                "id": layer_id,
                "label": f"{label} Layer",
                "type": "layer",
                "x": 100 + i * 150,
                "y": 200,
                "metrics": metrics,
                "active": layer_output is not None
            })
        
        # Output node
        nodes.append({
            "id": "output",
            "label": trace.final_decision or "ESCALATE",
            "type": "escalate" if trace.escalated else "output",
            "x": 1000,
            "y": 0,
            "metrics": {
                "confidence": trace.final_confidence,
                "escalated": trace.escalated
            }
        })
        
        # Links
        link_sequence = ["input", "factual", "temporal", "causal", 
                        "counterfactual", "strategic", "meta", "output"]
        
        for i in range(len(link_sequence) - 1):
            links.append({
                "source": link_sequence[i],
                "target": link_sequence[i + 1],
                "strength": 0.8
            })
        
        return {
            "nodes": nodes,
            "links": links,
            "trace_id": trace.trace_id,
            "metadata": {
                "total_duration_ms": trace.total_duration_ms,
                "data_quality": trace.data_quality_score,
                "reasoning_quality": trace.reasoning_quality_score,
                "escalated": trace.escalated,
                "started_at": trace.started_at.isoformat() if trace.started_at else None,
                "completed_at": trace.completed_at.isoformat() if trace.completed_at else None,
            }
        }
    
    def to_svg_confidence_gauge(
        self,
        confidence: float,
        label: str = "Confidence",
        width: int = 200,
        height: int = 120
    ) -> str:
        """
        Generate SVG confidence gauge.
        
        Args:
            confidence: Confidence value (0-1)
            label: Label for the gauge
            width: SVG width
            height: SVG height
            
        Returns:
            SVG string
        """
        # Calculate angle (180 degree arc, 0% = left, 100% = right)
        angle = 180 * (1 - confidence)
        
        # Center and radius
        cx, cy = width // 2, height - 20
        radius = min(width // 2 - 20, height - 40)
        
        # Calculate needle endpoint
        rad = math.radians(angle)
        needle_x = cx + radius * 0.85 * math.cos(rad)
        needle_y = cy - radius * 0.85 * math.sin(rad)
        
        # Color based on confidence
        if confidence >= 0.8:
            color = "#22c55e"  # Green
        elif confidence >= 0.6:
            color = "#84cc16"  # Lime
        elif confidence >= 0.4:
            color = "#f59e0b"  # Amber
        else:
            color = "#ef4444"  # Red
        
        svg = f'''<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
  <!-- Background arc -->
  <path d="M {cx - radius} {cy} A {radius} {radius} 0 0 1 {cx + radius} {cy}" 
        fill="none" stroke="#e5e7eb" stroke-width="15" stroke-linecap="round"/>
  
  <!-- Colored segments -->
  <path d="M {cx - radius} {cy} A {radius} {radius} 0 0 1 {cx - radius * 0.5} {cy - radius * 0.866}" 
        fill="none" stroke="#ef4444" stroke-width="15" stroke-linecap="round"/>
  <path d="M {cx - radius * 0.5} {cy - radius * 0.866} A {radius} {radius} 0 0 1 {cx} {cy - radius}" 
        fill="none" stroke="#f59e0b" stroke-width="15"/>
  <path d="M {cx} {cy - radius} A {radius} {radius} 0 0 1 {cx + radius * 0.5} {cy - radius * 0.866}" 
        fill="none" stroke="#84cc16" stroke-width="15"/>
  <path d="M {cx + radius * 0.5} {cy - radius * 0.866} A {radius} {radius} 0 0 1 {cx + radius} {cy}" 
        fill="none" stroke="#22c55e" stroke-width="15" stroke-linecap="round"/>
  
  <!-- Needle -->
  <line x1="{cx}" y1="{cy}" x2="{needle_x:.1f}" y2="{needle_y:.1f}" 
        stroke="{color}" stroke-width="3" stroke-linecap="round"/>
  <circle cx="{cx}" cy="{cy}" r="8" fill="{color}"/>
  
  <!-- Labels -->
  <text x="{cx - radius - 5}" y="{cy + 15}" font-size="10" fill="#6b7280" text-anchor="end">0%</text>
  <text x="{cx + radius + 5}" y="{cy + 15}" font-size="10" fill="#6b7280">100%</text>
  <text x="{cx}" y="{cy + 35}" font-size="12" fill="#374151" text-anchor="middle" font-weight="bold">{label}: {confidence:.0%}</text>
</svg>'''
        
        return svg
    
    def to_layer_breakdown_svg(self, trace: ReasoningTrace, width: int = 400, height: int = 200) -> str:
        """
        Generate SVG showing confidence breakdown by layer.
        
        Args:
            trace: Reasoning trace
            width: SVG width
            height: SVG height
            
        Returns:
            SVG string with bar chart
        """
        layers = [
            ("Factual", trace.factual),
            ("Temporal", trace.temporal),
            ("Causal", trace.causal),
            ("Counterfactual", trace.counterfactual),
            ("Strategic", trace.strategic),
            ("Meta", trace.meta),
        ]
        
        bar_height = 20
        bar_spacing = 10
        margin_left = 100
        margin_top = 20
        bar_max_width = width - margin_left - 40
        
        svg_parts = [f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">']
        svg_parts.append('  <style>.label { font-size: 11px; fill: #374151; } .value { font-size: 10px; fill: #6b7280; }</style>')
        
        for i, (name, layer) in enumerate(layers):
            y = margin_top + i * (bar_height + bar_spacing)
            confidence = layer.confidence if layer else 0
            bar_width = confidence * bar_max_width
            
            # Color based on confidence
            if confidence >= 0.8:
                color = "#22c55e"
            elif confidence >= 0.6:
                color = "#84cc16"
            elif confidence >= 0.4:
                color = "#f59e0b"
            else:
                color = "#ef4444"
            
            # Background bar
            svg_parts.append(f'  <rect x="{margin_left}" y="{y}" width="{bar_max_width}" height="{bar_height}" fill="#f3f4f6" rx="3"/>')
            
            # Confidence bar
            if bar_width > 0:
                svg_parts.append(f'  <rect x="{margin_left}" y="{y}" width="{bar_width:.1f}" height="{bar_height}" fill="{color}" rx="3"/>')
            
            # Label
            svg_parts.append(f'  <text x="{margin_left - 5}" y="{y + 14}" class="label" text-anchor="end">{name}</text>')
            
            # Value
            svg_parts.append(f'  <text x="{margin_left + bar_max_width + 5}" y="{y + 14}" class="value">{confidence:.0%}</text>')
        
        svg_parts.append('</svg>')
        return '\n'.join(svg_parts)


class TraceExporter:
    """Export reasoning traces in various formats."""
    
    def __init__(self):
        self.renderer = DecisionGraphRenderer()
    
    def to_json(self, trace: ReasoningTrace, include_graph: bool = True) -> str:
        """
        Export trace as JSON.
        
        Args:
            trace: Reasoning trace
            include_graph: Whether to include D3 graph data
            
        Returns:
            JSON string
        """
        data = {
            "trace_id": trace.trace_id,
            "started_at": trace.started_at.isoformat() if trace.started_at else None,
            "completed_at": trace.completed_at.isoformat() if trace.completed_at else None,
            "total_duration_ms": trace.total_duration_ms,
            "final_decision": trace.final_decision,
            "final_confidence": trace.final_confidence,
            "escalated": trace.escalated,
            "escalation_reason": trace.escalation_reason,
            "data_quality_score": trace.data_quality_score,
            "reasoning_quality_score": trace.reasoning_quality_score,
            "layer_summary": trace.get_layer_summary(),
            "warnings": trace.get_all_warnings(),
        }
        
        if include_graph:
            data["graph"] = self.renderer.to_d3_json(trace)
        
        return json.dumps(data, indent=2, default=str)
    
    def to_mermaid(self, trace: ReasoningTrace) -> str:
        """Export trace as Mermaid diagram."""
        return self.renderer.to_mermaid(trace)
    
    def to_html_report(self, trace: ReasoningTrace) -> str:
        """
        Export trace as standalone HTML report.
        
        Returns:
            Complete HTML document with embedded visualizations.
        """
        mermaid = self.renderer.to_mermaid(trace)
        confidence_gauge = self.renderer.to_svg_confidence_gauge(trace.final_confidence, "Final Confidence")
        layer_breakdown = self.renderer.to_layer_breakdown_svg(trace)
        
        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Reasoning Trace: {trace.trace_id}</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #1f2937; }}
        .section {{ margin: 30px 0; padding: 20px; background: #f9fafb; border-radius: 8px; }}
        .metrics {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; }}
        .metric {{ text-align: center; padding: 15px; background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #2563eb; }}
        .metric-label {{ font-size: 12px; color: #6b7280; margin-top: 5px; }}
        .warning {{ background: #fef3c7; padding: 10px; margin: 5px 0; border-radius: 4px; font-size: 14px; }}
        .escalated {{ background: #fee2e2; color: #dc2626; }}
        .success {{ background: #dcfce7; color: #22c55e; }}
    </style>
</head>
<body>
    <h1>🧠 Reasoning Trace Report</h1>
    <p><strong>Trace ID:</strong> {trace.trace_id}</p>
    <p><strong>Duration:</strong> {trace.total_duration_ms}ms</p>
    
    <div class="section {'escalated' if trace.escalated else 'success'}">
        <h2>{'⚠️ ESCALATED TO HUMAN' if trace.escalated else '✅ DECISION: ' + (trace.final_decision or 'N/A')}</h2>
        {f'<p><strong>Reason:</strong> {trace.escalation_reason}</p>' if trace.escalated else ''}
    </div>
    
    <div class="section">
        <h2>📊 Key Metrics</h2>
        <div class="metrics">
            <div class="metric">
                <div class="metric-value">{trace.final_confidence:.0%}</div>
                <div class="metric-label">Final Confidence</div>
            </div>
            <div class="metric">
                <div class="metric-value">{trace.data_quality_score:.0%}</div>
                <div class="metric-label">Data Quality</div>
            </div>
            <div class="metric">
                <div class="metric-value">{trace.reasoning_quality_score:.0%}</div>
                <div class="metric-label">Reasoning Quality</div>
            </div>
            <div class="metric">
                <div class="metric-value">{len(trace.get_all_warnings())}</div>
                <div class="metric-label">Warnings</div>
            </div>
        </div>
    </div>
    
    <div class="section">
        <h2>🎯 Confidence Gauge</h2>
        {confidence_gauge}
    </div>
    
    <div class="section">
        <h2>📈 Layer Breakdown</h2>
        {layer_breakdown}
    </div>
    
    <div class="section">
        <h2>🔄 Decision Flow</h2>
        <pre class="mermaid">
{mermaid}
        </pre>
    </div>
    
    {'<div class="section"><h2>⚠️ Warnings</h2>' + ''.join(f'<div class="warning">{w}</div>' for w in trace.get_all_warnings()) + '</div>' if trace.get_all_warnings() else ''}
    
    <script>mermaid.initialize({{ startOnLoad: true }});</script>
</body>
</html>'''
        
        return html
