"""
Post-Mortem Templates.

Provides templates for post-mortem documentation to ensure consistency.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.ops.postmortem.tracker import PostMortem, ActionItem, IncidentTimeline


# ============================================================================
# TEMPLATE CONSTANTS
# ============================================================================


TIMELINE_TEMPLATE = """
## Timeline

| Time (UTC) | Event | Description | Actor |
|------------|-------|-------------|-------|
{timeline_rows}
"""

ROOT_CAUSE_TEMPLATE = """
## Root Cause Analysis

### Root Causes
{root_causes}

### Contributing Factors
{contributing_factors}

### 5 Whys Analysis
1. Why did the incident occur?
   - [Answer]
2. Why did that happen?
   - [Answer]
3. Why did that happen?
   - [Answer]
4. Why did that happen?
   - [Answer]
5. Why did that happen?
   - [Answer]
"""

ACTION_ITEM_TEMPLATE = """
## Action Items

| ID | Description | Owner | Due Date | Priority | Status |
|----|-------------|-------|----------|----------|--------|
{action_item_rows}
"""

RETROSPECTIVE_TEMPLATE = """
## Retrospective

### What Went Well
{what_went_well}

### What Went Poorly
{what_went_poorly}

### Where We Got Lucky
{where_we_got_lucky}
"""


# ============================================================================
# TEMPLATE GENERATOR
# ============================================================================


class PostMortemTemplate(BaseModel):
    """Generated post-mortem template."""
    
    markdown: str = Field(description="Full markdown document")
    summary: str = Field(description="Executive summary")
    timeline_section: str
    root_cause_section: str
    impact_section: str
    retrospective_section: str
    action_items_section: str


def generate_postmortem_template(postmortem: PostMortem) -> PostMortemTemplate:
    """
    Generate a complete post-mortem template from a PostMortem object.
    
    Args:
        postmortem: PostMortem object with data
        
    Returns:
        PostMortemTemplate with formatted markdown
    """
    # Header
    header = f"""# Post-Mortem: {postmortem.title}

**Incident ID:** {postmortem.incident_id}  
**Severity:** {postmortem.severity.value.upper()}  
**Date:** {postmortem.incident_start.strftime('%Y-%m-%d')}  
**Author:** {postmortem.author}  
**Status:** {postmortem.status.value.title()}  

---

## Executive Summary

{postmortem.summary if postmortem.summary else "[Provide a 2-3 sentence summary of what happened and the impact]"}

### Key Metrics

| Metric | Value |
|--------|-------|
| Time to Detect | {postmortem.time_to_detect_minutes:.1f} minutes |
| Time to Mitigate | {postmortem.time_to_mitigate_minutes:.1f} minutes |
| Time to Resolve | {postmortem.time_to_resolve_minutes:.1f} minutes |
| Customer Impact | {postmortem.customer_impact_minutes:.1f} minutes |
| Customers Affected | {postmortem.customers_affected:,} |
| Revenue Impact | ${postmortem.revenue_impact_usd:,.2f} |
| Decisions Affected | {postmortem.decisions_affected:,} |

---
"""
    
    # Timeline section
    if postmortem.timeline:
        timeline_rows = "\n".join([
            f"| {t.timestamp.strftime('%H:%M:%S')} | {t.event} | {t.description or '-'} | {t.actor or '-'} |"
            for t in postmortem.timeline
        ])
    else:
        timeline_rows = "| | [Add timeline entries] | | |"
    
    timeline_section = TIMELINE_TEMPLATE.format(timeline_rows=timeline_rows)
    
    # Add key incident times
    timeline_section = f"""## Incident Timeline

**Incident Start:** {postmortem.incident_start.strftime('%Y-%m-%d %H:%M:%S UTC')}  
**Detected:** {postmortem.incident_detected.strftime('%Y-%m-%d %H:%M:%S UTC')}  
**Mitigated:** {postmortem.incident_mitigated.strftime('%Y-%m-%d %H:%M:%S UTC')}  
**Resolved:** {postmortem.incident_resolved.strftime('%Y-%m-%d %H:%M:%S UTC')}  

{timeline_section}
"""
    
    # Root cause section
    if postmortem.root_causes:
        root_causes = "\n".join([f"- {rc}" for rc in postmortem.root_causes])
    else:
        root_causes = "- [Identify the root cause(s)]"
    
    if postmortem.contributing_factors:
        contributing_factors = "\n".join([f"- {cf}" for cf in postmortem.contributing_factors])
    else:
        contributing_factors = "- [Identify contributing factors]"
    
    root_cause_section = ROOT_CAUSE_TEMPLATE.format(
        root_causes=root_causes,
        contributing_factors=contributing_factors,
    )
    
    # Impact section
    impact_section = f"""## Impact Assessment

### Customer Impact
- **Customers Affected:** {postmortem.customers_affected:,}
- **Customer Experience:** [Describe how customers were affected]

### Business Impact
- **Revenue Impact:** ${postmortem.revenue_impact_usd:,.2f}
- **Decisions Affected:** {postmortem.decisions_affected:,}
- **SLO Impact:** {postmortem.slo_impact or 'None identified'}

### Operational Impact
- **Duration:** {postmortem.customer_impact_minutes:.1f} minutes
- **Teams Involved:** [List responding teams]
- **Escalations:** [List any escalations]
"""
    
    # Retrospective section
    if postmortem.what_went_well:
        went_well = "\n".join([f"- {item}" for item in postmortem.what_went_well])
    else:
        went_well = "- [What worked well during the incident?]"
    
    if postmortem.what_went_poorly:
        went_poorly = "\n".join([f"- {item}" for item in postmortem.what_went_poorly])
    else:
        went_poorly = "- [What didn't work well?]"
    
    if postmortem.where_we_got_lucky:
        got_lucky = "\n".join([f"- {item}" for item in postmortem.where_we_got_lucky])
    else:
        got_lucky = "- [Were there any near-misses or lucky breaks?]"
    
    retrospective_section = RETROSPECTIVE_TEMPLATE.format(
        what_went_well=went_well,
        what_went_poorly=went_poorly,
        where_we_got_lucky=got_lucky,
    )
    
    # Action items section
    if postmortem.action_items:
        action_rows = "\n".join([
            f"| {item.item_id} | {item.description} | {item.owner} | {item.due_date.strftime('%Y-%m-%d')} | {item.priority} | {item.status.value} |"
            for item in postmortem.action_items
        ])
    else:
        action_rows = "| | [Add action items] | | | | |"
    
    action_items_section = ACTION_ITEM_TEMPLATE.format(action_item_rows=action_rows)
    
    # Add action item guidance
    action_items_section += """
### Action Item Categories
- **Bug Fix:** Fix the immediate issue
- **Improvement:** Prevent recurrence
- **Process:** Update procedures/runbooks
- **Monitoring:** Add/improve alerting

### Action Item Guidelines
- Each item must have an owner
- Due dates should be realistic but aggressive
- P0: 1 week, P1: 2 weeks, P2: 1 month, P3: 1 quarter
"""
    
    # Lessons learned section
    lessons_section = """## Lessons Learned

### Key Takeaways
1. [Takeaway 1]
2. [Takeaway 2]
3. [Takeaway 3]

### Process Improvements
- [What process changes should we make?]

### Technical Improvements
- [What technical changes should we make?]

### Documentation Updates
- [ ] Update runbook: [link]
- [ ] Update architecture docs: [link]
- [ ] Update on-call procedures: [link]
"""
    
    # Footer
    footer = f"""
---

## Appendix

### Related Links
- Incident Ticket: [link]
- Slack Channel: [link]
- Grafana Dashboard: [link]
- Relevant PRs: [links]

### Related Post-Mortems
{chr(10).join([f"- {pm}" for pm in postmortem.related_postmortems]) if postmortem.related_postmortems else "- None identified"}

### Document History
| Date | Author | Change |
|------|--------|--------|
| {datetime.utcnow().strftime('%Y-%m-%d')} | {postmortem.author} | Initial draft |

---

*Post-mortem created: {postmortem.created_at.strftime('%Y-%m-%d %H:%M UTC')}*  
{f"*Published: {postmortem.published_at.strftime('%Y-%m-%d %H:%M UTC')}*" if postmortem.published_at else "*Status: Draft*"}
"""
    
    # Combine all sections
    full_markdown = "\n".join([
        header,
        timeline_section,
        root_cause_section,
        impact_section,
        retrospective_section,
        action_items_section,
        lessons_section,
        footer,
    ])
    
    # Generate summary
    summary = f"""**Incident:** {postmortem.title}
**Severity:** {postmortem.severity.value.upper()}
**Duration:** {postmortem.customer_impact_minutes:.0f} minutes
**Impact:** {postmortem.customers_affected:,} customers, ${postmortem.revenue_impact_usd:,.0f} revenue impact
**Root Causes:** {len(postmortem.root_causes)} identified
**Action Items:** {len(postmortem.action_items)} ({postmortem.action_items_complete} completed)"""
    
    return PostMortemTemplate(
        markdown=full_markdown,
        summary=summary,
        timeline_section=timeline_section,
        root_cause_section=root_cause_section,
        impact_section=impact_section,
        retrospective_section=retrospective_section,
        action_items_section=action_items_section,
    )


def generate_blank_template(
    title: str,
    severity: str,
    incident_date: datetime,
    author: str,
) -> str:
    """
    Generate a blank post-mortem template for manual completion.
    
    Args:
        title: Incident title
        severity: Severity level
        incident_date: Date of incident
        author: Author name
        
    Returns:
        Markdown template string
    """
    return f"""# Post-Mortem: {title}

**Incident ID:** [Auto-generated]  
**Severity:** {severity.upper()}  
**Date:** {incident_date.strftime('%Y-%m-%d')}  
**Author:** {author}  
**Status:** Draft  

---

## Executive Summary

[Provide a 2-3 sentence summary of what happened and the impact]

### Key Metrics

| Metric | Value |
|--------|-------|
| Time to Detect | [X] minutes |
| Time to Mitigate | [X] minutes |
| Time to Resolve | [X] minutes |
| Customer Impact | [X] minutes |
| Customers Affected | [X] |
| Revenue Impact | $[X] |

---

## Incident Timeline

**Incident Start:** [YYYY-MM-DD HH:MM UTC]  
**Detected:** [YYYY-MM-DD HH:MM UTC]  
**Mitigated:** [YYYY-MM-DD HH:MM UTC]  
**Resolved:** [YYYY-MM-DD HH:MM UTC]  

| Time (UTC) | Event | Description | Actor |
|------------|-------|-------------|-------|
| | Incident starts | | |
| | Alert fires | | |
| | Engineer responds | | |
| | Root cause identified | | |
| | Mitigation applied | | |
| | Incident resolved | | |

---

## Root Cause Analysis

### Root Causes
- [Primary root cause]
- [Secondary root cause if applicable]

### Contributing Factors
- [Factor 1]
- [Factor 2]

### 5 Whys Analysis
1. Why did the incident occur?
   - 
2. Why did that happen?
   - 
3. Why did that happen?
   - 
4. Why did that happen?
   - 
5. Why did that happen?
   - 

---

## Impact Assessment

### Customer Impact
- **Customers Affected:** 
- **Customer Experience:** 

### Business Impact
- **Revenue Impact:** $
- **Decisions Affected:** 
- **SLO Impact:** 

---

## Retrospective

### What Went Well
- 

### What Went Poorly
- 

### Where We Got Lucky
- 

---

## Action Items

| ID | Description | Owner | Due Date | Priority | Status |
|----|-------------|-------|----------|----------|--------|
| AI-1 | | | | P1 | Open |
| AI-2 | | | | P1 | Open |
| AI-3 | | | | P2 | Open |

---

## Lessons Learned

### Key Takeaways
1. 
2. 
3. 

---

*Created: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*  
*Author: {author}*
"""
