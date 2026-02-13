# RISKCAST UI/UX SPECIFICATION

> Complete UI/UX Design Documentation for RISKCAST Decision Intelligence Platform

**Version:** 1.0  
**Created:** February 2026  
**Status:** Design Complete - Ready for Implementation

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [User Research](#2-user-research)
3. [Information Architecture](#3-information-architecture)
4. [Design System](#4-design-system)
5. [Key Screens](#5-key-screens)
6. [Interaction Design](#6-interaction-design)
7. [Implementation Guide](#7-implementation-guide)

---

## 1. Executive Summary

### What is RISKCAST?

RISKCAST is an **Autonomous Decision Intelligence System** for supply chain risk management. Unlike traditional alerting systems that notify users of risks, RISKCAST transforms signals into **personalized, actionable decisions** with specific costs, deadlines, and consequences.

### The Key Differentiator

```
COMPETITORS:   "Red Sea disruption detected - Risk Level: HIGH"

RISKCAST:      "REROUTE shipment PO-4521 via Cape with MSC.
                Cost: $8,500. Book by 6PM today.
                If wait 24h: cost becomes $15,000."
```

### The Pipeline

```
OMEN (Signals)  →  ORACLE (Reality)  →  RISKCAST (Decisions)  →  ALERTER (Delivery)
Polymarket         AIS Tracking         7 Questions               WhatsApp
News APIs          Freight Rates        Personalized              Vietnamese
Probability        Correlation          $ Amounts                 Mobile-first
```

### The 7 Questions Framework (SACRED)

Every decision MUST answer these 7 questions:

| # | Question | Output Type |
|---|----------|-------------|
| Q1 | What's happening? | Personalized event summary |
| Q2 | When? | Timeline + urgency (IMMEDIATE/URGENT/SOON/WATCH) |
| Q3 | How bad? | $ exposure + delay days WITH confidence intervals |
| Q4 | Why? | Causal chain from root cause to YOUR impact |
| Q5 | What to do? | Specific action + cost + deadline + carrier |
| Q6 | Confidence? | Score + breakdown + caveats |
| Q7 | If nothing? | Cost escalation at 6h/24h/48h + point of no return |

### The MOAT

The competitive advantage is **CUSTOMER DATA**, not algorithms:

- Day 1: Generic alerts (competitors can copy)
- Day 30: Personalized decisions (know customer routes, shipments, preferences)
- Day 90: Self-improving system (historical accuracy data for calibration)

---

## 2. User Research

### 2.1 User Personas

#### Persona 1: Supply Chain Manager (Primary User)

| Attribute | Detail |
|-----------|--------|
| **Name** | Minh Nguyen |
| **Role** | Supply Chain Manager at Vietnam Exports Co. |
| **Tech Savviness** | Moderate |
| **Primary Device** | Smartphone (WhatsApp) + Laptop |
| **Language** | Vietnamese primary, English for business |
| **Goals** | Protect shipments, minimize costs, quick decisions |
| **Pain Points** | Too many alerts, generic notifications, no clear action |
| **Quote** | *"I don't need to know there's a disruption. I need to know what to do about MY shipments."* |

#### Persona 2: Operations Analyst (Power User)

| Attribute | Detail |
|-----------|--------|
| **Name** | Sarah Chen |
| **Role** | Operations Analyst at Logistics Corp |
| **Tech Savviness** | High - data-driven |
| **Primary Device** | Desktop with multiple monitors |
| **Language** | English |
| **Goals** | Monitor all exposures, understand WHY, optimize over time |
| **Pain Points** | Need aggregate view, want reasoning transparency |
| **Quote** | *"Show me the reasoning. I need to understand before I trust."* |

#### Persona 3: Risk Manager (Escalation Reviewer)

| Attribute | Detail |
|-----------|--------|
| **Name** | David Park |
| **Role** | Senior Risk Manager |
| **Tech Savviness** | Moderate |
| **Primary Device** | Desktop |
| **Language** | English |
| **Goals** | Review escalations, ensure compliance, track performance |
| **Pain Points** | Too many escalations, need full context quickly |
| **Quote** | *"If I override the AI, I need to document why. The system should make that easy."* |

#### Persona 4: Customer (End Recipient)

| Attribute | Detail |
|-----------|--------|
| **Name** | Hà Trần |
| **Role** | Freight Forwarder Owner (SMB) |
| **Tech Savviness** | Low-Moderate |
| **Primary Device** | Smartphone only |
| **Language** | Vietnamese |
| **Goals** | Simple alerts, clear recommendations |
| **Pain Points** | Not tech-savvy, needs Vietnamese, wants to call if confused |
| **Quote** | *"Nói cho tôi biết phải làm gì, bằng tiếng Việt, trên điện thoại của tôi."* |

### 2.2 User Journeys

#### Journey 1: Signal → Decision → Action

**Persona:** Minh (Supply Chain Manager)  
**Trigger:** Red Sea disruption affects his shipments

```
[WhatsApp Alert] → [Open Detail] → [Review 7Q] → [Take Action] → [Confirm]
     30 sec           2-5 min         1 min          Done
```

**Key Moments:**
1. Alert Reception - Must be clear, urgent, personalized
2. Context Loading - 7 Questions must load fast, be scannable
3. Decision Point - Clear CTA with deadline and cost
4. Confirmation - Acknowledgment and next steps

#### Journey 2: Escalation → Human Review → Resolution

**Persona:** David (Risk Manager)  
**Trigger:** AI escalates high-value, low-confidence decision

```
[Notification] → [Review Queue] → [Full Context] → [Resolution Form] → [Submit]
                  Priority sort    Reasoning trace   Approve/Modify/Reject
```

**SLA Targets:**
- CRITICAL: 2 hours
- HIGH: 24 hours
- NORMAL: 72 hours

#### Journey 3: Decision Challenge

**Persona:** Customer via Operations (Sarah)  
**Trigger:** Customer claims decision led to unexpected loss

```
[Customer Call] → [Challenge Form] → [Investigation] → [Resolution]
                  Evidence, Impact    Audit trail       Remedy
```

#### Journey 4: Performance Review

**Persona:** Sarah (Operations Analyst)  
**Trigger:** Monthly review of system performance

```
[Metrics Dashboard] → [Drill Down] → [Identify Issues] → [Action Items]
```

---

## 3. Information Architecture

### 3.1 Complete Sitemap

```
RISKCAST
├── 📊 Dashboard (Home)
│   ├── Overview Cards (Signals, Decisions, Escalations, Health)
│   ├── Active Alerts Timeline
│   ├── Portfolio Exposure Map
│   └── Quick Actions
│
├── 🚨 Signals (OMEN)
│   ├── Signal List
│   │   ├── Filters: Chokepoint, Severity, Status, Date
│   │   └── Sort: Probability, Confidence, Recency
│   ├── Signal Detail
│   │   ├── Signal Metadata
│   │   ├── Evidence Sources
│   │   ├── Affected Customers/Shipments
│   │   └── Timeline
│   └── Signal History
│
├── 📋 Decisions (RISKCAST - THE CORE)
│   ├── Decision List
│   │   ├── Filters: Status, Urgency, Customer, Date
│   │   └── Sort: Urgency, Exposure, Deadline
│   ├── Decision Detail (⭐ 7 Questions View)
│   │   ├── Q1: What's Happening
│   │   ├── Q2: When (Timeline + Urgency)
│   │   ├── Q3: How Bad (Exposure with CI)
│   │   ├── Q4: Why (Causal Chain)
│   │   ├── Q5: What To Do (Action CTA)
│   │   ├── Q6: Confidence (Meter + Breakdown)
│   │   ├── Q7: If Nothing (Cost Escalation)
│   │   ├── Alternative Actions
│   │   ├── Reasoning Trace (Expandable)
│   │   └── Audit Trail Link
│   └── Decision History
│
├── 👥 Customers
│   ├── Customer List
│   ├── Customer Profile
│   │   ├── Company Info
│   │   ├── Routes & Chokepoints
│   │   ├── Risk Tolerance
│   │   └── Notification Preferences
│   ├── Shipments
│   │   ├── Shipment List
│   │   └── Shipment Detail
│   └── Onboarding Wizard
│
├── 🔔 Human Review
│   ├── Escalation Queue
│   │   ├── Priority Sorting (Critical > High > Normal)
│   │   ├── SLA Countdown
│   │   └── Quick Assign
│   ├── Escalation Detail & Resolution
│   ├── Override History
│   ├── Challenge Center
│   └── Feedback Center
│
├── 📈 Analytics
│   ├── Performance Dashboard
│   ├── Calibration Metrics
│   ├── Trust Metrics
│   └── Reports
│
├── 🔍 Audit
│   ├── Audit Trail
│   ├── Integrity Verification
│   └── Export
│
├── 🌍 Reality (Oracle)
│   ├── Chokepoint Health
│   └── Data Sources Status
│
└── ⚙️ Settings
    ├── User Profile
    ├── Notifications
    ├── Thresholds
    └── Team Management
```

### 3.2 Navigation Structure

| Platform | Primary Nav | Secondary Nav |
|----------|-------------|---------------|
| Desktop | Left sidebar (always visible) | Top tabs within section |
| Tablet | Collapsible left sidebar | Horizontal tabs |
| Mobile | Bottom tab bar (5 items) | Back arrow + title |

---

## 4. Design System

### 4.1 Color Palette

#### Primary Colors

| Name | Hex | Usage |
|------|-----|-------|
| Primary | `#0F172A` | Navigation, headers, primary text |
| Primary Light | `#1E293B` | Secondary backgrounds |
| Accent | `#3B82F6` | CTAs, links, focus states |
| Accent Hover | `#2563EB` | Button hover |

#### Semantic Colors

| Name | Hex | Usage |
|------|-----|-------|
| Critical | `#DC2626` | IMMEDIATE urgency, CRITICAL severity, >$100K |
| Warning | `#F97316` | URGENT urgency, HIGH severity, $25-100K |
| Caution | `#EAB308` | SOON urgency, MEDIUM severity, $5-25K |
| Success | `#22C55E` | LOW severity, Confirmed, <$5K |
| Info | `#0EA5E9` | WATCH urgency, Informational |

#### Neutral Colors

| Name | Hex | Usage |
|------|-----|-------|
| Gray 900 | `#111827` | Primary text |
| Gray 700 | `#374151` | Secondary text |
| Gray 500 | `#6B7280` | Placeholder, disabled |
| Gray 300 | `#D1D5DB` | Borders, dividers |
| Gray 100 | `#F3F4F6` | Backgrounds |
| White | `#FFFFFF` | Card backgrounds |

#### Usage Matrix

```
URGENCY:     IMMEDIATE    URGENT       SOON         WATCH
             #DC2626      #F97316      #EAB308      #6B7280

SEVERITY:    CRITICAL     HIGH         MEDIUM       LOW
             #DC2626      #F97316      #EAB308      #22C55E

CONFIDENCE:  HIGH (≥80%)  MEDIUM       LOW (<60%)
             #22C55E      #EAB308      #DC2626
```

### 4.2 Typography

#### Font Families

```css
--font-primary: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
--font-mono: 'JetBrains Mono', 'SF Mono', monospace;
```

#### Type Scale

| Name | Size | Weight | Usage |
|------|------|--------|-------|
| Display | 36px | 700 | Hero numbers, page titles |
| H1 | 30px | 600 | Section headers |
| H2 | 24px | 600 | Card titles |
| H3 | 20px | 600 | Subsection headers |
| Body | 14px | 400 | Default text |
| Body Small | 12px | 400 | Secondary text |
| Label | 12px | 500 | Form labels, badges |
| Overline | 10px | 600 | Category labels (ALL CAPS) |

#### Number Formatting

- Use monospace font for all numbers
- Enable tabular figures (`font-feature-settings: 'tnum'`)
- Format currency: `$47,000` (with commas)
- Format percentages: `87%` (no decimals unless needed)

### 4.3 Spacing

Base unit: **4px**

| Token | Value | Usage |
|-------|-------|-------|
| space-1 | 4px | Tight spacing |
| space-2 | 8px | Compact elements |
| space-3 | 12px | Small gaps |
| space-4 | 16px | Default padding |
| space-6 | 24px | Section spacing |
| space-8 | 32px | Large gaps |

### 4.4 Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| radius-sm | 4px | Buttons, inputs |
| radius-md | 6px | Cards |
| radius-lg | 8px | Large cards |
| radius-full | 9999px | Pills, badges |

### 4.5 Shadows

| Token | Value | Usage |
|-------|-------|-------|
| shadow-sm | `0 1px 2px rgba(0,0,0,0.05)` | Subtle elevation |
| shadow-md | `0 4px 6px rgba(0,0,0,0.07)` | Cards, dropdowns |
| shadow-lg | `0 10px 15px rgba(0,0,0,0.1)` | Modals |

### 4.6 Icons

**Library:** Lucide Icons (open source, MIT license)

**Size Scale:**
- xs: 12px
- sm: 16px
- md: 20px
- lg: 24px
- xl: 32px

**Domain-Specific Icons:**

| Concept | Icon |
|---------|------|
| IMMEDIATE | AlertCircle (red) |
| URGENT | AlertTriangle (orange) |
| SOON | Clock (yellow) |
| WATCH | Eye (gray) |
| REROUTE | RotateCcw |
| DELAY | Pause |
| INSURE | Shield |
| MONITOR | Eye |
| DO_NOTHING | Square |

---

## 5. Key Screens

### 5.1 Dashboard

**Purpose:** At-a-glance overview of system health and pending actions.

**Key Components:**
- 4 stat cards (Signals, Decisions, Escalations, Exposure)
- Immediate action required section (sorted by urgency)
- Chokepoint health indicators
- Recent activity feed
- System health status

### 5.2 Decision Detail (7 Questions View) ⭐ THE CORE

**Purpose:** Display complete decision with all 7 questions answered.

**Layout:**
```
┌─────────────────────────────────────────────┐
│ Header: Customer, Shipment, Status, Urgency │
├─────────────────────────────────────────────┤
│ Q1: What's Happening                        │
│     Personalized event summary              │
│     Affected shipments table                │
├─────────────────────────────────────────────┤
│ Q2: When                                    │
│     Timeline visualization                  │
│     Decision deadline with countdown        │
├─────────────────────────────────────────────┤
│ Q3: How Bad                                 │
│     Exposure: $XXX,XXX (with 90% CI)        │
│     Delay: X-Y days                         │
├─────────────────────────────────────────────┤
│ Q4: Why                                     │
│     Causal chain diagram: A → B → C → You   │
│     Evidence sources                        │
├─────────────────────────────────────────────┤
│ Q5: What To Do ⭐                           │
│     Primary action card with CTA            │
│     Cost, deadline, carrier info            │
│     Alternative actions                     │
├─────────────────────────────────────────────┤
│ Q6: Confidence                              │
│     Overall score with bar                  │
│     Factor breakdown                        │
│     Caveats                                 │
├─────────────────────────────────────────────┤
│ Q7: If Nothing                              │
│     Cost escalation chart over time         │
│     Point of no return                      │
├─────────────────────────────────────────────┤
│ Actions: [Acknowledge] [Act] [Override]     │
├─────────────────────────────────────────────┤
│ Audit Trail: ID, Hash, Model version        │
└─────────────────────────────────────────────┘
```

### 5.3 Decision Detail (Mobile)

**Purpose:** Mobile-optimized for WhatsApp deep links.

**Key Adaptations:**
- Collapsible Q sections
- Sticky CTA at bottom
- Larger touch targets (44x44px minimum)
- Countdown in large format
- Swipe actions

### 5.4 Escalation Queue

**Purpose:** Prioritized list of items needing human review.

**Features:**
- Priority grouping (Critical > High > Normal)
- SLA countdown per item
- Trigger reason visible
- Quick assign button
- Recently resolved section

### 5.5 Escalation Resolution Form

**Purpose:** Structured form for resolving escalations.

**Fields:**
- Resolution type: Approve / Modify / Reject
- Final action (dropdown)
- Resolution reason (min 20 chars, required)
- Additional notes (optional)

**Context Panel:**
- Full decision context
- AI recommendation
- Reasoning trace link
- Similar past decisions

---

## 6. Interaction Design

### 6.1 Key Principles

1. **Trust Through Transparency** - Always show WHY, never hide uncertainty
2. **Urgency-Driven Hierarchy** - Visual prominence based on urgency
3. **Confidence Intervals** - Ranges, not false precision
4. **Action-Oriented** - Every screen has a clear next step
5. **Mobile-First for Alerts** - Actionable on phone
6. **Vietnamese Support** - 20-30% longer text accommodation
7. **Enterprise Aesthetic** - Data-dense but clean

### 6.2 Animation Specifications

| Animation | Duration | Easing | Usage |
|-----------|----------|--------|-------|
| Button hover | 100ms | ease-out | Scale, shadow |
| Modal open | 200ms | ease-out | Fade + slide |
| Urgency pulse | 2s infinite | ease-in-out | IMMEDIATE badge |
| Confidence fill | 500ms | ease-out | Bar width |
| Toast appear | 200ms | ease-out | Slide from right |

### 6.3 Critical Flows

**Acknowledge Decision:**
1. Click → Loading → Success → Update card → Toast

**Override Decision:**
1. Click → Modal → Form → Submit → Confirm → Redirect → Audit

**Resolve Escalation:**
1. Review → Select resolution → Type reason → Submit → Confirm → Notify customer

---

## 7. Implementation Guide

### 7.1 Recommended Tech Stack

| Layer | Technology |
|-------|------------|
| Framework | Next.js 14 (App Router) |
| Styling | Tailwind CSS |
| Components | shadcn/ui |
| Charts | Recharts |
| Maps | Mapbox GL |
| State | Zustand + React Query |
| Forms | React Hook Form + Zod |

### 7.2 Component Priority

**Phase 1 (MVP):**
- Decision Detail (7 Questions)
- Decision List
- Dashboard
- Mobile Decision View
- Navigation

**Phase 2:**
- Escalation Queue & Resolution
- Signal Detail
- Customer Profile
- Override Flow

**Phase 3:**
- Analytics Dashboards
- Audit Trail
- Challenge Center
- Advanced Filters

### 7.3 Responsive Breakpoints

| Breakpoint | Width | Layout |
|------------|-------|--------|
| Mobile | <640px | Single column |
| Tablet | 640-1024px | Two column |
| Desktop | 1024-1440px | Three column + sidebar |
| Wide | >1440px | Three column + detail panel |

### 7.4 Accessibility Requirements

- WCAG AA color contrast (4.5:1 minimum)
- Visible focus indicators
- Full keyboard navigation
- ARIA labels on icons
- Support prefers-reduced-motion
- 200% zoom support

---

## Appendix: CSS Variables

```css
:root {
  /* Colors */
  --color-primary: #0F172A;
  --color-accent: #3B82F6;
  --color-critical: #DC2626;
  --color-warning: #F97316;
  --color-caution: #EAB308;
  --color-success: #22C55E;
  --color-info: #0EA5E9;
  
  /* Typography */
  --font-sans: 'Inter', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
  
  /* Spacing */
  --space-1: 4px;
  --space-2: 8px;
  --space-4: 16px;
  --space-6: 24px;
  --space-8: 32px;
  
  /* Radius */
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;
  
  /* Shadows */
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
  --shadow-md: 0 4px 6px rgba(0,0,0,0.07);
  --shadow-lg: 0 10px 15px rgba(0,0,0,0.1);
  
  /* Transitions */
  --transition-fast: 100ms ease-out;
  --transition-normal: 200ms ease-out;
}
```

---

**Document Version:** 1.0  
**Last Updated:** February 2026  
**Author:** AI Design Assistant  
**Status:** Ready for Implementation
