# RISKCAST UI/UX Comprehensive Guide
## AI-Readable Documentation for Decision Intelligence Platform

> **Version**: 2.0  
> **Last Updated**: February 2026  
> **Style**: AI Risk Terminal - Data-dense Enterprise  
> **Mood**: Dark, analytical, precise, high-trust  

---

## 📋 TABLE OF CONTENTS

1. [Design Philosophy](#1-design-philosophy)
2. [Visual Identity](#2-visual-identity)
3. [Color System](#3-color-system)
4. [Typography](#4-typography)
5. [Layout System](#5-layout-system)
6. [Component Library](#6-component-library)
7. [Page Specifications](#7-page-specifications)
8. [Animation System](#8-animation-system)
9. [Interaction Patterns](#9-interaction-patterns)
10. [Responsive Design](#10-responsive-design)
11. [Accessibility](#11-accessibility)
12. [Chart & Data Visualization](#12-chart--data-visualization)

---

## 1. DESIGN PHILOSOPHY

### 1.1 Core Principles

RISKCAST follows the **"AI Risk Terminal"** design paradigm - a Bloomberg Terminal-inspired interface optimized for supply chain decision intelligence.

```
┌─────────────────────────────────────────────────────────────┐
│  DESIGN PRINCIPLES                                          │
├─────────────────────────────────────────────────────────────┤
│  1. DATA DENSITY    → Maximum information per pixel         │
│  2. DARK INTERFACE  → Reduced eye strain, professional feel │
│  3. ANALYTICAL      → Clear hierarchies, scannable layouts  │
│  4. PRECISE         → Exact numbers, no vague descriptions  │
│  5. HIGH-TRUST      → Transparent reasoning, audit trails   │
│  6. ACTION-ORIENTED → Clear CTAs, obvious next steps        │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Design Goals

| Goal | Implementation |
|------|----------------|
| **Speed** | Users understand situation in <5 seconds |
| **Clarity** | Zero ambiguity in recommended actions |
| **Trust** | Every decision backed by visible evidence |
| **Efficiency** | Minimal clicks to complete critical tasks |
| **Consistency** | Same patterns across all features |

### 1.3 User Personas

```
PRIMARY USER: Supply Chain Operations Manager
├── Works in high-pressure environment
├── Needs quick decision-making support
├── Values accuracy over fancy visuals
├── Uses system 8+ hours daily
└── Requires mobile access for alerts

SECONDARY USER: Risk Analyst
├── Deep-dives into data
├── Needs detailed audit trails
├── Reviews AI reasoning
└── Validates recommendations
```

---

## 2. VISUAL IDENTITY

### 2.1 Brand Expression

```
RISKCAST
├── Logo: Stylized shield with pulse line
├── Tagline: "Decision Intelligence for Supply Chain"
├── Personality: Authoritative, Precise, Trustworthy
└── Visual Style: Terminal/HUD aesthetic
```

### 2.2 Design Language

| Element | Style |
|---------|-------|
| **Cards** | Dark backgrounds, subtle borders, corner accents |
| **Borders** | Thin (1px), gradient accents on important items |
| **Corners** | Rounded (8-12px), sharper on data displays |
| **Shadows** | Glow effects for emphasis, subtle for depth |
| **Icons** | Lucide icons, consistent stroke width |

### 2.3 Terminal Aesthetics

```css
/* Terminal Decorations */
.terminal-card {
  /* Corner brackets */
  border-color: transparent;
  position: relative;
}
.terminal-card::before {
  /* Top-left and top-right corners */
  content: '';
  position: absolute;
  width: 12px;
  height: 12px;
  border-left: 2px solid;
  border-top: 2px solid;
}

/* Scan line effect (subtle) */
.scan-lines {
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(0, 245, 255, 0.01) 2px,
    rgba(0, 245, 255, 0.01) 4px
  );
}

/* Grid pattern background */
.grid-pattern {
  background-image: radial-gradient(
    rgba(100, 116, 139, 0.1) 1px,
    transparent 1px
  );
  background-size: 20px 20px;
}
```

---

## 3. COLOR SYSTEM

### 3.1 Primary Palette

```
┌─────────────────────────────────────────────────────────────┐
│  PRIMARY COLORS                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  DEEP NAVY (Background)                                     │
│  ████████  #0F172A  rgb(15, 23, 42)                        │
│                                                             │
│  SLATE (Secondary Background)                               │
│  ████████  #1E293B  rgb(30, 41, 59)                        │
│                                                             │
│  CYAN (Primary Accent - Terminal)                           │
│  ████████  #00F5FF  rgb(0, 245, 255)                       │
│  Glow: rgba(0, 245, 255, 0.5)                              │
│                                                             │
│  BLUE (Accent - Actions)                                    │
│  ████████  #3B82F6  rgb(59, 130, 246)                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Semantic Colors - Urgency Levels

```
URGENCY SYSTEM (Time-critical decisions)
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  IMMEDIATE (Act within hours)                               │
│  ████████  #DC2626  Red                                    │
│  ├── Background: rgba(220, 38, 38, 0.1)                    │
│  ├── Border: rgba(220, 38, 38, 0.5)                        │
│  ├── Glow: 0 0 20px rgba(220, 38, 38, 0.5)                │
│  └── Animation: Pulse at 1.5s interval                     │
│                                                             │
│  URGENT (Act within 1-2 days)                               │
│  ████████  #F97316  Orange                                 │
│  ├── Background: rgba(249, 115, 22, 0.1)                   │
│  ├── Border: rgba(249, 115, 22, 0.5)                       │
│  └── Glow: 0 0 15px rgba(249, 115, 22, 0.4)               │
│                                                             │
│  SOON (Act within a week)                                   │
│  ████████  #EAB308  Yellow/Amber                           │
│  ├── Background: rgba(234, 179, 8, 0.1)                    │
│  └── Border: rgba(234, 179, 8, 0.3)                        │
│                                                             │
│  WATCH (Monitor situation)                                  │
│  ████████  #6B7280  Gray                                   │
│  └── Standard styling, no glow                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 Semantic Colors - Severity Levels

```
SEVERITY SYSTEM (Financial impact)
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  CRITICAL (>$100,000 exposure)                              │
│  ████████  #DC2626  Red                                    │
│                                                             │
│  HIGH ($25,000 - $100,000)                                  │
│  ████████  #F97316  Orange                                 │
│                                                             │
│  MEDIUM ($5,000 - $25,000)                                  │
│  ████████  #EAB308  Amber                                  │
│                                                             │
│  LOW (<$5,000)                                              │
│  ████████  #22C55E  Green                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.4 Semantic Colors - Confidence Levels

```
CONFIDENCE SYSTEM (AI prediction reliability)
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  HIGH (≥80%)                                                │
│  ████████  #22C55E  Emerald Green                          │
│  └── Gradient: #22C55E → #10B981 → #059669                 │
│                                                             │
│  MEDIUM (60-79%)                                            │
│  ████████  #EAB308  Amber                                  │
│  └── Gradient: #EAB308 → #F59E0B → #D97706                 │
│                                                             │
│  LOW (<60%)                                                 │
│  ████████  #DC2626  Red                                    │
│  └── Gradient: #DC2626 → #EF4444 → #F87171                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.5 Action Type Colors

```
ACTION COLORS (Decision recommendations)
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  REROUTE    ████████  #00F5FF  Cyan (Primary)              │
│  DELAY      ████████  #A855F7  Purple                      │
│  INSURE     ████████  #00FF94  Bright Green                │
│  MONITOR    ████████  #64748B  Slate Gray                  │
│  DO_NOTHING ████████  #475569  Dark Gray                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.6 Status Colors

```
STATUS SYSTEM
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  SUCCESS     ████████  #22C55E  (Confirmed, Acknowledged)  │
│  ERROR       ████████  #EF4444  (Failed, Rejected)         │
│  WARNING     ████████  #F59E0B  (Needs attention)          │
│  INFO        ████████  #3B82F6  (Informational)            │
│  PENDING     ████████  #6B7280  (Awaiting action)          │
│  ESCALATED   ████████  #8B5CF6  (Sent to human review)     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. TYPOGRAPHY

### 4.1 Font Stack

```css
/* Primary Font - UI Elements */
--font-sans: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 
             'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;

/* Monospace Font - Data, Numbers, Code */
--font-mono: 'JetBrains Mono', 'SF Mono', Monaco, Consolas, 
             'Liberation Mono', 'Courier New', monospace;
```

### 4.2 Type Scale

```
TYPOGRAPHY SCALE
┌─────────────────────────────────────────────────────────────┐
│  SIZE       │ PX   │ USE CASE                              │
├─────────────────────────────────────────────────────────────┤
│  text-xs    │ 12px │ Labels, captions, timestamps          │
│  text-sm    │ 14px │ Body text, descriptions               │
│  text-base  │ 16px │ Primary content                       │
│  text-lg    │ 18px │ Subheadings, emphasis                 │
│  text-xl    │ 20px │ Card titles, section headers          │
│  text-2xl   │ 24px │ Page titles                           │
│  text-3xl   │ 30px │ Large numbers, KPIs                   │
│  text-4xl   │ 36px │ Hero numbers                          │
│  text-5xl   │ 48px │ Dashboard metrics                     │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 Font Weights

```
WEIGHT SYSTEM
├── 400 (normal)   → Body text, descriptions
├── 500 (medium)   → Labels, navigation items
├── 600 (semibold) → Headings, important text
├── 700 (bold)     → Numbers, emphasis
└── 800 (black)    → Hero metrics, gauges
```

### 4.4 Special Typography Styles

```css
/* Monospace Numbers (tabular figures) */
.font-mono {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

/* Terminal Text */
.terminal-text {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

/* Data Value */
.data-value {
  font-family: var(--font-mono);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

/* Glow Text */
.glow-text {
  text-shadow: 0 0 10px currentColor;
}
```

---

## 5. LAYOUT SYSTEM

### 5.1 Application Shell

```
┌─────────────────────────────────────────────────────────────┐
│  RISKCAST APPLICATION LAYOUT                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────┬────────────────────────────────────────────┐ │
│  │          │  TOP BAR (h-14, sticky)                    │ │
│  │          │  ┌──────┬────────────────────┬──────────┐  │ │
│  │          │  │ Menu │  Search (Cmd+K)    │ Actions  │  │ │
│  │          │  └──────┴────────────────────┴──────────┘  │ │
│  │          ├────────────────────────────────────────────┤ │
│  │ SIDEBAR  │                                            │ │
│  │ (w-64    │  MAIN CONTENT AREA                         │ │
│  │  or      │                                            │ │
│  │  w-16    │  ┌────────────────────────────────────┐    │ │
│  │  when    │  │                                    │    │ │
│  │  collapsed)│ │  Page Content                     │    │ │
│  │          │  │  (with padding and scroll)        │    │ │
│  │          │  │                                    │    │ │
│  │          │  └────────────────────────────────────┘    │ │
│  │          │                                            │ │
│  └──────────┴────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Sidebar Specification

```
SIDEBAR NAVIGATION
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  WIDTH                                                      │
│  ├── Expanded: 256px (w-64)                                │
│  └── Collapsed: 64px (w-16)                                │
│                                                             │
│  STRUCTURE                                                  │
│  ┌──────────────────────────────────────────┐              │
│  │  ▼ LOGO & BRAND                          │              │
│  │    Logo icon + "RISKCAST" text           │              │
│  │    Animated glow effect on logo          │              │
│  ├──────────────────────────────────────────┤              │
│  │  ▼ PRIMARY NAVIGATION                    │              │
│  │    • Dashboard        (no badge)         │              │
│  │    • Signals          (count badge)      │              │
│  │    • Decisions        (urgent count)     │              │
│  │    • Customers        (no badge)         │              │
│  │    • Human Review     (escalation count) │              │
│  ├──────────────────────────────────────────┤              │
│  │  ▼ SECONDARY NAVIGATION                  │              │
│  │    • Analytics                           │              │
│  │    • Audit                               │              │
│  │    • Reality                             │              │
│  │    • Settings                            │              │
│  ├──────────────────────────────────────────┤              │
│  │  ▼ FOOTER                                │              │
│  │    System status indicator               │              │
│  │    Version number                        │              │
│  └──────────────────────────────────────────┘              │
│                                                             │
│  ACTIVE STATE                                               │
│  ├── Left border indicator (3px cyan)                      │
│  ├── Background highlight                                  │
│  └── Icon/text color change                                │
│                                                             │
│  COLLAPSED STATE                                            │
│  ├── Only icons visible                                    │
│  ├── Tooltip on hover                                      │
│  └── Badge still visible                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 5.3 Top Bar Specification

```
TOP BAR
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  HEIGHT: 56px (h-14)                                        │
│  POSITION: Sticky top-0                                     │
│  BACKGROUND: slate-900/95 with backdrop-blur                │
│                                                             │
│  ┌─────────┬───────────────────────────────┬─────────────┐ │
│  │  LEFT   │         CENTER                │    RIGHT    │ │
│  │         │                               │             │ │
│  │  Menu   │  Search Bar (max-w-md)        │  Theme      │ │
│  │  Button │  "Search decisions..."        │  Notifs (3) │ │
│  │ (mobile)│  Keyboard hint: ⌘K           │  User Menu  │ │
│  └─────────┴───────────────────────────────┴─────────────┘ │
│                                                             │
│  USER MENU BUTTON                                           │
│  ┌────────────────────────┐                                │
│  │  [Avatar] Admin  ▼    │                                 │
│  │   ├── 28x28 circle    │                                 │
│  │   ├── Gradient bg     │                                 │
│  │   └── Status dot      │                                 │
│  └────────────────────────┘                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 5.4 Grid System

```
GRID SPECIFICATIONS
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  DASHBOARD GRID                                             │
│  ├── KPI Cards: grid-cols-4 (responsive)                   │
│  ├── Main Charts: grid-cols-2                              │
│  └── Gap: 24px (gap-6)                                     │
│                                                             │
│  LIST PAGES (Signals, Decisions)                           │
│  ├── Cards: grid-cols-1 or grid-cols-2                     │
│  ├── Gap: 16px (gap-4)                                     │
│  └── Max items visible: Scroll for more                    │
│                                                             │
│  DETAIL PAGES                                               │
│  ├── Header: Full width                                    │
│  ├── Content: max-w-4xl centered                           │
│  └── Sidebar info: Fixed width on desktop                  │
│                                                             │
│  7 QUESTIONS LAYOUT                                         │
│  ├── Q1-Q4: Standard cards                                 │
│  ├── Q5: Highlighted with border + glow                    │
│  ├── Q6-Q7: Standard cards                                 │
│  └── Staggered animation on entry                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 5.5 Spacing Scale

```
SPACING (4px base unit)
┌─────────────────────────────────────────────────────────────┐
│  TOKEN     │ VALUE │ USE CASE                              │
├─────────────────────────────────────────────────────────────┤
│  space-0   │ 0     │ No spacing                            │
│  space-0.5 │ 2px   │ Tight icon gaps                       │
│  space-1   │ 4px   │ Inline elements                       │
│  space-1.5 │ 6px   │ Small gaps                            │
│  space-2   │ 8px   │ Icon + text                           │
│  space-3   │ 12px  │ Card padding (compact)                │
│  space-4   │ 16px  │ Standard gaps                         │
│  space-5   │ 20px  │ Card padding (default)                │
│  space-6   │ 24px  │ Section gaps                          │
│  space-8   │ 32px  │ Large section gaps                    │
│  space-10  │ 40px  │ Page margins                          │
│  space-12  │ 48px  │ Major section separation              │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. COMPONENT LIBRARY

### 6.1 Button Component

```
BUTTON VARIANTS
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  STANDARD VARIANTS                                          │
│  ├── default     │ Blue bg, white text                     │
│  ├── secondary   │ Slate bg, light text                    │
│  ├── outline     │ Transparent, border only                │
│  ├── ghost       │ No bg, hover reveals                    │
│  ├── link        │ Underline on hover                      │
│  └── destructive │ Red bg for danger actions               │
│                                                             │
│  ACTION VARIANTS (Decision-specific)                        │
│  ├── reroute     │ Cyan bg, terminal style                 │
│  ├── delay       │ Purple bg                               │
│  ├── insure      │ Green bg                                │
│  ├── monitor     │ Gray bg                                 │
│  └── nothing     │ Outline only                            │
│                                                             │
│  URGENCY VARIANTS                                           │
│  ├── immediate   │ Red bg, pulse animation                 │
│  └── urgent      │ Orange bg, subtle pulse                 │
│                                                             │
│  SIZE VARIANTS                                              │
│  ├── sm    │ h-8  px-3 text-xs                             │
│  ├── default │ h-9 px-4 text-sm                            │
│  ├── lg    │ h-10 px-6 text-base                           │
│  ├── xl    │ h-12 px-8 text-lg                             │
│  ├── icon  │ h-9  w-9  (square)                            │
│  └── icon-sm │ h-8 w-8 (small square)                      │
│                                                             │
│  FEATURES                                                   │
│  ├── Loading state with spinner                            │
│  ├── Disabled state (opacity + cursor)                     │
│  ├── Ripple effect on click                                │
│  ├── Icon support (left or right)                          │
│  └── Full-width option                                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Card Component

```
CARD VARIANTS
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  CARD STRUCTURE                                             │
│  ┌──────────────────────────────────────────┐              │
│  │  Top accent line (gradient, 1px)         │              │
│  ├──────────────────────────────────────────┤              │
│  │  CardHeader                              │              │
│  │  ├── CardTitle                           │              │
│  │  └── CardDescription                     │              │
│  ├──────────────────────────────────────────┤              │
│  │  CardContent                             │              │
│  │  └── Main content area                   │              │
│  ├──────────────────────────────────────────┤              │
│  │  CardFooter (optional)                   │              │
│  └──────────────────────────────────────────┘              │
│  Corner decorations (terminal style)                       │
│                                                             │
│  STYLE VARIANTS                                             │
│  ├── default  │ Slate bg, subtle border                    │
│  ├── premium  │ Gradient border effect                     │
│  ├── glass    │ Glassmorphism (blur + transparency)        │
│  ├── outline  │ Border only, transparent bg                │
│  └── ghost    │ Minimal styling                            │
│                                                             │
│  HOVER EFFECTS                                              │
│  ├── lift   │ translateY(-4px) + shadow                    │
│  ├── glow   │ Box-shadow glow effect                       │
│  ├── scale  │ scale(1.02)                                  │
│  └── none   │ No hover effect                              │
│                                                             │
│  URGENCY CARD (Special)                                     │
│  ├── Left border indicator (4px)                           │
│  ├── Color based on urgency level                          │
│  └── Glow effect for IMMEDIATE/URGENT                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 6.3 Badge Component

```
BADGE VARIANTS (20+ types)
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  STANDARD                                                   │
│  ├── default       │ Slate background                      │
│  ├── secondary     │ Lighter slate                         │
│  ├── outline       │ Border only                           │
│  └── premium       │ Gradient background                   │
│                                                             │
│  SEMANTIC                                                   │
│  ├── success       │ Green (for positive outcomes)         │
│  ├── warning       │ Amber (needs attention)               │
│  ├── destructive   │ Red (errors, critical)                │
│  └── info          │ Blue (informational)                  │
│                                                             │
│  URGENCY                                                    │
│  ├── immediate     │ Red + pulse animation                 │
│  ├── urgent        │ Orange                                │
│  ├── soon          │ Yellow                                │
│  └── watch         │ Gray                                  │
│                                                             │
│  SEVERITY                                                   │
│  ├── critical      │ Red                                   │
│  ├── high          │ Orange                                │
│  ├── medium        │ Amber                                 │
│  └── low           │ Green                                 │
│                                                             │
│  CONFIDENCE                                                 │
│  ├── confidence-high    │ Green                            │
│  ├── confidence-medium  │ Amber                            │
│  └── confidence-low     │ Red                              │
│                                                             │
│  ACTION TYPE                                                │
│  ├── reroute       │ Cyan                                  │
│  ├── delay         │ Purple                                │
│  ├── insure        │ Green                                 │
│  ├── monitor       │ Gray                                  │
│  └── nothing       │ Dark gray                             │
│                                                             │
│  STATUS                                                     │
│  ├── pending       │ Gray (awaiting)                       │
│  ├── acknowledged  │ Green (confirmed)                     │
│  ├── overridden    │ Orange (user changed)                 │
│  ├── expired       │ Red (missed deadline)                 │
│  └── escalated     │ Purple (sent to review)               │
│                                                             │
│  SIZE                                                       │
│  ├── sm    │ text-[10px] px-1.5 py-0.5                     │
│  ├── default │ text-xs px-2 py-0.5                         │
│  └── lg    │ text-sm px-2.5 py-1                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 6.4 Toast/Notification System

```
TOAST SPECIFICATIONS
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  TYPES                                                      │
│  ├── success  │ Green accent, checkmark icon               │
│  ├── error    │ Red accent, X icon                         │
│  ├── warning  │ Amber accent, warning icon                 │
│  ├── info     │ Blue accent, info icon                     │
│  └── loading  │ Spinner animation                          │
│                                                             │
│  ANATOMY                                                    │
│  ┌──────────────────────────────────────────┐              │
│  │ [Icon] Title                        [X] │              │
│  │        Description text                  │              │
│  │        [Action Button] (optional)        │              │
│  │ ────────────────────────────────────     │ ← Progress   │
│  └──────────────────────────────────────────┘              │
│                                                             │
│  BEHAVIOR                                                   │
│  ├── Auto-dismiss: 5 seconds (configurable)                │
│  ├── Progress bar shows time remaining                     │
│  ├── Pause on hover                                        │
│  ├── Stack multiple toasts                                 │
│  └── Slide in/out animation                                │
│                                                             │
│  POSITIONS                                                  │
│  ├── top-right (default)                                   │
│  ├── top-left                                              │
│  ├── top-center                                            │
│  ├── bottom-right                                          │
│  ├── bottom-left                                           │
│  └── bottom-center                                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 6.5 Command Palette (Cmd+K)

```
COMMAND PALETTE
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  TRIGGER: Cmd+K (Mac) / Ctrl+K (Windows)                   │
│                                                             │
│  ANATOMY                                                    │
│  ┌──────────────────────────────────────────┐              │
│  │ 🔍 Search decisions, signals, customers... │            │
│  ├──────────────────────────────────────────┤              │
│  │ RECENT                                    │              │
│  │  → Decision DEC-001                       │              │
│  │  → Signal SIG-042                         │              │
│  ├──────────────────────────────────────────┤              │
│  │ QUICK ACTIONS                             │              │
│  │  ⚡ New Decision                          │              │
│  │  📊 View Analytics                        │              │
│  │  ⚙️ Settings                              │              │
│  └──────────────────────────────────────────┘              │
│                                                             │
│  FEATURES                                                   │
│  ├── Fuzzy search matching                                 │
│  ├── Highlight matched characters                          │
│  ├── Keyboard navigation (↑↓ Enter Esc)                   │
│  ├── Category grouping                                     │
│  └── Action shortcuts                                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. PAGE SPECIFICATIONS

### 7.1 Dashboard Page

```
DASHBOARD LAYOUT
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  PAGE HEADER                                                │
│  ├── Title: "Dashboard"                                    │
│  ├── Subtitle: "Supply chain intelligence overview"        │
│  └── Time range selector (7d, 30d, 90d)                    │
│                                                             │
│  KPI CARDS ROW (4 cards)                                    │
│  ┌──────────┬──────────┬──────────┬──────────┐             │
│  │ Active   │ Pending  │ Total    │ System   │             │
│  │ Signals  │ Decisions│ Exposure │ Accuracy │             │
│  │   12     │    5     │  $1.2M   │   87%    │             │
│  │  ↑15%    │  ↓3%     │  ↑8%     │  ↑2%     │             │
│  └──────────┴──────────┴──────────┴──────────┘             │
│                                                             │
│  MAIN CONTENT (2 columns)                                   │
│  ┌─────────────────────┬───────────────────────┐           │
│  │ Urgent Decisions    │ Chokepoint Health     │           │
│  │ (Scrollable list)   │ (Status cards)        │           │
│  │                     │                       │           │
│  │ • DEC-001 IMMEDIATE │ • Red Sea ⚠️ ELEVATED │           │
│  │ • DEC-002 URGENT    │ • Suez ✓ NORMAL      │           │
│  │ • DEC-003 SOON      │ • Panama ✓ NORMAL    │           │
│  └─────────────────────┴───────────────────────┘           │
│                                                             │
│  SECONDARY ROW                                              │
│  ┌─────────────────────┬───────────────────────┐           │
│  │ Recent Activity     │ Quick Stats           │           │
│  │ (Timeline)          │ (Mini charts)         │           │
│  └─────────────────────┴───────────────────────┘           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 Decisions List Page

```
DECISIONS LIST
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  PAGE HEADER                                                │
│  ├── Title: "Decisions" + count badge                      │
│  └── Filters: Status, Urgency, Date range                  │
│                                                             │
│  DECISION CARDS                                             │
│  ┌──────────────────────────────────────────────────┐      │
│  │ [IMMEDIATE] DEC-001                    $45,000  │      │
│  │ Red Sea disruption affecting 5 shipments         │      │
│  │                                                  │      │
│  │ Action: REROUTE    Confidence: 87% HIGH         │      │
│  │ Deadline: 6h remaining ████████░░               │      │
│  │                                                  │      │
│  │ [View Details] [Acknowledge] [Escalate]         │      │
│  └──────────────────────────────────────────────────┘      │
│                                                             │
│  ┌──────────────────────────────────────────────────┐      │
│  │ [URGENT] DEC-002                       $28,000   │      │
│  │ ...                                              │      │
│  └──────────────────────────────────────────────────┘      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 7.3 Decision Detail Page (7 Questions)

```
DECISION DETAIL - 7 QUESTIONS VIEW
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  HEADER                                                     │
│  ┌──────────────────────────────────────────────────┐      │
│  │ ← Back    DEC-001                    [IMMEDIATE] │      │
│  │                                                  │      │
│  │ Red Sea disruption: Houthi attacks affecting     │      │
│  │ commercial shipping routes                       │      │
│  │                                                  │      │
│  │ Exposure: $245,000    Confidence: 87% HIGH      │      │
│  │ Deadline: Feb 6, 2026 18:00 UTC (5h 23m)        │      │
│  └──────────────────────────────────────────────────┘      │
│                                                             │
│  7 QUESTIONS (Staggered layout)                             │
│                                                             │
│  Q1: WHAT IS HAPPENING?                                     │
│  ┌──────────────────────────────────────────────────┐      │
│  │ Houthi militants have launched 3 attacks on     │      │
│  │ commercial vessels in the Red Sea in the past   │      │
│  │ 48 hours. Major shipping lines are rerouting... │      │
│  └──────────────────────────────────────────────────┘      │
│                                                             │
│  Q2: WHEN? (Timeline)                                       │
│  ┌──────────────────────────────────────────────────┐      │
│  │ NOW ──●──── DEADLINE ──●──── PONR ──●──→        │      │
│  │       ↓      6 hours    ↓     12 hours ↓        │      │
│  └──────────────────────────────────────────────────┘      │
│                                                             │
│  Q3: HOW BAD? (Severity)                                    │
│  ┌──────────────────────────────────────────────────┐      │
│  │ Your Exposure: $245,000 across 5 shipments      │      │
│  │                                                  │      │
│  │ Scenario Analysis:                              │      │
│  │ Best (15%)  Base (60%)  Worst (25%)            │      │
│  │ $73K        $245K       $612K                   │      │
│  └──────────────────────────────────────────────────┘      │
│                                                             │
│  Q4: WHY? (Causal Chain)                                    │
│  ┌──────────────────────────────────────────────────┐      │
│  │ [Houthi Attack] →85%→ [Route Closure] →92%→    │      │
│  │ [Shipping Delay] →78%→ [YOUR EXPOSURE]         │      │
│  └──────────────────────────────────────────────────┘      │
│                                                             │
│  ═══════════════════════════════════════════════════       │
│  Q5: WHAT TO DO? (HIGHLIGHTED - PRIMARY ACTION)             │
│  ╔══════════════════════════════════════════════════╗      │
│  ║                                                  ║      │
│  ║  Recommended: REROUTE via Cape of Good Hope     ║      │
│  ║                                                  ║      │
│  ║  Cost: $8,500    Additional Delay: 10-14 days   ║      │
│  ║  Deadline: Feb 6, 6PM UTC                       ║      │
│  ║                                                  ║      │
│  ║  Why this action:                               ║      │
│  ║  • Avoids Red Sea risk zone entirely            ║      │
│  ║  • MSC has available capacity                   ║      │
│  ║  • Insurance coverage maintained                ║      │
│  ║                                                  ║      │
│  ║  [ACKNOWLEDGE]  [OVERRIDE]  [ESCALATE]          ║      │
│  ║                                                  ║      │
│  ╚══════════════════════════════════════════════════╝      │
│  ═══════════════════════════════════════════════════       │
│                                                             │
│  Q6: HOW CONFIDENT? (Gauge + Factors)                       │
│  ┌──────────────────────────────────────────────────┐      │
│  │      ┌───────┐                                  │      │
│  │      │  87%  │  HIGH CONFIDENCE                 │      │
│  │      │ ████  │                                  │      │
│  │      └───────┘                                  │      │
│  │                                                  │      │
│  │ Contributing factors:                           │      │
│  │ + Signal corroboration    +15%                 │      │
│  │ + Historical accuracy     +12%                 │      │
│  │ - Data freshness          -5%                  │      │
│  └──────────────────────────────────────────────────┘      │
│                                                             │
│  Q7: IF NOTHING? (Inaction Cost)                            │
│  ┌──────────────────────────────────────────────────┐      │
│  │ Cost Escalation Over Time                       │      │
│  │                                                  │      │
│  │ $600K ─────────────────────────────────● PONR   │      │
│  │ $400K ──────────────────────●                   │      │
│  │ $245K ─────────────●                            │      │
│  │ NOW ───────────────────────────────→ TIME      │      │
│  │                                                  │      │
│  │ ⚠️ Inaction cost: Additional $367,000          │      │
│  │ ⚠️ Point of no return: 12 hours                │      │
│  └──────────────────────────────────────────────────┘      │
│                                                             │
│  AUDIT TRAIL FOOTER                                         │
│  ┌──────────────────────────────────────────────────┐      │
│  │ Created: Feb 6, 10:00 • Signal: SIG-042         │      │
│  │ [View AI Reasoning] [View Full Audit Trail]     │      │
│  └──────────────────────────────────────────────────┘      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 7.4 Analytics Page

```
ANALYTICS DASHBOARD
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  HEADER                                                     │
│  ├── Title: "ANALYTICS" (terminal style)                   │
│  ├── Live indicator (pulsing)                              │
│  └── Date range + Export button                            │
│                                                             │
│  SYSTEM STATUS BAR                                          │
│  ┌──────────────────────────────────────────────────┐      │
│  │ ● SYSTEM ONLINE  │  12 sessions  │  1,847 signals │     │
│  └──────────────────────────────────────────────────┘      │
│                                                             │
│  KPI CARDS (4 columns)                                      │
│  ┌────────┬────────┬────────┬────────┐                     │
│  │ Total  │ Ack'd  │ Avg    │ Total  │                     │
│  │ Decis. │ Rate   │ Resp.  │ Savings│                     │
│  │  247   │  82%   │ 2.4h   │ $1.85M │                     │
│  └────────┴────────┴────────┴────────┘                     │
│                                                             │
│  MAIN CHARTS (2 columns)                                    │
│  ┌─────────────────────┬───────────────────────┐           │
│  │ Weekly Decisions    │ Action Distribution   │           │
│  │ (Stacked bar +line) │ (Donut + legend)      │           │
│  │                     │                       │           │
│  │ W1 W2 W3 W4 W5      │     REROUTE 45%      │           │
│  │ ██ ██ ██ ██ ██      │     DELAY   28%      │           │
│  │ ▓▓ ▓▓ ▓▓ ▓▓ ▓▓      │     INSURE  15%      │           │
│  └─────────────────────┴───────────────────────┘           │
│                                                             │
│  CALIBRATION SECTION (3 columns)                            │
│  ┌─────────────────────────────┬───────────┐               │
│  │ Calibration Curve           │ Overall   │               │
│  │                             │ Accuracy  │               │
│  │ Predicted vs Actual         │           │               │
│  │     ───●────●───            │   87%     │               │
│  │    ─────────────            │   HIGH    │               │
│  │                             │           │               │
│  └─────────────────────────────┴───────────┘               │
│                                                             │
│  SYSTEM HEALTH MATRIX                                       │
│  ┌─────────────────────────────────────────────────┐       │
│  │ [Radar Chart]          [Progress Bars]          │       │
│  │                        Signal Quality    92%    │       │
│  │                        Data Freshness    98%    │       │
│  │                        Model Confidence  87%    │       │
│  │                        Coverage          78%    │       │
│  │                        Response Time     95%    │       │
│  └─────────────────────────────────────────────────┘       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. ANIMATION SYSTEM

### 8.1 Spring Configurations

```javascript
// Animation spring presets
const springs = {
  // Fast, snappy - for buttons, toggles
  snappy: { stiffness: 400, damping: 30 },
  
  // Smooth - for cards, modals
  smooth: { stiffness: 300, damping: 30 },
  
  // Gentle - for page transitions
  gentle: { stiffness: 200, damping: 25 },
  
  // Bouncy - for success states
  bouncy: { stiffness: 500, damping: 15 },
  
  // Stiff - for micro-interactions
  stiff: { stiffness: 600, damping: 40 }
};
```

### 8.2 Duration Scale

```
ANIMATION DURATIONS
┌─────────────────────────────────────────────────────────────┐
│  TOKEN      │ MS    │ USE CASE                             │
├─────────────────────────────────────────────────────────────┤
│  instant    │ 100   │ State changes, toggles               │
│  fast       │ 150   │ Hover effects, button feedback       │
│  normal     │ 200   │ Standard transitions                 │
│  slow       │ 300   │ Card entrances, reveals              │
│  slower     │ 500   │ Page transitions                     │
│  slowest    │ 800   │ Chart animations                     │
└─────────────────────────────────────────────────────────────┘
```

### 8.3 Motion Variants

```javascript
// Page transition
const pageTransition = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -20 },
  transition: { duration: 0.3 }
};

// Card entrance (staggered)
const staggerContainer = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.1
    }
  }
};

const staggerItem = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 }
};

// Urgency pulse (for critical items)
const urgencyPulse = {
  animate: {
    boxShadow: [
      '0 0 0 0 rgba(220, 38, 38, 0.4)',
      '0 0 0 10px rgba(220, 38, 38, 0)',
    ]
  },
  transition: {
    duration: 1.5,
    repeat: Infinity
  }
};

// Chart line drawing
const chartLine = {
  hidden: { pathLength: 0 },
  visible: {
    pathLength: 1,
    transition: { duration: 2, ease: 'easeOut' }
  }
};
```

### 8.4 Reduced Motion Support

```javascript
// Respect user preferences
const prefersReducedMotion = 
  window.matchMedia('(prefers-reduced-motion: reduce)').matches;

// Simplified variants for reduced motion
const getReducedMotionVariants = (variants) => {
  if (prefersReducedMotion) {
    return {
      initial: { opacity: 0 },
      animate: { opacity: 1 },
      exit: { opacity: 0 }
    };
  }
  return variants;
};
```

---

## 9. INTERACTION PATTERNS

### 9.1 Decision Actions

```
DECISION ACTION FLOW
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  ACKNOWLEDGE (Green button)                                 │
│  ├── Click → Confirmation toast                            │
│  ├── Status changes to "ACKNOWLEDGED"                      │
│  ├── Audit trail updated                                   │
│  └── Optional: Trigger downstream actions                  │
│                                                             │
│  OVERRIDE (Orange button)                                   │
│  ├── Click → Opens reason modal                            │
│  │   ┌────────────────────────────────┐                    │
│  │   │ Why are you overriding?        │                    │
│  │   │                                │                    │
│  │   │ ○ Better information available │                    │
│  │   │ ○ Customer preference          │                    │
│  │   │ ○ Cost considerations          │                    │
│  │   │ ○ Other: [____________]        │                    │
│  │   │                                │                    │
│  │   │ Select alternative action:     │                    │
│  │   │ [DELAY] [INSURE] [MONITOR]    │                    │
│  │   │                                │                    │
│  │   │ [Cancel] [Confirm Override]   │                    │
│  │   └────────────────────────────────┘                    │
│  ├── Requires reason selection                             │
│  └── Creates audit record with justification               │
│                                                             │
│  ESCALATE (Purple button)                                   │
│  ├── Click → Opens escalation form                         │
│  │   ┌────────────────────────────────┐                    │
│  │   │ Escalate to Human Review       │                    │
│  │   │                                │                    │
│  │   │ Reason: [___________________]  │                    │
│  │   │ Priority: ○High ○Normal ○Low   │                    │
│  │   │ Assign to: [Dropdown________]  │                    │
│  │   │                                │                    │
│  │   │ [Cancel] [Create Escalation]  │                    │
│  │   └────────────────────────────────┘                    │
│  ├── Creates escalation ticket                             │
│  ├── Notifies assigned reviewer                            │
│  └── Status changes to "ESCALATED"                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 9.2 Navigation Patterns

```
NAVIGATION HIERARCHY
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  PRIMARY NAVIGATION (Sidebar)                               │
│  ├── Always visible on desktop                             │
│  ├── Collapsible to icons only                             │
│  └── Active state with left border indicator               │
│                                                             │
│  SECONDARY NAVIGATION (Within pages)                        │
│  ├── Tabs for related views                                │
│  ├── Breadcrumbs for detail pages                          │
│  └── Back buttons for drill-down                           │
│                                                             │
│  QUICK NAVIGATION                                           │
│  ├── Command palette (Cmd+K)                               │
│  ├── Notification click → related page                     │
│  └── Card click → detail view                              │
│                                                             │
│  KEYBOARD SHORTCUTS                                         │
│  ├── Cmd+K  → Command palette                              │
│  ├── Esc    → Close modals/dropdowns                       │
│  ├── ↑↓    → Navigate lists                                │
│  ├── Enter  → Select/confirm                               │
│  └── Tab    → Focus navigation                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 9.3 Filtering & Search

```
FILTER PATTERNS
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  INLINE FILTERS (List pages)                                │
│  ┌──────────────────────────────────────────────────┐      │
│  │ Status: [All ▼] Urgency: [All ▼] Date: [30d ▼] │      │
│  │                                                  │      │
│  │ Active filters: [URGENT ×] [This week ×]        │      │
│  └──────────────────────────────────────────────────┘      │
│                                                             │
│  SEARCH BEHAVIOR                                            │
│  ├── Debounced input (300ms)                               │
│  ├── Fuzzy matching                                        │
│  ├── Highlight matched text                                │
│  ├── Recent searches remembered                            │
│  └── Empty state with suggestions                          │
│                                                             │
│  SORT OPTIONS                                               │
│  ├── Date (newest/oldest)                                  │
│  ├── Urgency (most/least urgent)                           │
│  ├── Exposure (highest/lowest)                             │
│  └── Status                                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 10. RESPONSIVE DESIGN

### 10.1 Breakpoints

```
RESPONSIVE BREAKPOINTS
┌─────────────────────────────────────────────────────────────┐
│  NAME    │ MIN-WIDTH │ TYPICAL DEVICES                     │
├─────────────────────────────────────────────────────────────┤
│  mobile  │ 0px       │ Phones (portrait)                   │
│  sm      │ 640px     │ Phones (landscape), small tablets   │
│  md      │ 768px     │ Tablets                             │
│  lg      │ 1024px    │ Laptops, small desktops             │
│  xl      │ 1280px    │ Desktops                            │
│  2xl     │ 1536px    │ Large monitors                      │
└─────────────────────────────────────────────────────────────┘
```

### 10.2 Layout Adaptations

```
RESPONSIVE BEHAVIOR
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  MOBILE (< 768px)                                           │
│  ├── Sidebar: Hidden, hamburger menu                       │
│  ├── TopBar: Simplified, menu button                       │
│  ├── Cards: Single column                                  │
│  ├── Charts: Simplified, smaller                           │
│  ├── Tables: Horizontal scroll or card view                │
│  └── Touch: Swipe gestures enabled                         │
│                                                             │
│  TABLET (768px - 1024px)                                    │
│  ├── Sidebar: Collapsed by default                         │
│  ├── Cards: 2 columns                                      │
│  ├── Charts: Standard size                                 │
│  └── Touch: Larger tap targets                             │
│                                                             │
│  DESKTOP (> 1024px)                                         │
│  ├── Sidebar: Expanded                                     │
│  ├── Cards: 2-4 columns                                    │
│  ├── Charts: Full size with tooltips                       │
│  └── Hover states enabled                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 10.3 Mobile-Specific Features

```
MOBILE OPTIMIZATIONS
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  BOTTOM NAVIGATION                                          │
│  ┌────────────────────────────────────────┐                │
│  │  🏠     📊     📋     👥     ⚡     │                │
│  │ Home  Signals Decis. Customers Review │                │
│  └────────────────────────────────────────┘                │
│                                                             │
│  SWIPE GESTURES                                             │
│  ├── Swipe left: Quick actions (acknowledge)               │
│  ├── Swipe right: Archive/dismiss                          │
│  └── Pull down: Refresh data                               │
│                                                             │
│  TOUCH TARGETS                                              │
│  ├── Minimum 44x44px tap area                              │
│  ├── Adequate spacing between targets                      │
│  └── Visual feedback on touch                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 11. ACCESSIBILITY

### 11.1 WCAG Compliance

```
ACCESSIBILITY STANDARDS
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  TARGET: WCAG 2.1 Level AAA                                 │
│                                                             │
│  COLOR CONTRAST                                             │
│  ├── Normal text: 7:1 minimum                              │
│  ├── Large text: 4.5:1 minimum                             │
│  ├── UI components: 3:1 minimum                            │
│  └── Focus indicators: 3:1 minimum                         │
│                                                             │
│  KEYBOARD NAVIGATION                                        │
│  ├── All interactive elements focusable                    │
│  ├── Logical tab order                                     │
│  ├── Skip links for main content                           │
│  ├── Focus visible at all times                            │
│  └── No keyboard traps                                     │
│                                                             │
│  SCREEN READERS                                             │
│  ├── Semantic HTML structure                               │
│  ├── ARIA labels for icons                                 │
│  ├── Live regions for updates                              │
│  ├── Form field associations                               │
│  └── Image alt text                                        │
│                                                             │
│  MOTION                                                     │
│  ├── Respect prefers-reduced-motion                        │
│  ├── No auto-playing animations                            │
│  ├── Pause/stop controls for animations                    │
│  └── No flashing content (>3 flashes/sec)                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 11.2 Focus Management

```css
/* Focus ring styles */
.focus-visible:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

/* Skip link */
.skip-link {
  position: absolute;
  top: -40px;
  left: 0;
  padding: 8px 16px;
  background: var(--color-accent);
  color: white;
  z-index: 100;
}
.skip-link:focus {
  top: 0;
}

/* Screen reader only */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}
```

---

## 12. CHART & DATA VISUALIZATION

### 12.1 Chart Library (Recharts)

```
CHART COMPONENTS
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  BAR CHARTS                                                 │
│  ├── Stacked bars for composition                          │
│  ├── Grouped bars for comparison                           │
│  ├── Horizontal bars for rankings                          │
│  └── Gradient fills with glow effects                      │
│                                                             │
│  LINE CHARTS                                                │
│  ├── Time series with area fills                           │
│  ├── Multi-line comparison                                 │
│  ├── Reference lines for thresholds                        │
│  └── Animated path drawing                                 │
│                                                             │
│  PIE/DONUT CHARTS                                           │
│  ├── Action distribution                                   │
│  ├── Inner radius for donut style                          │
│  ├── Legend with percentages                               │
│  └── Hover highlight                                       │
│                                                             │
│  SPECIALIZED                                                │
│  ├── Radar: System health matrix                           │
│  ├── Gauge: Confidence scores                              │
│  ├── Sankey: Causal chains                                 │
│  └── Timeline: Decision timeline                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 12.2 Chart Styling

```
TERMINAL CHART THEME
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  COLORS                                                     │
│  ├── Primary: Cyan (#00F5FF)                               │
│  ├── Success: Green (#00FF94)                              │
│  ├── Warning: Amber (#FFB800)                              │
│  ├── Danger: Red (#FF3B3B)                                 │
│  └── Neutral: Slate (#64748B)                              │
│                                                             │
│  GRID                                                       │
│  ├── Color: rgba(100, 116, 139, 0.15)                      │
│  ├── Pattern: Dashed (2px dash, 6px gap)                   │
│  └── Vertical lines optional                               │
│                                                             │
│  AXES                                                       │
│  ├── Font: JetBrains Mono, 10px                            │
│  ├── Color: #64748B                                        │
│  ├── No tick lines                                         │
│  └── Axis line: #334155                                    │
│                                                             │
│  TOOLTIPS                                                   │
│  ├── Background: rgba(2, 6, 23, 0.95)                      │
│  ├── Border: 1px solid #334155                             │
│  ├── Border radius: 12px                                   │
│  ├── Backdrop blur                                         │
│  └── Motion animation                                      │
│                                                             │
│  EFFECTS                                                    │
│  ├── Glow filters on lines/bars                            │
│  ├── Gradient fills                                        │
│  ├── Animated entry                                        │
│  └── Data point glow on hover                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 12.3 Custom Visualizations

```
CUSTOM COMPONENTS
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  CONFIDENCE GAUGE                                           │
│  ┌─────────────────┐                                       │
│  │      ╭───╮      │  Features:                            │
│  │    ╭─┤87%├─╮    │  • Circular SVG gauge                 │
│  │   │  ╰───╯  │   │  • Multi-ring design                  │
│  │   │  HIGH   │   │  • Animated progress                  │
│  │    ╰───────╯    │  • Tick marks                         │
│  │                 │  • Scanner line effect                │
│  └─────────────────┘  • Glow based on level               │
│                                                             │
│  COST ESCALATION CHART                                      │
│  ┌─────────────────────────────────────┐                   │
│  │    $                        ●PONR   │  Features:        │
│  │    │              ●──●──●          │  • Area + line     │
│  │    │     ●──●──●                   │  • NOW marker      │
│  │    │●──●                           │  • PONR marker     │
│  │    └──────────────────────→ Time   │  • Gradient fill   │
│  └─────────────────────────────────────┘  • Tooltip       │
│                                                             │
│  TIMELINE VISUALIZATION                                     │
│  ┌─────────────────────────────────────┐                   │
│  │ NOW ──●─────●─────●────────→       │  Features:        │
│  │       ↓     ↓     ↓                │  • HUD markers     │
│  │      Now  Dead  PONR               │  • Progress line   │
│  │            line                     │  • Pulse effects   │
│  └─────────────────────────────────────┘  • Time labels   │
│                                                             │
│  CAUSAL CHAIN DIAGRAM                                       │
│  ┌─────────────────────────────────────┐                   │
│  │ [Root] →85%→ [Effect] →92%→ [You]  │  Features:        │
│  │  Cause       Chain       Impact    │  • Node cards      │
│  │                                     │  • Confidence %    │
│  └─────────────────────────────────────┘  • Flow animation │
│                                                             │
│  SCENARIO COMPARISON                                        │
│  ┌────────┬────────┬────────┐                              │
│  │ BEST   │ BASE   │ WORST  │  Features:                   │
│  │ 15%    │ 60%    │ 25%    │  • 3-card layout             │
│  │ $73K   │ $245K  │ $612K  │  • Probability bar           │
│  └────────┴────────┴────────┘  • Expected value calc       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📚 APPENDIX

### A. File Structure

```
frontend/
├── src/
│   ├── app/                    # Page components
│   │   ├── dashboard/
│   │   ├── signals/
│   │   ├── decisions/
│   │   ├── customers/
│   │   ├── human-review/
│   │   ├── analytics/
│   │   ├── audit/
│   │   ├── reality/
│   │   └── settings/
│   ├── components/
│   │   ├── ui/                 # Base UI components
│   │   ├── domain/             # Business components
│   │   │   ├── decisions/
│   │   │   ├── signals/
│   │   │   ├── common/
│   │   │   └── layout/
│   │   └── charts/             # Chart components
│   ├── lib/
│   │   ├── animations.ts       # Animation variants
│   │   ├── chart-theme.ts      # Chart styling
│   │   ├── formatters.ts       # Data formatting
│   │   └── utils.ts            # Utilities
│   ├── types/                  # TypeScript types
│   └── index.css               # Global styles
├── tailwind.config.ts          # Tailwind configuration
└── package.json
```

### B. Technology Stack

| Category | Technology | Version |
|----------|------------|---------|
| Framework | React | 19.2.0 |
| Language | TypeScript | 5.x |
| Routing | React Router | 7.13.0 |
| Styling | Tailwind CSS | 4.x |
| Animations | Framer Motion | 12.33.0 |
| Charts | Recharts | 3.7.0 |
| State | Zustand | 5.0.11 |
| Forms | React Hook Form | 7.71.1 |
| Validation | Zod | 4.3.6 |
| Icons | Lucide React | 0.563.0 |
| Build | Vite | 7.2.4 |

### C. CSS Custom Properties

```css
:root {
  /* Colors */
  --color-background: #0F172A;
  --color-foreground: #F8FAFC;
  --color-card: #1E293B;
  --color-border: #334155;
  --color-accent: #3B82F6;
  --color-cyan: #00F5FF;
  --color-green: #00FF94;
  --color-amber: #FFB800;
  --color-red: #FF3B3B;
  
  /* Typography */
  --font-sans: 'Inter', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
  
  /* Spacing */
  --spacing-unit: 4px;
  
  /* Radius */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  
  /* Shadows */
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
  --shadow-md: 0 4px 6px rgba(0,0,0,0.1);
  --shadow-lg: 0 10px 15px rgba(0,0,0,0.1);
  --shadow-glow-cyan: 0 0 20px rgba(0,245,255,0.5);
}
```

---

## 📝 CHANGELOG

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | Feb 2026 | Terminal style upgrade, chart overhaul |
| 1.5 | Jan 2026 | 7 Questions layout, animations |
| 1.0 | Dec 2025 | Initial design system |

---

*This document is maintained by the RISKCAST Design Team and should be updated with any UI/UX changes.*

**Document generated for AI comprehension - contains complete UI/UX specifications for the RISKCAST Decision Intelligence Platform.**
