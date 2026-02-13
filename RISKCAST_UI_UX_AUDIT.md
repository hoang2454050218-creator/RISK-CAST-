# RISKCAST Frontend — Complete UI/UX Architecture Audit

**Generated:** February 6, 2026
**Codebase:** `frontend/` directory of RISKCAST Decision Intelligence Platform
**Total Source Files:** ~81 TypeScript/TSX files | ~21,180 lines of code

---

## Table of Contents

1. [Project Structure Map](#1-project-structure-map)
2. [Routing & Navigation Flow](#2-routing--navigation-flow)
3. [Page-by-Page Breakdown](#3-page-by-page-breakdown)
4. [Component Inventory](#4-component-inventory)
5. [Design System & Visual Language](#5-design-system--visual-language)
6. [Layout Architecture](#6-layout-architecture)
7. [State Management Architecture](#7-state-management-architecture)
8. [API & Data Layer](#8-api--data-layer)
9. [UX Patterns & Interactions](#9-ux-patterns--interactions)
10. [Flow Diagrams](#10-flow-diagrams)
11. [Known Issues & Gaps](#11-known-issues--gaps)
12. [Tech Stack Summary](#12-tech-stack-summary)

---

## 1. PROJECT STRUCTURE MAP

```
frontend/
├── .gitignore                          # Git ignore rules
├── eslint.config.js                    # ESLint flat config (TS + React Hooks + React Refresh)
├── index.html                          # Vite entry HTML
├── package.json                        # Dependencies and scripts
├── package-lock.json                   # Lockfile
├── README.md                           # Project readme (Vite boilerplate)
├── tsconfig.json                       # Base TypeScript config
├── tsconfig.app.json                   # App-specific TS config
├── tsconfig.node.json                  # Node-specific TS config
├── vite.config.ts                      # Vite config (React + Tailwind + @ alias)
│
├── public/
│   └── vite.svg                        # ⚠️ DEAD FILE — never referenced
│
└── src/
    ├── App.tsx                         # ⚠️ DEAD FILE — original prototype, replaced by router
    ├── index.css                       # Master design system (960 lines, themes, keyframes)
    ├── main.tsx                        # Entry point — providers + router mount
    ├── router.tsx                      # All routes with lazy loading + Suspense
    │
    ├── app/                            # === PAGES ===
    │   ├── analytics/page.tsx          # Analytics dashboard with charts (1040 lines)
    │   ├── audit/page.tsx              # Audit trail event log (239 lines)
    │   ├── customers/
    │   │   ├── page.tsx                # Customer list with search (242 lines)
    │   │   └── [id]/page.tsx           # Customer detail view (399 lines)
    │   ├── dashboard/page.tsx          # Main dashboard — stats, urgent items (601 lines)
    │   ├── decisions/
    │   │   ├── page.tsx                # Decision list with filters/sort (327 lines)
    │   │   └── [id]/page.tsx           # Decision detail — 7 Questions view (56 lines)
    │   ├── human-review/
    │   │   ├── page.tsx                # Escalation queue (673 lines)
    │   │   └── [id]/page.tsx           # Escalation detail with actions (484 lines)
    │   ├── reality/page.tsx            # Oracle reality snapshot — chokepoints/rates (237 lines)
    │   ├── settings/page.tsx           # Settings with tabs (242 lines)
    │   └── signals/
    │       ├── page.tsx                # Signal list with filters (300 lines)
    │       └── [id]/page.tsx           # Signal detail view (332 lines)
    │
    ├── assets/
    │   └── react.svg                   # ⚠️ DEAD FILE — never referenced
    │
    ├── components/                     # === COMPONENTS ===
    │   ├── charts/                     # Data visualization components
    │   │   ├── CausalChainDiagram.tsx  # Causal chain flowchart (521 lines)
    │   │   ├── ConfidenceGauge.tsx     # Circular confidence gauge (492 lines)
    │   │   ├── CostEscalationChart.tsx # Cost trajectory line chart (483 lines)
    │   │   ├── ExposureChart.tsx       # Exposure bar chart (372 lines)
    │   │   ├── ScenarioVisualization.tsx # Best/base/worst scenarios (452 lines)
    │   │   ├── TimelineVisualization.tsx # Horizontal timeline (450 lines)
    │   │   └── index.ts               # Barrel export
    │   │
    │   ├── domain/                     # Business-logic components
    │   │   ├── common/                 # Shared domain badges/displays
    │   │   │   ├── ActionBadge.tsx     # Action type badge (132 lines)
    │   │   │   ├── ConfidenceIndicator.tsx # Confidence level display (183 lines)
    │   │   │   ├── CostDisplay.tsx     # Currency display with CI bars (253 lines)
    │   │   │   ├── CountdownTimer.tsx  # Live countdown timer (280 lines)
    │   │   │   ├── SeverityBadge.tsx   # Severity level badge (110 lines)
    │   │   │   ├── UrgencyBadge.tsx    # Urgency level badge (106 lines)
    │   │   │   └── index.ts           # Barrel export
    │   │   │
    │   │   ├── decisions/              # Decision-related components
    │   │   │   ├── ActionButtons.tsx    # Action CTA buttons (274 lines)
    │   │   │   ├── AuditTrailFooter.tsx # Hash/integrity footer (313 lines)
    │   │   │   ├── BatchOperations.tsx  # ⚠️ DEAD — never imported (386 lines)
    │   │   │   ├── DecisionCard.tsx     # Decision list card (367 lines)
    │   │   │   ├── DecisionHeader.tsx   # Decision page header (139 lines)
    │   │   │   ├── Q1WhatIsHappening.tsx # Q1 section (234 lines)
    │   │   │   ├── Q2When.tsx          # Q2 section (219 lines)
    │   │   │   ├── Q3HowBad.tsx        # Q3 section (279 lines)
    │   │   │   ├── Q4Why.tsx           # Q4 section (282 lines)
    │   │   │   ├── Q5WhatToDo.tsx      # Q5 section (679 lines)
    │   │   │   ├── Q6Confidence.tsx    # Q6 section (320 lines)
    │   │   │   ├── Q7IfNothing.tsx     # Q7 section (472 lines)
    │   │   │   ├── ReasoningTraceModal.tsx # AI reasoning trace modal (451 lines)
    │   │   │   ├── SevenQuestionsView.tsx  # Full 7Q orchestrator (300 lines)
    │   │   │   └── index.ts           # Barrel export
    │   │   │
    │   │   ├── layout/                 # App shell components
    │   │   │   ├── AppLayout.tsx       # Root layout with Outlet (109 lines)
    │   │   │   ├── MobileNav.tsx       # Bottom nav bar (91 lines)
    │   │   │   ├── Sidebar.tsx         # Left sidebar nav (388 lines)
    │   │   │   ├── TopBar.tsx          # Top header bar (416 lines)
    │   │   │   └── index.ts           # Barrel export
    │   │   │
    │   │   └── signals/                # Signal-related components
    │   │       ├── EvidenceList.tsx     # Evidence cards list (157 lines)
    │   │       ├── SignalCard.tsx       # Signal list card (316 lines)
    │   │       └── index.ts           # Barrel export
    │   │
    │   └── ui/                         # === PRIMITIVES ===
    │       ├── animated-number.tsx     # Animated number displays (416 lines)
    │       ├── badge.tsx               # Badge variants (235 lines)
    │       ├── button.tsx              # Button variants + ripple (230 lines)
    │       ├── card.tsx                # Card variants + motion (281 lines)
    │       ├── command-palette.tsx     # Cmd+K command palette (441 lines)
    │       ├── error-boundary.tsx      # Error boundary + fallback (184 lines)
    │       ├── language-switcher.tsx   # ⚠️ DEAD — never imported (94 lines)
    │       ├── progress-ring.tsx       # ⚠️ DEAD — never imported (410 lines)
    │       ├── skeleton.tsx            # Loading skeletons (315 lines)
    │       ├── swipeable-card.tsx      # Swipeable card (199 lines)
    │       ├── theme-provider.tsx      # Theme context provider (106 lines)
    │       ├── toast.tsx               # Toast notification system (401 lines)
    │       └── index.ts               # Barrel export (partial)
    │
    ├── hooks/                          # === HOOKS ===
    │   ├── useDecisions.ts            # ⚠️ DEAD — never imported (121 lines)
    │   └── useSwipeGesture.ts         # Swipe gesture detection (210 lines)
    │
    ├── lib/                            # === UTILITIES ===
    │   ├── animations.ts              # Complete animation system (689 lines)
    │   ├── api.ts                     # API client (221 lines)
    │   ├── chart-theme.ts             # Chart color system (489 lines)
    │   ├── formatters.ts              # Currency/date/number formatters (302 lines)
    │   ├── mock-data.ts               # Mock Decision data (329 lines)
    │   ├── utils.ts                   # cn(), sleep, generateId, etc. (50 lines)
    │   └── i18n/                      # Internationalization
    │       ├── index.ts               # EN + VI translations (342 lines)
    │       ├── provider.tsx           # I18n context provider (69 lines)
    │       └── useFormatters.ts       # Locale-aware formatters hook (28 lines)
    │
    ├── stores/                         # === STATE ===
    │   └── app.ts                     # ⚠️ DEAD — 4 Zustand stores never imported (250 lines)
    │
    └── types/                          # === TYPES ===
        ├── decision.ts                # Decision + 7Q types (258 lines)
        └── signal.ts                  # Signal + Evidence types + mock data (205 lines)
```

### File Classification Summary

| Category | Count | Total Lines |
|----------|-------|-------------|
| Pages | 13 files | ~5,371 |
| Domain Components | 24 files | ~6,186 |
| UI Primitives | 13 files | ~3,312 |
| Chart Components | 7 files | ~2,778 |
| Hooks | 2 files | ~331 |
| Lib/Utils | 9 files | ~2,489 |
| Stores | 1 file | ~250 |
| Types | 2 files | ~463 |
| Config/Entry | 10 files | — |
| **TOTAL** | **~81 source files** | **~21,180 lines** |

### Dead Files (Imported Nowhere)

| File | Why Dead |
|------|----------|
| `src/App.tsx` | Original prototype; `main.tsx` uses `RouterProvider` → `AppLayout` instead |
| `public/vite.svg` | Vite boilerplate, never referenced |
| `src/assets/react.svg` | Vite boilerplate, never referenced |
| `src/components/ui/language-switcher.tsx` | Defined but never imported by any component |
| `src/components/ui/progress-ring.tsx` | Defined but never imported by any component |
| `src/components/domain/decisions/BatchOperations.tsx` | Defined but never imported by any page |
| `src/hooks/useDecisions.ts` | React Query hooks defined but all pages use mock data directly |
| `src/stores/app.ts` | 4 Zustand stores defined but never imported by any component |

---

## 2. ROUTING & NAVIGATION FLOW

### Route Table

| Path | Component | Type |
|------|-----------|------|
| `/` | `DashboardPage` | Index (landing) |
| `/decisions` | `DecisionsPage` | List |
| `/decisions/:id` | `DecisionDetailPage` | Detail (dynamic) |
| `/signals` | `SignalsPage` | List |
| `/signals/:id` | `SignalDetailPage` | Detail (dynamic) |
| `/customers` | `CustomersPage` | List |
| `/customers/:id` | `CustomerDetailPage` | Detail (dynamic) |
| `/human-review` | `HumanReviewPage` | List |
| `/human-review/:id` | `EscalationDetailPage` | Detail (dynamic) |
| `/analytics` | `AnalyticsPage` | Single page |
| `/audit` | `AuditPage` | Single page |
| `/reality` | `RealityPage` | Single page |
| `/settings` | `SettingsPage` | Single page |
| `*` | Inline 404 | Catch-all |

### Navigation Architecture

- **All routes** are children of `AppLayout` (provides sidebar, topbar, error boundary)
- **All pages** are lazy-loaded with `React.lazy()` + `Suspense` (with spinner fallback)
- **No protected routes** — no auth guards exist
- **No nested layouts** — single flat layout for all pages
- **Dynamic routes** — 4 `:id` patterns (decisions, signals, customers, human-review)

### Navigation Tree

```
AppLayout (/)
├── Dashboard (/) ← landing page
│
├── Signals (/signals)
│   └── Signal Detail (/signals/:id)
│
├── Decisions (/decisions)
│   └── Decision Detail (/decisions/:id) → SevenQuestionsView
│
├── Customers (/customers)
│   └── Customer Detail (/customers/:id)
│
├── Human Review (/human-review)
│   └── Escalation Detail (/human-review/:id)
│
├── Analytics (/analytics)
├── Audit (/audit)
├── Reality (/reality)
├── Settings (/settings)
│
└── 404 Catch-all (*)
```

### User Journey (Primary Flow)

```
Landing (Dashboard)
  → See urgent decisions + stats
  → Click urgent decision
  → Decision Detail (7 Questions View)
    → Read Q1-Q7
    → Accept / Override / Escalate
    → Toast confirmation → back to /decisions
```

### Sidebar Navigation Groups

**Main:**
1. Dashboard (`/`)
2. Signals (`/signals`) — badge: "12"
3. Decisions (`/decisions`) — badge: "3" (critical variant)
4. Customers (`/customers`)
5. Human Review (`/human-review`) — badge: "2" (warning variant)

**Secondary:**
6. Analytics (`/analytics`)
7. Audit (`/audit`)
8. Reality (`/reality`)
9. Settings (`/settings`)

---

## 3. PAGE-BY-PAGE BREAKDOWN

### 3.1 Dashboard (`/`)

| Aspect | Detail |
|--------|--------|
| **Purpose** | Executive overview — stats, urgent items, chokepoint health, activity feed |
| **Layout** | Animated heading + 4 stat cards (2x2 grid) + urgent decisions list + chokepoint health + recent activity |
| **Components** | `StatCard` (local), `UrgencyBadge`, `SeverityBadge`, `CompactCountdown`, `AnimatedNumber`, `AnimatedCurrency`, `Button`, `Badge`, `Link` |
| **State** | None (stateless) |
| **Data Source** | 100% hardcoded inline mock data (stats, urgentDecisions, chokepointHealth, recentActivity) |
| **Interactions** | Click stat cards → navigate to list pages; click urgent decision → `/decisions/:id`; click "SYSTEM: HEALTHY" → toast |
| **Conditional Rendering** | Empty state for no urgent decisions; pulsing animation for IMMEDIATE urgency; pulsing dot for CRITICAL chokepoints |
| **Loading/Error/Empty** | Empty state for urgent decisions only; no loading or error states |
| **Lines** | 601 |

### 3.2 Signals List (`/signals`)

| Aspect | Detail |
|--------|--------|
| **Purpose** | Browse and filter OMEN signals |
| **Layout** | Header + search bar + filter dropdowns + view toggle (grid/list) + signal cards grid |
| **Components** | `SignalCard`, `FilterDropdown` (local), `Button` |
| **State** | `viewMode`, `sortBy`, `filterStatus`, `filterType`, `searchQuery`, `isRefreshing` |
| **Data Source** | `mockSignals` from `@/types/signal` |
| **Interactions** | Search input, filter dropdowns (Status, Type, Sort), view mode toggle, refresh button |
| **Conditional Rendering** | Grid vs list layout; empty state when no matches |
| **Loading/Error/Empty** | Empty state with icon; refresh spinner; no error state |
| **Lines** | 300 |

### 3.3 Signal Detail (`/signals/:id`)

| Aspect | Detail |
|--------|--------|
| **Purpose** | Deep dive into a single signal — evidence, metrics, actions |
| **Layout** | Back button + header with badges + metric cards (probability/confidence/impact/shipments) + evidence list + related decisions + chokepoints |
| **Components** | `MetricCard` (local), `EvidenceList`, `Card`, `Badge`, `Button`, `Link` |
| **State** | `isRefreshing` |
| **Data Source** | `mockSignals.find()` with fallback |
| **Interactions** | Refresh, dismiss signal, generate decision, navigate to related decisions |
| **Conditional Rendering** | Status-specific dismiss button; high probability highlight; decisions vs "Generate Decision" button; expiry date |
| **Loading/Error/Empty** | No loading/error states; empty state for no related decisions |
| **Lines** | 332 |

### 3.4 Decisions List (`/decisions`)

| Aspect | Detail |
|--------|--------|
| **Purpose** | Browse, filter, sort, and act on decisions |
| **Layout** | Header + search + filters (Status/Urgency/Severity/Sort) + active filter chips + view toggle + saved views + decision cards |
| **Components** | `DecisionCard`, `FilterDropdown` (local), `ActiveFilterChip` (local), `Button` |
| **State** | `viewMode`, `sortBy`, `filterStatus`, `filterUrgency`, `filterSeverity`, `searchQuery`, `isLoading`, `savedViews`, `activeViewId`, `showSavedViewsPanel`, `isRefreshing` |
| **Data Source** | `mockDecisions` from `@/lib/mock-data` (duplicated and modified locally) |
| **Interactions** | Search, 4 filter dropdowns with keyboard nav, view mode toggle, saved views panel, save current view, refresh, acknowledge decisions, clear filters |
| **Conditional Rendering** | Active filter chips bar; grid vs list; empty state |
| **Loading/Error/Empty** | Empty state; refresh "SYNCING..."; loading passed to cards |
| **Lines** | 327 |

### 3.5 Decision Detail (`/decisions/:id`)

| Aspect | Detail |
|--------|--------|
| **Purpose** | Full 7 Questions decision view |
| **Layout** | `SevenQuestionsView` fills the content area |
| **Components** | `SevenQuestionsView` (which renders all Q1-Q7, DecisionHeader, ActionButtons, AuditTrailFooter) |
| **State** | `isLoading` |
| **Data Source** | `mockDecision` / `mockDecisions` lookup by ID |
| **Interactions** | Acknowledge (toast + navigate), Override (toast), Escalate (toast + navigate), Request More (toast), Back button |
| **Conditional Rendering** | Delegated to SevenQuestionsView |
| **Loading/Error/Empty** | Loading state passed through |
| **Lines** | 56 |

### 3.6 Customers List (`/customers`)

| Aspect | Detail |
|--------|--------|
| **Purpose** | Browse customer profiles |
| **Layout** | Header + 3 stat cards + search + customer cards grid |
| **Components** | `StatCard` (local), `CustomerCard` (local), `AnimatedNumber`, `AnimatedCurrency`, `Card`, `Badge`, `Button`, `Link` |
| **State** | `searchQuery` |
| **Data Source** | 4 hardcoded inline mock customers |
| **Interactions** | Search by name/email; "Add Customer" button (demo toast); click customer → `/customers/:id` |
| **Conditional Rendering** | Empty state for no search matches; conditional phone display |
| **Loading/Error/Empty** | Empty state with Building icon |
| **Lines** | 242 |

### 3.7 Customer Detail (`/customers/:id`)

| Aspect | Detail |
|--------|--------|
| **Purpose** | Customer profile with shipments and decisions |
| **Layout** | Back button + contact info card + active shipments grid + recent decisions list |
| **Components** | `Card`, `Badge`, `Button`, `Link` |
| **State** | None |
| **Data Source** | Inline `mockCustomerDetails` record with fallback |
| **Interactions** | Edit customer (demo toast); navigate to decisions; navigate to individual decision |
| **Conditional Rendering** | Phone conditional; shipment vessel name; empty decisions state |
| **Loading/Error/Empty** | Empty state for no recent decisions |
| **Lines** | 399 |

### 3.8 Human Review (`/human-review`)

| Aspect | Detail |
|--------|--------|
| **Purpose** | Escalation queue for human review |
| **Layout** | Alert status bar + 4 stat cards + priority/status filter buttons + escalation cards |
| **Components** | `StatCard` (local), `EscalationCard` (local), `CompactCountdown`, `AnimatedNumber`, `Badge`, `Button`, `Link` |
| **State** | `filterPriority`, `filterStatus`, `isRefreshing` |
| **Data Source** | 3 hardcoded inline mock escalations |
| **Interactions** | Priority filters (ALL/CRITICAL/HIGH/NORMAL), status filters (ALL/PENDING/IN_REVIEW/RESOLVED), refresh, click REVIEW → detail |
| **Conditional Rendering** | Critical count pulsing alert; SLA breached badge; terminal corner decorations in dark mode; "Queue Clear" empty state |
| **Loading/Error/Empty** | Empty state with CheckCircle; refresh spinner |
| **Lines** | 673 |

### 3.9 Escalation Detail (`/human-review/:id`)

| Aspect | Detail |
|--------|--------|
| **Purpose** | Review and act on a single escalation |
| **Layout** | Back button + header + decision summary card + activity timeline + comment input + action buttons |
| **Components** | `CompactCountdown`, `Card`, `Badge`, `Button`, `Link` |
| **State** | `comment` |
| **Data Source** | Inline `mockEscalations` record with fallback |
| **Interactions** | Add comment (text input + enter key), Approve (toast + navigate), Reject (toast), Assign to Me (toast), navigate to full decision, navigate to customer |
| **Conditional Rendering** | SLA breached; resolved hides action buttons; assigned/unassigned user info |
| **Loading/Error/Empty** | No explicit loading/error states |
| **Lines** | 484 |

### 3.10 Analytics (`/analytics`)

| Aspect | Detail |
|--------|--------|
| **Purpose** | System performance dashboard with charts |
| **Layout** | Header + date range toggle + 4 KPI cards + decisions by week chart + decisions by type pie + calibration radar + confidence gauge + system health grid |
| **Components** | `TerminalCard` (local), `TerminalKPICard` (local), `ConfidenceGauge`, `AnimatedNumber`, `AnimatedCurrency`, `AnimatedPercentage`, Recharts (`ComposedChart`, `PieChart`, `RadarChart`), `Card`, `Button` |
| **State** | `dateRange` |
| **Data Source** | 100% hardcoded inline (performanceMetrics, decisionsByWeek, decisionsByType, calibrationData, systemMetrics) |
| **Interactions** | Date range cycle (7d/30d/90d — cosmetic only); export report (demo toast) |
| **Conditional Rendering** | Trend up/down arrow + color; health bar coloring by threshold |
| **Loading/Error/Empty** | None |
| **Lines** | 1040 |

### 3.11 Audit (`/audit`)

| Aspect | Detail |
|--------|--------|
| **Purpose** | Audit trail / event log |
| **Layout** | Header + 3 stat cards + search + date range + filter toggle + event list |
| **Components** | `StatCard` (local), `AnimatedNumber`, `Card`, `Badge`, `Button`, `Link` |
| **State** | `searchQuery`, `filterType`, `showFilters`, `dateRange` |
| **Data Source** | 5 hardcoded inline mock audit events |
| **Interactions** | Search, date range cycle, export (toast), filter toggle, filter type buttons, resource links |
| **Conditional Rendering** | Filter panel toggle; empty state; hash display; metadata formatting |
| **Loading/Error/Empty** | Empty state for no matching events |
| **Lines** | 239 |

### 3.12 Reality (`/reality`)

| Aspect | Detail |
|--------|--------|
| **Purpose** | ORACLE reality snapshot — live chokepoint/rate/vessel data |
| **Layout** | Header + 3 stat cards + chokepoint cards + freight rate cards + vessel alert cards |
| **Components** | `StatCard` (local), `AnimatedNumber`, `AnimatedCurrency`, `Card`, `Badge`, `Button` |
| **State** | `isRefreshing` |
| **Data Source** | Hardcoded inline (4 chokepoints, 4 rates, 3 vessel alerts) |
| **Interactions** | Refresh button only |
| **Conditional Rendering** | CRITICAL/DISRUPTED ring borders; pulsing status; trend up/down colors; incident lists |
| **Loading/Error/Empty** | Refresh spinner |
| **Lines** | 237 |

### 3.13 Settings (`/settings`)

| Aspect | Detail |
|--------|--------|
| **Purpose** | App configuration — profile, notifications, thresholds, team, appearance |
| **Layout** | Header + tab navigation (5 tabs) + animated tab content + save button |
| **Components** | `ProfileSettings`/`NotificationSettings`/`ThresholdSettings`/`TeamSettings`/`AppearanceSettings` (all local), `Card`, `Badge`, `Button`, `useTheme` |
| **State** | `activeTab`, `isSaving`, `saved`; nested `density` in AppearanceSettings |
| **Data Source** | All local state; settings are NOT persisted to any backend |
| **Interactions** | Tab switching, form inputs (name/email/role/language), notification checkboxes, threshold number inputs, theme toggle (**only real side effect**), density toggle, save button (fake) |
| **Conditional Rendering** | AnimatePresence for tab switching; save button state (saving/saved/default) |
| **Loading/Error/Empty** | isSaving/saved states on save button |
| **Lines** | 242 |

---

## 4. COMPONENT INVENTORY

### 4.1 UI Primitives

| Component | File | Props | Used By | Reusable? | Internal State | API? | A11y |
|-----------|------|-------|---------|-----------|----------------|------|------|
| `Button` | `ui/button.tsx` | `variant, size, isLoading, ...motion` | Almost all pages | Yes | No | No | Focus ring |
| `IconButton` | `ui/button.tsx` | `variant, size, ...` | None directly | Yes | No | No | Focus ring |
| `ButtonGroup` | `ui/button.tsx` | `orientation, children` | None directly | Yes | No | No | No |
| `Badge` | `ui/badge.tsx` | `variant (25+ variants), size` | All pages | Yes | No | No | No |
| `AnimatedBadge` | `ui/badge.tsx` | Same as Badge | Used in Sidebar | Yes | No | No | No |
| `CountBadge` | `ui/badge.tsx` | `count, max, variant` | Used in Sidebar, MobileNav | Yes | No | No | No |
| `DotBadge` | `ui/badge.tsx` | `color` | Used in TopBar | Yes | No | No | No |
| `StatusDot` | `ui/badge.tsx` | `status` | None directly | Yes | No | No | No |
| `Card` + parts | `ui/card.tsx` | `variant, hover, className` | All pages | Yes | No | No | No |
| `AnimatedCard` | `ui/card.tsx` | `hoverEffect, ...motion` | Various | Yes | No | No | No |
| `UrgencyCard` | `ui/card.tsx` | `urgency` | None directly | Yes | No | No | No |
| `DataCard` | `ui/card.tsx` | `label, value, trend, ...` | None directly | Yes | No | No | No |
| `AnimatedNumber` | `ui/animated-number.tsx` | `value, decimals, prefix, suffix` | Dashboard, Customers, Analytics, Audit, Reality, Human Review | Yes | Framer Motion spring | No | No |
| `AnimatedCurrency` | `ui/animated-number.tsx` | `value, currency` | Dashboard, Customers, Reality | Yes | Framer Motion spring | No | No |
| `AnimatedPercentage` | `ui/animated-number.tsx` | `value` | Analytics | Yes | Framer Motion spring | No | No |
| `SlotMachineNumber` | `ui/animated-number.tsx` | `value, digits` | None | Yes | Yes (animation) | No | No |
| `LiveDataValue` | `ui/animated-number.tsx` | `value, label, unit` | None | Yes | Yes (pulse highlight) | No | No |
| `Skeleton` + variants | `ui/skeleton.tsx` | `className, variant` | AppLayout loading | Yes | No | No | No |
| `SkeletonDecisionView` | `ui/skeleton.tsx` | None | App.tsx (dead) | Yes | No | No | No |
| `SwipeableCard` | `ui/swipeable-card.tsx` | `leftActions, rightActions, threshold, ...` | DecisionCard | Yes | Yes (drag state) | No | No |
| `CommandPalette` | `ui/command-palette.tsx` | `isOpen, onClose` | AppLayout | Yes | Yes (search, selection) | No | Keyboard nav |
| `ErrorBoundary` | `ui/error-boundary.tsx` | `children, fallback?` | AppLayout | Yes | Yes (error catch) | No | No |
| `ThemeProvider` | `ui/theme-provider.tsx` | `children, defaultTheme?` | main.tsx | Yes (context) | Yes (theme) | No | N/A |
| `ToastProvider` | `ui/toast.tsx` | `children, position?` | main.tsx | Yes (context) | Yes (toast queue) | No | No |
| `LanguageSwitcher` | `ui/language-switcher.tsx` | `locale, onChange` | **DEAD** | Yes | No | No | No |
| `ProgressRing` + variants | `ui/progress-ring.tsx` | `value, size, color, ...` | **DEAD** | Yes | Framer spring | No | No |

### 4.2 Domain Components

| Component | File | Props | Used By | Reusable? | Internal State | A11y |
|-----------|------|-------|---------|-----------|----------------|------|
| `AppLayout` | `layout/AppLayout.tsx` | None | Router root | Layout shell | `sidebarCollapsed`, `mobileMenuOpen`, `commandPalette` | Skip-to-content link, landmarks |
| `Sidebar` | `layout/Sidebar.tsx` | `isCollapsed, onToggle, className?` | AppLayout | Layout | No (uses useLocation) | `<nav>`, title tooltips |
| `TopBar` | `layout/TopBar.tsx` | `onMenuClick?, onSearchClick?, showMenuButton?` | AppLayout | Layout | `showUserMenu`, `showNotifications`, `showThemeMenu` | `role="banner"`, aria-labels, aria-expanded, aria-haspopup |
| `MobileNav` | `layout/MobileNav.tsx` | `className?` | AppLayout | Layout | No | `role="navigation"`, aria-labels, WCAG touch targets |
| `SevenQuestionsView` | `decisions/SevenQuestionsView.tsx` | `decision, onAcknowledge, onOverride, onEscalate, ...` | decisions/[id] | Orchestrator | No | Delegates to children |
| `DecisionCard` | `decisions/DecisionCard.tsx` | `decision, onAcknowledge?, variant?, enableSwipe?` | decisions/page | Domain card | No | Minimal |
| `DecisionHeader` | `decisions/DecisionHeader.tsx` | `decision, showNavigation?, onBack?` | SevenQuestionsView | Domain header | No | `<nav>` breadcrumb |
| `ActionButtons` | `decisions/ActionButtons.tsx` | `onAcknowledge, onOverride, onEscalate, ...` | SevenQuestionsView | Action bar | No | Keyboard hints (visual) |
| `AuditTrailFooter` | `decisions/AuditTrailFooter.tsx` | `decision, onViewFullAudit?, onViewReasoning?` | SevenQuestionsView | Footer | `verificationStatus`, `copiedHash` | `aria-label="Copy hash"` |
| `BatchOperations` | `decisions/BatchOperations.tsx` | `selectedIds, onSelectAll, ...` | **DEAD** | Would be reusable | `isActionsLoading` | `aria-pressed`, `role="checkbox"`, `aria-checked` |
| `Q1WhatIsHappening` | `decisions/Q1...tsx` | `data: Q1Data, affectedShipments?` | SevenQuestionsView | Q1 section | No | None |
| `Q2When` | `decisions/Q2When.tsx` | `data: Q2Data` | SevenQuestionsView | Q2 section | No | None |
| `Q3HowBad` | `decisions/Q3...tsx` | `data: Q3Data` | SevenQuestionsView | Q3 section | No | None |
| `Q4Why` | `decisions/Q4Why.tsx` | `data: Q4Data` | SevenQuestionsView | Q4 section | `<details>` native | `<details>/<summary>` |
| `Q5WhatToDo` | `decisions/Q5...tsx` | `data: Q5Data, isRecommended?` | SevenQuestionsView | Q5 section | `viewMode`, `expandedIndex` | None |
| `Q6Confidence` | `decisions/Q6...tsx` | `data: Q6Data, decisionId?` | SevenQuestionsView | Q6 section | `showReasoningTrace` | None |
| `Q7IfNothing` | `decisions/Q7...tsx` | `data: Q7Data` | SevenQuestionsView | Q7 section | `timeRemaining` (live tick) | None |
| `ReasoningTraceModal` | `decisions/ReasoningTraceModal.tsx` | `isOpen, onClose, trace` | Q6Confidence | Modal | `activeStep`, `copied` | `role="dialog"`, `aria-modal`, escape key, sr-only |
| `SignalCard` | `signals/SignalCard.tsx` | `signal, variant?, className?` | signals/page | Domain card | No | None |
| `EvidenceList` | `signals/EvidenceList.tsx` | `evidence, className?` | signals/[id] | Evidence display | No | `target="_blank" rel="noopener"` |
| `UrgencyBadge` | `common/UrgencyBadge.tsx` | `urgency, showIcon?, showDescription?, size?, animate?` | Dashboard, DecisionHeader, Q2When | Yes | No | None |
| `SeverityBadge` | `common/SeverityBadge.tsx` | `severity, showIcon?, showThreshold?, size?` | Dashboard, DecisionHeader, Q3HowBad | Yes | No | None |
| `ConfidenceIndicator` | `common/ConfidenceIndicator.tsx` | `level, score?, variant? (badge/bar/ring)` | SignalCard | Yes | No | None |
| `CostDisplay` | `common/CostDisplay.tsx` | `amount, confidenceInterval?, delta?, size?, label?` | Q5, Q7 | Yes | No | None |
| `CountdownTimer` | `common/CountdownTimer.tsx` | `deadline, label?, size?, onExpire?` | Q2When, SevenQuestionsView | Yes | `timeLeft` (live tick) | `role="timer"`, `aria-live`, `aria-label`, sr-only |
| `ActionBadge` | `common/ActionBadge.tsx` | `action, showIcon?, showDescription?, size?` | Q5, DecisionCard | Yes | No | None |

### 4.3 Chart Components

| Component | File | Props | Used By | Internal State | A11y |
|-----------|------|-------|---------|----------------|------|
| `CausalChainDiagram` | `charts/CausalChainDiagram.tsx` | `causalChain: CausalLink[], rootCause, className?` | Q4Why | No | None |
| `ConfidenceGauge` | `charts/ConfidenceGauge.tsx` | `score, level, factors?, size?` | Q6Confidence, Analytics | Animation springs | None |
| `CostEscalationChart` | `charts/CostEscalationChart.tsx` | `escalationPoints, pointOfNoReturn?, title?` | Q7IfNothing | `scanLinePos`, `showAnnotations` | None |
| `ExposureChart` | `charts/ExposureChart.tsx` | `shipments, title?, className?` | Q3HowBad | No (useMemo) | None |
| `ScenarioVisualization` | `charts/ScenarioVisualization.tsx` | `scenarios?, ...OR decision data` | Q3HowBad | No | None |
| `TimelineVisualization` | `charts/TimelineVisualization.tsx` | `milestones, progress?, className?` | Q2When | No | None |
| `MiniConfidenceGauge` | `charts/ConfidenceGauge.tsx` | `score, size?` | Not used directly | Spring animation | None |

---

## 5. DESIGN SYSTEM & VISUAL LANGUAGE

### Color Palette

#### Light Mode

| Token | Value | Purpose |
|-------|-------|---------|
| `--color-background` | `#FAFBFC` | Page background |
| `--color-foreground` | `#0F172A` | Primary text |
| `--color-card` | `#FFFFFF` | Card surfaces |
| `--color-accent` | `#3B82F6` | Electric Blue — primary CTA |
| `--color-accent-hover` | `#2563EB` | Hover state |
| `--color-muted` | `#F1F5F9` | Subtle backgrounds |
| `--color-muted-foreground` | `#64748B` | Secondary text |
| `--color-border` | `#E2E8F0` | Borders |
| `--color-urgency-immediate` | `#DC2626` | Red — hours |
| `--color-urgency-urgent` | `#F97316` | Orange — 1-2 days |
| `--color-urgency-soon` | `#EAB308` | Yellow — week |
| `--color-urgency-watch` | `#6B7280` | Gray — monitor |
| `--color-severity-critical` | `#DC2626` | Red |
| `--color-severity-high` | `#F97316` | Orange |
| `--color-severity-medium` | `#EAB308` | Yellow |
| `--color-severity-low` | `#22C55E` | Green |
| `--color-success` | `#22C55E` | Green |
| `--color-error` | `#EF4444` | Red |
| `--color-warning` | `#F59E0B` | Amber |
| `--color-info` | `#3B82F6` | Blue |
| `--color-action-reroute` | `#3B82F6` | Blue |
| `--color-action-delay` | `#8B5CF6` | Purple |
| `--color-action-insure` | `#06B6D4` | Cyan |
| `--color-action-monitor` | `#6B7280` | Gray |
| `--color-action-nothing` | `#9CA3AF` | Light Gray |

#### Dark Mode (Terminal Aesthetic)

| Token | Value | Purpose |
|-------|-------|---------|
| `--color-background` | `#0A0F1A` | Deep navy terminal |
| `--color-accent` | `#00F5FF` | Cyan neon |
| `--color-card` | `#0F172A` | Elevated surface |
| `--color-muted` | `#151D2E` | Subtle background |
| `--color-border` | `#1E293B` | Borders |
| `--color-success` | `#00FF94` | Neon green |
| `--color-severity-low` | `#00FF94` | Neon green |
| `--color-action-reroute` | `#00F5FF` | Neon cyan |
| `--color-action-delay` | `#A78BFA` | Soft purple |
| `--color-action-insure` | `#00FF94` | Neon green |

#### Chart Colors

| Mode | Chart 1 | Chart 2 | Chart 3 | Chart 4 | Chart 5 |
|------|---------|---------|---------|---------|---------|
| Light | `#2563EB` | `#16A34A` | `#9333EA` | `#D97706` | `#DC2626` |
| Dark | `#00F5FF` | `#00FF94` | `#A78BFA` | `#FACC15` | `#EF4444` |

### Typography

| Property | Value |
|----------|-------|
| **Sans Font** | `'Inter', system-ui, -apple-system, sans-serif` |
| **Mono Font** | `'JetBrains Mono', ui-monospace, monospace` |
| **H1** | 1.875rem (30px), weight 600, letter-spacing -0.02em |
| **H2** | 1.5rem (24px), weight 600 |
| **H3** | 1.25rem (20px), weight 600 |
| **H4** | 1.125rem (18px), weight 600 |
| **Base** | line-height 1.5 |
| **Data Values** | `font-feature-settings: 'tnum' 1` (tabular numbers) |
| **Data Value Large** | 2rem, weight 600 |
| **Data Value XL** | 2.5rem, weight 700 |

### Spacing System

4px base unit scale: `0, 1px, 0.125rem, 0.25rem, 0.375rem, 0.5rem, 0.625rem, 0.75rem, 0.875rem, 1rem, 1.25rem, 1.5rem, 1.75rem, 2rem, 2.25rem, 2.5rem, 2.75rem, 3rem, 3.5rem, 4rem, 5rem, 6rem`

### Border Radius

`none (0) | sm (4px) | md (6px) | lg (8px) | xl (12px) | 2xl (16px) | 3xl (24px) | full (9999px)`

### Shadows

- **Light mode:** Subtle multi-layer shadows (`rgba(0,0,0,0.04–0.15)`)
- **Dark mode:** Heavier shadows + neon glow effects
- **Glow shadows:** `--shadow-glow-accent`, `--shadow-glow-success`, `--shadow-glow-error`, `--shadow-glow-warning`
- **Card shadows:** Separate `card`, `card-hover`, `card-active` tokens
- **Terminal glow:** `--terminal-glow`, `--terminal-border-glow` (dark mode only)

### Glassmorphism & Special Effects

- `card-glass`: `backdrop-filter: blur(16px)`, semi-transparent white/dark backgrounds
- `card-premium`: Gradient border (blue → purple at 135deg)
- `card-terminal`: Terminal glow border (dark mode only)
- `terminal-corners`: Corner bracket decorations (dark mode only)
- `terminal-scanlines`: CRT scan line effect (dark mode only)
- `terminal-grid`: 20px grid pattern overlay (dark mode only)
- `backdrop-blur-premium`: `blur(24px) saturate(180%)`
- `text-gradient`: Blue → Purple gradient text

### Icon Library

**Lucide React** (`lucide-react@0.563.0`) — used extensively across all components. ~60+ unique icons used including: `AlertTriangle`, `Shield`, `Zap`, `MapPin`, `Clock`, `DollarSign`, `TrendingUp`, `ChevronRight`, `Ship`, `Globe`, `Eye`, `Target`, `Flame`, `Radio`, `Activity`, etc.

### Animation System

**Framer Motion** (`framer-motion@12.33.0`) — used for all animations:

| Category | Animations |
|----------|------------|
| **Spring Physics** | 5 presets: gentle, smooth, bouncy, snappy, stiff |
| **Page Transitions** | fadeInUp with stagger |
| **Card Hover** | Lift + shadow enhancement |
| **Stagger Containers** | 0.05s per item |
| **Button Tap** | Scale 0.98 |
| **Sidebar** | Width spring animation, shared `layoutId` for active indicator |
| **Modal** | Scale + fade with backdrop blur |
| **Toast** | Slide from edge + bounce |
| **Charts** | Line draw, bar grow, gauge spin |
| **Urgency Pulse** | CSS infinite pulse for IMMEDIATE items |
| **Data Pulse** | Background flash on value update |

**CSS Keyframe Animations (12):**
`pulse`, `spin`, `bounce`, `shimmer`, `urgency-pulse`, `urgency-glow`, `glow`, `float`, `fadeIn`, `fadeInUp`, `fadeInScale`, `dataPulse`, `slideInRight`, `slideOutRight`

**Reduced Motion:** Full `prefers-reduced-motion` support — all animations and transitions disabled.

### Dark/Light Mode

| Property | Detail |
|----------|--------|
| **Supported** | Yes — full dual-theme system |
| **Toggle** | ThemeProvider via `useTheme()` hook |
| **Storage** | `localStorage('riskcast-theme')` |
| **Options** | Light / Dark / System |
| **Implementation** | CSS class on `<html>` element (`html.dark`) |
| **System detection** | `prefers-color-scheme` media query listener |
| **Dark mode style** | "Bloomberg Terminal meets Palantir Gotham" — neon cyan/green on deep navy |

### Responsive Design

| Aspect | Detail |
|--------|--------|
| **Mobile detection** | `window.innerWidth < 1024` in AppLayout |
| **Sidebar** | Hidden on mobile, replaced by bottom `MobileNav` + slide-out overlay |
| **TopBar** | Shows hamburger menu on mobile |
| **Content** | `container max-w-5xl mx-auto px-4 sm:px-6` |
| **Cards** | Responsive grid `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3` |
| **MobileNav** | Fixed bottom, hidden on `md+`, safe-area padding for notched devices |
| **Breakpoints** | Standard Tailwind (`sm: 640px, md: 768px, lg: 1024px`) |
| **Tablet** | No dedicated tablet breakpoint handling |

### Design Tokens

**Centralized** in `src/index.css` via Tailwind v4's `@theme` directive. All colors, spacing, radii, shadows, blur, animations, and timing functions are tokenized. Chart theme separately centralized in `lib/chart-theme.ts`.

---

## 6. LAYOUT ARCHITECTURE

### Layout Wrappers

**Single layout:** `AppLayout` wraps all routes.

```
AppLayout
├── Gradient background overlay (dark mode subtle effect)
├── Sidebar (desktop only, lg+)
│   ├── Logo with glow pulse
│   ├── Main nav (5 items with badges)
│   ├── Divider
│   ├── Secondary nav (4 items)
│   └── Version footer ("System Online", "v1.0.0")
├── Main content area (pl-64 or pl-16 when collapsed)
│   ├── TopBar (sticky top-0 z-30)
│   │   ├── Mobile hamburger (mobile only)
│   │   ├── Search bar (Cmd+K trigger)
│   │   ├── Theme toggle dropdown (Light/Dark/System)
│   │   ├── Notifications dropdown (3 hardcoded items)
│   │   └── User menu dropdown (Admin User)
│   ├── <main id="main-content"> (ErrorBoundary wrapped)
│   │   └── <Outlet /> (page content with fade-in)
│   └── (no footer in AppLayout)
├── MobileNav (fixed bottom, mobile only, 5 items)
├── Mobile sidebar overlay (AnimatePresence slide + backdrop)
└── CommandPalette (global, triggered by Cmd+K)
```

### Sidebar Details

- **Width:** 256px expanded, 64px collapsed
- **Collapsible:** Yes, via toggle button with spring animation
- **Active route:** `layoutId="activeIndicator"` shared layout animation (background highlight)
- **Badges:** Hardcoded counts (3 decisions, 12 signals, 2 reviews)
- **Mobile:** Hidden; replaced by bottom MobileNav + slide-out overlay

### TopBar Details

- **Position:** `sticky top-0 z-30`
- **Search:** Cmd+K shortcut badge triggers CommandPalette
- **Theme toggle:** Dropdown with Light/Dark/System options, animated icon swap
- **Notifications:** 3 hardcoded items with urgency dots, navigates on click
- **User menu:** Avatar, "Admin User", Profile/Settings/Help/Sign out (only Settings functional)

### Modal/Drawer/Tooltip/Popover System

| Type | Implementation |
|------|----------------|
| **Modals** | `ReasoningTraceModal` — full-screen with backdrop blur, escape key close, body scroll lock, `role="dialog"` |
| **Drawers** | None |
| **Tooltips** | CSS `title` attributes on collapsed sidebar items (native browser tooltips) |
| **Popovers** | TopBar dropdowns (theme, notifications, user) — click-outside close via document click listeners |
| **Command Palette** | Full-screen overlay with fuzzy search, keyboard nav, grouped results |

### Toast/Notification System

- **Engine:** Zustand store (`useToastStore`)
- **Types:** 5 (success, error, warning, info, loading)
- **Duration:** 5000ms default, loading = Infinity
- **Features:** Auto-dismiss with progress bar, action buttons, promise helper for async operations
- **Positions:** 6 configurable positions (top/bottom × left/center/right)

---

## 7. STATE MANAGEMENT ARCHITECTURE

### Solutions Used

| Solution | Scope | Actually Used? |
|----------|-------|----------------|
| **React useState** | Local component state | Yes — all pages |
| **React Context** | Theme, I18n, Toast | Yes — providers in main.tsx |
| **Zustand** | UI, User, Notifications, Filters | **Defined but NEVER imported** |
| **React Query** | Server state (decisions) | **Defined but NEVER imported** |
| **URL params** | `useParams()` for `:id` routes | Yes |
| **localStorage** | Theme preference, locale | Yes |

### Context Providers (in `main.tsx`)

```
<StrictMode>
  <QueryClientProvider>       ← React Query (staleTime: 30s, retry: 1)
    <I18nProvider>             ← Locale context (EN/VI, persisted)
      <ThemeProvider>          ← Theme context (light/dark/system, persisted)
        <ToastProvider>        ← Toast notification context
          <RouterProvider />   ← React Router
        </ToastProvider>
      </ThemeProvider>
    </I18nProvider>
  </QueryClientProvider>
</StrictMode>
```

### Zustand Stores (Defined but NEVER Used)

| Store | Data | Status |
|-------|------|--------|
| `useUIStore` | sidebarCollapsed, mobileMenuOpen, theme | DEAD — never imported |
| `useUserStore` | currentUser, isAuthenticated | DEAD — never imported |
| `useNotificationsStore` | notifications[], unreadCount | DEAD — never imported |
| `useFiltersStore` | decision/signal filters, sort | DEAD — never imported |

### React Query Hooks (Defined but NEVER Used)

| Hook | Purpose | Status |
|------|---------|--------|
| `useDecisions` | Fetch decision list | DEAD — never imported |
| `useDecision` | Fetch single decision | DEAD — never imported |
| `useAcknowledgeDecision` | Acknowledge mutation | DEAD — never imported |
| `useOverrideDecision` | Override mutation | DEAD — never imported |
| `useEscalateDecision` | Escalate mutation | DEAD — never imported |
| `usePendingDecisionsCount` | Pending count | DEAD — never imported |

### Data Flow Between Pages

Currently **none**. Each page independently imports its own mock data. There is no shared state passing between pages except URL params (`:id`).

### Form State

- **Settings page:** Native `useState` for form fields; no form library used
- **Escalation detail:** `useState` for comment text
- **Search fields:** `useState` per page
- **React Hook Form + Zod:** Listed in `package.json` dependencies but **never used anywhere**

### Caching

- **React Query:** QueryClient configured (staleTime 30s) but never used by any page
- **No SWR or custom caching**

---

## 8. API & DATA LAYER

### API Client (`lib/api.ts`)

The API client is fully implemented but **never called by any page** (all pages use hardcoded mock data).

**Base URL:** `import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'`

### Defined Endpoints

| Method | Endpoint | Sends | Receives | Used By |
|--------|----------|-------|----------|---------|
| `GET` | `/decisions` | `?status, urgency, severity, sort_by, limit, offset` | `DecisionListResponse` | `useDecisions` hook (dead) |
| `GET` | `/decisions/:id` | — | `Decision` | `useDecision` hook (dead) |
| `POST` | `/decisions/:id/acknowledge` | `{ acknowledged_by, notes? }` | `Decision` | `useAcknowledgeDecision` hook (dead) |
| `POST` | `/decisions/:id/override` | `{ overridden_by, new_action, justification }` | `Decision` | `useOverrideDecision` hook (dead) |
| `POST` | `/decisions/:id/escalate` | `{ escalated_by, reason, priority? }` | `Decision` | `useEscalateDecision` hook (dead) |
| `GET` | `/signals` | `?status, event_type, sort_by, limit, offset` | `SignalListResponse` | Never |
| `GET` | `/signals/:id` | — | `Signal` | Never |
| `GET` | `/customers/:id/profile` | — | `CustomerProfile` | Never |
| `GET` | `/health` | — | `HealthStatus` | Never |

### Error Handling

- `ApiError` class with `status`, `message`, `details` fields
- Throws on non-OK responses with parsed error body
- Network errors caught with generic message
- **UI-side:** No API error handling exists since no API calls are made. All "errors" are simulated via toasts with `setTimeout`.

### Mock Data Sources

| Page | Mock Data Location |
|------|--------------------|
| Dashboard | Inline in page file |
| Decisions List | `mockDecisions` from `@/lib/mock-data` (duplicated locally) |
| Decision Detail | `mockDecision` from `@/lib/mock-data` |
| Signals List | `mockSignals` from `@/types/signal` |
| Signal Detail | `mockSignals` from `@/types/signal` |
| Customers List | Inline in page file (4 customers) |
| Customer Detail | Inline in page file (record by ID) |
| Human Review | Inline in page file (3 escalations) |
| Escalation Detail | Inline in page file (record by ID) |
| Analytics | Inline in page file |
| Audit | Inline in page file (5 events) |
| Reality | Inline in page file |
| Settings | Inline defaults (not data-driven) |

---

## 9. UX PATTERNS & INTERACTIONS

### Form Patterns

| Aspect | Status |
|--------|--------|
| **Validation** | None. No form validation exists anywhere. |
| **Error display** | None. No inline field errors. |
| **Submit flow** | Settings save is a fake `setTimeout` with button state change. |
| **Form libraries** | React Hook Form + Zod installed but **never used**. |

### Table/List Patterns

| Feature | Status |
|---------|--------|
| **Grid/List toggle** | Decisions and Signals pages offer grid vs list view modes |
| **Sorting** | Custom sort dropdowns (urgency, exposure, deadline, probability, confidence, impact) |
| **Filtering** | Multi-filter dropdowns with keyboard nav (Arrow keys, Enter, Escape). Active filter chips with remove. "Clear All" option |
| **Pagination** | **Not implemented.** All data renders at once |
| **Search** | Text search with `includes()` match on relevant fields |

### Card Patterns

| Pattern | Used In |
|---------|---------|
| Stat card (icon + number + trend) | Dashboard, Customers, Human Review, Audit, Reality |
| Decision card (urgency bar + data grid + CTA) | Decisions list |
| Signal card (status bar + probability/confidence/impact) | Signals list |
| Escalation card (priority + countdown + SLA) | Human Review |
| Customer card (contact info + exposure) | Customers list |
| 7Q question card (numbered + accent border + content) | Decision detail |

### Progressive Disclosure

| Pattern | Location |
|---------|----------|
| Q1-Q7 sequential layout | Decision Detail (accordion variant available for mobile but not used) |
| `<details>/<summary>` | Q4 Why — expandable causal chain steps |
| Expandable cards | Q5 What To Do — alternative action cards |
| Modal on demand | Q6 Confidence → "View Reasoning" opens ReasoningTraceModal |
| Tab-based | Settings — 5 tab panels |
| Filter panel toggle | Audit page |

### Feedback Patterns

| Pattern | Implementation |
|---------|----------------|
| Loading spinners | Spinning border circle (Suspense fallback, refresh buttons) |
| Skeleton screens | `Skeleton` primitives available but mostly unused by pages |
| Success messages | Toast (green) |
| Error messages | Toast (red) |
| Info messages | Toast (blue) |
| Warning messages | Toast (amber) |
| Progress bar | Toast auto-dismiss progress; cost escalation charts |
| Data pulse | `data-pulse` CSS animation for real-time value updates |

### Empty States

| Page | Empty State Message |
|------|-------------------|
| Dashboard urgent items | "All caught up! No decisions require immediate attention." |
| Decisions list | "No decisions found" with Filter icon |
| Signals list | "No signals found" with Filter icon |
| Customers list | "No customers found" with Building icon |
| Human Review | "Queue Clear — All escalations have been resolved" |
| Audit | "No events found" |
| Signal detail (no decisions) | "No decisions generated yet" with "Generate Decision" button |
| Customer detail (no decisions) | "No recent decisions" |

### Onboarding

**Not implemented.** No guided flow, tooltips, or first-time user experience.

### Keyboard Shortcuts

| Shortcut | Action | Scope |
|----------|--------|-------|
| `Cmd+K` / `Ctrl+K` | Open command palette | Global |
| `Escape` | Close command palette / modal | Global |
| `Arrow Up/Down` | Navigate command palette results | Command palette |
| `Enter` | Select command palette result | Command palette |
| `Arrow Up/Down` | Navigate filter dropdown options | Filter dropdowns |
| `Enter` | Select filter option | Filter dropdowns |
| `Escape` | Close filter dropdown | Filter dropdowns |
| `Enter` in comment field | Submit comment | Escalation detail |
| `Enter` / `O` / `E` | Accept / Override / Escalate | Action buttons (visual hints only — **no key listeners**) |

### Drag and Drop

**Not implemented.** The `SwipeableCard` supports touch swipe gestures but not drag-and-drop.

### Swipe Gestures

- `DecisionCard` supports swipe-left (accept) and swipe-right (escalate/archive/view)
- `useSwipeGesture` hook provides touch gesture detection with velocity tracking
- `SwipeableCard` primitive with configurable thresholds and snap-back physics

---

## 10. FLOW DIAGRAMS

### a) Main User Flow

```
Entry (/)
  │
  ├─→ Dashboard
  │     │
  │     ├─→ Click Stat Card ─→ /signals or /decisions or /human-review
  │     │
  │     └─→ Click Urgent Decision ─→ /decisions/:id
  │           │
  │           ├─→ Read Q1: What is Happening?
  │           ├─→ Read Q2: When?
  │           ├─→ Read Q3: How Bad?
  │           ├─→ Read Q4: Why?
  │           ├─→ Read Q5: What To Do? (Recommended)
  │           ├─→ Read Q6: Confidence (→ View Reasoning Trace)
  │           ├─→ Read Q7: What If Nothing?
  │           │
  │           ├─→ [Accept] ─→ Toast ─→ /decisions
  │           ├─→ [Override] ─→ Toast (modal placeholder)
  │           └─→ [Escalate] ─→ Toast ─→ /human-review
  │
  ├─→ Signals ─→ Filter/Search ─→ Click Signal ─→ /signals/:id
  │     │                                            │
  │     │                                            ├─→ View evidence
  │     │                                            ├─→ [Dismiss Signal]
  │     │                                            └─→ [Generate Decision] ─→ /decisions/:id
  │     │
  ├─→ Human Review ─→ Filter ─→ Click REVIEW ─→ /human-review/:id
  │                                                │
  │                                                ├─→ [Approve] ─→ /human-review
  │                                                ├─→ [Reject] ─→ Toast
  │                                                ├─→ [Assign to Me] ─→ Toast
  │                                                └─→ [Add Comment] ─→ Toast
  │
  ├─→ Customers ─→ Search ─→ Click Customer ─→ /customers/:id
  │                                              ├─→ View shipments
  │                                              └─→ Click decision ─→ /decisions/:id
  │
  ├─→ Analytics (view-only charts)
  ├─→ Audit (view-only log)
  ├─→ Reality (view-only snapshot)
  └─→ Settings (theme toggle is only real action)
```

### b) Data Flow

```
Currently (MVP Demo):
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  Hardcoded   │ ───→ │   Page       │ ───→ │  Components  │
│  Mock Data   │      │  Component   │      │  (via props) │
│  (inline or  │      │              │      │              │
│  mock-data.ts│      │              │      │              │
└──────────────┘      └──────────────┘      └──────────────┘

Intended (with backend connected):
┌──────────────┐      ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  User Input  │ ───→ │  React Query │ ───→ │  API Client  │ ───→ │  Backend     │
│  (filters,   │      │  Hooks       │      │  (lib/api.ts)│      │  /api/v1/... │
│   search)    │      │  (hooks/     │      │              │      │              │
│              │      │   useDecis.) │      │              │      │              │
└──────────────┘      └──────────────┘      └──────────────┘      └──────────────┘
        │                                           │
        │                                           ↓
        │                                   ┌──────────────┐
        │                                   │   Response   │
        │                                   └──────┬───────┘
        │                                          ↓
        │              ┌──────────────┐      ┌──────────────┐
        └──────────── │  UI Update   │ ←─── │  React Query │
                       │  (re-render) │      │  Cache       │
                       └──────────────┘      └──────────────┘
```

### c) Component Hierarchy

```
<StrictMode>
└── <QueryClientProvider>
    └── <I18nProvider>
        └── <ThemeProvider>
            └── <ToastProvider>
                └── <RouterProvider>
                    └── <AppLayout>
                        ├── <Sidebar>
                        │   └── NavItem[] (with badges, shared layout animation)
                        │
                        ├── <TopBar>
                        │   ├── Search trigger
                        │   ├── ThemeDropdown
                        │   ├── NotificationsDropdown
                        │   └── UserMenuDropdown
                        │
                        ├── <CommandPalette> (global overlay)
                        │
                        ├── <MobileNav> (mobile bottom bar)
                        │
                        ├── <ErrorBoundary>
                        │   └── <Outlet> ← per-route content
                        │       │
                        │       ├── DashboardPage
                        │       │   ├── StatCard[]
                        │       │   ├── UrgencyBadge, SeverityBadge
                        │       │   ├── CompactCountdown
                        │       │   └── AnimatedNumber, AnimatedCurrency
                        │       │
                        │       ├── DecisionsPage
                        │       │   ├── FilterDropdown[]
                        │       │   └── DecisionCard[]
                        │       │       ├── UrgencyBadge, SeverityBadge, ActionBadge
                        │       │       └── SwipeableCard
                        │       │
                        │       ├── DecisionDetailPage
                        │       │   └── SevenQuestionsView
                        │       │       ├── DecisionHeader
                        │       │       │   └── UrgencyBadge, SeverityBadge, CompactCountdown
                        │       │       ├── Q1WhatIsHappening
                        │       │       │   └── Badge, AnimatedCurrency
                        │       │       ├── Q2When
                        │       │       │   ├── UrgencyBadge, CountdownTimer
                        │       │       │   └── TimelineVisualization
                        │       │       ├── Q3HowBad
                        │       │       │   ├── SeverityBadge, AnimatedNumber
                        │       │       │   ├── ScenarioVisualization
                        │       │       │   └── ExposureChart
                        │       │       ├── Q4Why
                        │       │       │   └── CausalChainDiagram
                        │       │       ├── Q5WhatToDo
                        │       │       │   ├── ActionBadge, CountdownTimer
                        │       │       │   └── CostDisplay, CostComparison
                        │       │       ├── Q6Confidence
                        │       │       │   ├── ConfidenceGauge
                        │       │       │   └── ReasoningTraceModal
                        │       │       ├── Q7IfNothing
                        │       │       │   ├── CostDisplay, CostEscalationChart
                        │       │       │   └── PONRCountdown (live timer)
                        │       │       ├── ActionButtons
                        │       │       └── AuditTrailFooter
                        │       │
                        │       ├── SignalsPage
                        │       │   └── SignalCard[]
                        │       │       └── ConfidenceIndicator
                        │       │
                        │       ├── SignalDetailPage
                        │       │   └── EvidenceList, MetricCard[]
                        │       │
                        │       ├── CustomersPage / CustomerDetailPage
                        │       ├── HumanReviewPage / EscalationDetailPage
                        │       ├── AnalyticsPage (Recharts charts)
                        │       ├── AuditPage
                        │       ├── RealityPage
                        │       └── SettingsPage
                        │
                        └── Mobile Sidebar Overlay (AnimatePresence)
```

---

## 11. KNOWN ISSUES & GAPS

### Dead Code

| Item | Lines Wasted |
|------|-------------|
| `App.tsx` — unused prototype | 270 |
| `stores/app.ts` — 4 Zustand stores never imported | 250 |
| `hooks/useDecisions.ts` — React Query hooks never used | 121 |
| `ui/language-switcher.tsx` — built but never integrated | 94 |
| `ui/progress-ring.tsx` — built but never integrated | 410 |
| `decisions/BatchOperations.tsx` — built but never integrated | 386 |
| `react.svg`, `vite.svg` — boilerplate assets | — |
| **Total dead code:** | **~1,531 lines** |

### Unused Dependencies (in package.json)

| Package | Version | Status |
|---------|---------|--------|
| `react-hook-form` | ^7.71.1 | Never imported |
| `@hookform/resolvers` | ^5.2.2 | Never imported |
| `zod` | ^4.3.6 | Never imported |
| `@tanstack/react-query` | ^5.90.20 | Configured in main.tsx but hooks never used by pages |

### Hardcoded Data That Should Be Dynamic

- **All 13 pages** use hardcoded mock data — zero real API calls
- Sidebar badge counts (3 decisions, 12 signals, 2 reviews) are hardcoded
- TopBar notifications (3 items) are hardcoded
- TopBar user info ("Admin User") is hardcoded
- Settings form values are not persisted to any backend

### Inconsistent Patterns

| Issue | Details |
|-------|---------|
| **Mock data location** | Some pages import from `@/lib/mock-data` or `@/types/signal`, others define mock data inline. No consistent pattern. |
| **Empty states** | Well-handled on all list pages but missing on detail pages (if ID not found, uses first item or default instead of 404/error). |
| **Error states** | No page has API error handling. All actions use `setTimeout` to simulate async. |
| **Loading states** | Inconsistent — some pages have skeleton/loading support, others show nothing during "refresh." |
| **Filter components** | Each page reimplements `FilterDropdown` locally instead of sharing a common component. |
| **StatCard** | Reimplemented locally in Dashboard, Customers, Human Review, Audit, Reality — 5 separate implementations. |
| **State management** | Zustand stores + React Query hooks built but unused; pages manage all state locally with useState. |
| **Mock signals location** | `mockSignals` is defined in `types/signal.ts` (a type file), not in `lib/mock-data.ts`. |

### Accessibility Gaps

| Issue | Severity |
|-------|----------|
| Q1-Q5, Q7 question components have no ARIA attributes | Medium |
| DecisionCard, SignalCard have no ARIA roles/labels | Medium |
| Filter dropdowns lack `role="listbox"` and `aria-selected` | Medium |
| Charts (Recharts + custom SVG) have no alt text or ARIA descriptions | High |
| Action button keyboard hints (Enter/O/E) are visual only — no key listeners | Medium |
| Color-only status indicators (urgency/severity without text in compact views) | Medium |
| Toast notifications lack `role="alert"` or `aria-live` | Medium |
| No focus trap in TopBar dropdown menus | Low |
| **Best a11y:** CountdownTimer (`role="timer"`, `aria-live`), MobileNav (WCAG touch targets), ReasoningTraceModal (`role="dialog"`, escape key) | — |

### Responsive Design Gaps

| Issue | Details |
|-------|---------|
| Charts not optimized for mobile | Recharts charts may overflow or be unreadable on small screens |
| Decision detail too long on mobile | Accordion variant exists but isn't used on the actual route page |
| Command palette not optimized for mobile | Full-width overlay works but may be awkward on small screens |
| Filter dropdowns may overflow on mobile | No max-height or scrolling built in |
| No landscape tablet optimization | Single breakpoint split (mobile < 1024px, desktop >= 1024px) |

### Performance Concerns

| Issue | Impact |
|-------|--------|
| `Q7IfNothing` PONRCountdown runs `setInterval` every 1 second | Minor |
| `CountdownTimer` also runs `setInterval` per instance | Multiple timers on dashboard could stack |
| CostEscalationChart scan line runs `setInterval` every 50ms in dark mode | Could be expensive |
| No `React.memo` on any component | All children re-render on parent state change |
| No virtualization for lists | Fine for 3-5 mock items, breaks with hundreds of real decisions |
| All mock data embedded in JS bundles | Increases bundle size unnecessarily |
| No code splitting beyond lazy routes | Large shared component bundles |

### TODO/FIXME Comments

**Only 1 found across the entire codebase:**

- `error-boundary.tsx` line 55: `// TODO: Send to error reporting service (e.g., Sentry)`

### Production Comments (Noteworthy)

- `decisions/[id]/page.tsx`: `"// In production: open modal for user to select alternative"`
- `customers/[id]/page.tsx`: `"// In production: open edit modal or navigate to edit page"`
- `human-review/[id]/page.tsx`: `"// In production: update assignment in backend"`
- `AuditTrailFooter.tsx`: `"// In production, this would come from the backend"` and `"// In production, this would call the backend to verify the hash"`
- `BatchOperations.tsx`: `"// API call would go here"`, `"// Export logic would go here"`, `"// Assignment modal would open here"`

---

## 12. TECH STACK SUMMARY

| Category | Technology | Version | Status |
|----------|------------|---------|--------|
| **Framework** | Vite + React | Vite 7.2.4, React 19.2.0 | Active |
| **Language** | TypeScript | ~5.9.3 | Strict mode |
| **Styling** | Tailwind CSS v4 | 4.1.18 | Active (via `@tailwindcss/vite` plugin) |
| **UI Library** | Custom (no shadcn/Radix/MUI) | — | Hand-built with CVA |
| **Variant System** | class-variance-authority (CVA) | 0.7.1 | Active |
| **Class Merging** | clsx + tailwind-merge | 2.1.1 / 3.4.0 | Active |
| **Animation** | Framer Motion | 12.33.0 | Heavily used (every component) |
| **Icons** | Lucide React | 0.563.0 | ~60+ icons used |
| **Charts** | Recharts | 3.7.0 | Active (bar, line, area, pie, radar, composed) |
| **Routing** | React Router v7 | 7.13.0 | Active (createBrowserRouter, lazy loading) |
| **State (global)** | Zustand | 5.0.11 | Installed, stores defined, **NEVER used** |
| **State (server)** | React Query (TanStack) | 5.90.20 | Configured, hooks defined, **NEVER used** |
| **Forms** | React Hook Form | 7.71.1 | Installed, **NEVER used** |
| **Validation** | Zod | 4.3.6 | Installed, **NEVER used** |
| **Form Resolvers** | @hookform/resolvers | 5.2.2 | Installed, **NEVER used** |
| **HTTP Client** | Native fetch (in api.ts) | — | Defined, **NEVER called** |
| **i18n** | Custom (React Context) | — | EN + VI translations, provider active |
| **Testing** | **None** | — | No test files exist |
| **Build Tool** | Vite | 7.2.4 | Active |
| **Linting** | ESLint (flat config) | 9.39.1 | Active (TS + React Hooks + React Refresh) |
| **Formatting** | **None configured** | — | No Prettier config |
| **Path Aliasing** | `@` → `./src` | — | Via Vite resolve.alias |

---

## END OF AUDIT

**Generated from actual codebase scan — no assumptions made.**
**Every file, route, component, prop, state variable, interaction, and gap documented.**

---

*"OMEN sees the future. RISKCAST tells you what to DO."*
