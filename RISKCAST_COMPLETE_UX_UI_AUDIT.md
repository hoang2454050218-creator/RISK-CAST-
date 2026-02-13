# RISKCAST — Complete UX/UI Audit Report

**Generated:** February 13, 2026  
**Auditor:** AI Senior UX/UI Auditor & Frontend Architect  
**Codebase:** React 19.2.0 + TypeScript 5.9.3 + Vite 7.2.4 + Tailwind CSS 4.1.18  
**Key Dependencies:**
| Dependency | Version | Purpose |
|---|---|---|
| react | 19.2.0 | UI framework |
| react-dom | 19.2.0 | DOM rendering |
| react-router | 7.13.0 | Client-side routing |
| @tanstack/react-query | 5.90.20 | Server state management |
| framer-motion | 12.33.0 | Animations & transitions |
| recharts | 3.7.0 | Chart visualizations |
| zustand | 5.0.11 | Listed but NOT used (Context API used instead) |
| lucide-react | 0.563.0 | Icon library |
| class-variance-authority | 0.7.1 | Component variant management |
| clsx + tailwind-merge | 2.1.1 / 3.4.0 | Conditional class merging |

**Build Tool:** Vite 7.2.4 with `@tailwindcss/vite` plugin (no separate tailwind.config)  
**Testing:** Vitest 4.0.18 + React Testing Library 16.3.2 + jsdom 28.0.0  
**Linting:** ESLint 9.39.1 + Prettier 3.8.1  
**Backend Proxy:** Vite dev server proxies `/api`, `/health`, `/metrics`, `/reconcile` to `http://localhost:8002`

---

## 1. Project Structure Overview

```
frontend/src/
├── app/                              # Route pages (18 routes)
│   ├── analytics/page.tsx            # Analytics dashboard (1,115 lines)
│   ├── audit/page.tsx                # Audit trail viewer (584 lines)
│   ├── auth/
│   │   ├── login/page.tsx            # Login page (318 lines)
│   │   └── register/page.tsx         # Registration page (384 lines)
│   ├── chat/page.tsx                 # Dedicated chat page (105 lines)
│   ├── customers/
│   │   ├── [id]/page.tsx             # Customer detail (734 lines)
│   │   └── page.tsx                  # Customer list (802 lines)
│   ├── dashboard/page.tsx            # Main dashboard (756 lines)
│   ├── decisions/
│   │   ├── [id]/page.tsx             # Decision detail - 7 questions (343 lines)
│   │   └── page.tsx                  # Decisions list (750 lines)
│   ├── home/page.tsx                 # Landing/marketing page (1,114 lines)
│   ├── human-review/
│   │   ├── [id]/page.tsx             # Escalation detail (470 lines)
│   │   └── page.tsx                  # Human review queue (394 lines)
│   ├── not-found/page.tsx            # 404 page (67 lines)
│   ├── onboarding/page.tsx           # Setup wizard (1,008 lines)
│   ├── reality/page.tsx              # Oracle reality view (531 lines)
│   ├── settings/page.tsx             # Settings (7 tabs, 2,145 lines)
│   ├── signals/
│   │   ├── [id]/page.tsx             # Signal detail (372 lines)
│   │   └── page.tsx                  # Signals list (392 lines)
│   └── unauthorized/page.tsx         # Access denied (56 lines)
│
├── components/                       # Reusable components (~70 files)
│   ├── charts/                       # Data visualization (7 files)
│   │   ├── CausalChainDiagram.tsx    # Causal chain flowchart (557 lines)
│   │   ├── ConfidenceGauge.tsx       # Circular confidence gauge (562 lines)
│   │   ├── CostEscalationChart.tsx   # Cost over time chart (520 lines)
│   │   ├── ExposureChart.tsx         # Exposure bar chart (433 lines)
│   │   ├── ScenarioVisualization.tsx  # Scenario comparison (540 lines)
│   │   ├── TimelineVisualization.tsx  # Horizontal timeline (481 lines)
│   │   └── index.ts                  # Barrel export
│   ├── domain/                       # Domain-specific components
│   │   ├── chat/                     # AI chat (5 files)
│   │   │   ├── ChatInput.tsx         # Message input (80 lines)
│   │   │   ├── ChatMessage.tsx       # Message bubble (64 lines)
│   │   │   ├── ChatPanel.tsx         # Full chat interface (194 lines)
│   │   │   ├── ChatWidget.tsx        # Floating chat bubble (102 lines)
│   │   │   └── SuggestionCard.tsx    # Action suggestion (116 lines)
│   │   ├── common/                   # Shared domain components (11 files)
│   │   │   ├── ActionBadge.tsx       # Action type badge (120 lines)
│   │   │   ├── ConfidenceIndicator.tsx # Confidence display (184 lines)
│   │   │   ├── CostDisplay.tsx       # Cost with CI (242 lines)
│   │   │   ├── CountdownTimer.tsx    # Deadline countdown (272 lines)
│   │   │   ├── MorningBriefCard.tsx  # Daily brief card (103 lines)
│   │   │   ├── QuickActions.tsx      # Pipeline workflow (119 lines)
│   │   │   ├── SeverityBadge.tsx     # Severity indicator (103 lines)
│   │   │   ├── SignalFeedV2.tsx      # Real-time signal feed (134 lines)
│   │   │   ├── StatCard.tsx          # Stat/metric card (344 lines)
│   │   │   ├── UrgencyBadge.tsx      # Urgency indicator (104 lines)
│   │   │   └── index.ts             # Barrel export
│   │   ├── customers/               # Customer components (3 files)
│   │   │   ├── CustomerCard.tsx      # Customer card (99 lines)
│   │   │   ├── index.ts             # Barrel export
│   │   │   └── types.ts             # Customer types (42 lines)
│   │   ├── decisions/               # Decision components (13 files)
│   │   │   ├── AuditTrailFooter.tsx  # Audit metadata (365 lines)
│   │   │   ├── DecisionCard.tsx      # Decision list card (483 lines)
│   │   │   ├── Q1WhatIsHappening.tsx # Question 1 (243 lines)
│   │   │   ├── Q2When.tsx           # Question 2 (220 lines)
│   │   │   ├── Q3HowBad.tsx         # Question 3 (308 lines)
│   │   │   ├── Q4Why.tsx            # Question 4 (274 lines)
│   │   │   ├── Q5WhatToDo.tsx       # Question 5 (674 lines)
│   │   │   ├── Q6Confidence.tsx     # Question 6 (590 lines)
│   │   │   ├── Q7IfNothing.tsx      # Question 7 (452 lines)
│   │   │   ├── VerdictBanner.tsx    # Executive summary (215 lines)
│   │   │   ├── SevenQuestionsView.tsx # Accordion container
│   │   │   ├── DecisionHeader.tsx   # Decision header
│   │   │   ├── ActionButtons.tsx    # Action button bar
│   │   │   └── index.ts            # Barrel export
│   │   ├── escalations/            # Escalation components (3 files)
│   │   │   ├── EscalationCard.tsx   # Escalation card (211 lines)
│   │   │   ├── index.ts            # Barrel export
│   │   │   └── types.ts            # Escalation types (85 lines)
│   │   ├── layout/                  # Layout components (4 files)
│   │   │   ├── AppLayout.tsx        # Main app shell (145 lines)
│   │   │   ├── MobileNav.tsx        # Bottom nav bar (251 lines)
│   │   │   ├── Sidebar.tsx          # Left sidebar (557 lines)
│   │   │   └── TopBar.tsx           # Top navigation bar (796 lines)
│   │   └── signals/                 # Signal components (2 files)
│   │       ├── EvidenceList.tsx      # Evidence display (155 lines)
│   │       └── SignalCard.tsx        # Signal card (363 lines)
│   └── ui/                          # Primitive UI components (18+ files)
│       ├── active-filter-chip.tsx    # Filter chip (36 lines)
│       ├── animated-number.tsx       # Animated numbers (404 lines)
│       ├── badge.tsx                # Badge variants (245 lines)
│       ├── breadcrumbs.tsx          # Navigation breadcrumbs (70 lines)
│       ├── button.tsx               # Button component (222 lines)
│       ├── card.tsx                 # Card component (260 lines)
│       ├── command-palette.tsx       # Cmd+K palette (670 lines)
│       ├── confirmation-dialog.tsx   # Modal dialog (223 lines)
│       ├── error-boundary.tsx       # Error boundary (163 lines)
│       ├── error-state.tsx          # Error display (81 lines)
│       ├── filter-dropdown.tsx      # Filter dropdown (193 lines)
│       ├── FreshnessIndicator.tsx   # Data freshness (64 lines)
│       ├── index.ts                 # Barrel export (95 lines)
│       ├── keyboard-shortcuts-panel.tsx # Shortcuts panel (191 lines)
│       ├── not-found-state.tsx      # 404 inline state (61 lines)
│       ├── pagination.tsx           # Pagination (221 lines)
│       ├── skeleton.tsx             # Skeleton loaders (449 lines)
│       ├── states.tsx               # Loading/Empty/Error states (130 lines)
│       ├── swipeable-card.tsx       # Swipe card (237 lines)
│       ├── theme-provider.tsx       # Theme context (125 lines)
│       └── toast.tsx                # Toast notifications (402 lines)
│
├── contexts/                        # React contexts (2 files)
│   ├── plan-context.tsx             # Plan/subscription context (296 lines)
│   └── user-context.tsx             # User profile context (112 lines)
│
├── hooks/                           # Custom hooks (26 files incl. tests)
│   ├── useAnalytics.ts             # Analytics data
│   ├── useAuditTrail.ts            # Audit events
│   ├── useAsyncAction.ts           # Async action state
│   ├── useBrief.ts                 # Morning brief
│   ├── useChat.ts                  # SSE streaming chat (118 lines)
│   ├── useCustomers.ts             # Customer CRUD (299 lines)
│   ├── useDashboard.ts             # Dashboard data (239 lines)
│   ├── useDecisions.ts             # Decision management (301 lines)
│   ├── useEscalationDetail.ts      # Single escalation
│   ├── useEscalations.ts           # Escalation management (154 lines)
│   ├── useFeedback.ts              # Feedback submission
│   ├── useKeyboardShortcuts.ts     # Keyboard shortcuts
│   ├── usePagination.ts            # URL-synced pagination
│   ├── useRealityEngine.ts         # Reality engine (128 lines)
│   ├── useSignals.ts               # Signal management
│   ├── useSignalsV2.ts             # V2 signals API
│   ├── useSSE.ts                   # Server-Sent Events
│   ├── useSwipeGesture.ts          # Touch swipe
│   ├── useV2Auth.ts                # V2 authentication
│   └── index.ts                    # Barrel export (41 lines)
│
├── lib/                             # Libraries & utilities (24 files)
│   ├── animations.ts               # Framer Motion system (703 lines)
│   ├── api-v2.ts                   # V2 API client (509 lines)
│   ├── api.ts                      # Legacy API + mock fallback (435 lines)
│   ├── auth.tsx                    # Auth provider (258 lines)
│   ├── chart-theme.ts             # Chart theming (586 lines)
│   ├── formatters.ts              # Locale formatters (308 lines)
│   ├── i18n/                       # Internationalization
│   │   ├── index.ts                # Translations (342 lines)
│   │   ├── provider.tsx            # I18n context (67 lines)
│   │   └── useFormatters.ts        # Locale formatters hook
│   ├── mock-data/                  # Mock data system
│   │   ├── constants.ts            # Industry constants
│   │   ├── entities.ts             # Base entities (130 lines)
│   │   ├── generators/             # Data generators
│   │   │   ├── analytics.ts        # Analytics mock
│   │   │   ├── audit.ts            # Audit mock
│   │   │   ├── customers.ts        # Customer mock
│   │   │   ├── dashboard.ts        # Dashboard mock
│   │   │   ├── escalations.ts      # Escalation mock
│   │   │   └── reality.ts          # Reality mock
│   │   ├── index.ts                # Barrel export
│   │   ├── legacy.ts               # Legacy mock data
│   │   └── seed.ts                 # Seeded PRNG
│   ├── permissions.tsx             # RBAC system (179 lines)
│   └── utils.ts                    # Utility functions (50 lines)
│
├── test/
│   └── setup.ts                    # Vitest setup
│
├── types/                          # TypeScript types
│   ├── decision.ts                 # Decision types (278 lines)
│   └── signal.ts                   # Signal types (80 lines)
│
├── index.css                       # Design system (1,217 lines)
├── main.tsx                        # App entry point (43 lines)
├── router.tsx                      # Route definitions (179 lines)
└── vite-env.d.ts                   # Vite type declarations
```

**Total frontend source files: ~166 files**  
**Total lines of code (estimated): ~25,000+ lines**

---

## 2. Page-by-Page Audit

### 2.1 Landing Page — `/`

**File:** `frontend/src/app/home/page.tsx` (1,114 lines)  
**Route:** `/` (public, no auth required)  
**Purpose:** Marketing landing page to convert visitors and impress investors.

**Layout:**
- Full-page vertical scroll layout
- No sidebar or app shell — standalone page
- Sections stacked vertically: Navbar → Hero → Stats → Features → How It Works → Comparison → Pricing → CTA → Footer
- Parallax scroll effects via `useScroll` + `useTransform`

**Components Used:**
- Internal: `Navbar`, `HeroSection`, `StatsSection`, `FeaturesSection`, `HowItWorksSection`, `ComparisonSection`, `PricingSection`, `CTASection`, `Footer` (all defined in-file)
- External: `Link`, `useNavigate` (react-router), `motion`, `useScroll`, `useTransform`, `useInView`, `AnimatePresence` (framer-motion), `useAuth` (auth context)
- Icons: Shield, Zap, Globe, ArrowRight, ChevronRight, BarChart3, Clock, DollarSign, Eye, Brain, Target, TrendingUp, Users, CheckCircle, Star, ArrowUpRight, Menu, X, Ship, AlertTriangle, Activity, Lock

**Data Source:** Static/hardcoded content. No API calls.

**Interactions:**
- Responsive navbar with mobile hamburger menu
- Scroll-triggered section animations (fade-in-up, stagger)
- "Get Started" / "Schedule Demo" CTA buttons → navigates to `/auth/register`
- "Sign In" button in navbar → navigates to `/auth/login`
- Pricing toggle (Monthly/Annual) — UI only, no backend
- Feature cards with hover effects

**Visual Style:**
- Clean SaaS aesthetic inspired by Linear, Vercel, Stripe
- Background: `bg-background` (light: #f8fafc, dark: #0b0f1a)
- Hero has gradient text, large headline, animated counters
- Stats section: 4 animated stat counters
- Feature cards with hover lift effect
- Pricing cards: 3 tiers (Starter, Professional, Enterprise) with recommended highlight
- Comparison table (RISKCAST vs Competitors)
- CTA section with accent gradient background

**States:**
- Empty: N/A (static page)
- Loading: Suspense fallback shows spinner
- Filled: Full marketing page renders
- Error: N/A (no data fetching)

**Issues:**
- Pricing section is purely decorative — no actual Stripe integration
- All feature claims are static text — no live data proof
- Mobile hamburger menu implemented but needs testing for all viewport sizes
- No SEO metadata beyond `<title>` tag

---

### 2.2 Login Page — `/auth/login`

**File:** `frontend/src/app/auth/login/page.tsx` (318 lines)  
**Route:** `/auth/login` (public)  
**Purpose:** User authentication with email/password.

**Layout:**
- Centered single-card layout over full-screen dark background
- Background grid pattern (40px grid, 3% opacity) + radial accent glow
- Card: `max-w-md`, rounded-2xl, border, backdrop-blur

**Components Used:**
- `Button` (UI), `Link` (react-router), `motion`/`AnimatePresence` (framer-motion)
- Icons: Shield, Eye, EyeOff, AlertTriangle, Info, ArrowLeft, Mail, Lock
- `useAuth` from auth context

**Data Source:** Auth context (`login()` function → V2 API `/api/v2/auth/login`)

**Interactions:**
- Email + Password form inputs
- Show/hide password toggle
- Submit → authenticate → redirect to `/dashboard`
- Demo credential fill buttons (3 role-based demo accounts: Analyst, Manager, Executive)
- **SECURITY CONCERN:** Hardcoded test account visible: `hoangpro268@gmail.com` / `Hoang2672004`
- Login attempt lockout after 5 failed attempts (30-second cooldown, client-side only)
- "Create account" link → `/auth/register`
- "Back to home" link → `/`

**Visual Style:**
- Always dark aesthetic regardless of theme setting
- Grid pattern + accent glow background
- Animated shield logo with breathing scale
- Mono font labels, uppercase tracking
- Input fields: bg-muted/40, rounded-lg, h-11, pl-10 (icon space)
- Error messages: red border, AlertTriangle icon, mono font

**States:**
- Empty: Form with placeholder text visible
- Loading: Button shows "Authenticating..." with spinner
- Filled: Form fields populated
- Error: Red error banner with message (inline below password)
- Lockout: Timer message shown, submit button disabled

**Issues:**
- **CRITICAL:** Real credentials hardcoded in UI (`hoangpro268@gmail.com` / `Hoang2672004`)
- Lockout is client-side only — easily bypassed by refreshing
- Register page forces dark mode via `data-theme="dark"` but login page uses `bg-background` (inconsistent)
- No "Forgot Password" feature
- No OAuth/SSO options

---

### 2.3 Register Page — `/auth/register`

**File:** `frontend/src/app/auth/register/page.tsx` (384 lines)  
**Route:** `/auth/register` (public)  
**Purpose:** New user account creation.

**Layout:** Same centered card layout as login page.

**Components Used:** Same as login + `User`, `CheckCircle` icons.

**Data Source:** Auth context (`register()` function → V2 API `/api/v2/auth/register`)

**Interactions:**
- Full Name, Email, Password, Confirm Password fields
- Password strength meter (5 levels: Too short, Weak, Fair, Strong, Excellent)
- Password match validation (green checkmark when matching)
- Terms of Service checkbox (required)
- Submit → register → redirect to `/onboarding`
- "Sign in" link → `/auth/login`
- Test account info displayed (same hardcoded credentials)

**Visual Style:** Mirrors login page exactly — dark theme, grid background, accent glow, mono labels.

**States:** Same patterns as login (empty, loading, error, filled).

**Issues:**
- **CRITICAL:** Same hardcoded credentials visible
- Terms of Service and Privacy Policy links are `href="#"` — dead links
- Password strength algorithm is basic (length + character class counting)
- No email verification flow
- Registration page hardcodes `dark` class and `data-theme="dark"` — won't respect user's theme choice

---

### 2.4 Dashboard — `/dashboard`

**File:** `frontend/src/app/dashboard/page.tsx` (756 lines)  
**Route:** `/dashboard` (protected)  
**Purpose:** Mission control command center — overview of all risk activity.

**Layout:**
- Wrapped in `AppLayout` (sidebar + topbar + mobile nav)
- Grid layout: Stats row → Urgent Decisions + Chokepoint Health (2-col) → Recent Activity
- Responsive: stacks to single column on mobile

**Components Used:**
- `StatCard`, `UrgencyBadge`, `SeverityBadge`, `CompactCountdown` (domain/common)
- `Button`, `Badge`, `SkeletonDashboard`, `ErrorState` (UI)
- `PipelineStepper` (defined in-file) — 3-step flow visualization
- Icons: AlertTriangle, Bell, DollarSign, ChevronRight, CheckCircle, Clock, MapPin, Zap, ShieldCheck, Radio, Brain, Globe, Activity, ArrowRight, Shield, TrendingDown, Ship

**Data Source:**
- `useDashboardData()` → React Query → V2 API `/api/v2/dashboard/summary` → mock fallback
- `useDecisionsList()` → decisions data
- `useSignalsList()` → signals data
- `useEscalationsList()` → escalation data

**Interactions:**
- Stat cards are clickable → navigate to respective list pages
- Urgent decision items link to `/decisions/:id`
- Chokepoint health items show status (Operational, Disrupted, Congested)
- Recent activity timeline shows latest events
- Pipeline stepper: Signals → Engine → Decisions (visual only, not interactive)

**Visual Style:**
- Stats grid: 4 StatCards with icons, animated numbers, change indicators
- Urgent decisions: Cards with urgency color-coded left border (3px)
- Chokepoint health: Status dots (green/yellow/red) with vessel counts
- Activity timeline: Vertical line with event icons and timestamps
- All cards use `bg-card`, `border-border`, `rounded-xl`, `shadow-card`

**States:**
- Loading: `SkeletonDashboard` (grid of skeleton rectangles)
- Error: `ErrorState` component with retry button
- Filled: Full dashboard with live data
- Empty: Individual sections show empty states

**Issues:**
- Dashboard relies heavily on mock data when backend is unavailable
- `PipelineStepper` is purely decorative — does not reflect real pipeline status
- No real-time updates (polling-based via React Query staleTime: 30s)
- Chokepoint health data comes from mock generators — unclear from code if real API exists

---

### 2.5 Decisions List — `/decisions`

**File:** `frontend/src/app/decisions/page.tsx` (750 lines)  
**Route:** `/decisions` (protected)  
**Purpose:** Browse, filter, search, and act on AI-generated risk decisions.

**Layout:**
- Header with title, search bar, filter dropdowns, sort toggle
- Urgency summary strip (4 urgency level counts)
- Decision cards in responsive grid (auto-fill columns)
- Bottom pagination
- Floating action bar (appears when items selected)

**Components Used:**
- `DecisionCard` (domain/decisions)
- `Button`, `FilterDropdown`, `ActiveFilterChip`, `ConfirmationDialog`, `SkeletonDecisionsList`, `Pagination` (UI)
- Keyboard shortcuts handler

**Data Source:**
- `useDecisionsList()` → React Query → V2 API `/api/v2/decisions` → mock fallback
- `useAcknowledgeDecision()` → mutation
- `usePagination()` → URL-synced page state

**Interactions:**
- Search input (filters by ID, event summary, route, cargo type)
- Filter dropdowns: Urgency (IMMEDIATE/URGENT/SOON/WATCH), Status (PENDING/ACKNOWLEDGED/OVERRIDDEN/ESCALATED), Action Type
- Sort: Newest First / Oldest First toggle
- Saved Views: predefined filter presets (All Decisions, Urgent, Pending, Critical Exposure)
- Keyboard shortcuts: `/` to focus search, `j`/`k` to navigate, `Enter` to open, `Escape` to clear
- Click decision card → navigate to `/decisions/:id`
- Swipe actions on mobile (acknowledge, escalate)
- Floating action bar for bulk acknowledge
- Clear all filters button

**Visual Style:**
- Urgency summary strip: 4 colored counters (red/orange/yellow/gray)
- Decision cards: bordered, urgency-color left border, compact data display
- Active filter chips with `x` remove button
- Pagination: first/prev/page numbers/next/last with page size selector

**States:**
- Loading: `SkeletonDecisionsList` (grid of skeleton cards)
- Error: Error state component
- Empty: "No decisions found" with illustration
- Filled: Grid of DecisionCards

**Issues:**
- Keyboard shortcuts are custom implementation — may conflict with browser shortcuts
- Saved views are hardcoded, not user-customizable
- No bulk operations beyond acknowledge
- Search is client-side filtering — could be slow with large datasets

---

### 2.6 Decision Detail — `/decisions/:id`

**File:** `frontend/src/app/decisions/[id]/page.tsx` (343 lines)  
**Route:** `/decisions/:id` (protected)  
**Purpose:** Deep-dive into a single decision using the 7-Questions framework.

**Layout:**
- Breadcrumbs: Decisions > [Decision ID]
- VerdictBanner: Executive summary banner at top
- SevenQuestionsView: Accordion of 7 question cards
- Action buttons at bottom

**Components Used:**
- `VerdictBanner`, `SevenQuestionsView` (domain/decisions)
- `ConfirmationDialog`, `NotFoundState`, `ErrorState`, `SkeletonDecisionView`, `Breadcrumbs` (UI)
- `useDecision`, `useAcknowledgeDecision`, `useOverrideDecision`, `useEscalateDecision` (hooks)
- `useToast`, `useUser` (contexts)

**Data Source:**
- `useDecision(id)` → React Query → V2 API → mock fallback
- Mutations: acknowledge, override, escalate

**Interactions:**
- **Acknowledge** → confirmation dialog → "Decision acknowledged — action committed" → navigate to `/decisions`
- **Override** → confirmation dialog with action selector + reason textarea → "Override recorded — alternative action logged"
- **Escalate** → confirmation dialog with reason + priority selector → "Escalation created — routed to human review queue" → navigate to `/human-review`
- **Request More Info** → dialog with textarea for requesting additional analysis
- "Back to decisions" button
- Scroll to action buttons from VerdictBanner CTA

**The 7 Questions (displayed as accordion cards):**
1. **Q1: What is happening?** — Event summary, personalized impact, affected shipments, chokepoints
2. **Q2: When?** — Deadline countdown, timeline visualization, time to impact, escalation triggers
3. **Q3: How bad is it?** — Severity, total exposure with CI, scenario analysis, exposure chart
4. **Q4: Why?** — Root cause, causal chain diagram, evidence sources with confidence
5. **Q5: What to do?** — Recommended action + cost, alternatives comparison table, implementation steps
6. **Q6: How confident?** — Confidence gauge, contributing factors, calibration context, uncertainties
7. **Q7: What if nothing?** — Cost of inaction, point of no return countdown, cost escalation chart

**Visual Style:**
- VerdictBanner: colored based on severity, shows exposure, shipments, route, deadline
- Each Q card has themed left border and glow effects
- Charts use terminal/HUD aesthetic
- Action buttons: color-coded (green=acknowledge, amber=override, red=escalate)

**States:**
- Loading: `SkeletonDecisionView`
- Error: `ErrorState` with retry
- Not Found: `NotFoundState` with "decision" entity
- Filled: Full 7-questions view

**Issues:**
- All 7 question components are heavy (200-700 lines each) — could impact render performance
- Override action types are hardcoded dropdown options
- Request More Info is fire-and-forget — no actual API endpoint confirmed
- Escalation priority defaults to "high" — needs verification against backend schema

---

### 2.7 Signals List — `/signals`

**File:** `frontend/src/app/signals/page.tsx` (392 lines)  
**Route:** `/signals` (protected)  
**Purpose:** Browse and manage risk signals from OMEN intelligence system.

**Layout:**
- Header with title + signal count badge, search input
- Filter row: Status, Severity, Source dropdowns
- Active filter chips
- Signal cards in grid (auto-fill columns)

**Components Used:**
- `SignalCard` (domain/signals)
- `Button`, `Badge`, `FilterDropdown`, `ActiveFilterChip`, `SkeletonSignalsList` (UI)
- Icons: AlertTriangle, Search, Filter, X, Radio, Zap, ChevronRight, Info

**Data Source:**
- `useSignalsList()` → React Query → V2 API `/api/v2/signals` → mock fallback

**Interactions:**
- Search by title/ID/location
- Filter by status (Active, Confirmed, Expired, Dismissed)
- Filter by severity
- Filter by source
- Click signal → navigate to `/signals/:id`
- Clear all filters

**Visual Style:**
- Signal cards: glassmorphism style, severity-colored indicator
- Grid layout with responsive columns
- Active filters shown as removable chips

**States:**
- Loading: `SkeletonSignalsList`
- Error: Error state
- Empty: "No signals found" message
- Filled: Grid of SignalCards

**Issues:**
- No grid/list view toggle (mentioned in git status as potentially planned)
- No signal dismissal from list view
- No "Generate Decision" action from signal list
- Less interactive than decisions page (no keyboard shortcuts)

---

### 2.8 Signal Detail — `/signals/:id`

**File:** `frontend/src/app/signals/[id]/page.tsx` (372 lines)  
**Route:** `/signals/:id` (protected)  
**Purpose:** Detailed view of a single risk signal with evidence and related decisions.

**Layout:**
- Breadcrumbs
- Signal header (event type, status, severity, timestamp)
- Signal body (description, probability, impact)
- Evidence list
- Related decisions section
- Action buttons (Dismiss, Generate Decision)

**Components Used:**
- `EvidenceList` (domain/signals)
- `Breadcrumbs`, `Badge`, `Button`, `NotFoundState`, `ErrorState`, `SkeletonCard` (UI)
- `SeverityBadge` (domain/common)

**Data Source:**
- `useSignal(id)` → React Query → V2 API → mock fallback

**Interactions:**
- Dismiss signal (with confirmation)
- Generate decision from signal
- View related decisions (links to `/decisions/:id`)
- Evidence source links (external URLs)

**Visual Style:**
- Clean detail layout with section cards
- Evidence items show source type icon, confidence bar, timestamp
- Related decisions shown as compact cards

**States:** Loading → Error → Not Found → Filled

**Issues:**
- "Generate Decision" likely calls backend but result handling unclear
- Dismiss action confirmation UX needs verification
- Evidence source links may point to external APIs (Polymarket, NewsAPI)

---

### 2.9 Customers List — `/customers`

**File:** `frontend/src/app/customers/page.tsx` (802 lines)  
**Route:** `/customers` (protected)  
**Purpose:** CRM-like customer management with shipment tracking.

**Layout:**
- Header with title, search, "Add Customer" button
- Filter row: Status, Industry dropdowns
- Customer cards in grid
- Multi-step "Add Customer" modal

**Components Used:**
- `CustomerCard` (domain/customers)
- `Button`, `Badge`, `Card`, `FilterDropdown` (UI)
- Multi-step modal (defined in-file)

**Data Source:**
- `useCustomersList()` → React Query → V2 API `/api/v2/customers` → mock fallback
- `useCreateCustomer()` → mutation

**Interactions:**
- Search by company name
- Filter by status, industry
- Click customer → navigate to `/customers/:id`
- "Add Customer" → multi-step modal:
  - Step 1: Company info (name, industry, tier)
  - Step 2: Contact details (name, email, phone with country code)
  - Step 3: Trade routes (origin/destination port selection)
  - Step 4: Risk preferences (tolerance level, notification settings)
- Cancel/Back/Next/Submit navigation in modal

**Visual Style:**
- Customer cards show company name, industry, tier badge, exposure, shipment count
- Add modal has step indicators (1-4) with progress bar
- Port selection uses searchable dropdown

**States:** Loading → Error → Empty ("No customers yet") → Filled

**Issues:**
- Customer data heavily relies on mock data
- Add customer modal is 4 steps — may be overkill for MVP
- No CSV import option from customer list (only in onboarding)
- No customer deletion from list view

---

### 2.10 Customer Detail — `/customers/:id`

**File:** `frontend/src/app/customers/[id]/page.tsx` (734 lines)  
**Route:** `/customers/:id` (protected)  
**Purpose:** Full customer profile with shipments, exposure, and AI analysis.

**Layout:**
- Breadcrumbs
- Customer header (name, industry, status, contacts)
- Edit mode toggle
- Tabs: Overview, Shipments, Risk Analysis
- AI company analysis section

**Components Used:**
- `Card`, `Button`, `Badge`, `Breadcrumbs`, `NotFoundState`, `ErrorState` (UI)
- `SeverityBadge` (domain/common)

**Data Source:**
- `useCustomer(id)` → React Query → V2 API `/api/v2/customers/:id` → mock fallback
- `useUpdateCustomer()` → mutation
- `useAnalyzeCompany()` → AI analysis mutation
- `useCreateShipment()` → mutation

**Interactions:**
- Edit mode: inline editing of customer fields
- Save/Cancel edit
- Add shipment modal
- Trigger AI company analysis
- View shipment details
- Navigate back to customers list

**Visual Style:**
- Profile header with avatar/initials, badges
- Tabbed content area
- Shipment table with status badges
- AI analysis rendered as markdown-like text

**States:** Loading → Error → Not Found → View Mode → Edit Mode

**Issues:**
- Edit mode is basic inline inputs — no field validation beyond required
- AI analysis feature calls LLM — may be slow or unavailable
- Shipment creation form is minimal
- No customer deletion UI

---

### 2.11 Human Review Queue — `/human-review`

**File:** `frontend/src/app/human-review/page.tsx` (394 lines)  
**Route:** `/human-review` (protected)  
**Purpose:** Queue of escalated decisions requiring human review/approval.

**Layout:**
- Header with title, pending count, filter options
- Escalation cards in list
- Priority-based sorting

**Components Used:**
- `EscalationCard` (domain/escalations)
- `Button`, `Badge`, `FilterDropdown`, `SkeletonHumanReview` (UI)

**Data Source:**
- `useEscalationsList()` → React Query → V2 API → mock fallback

**Interactions:**
- Filter by priority (Critical, High, Medium, Low)
- Filter by status (Pending, Approved, Rejected)
- Click escalation → navigate to `/human-review/:id`
- SLA countdown visible on each card

**Visual Style:**
- Escalation cards with priority-colored left border
- SLA countdown timers (red when approaching deadline)
- Terminal-style decorations for critical items in dark mode

**States:** Loading → Error → Empty → Filled

**Issues:**
- No bulk approval/rejection
- SLA countdown is visual only — no actual notification when SLA breaches
- Limited filtering compared to decisions page

---

### 2.12 Escalation Detail — `/human-review/:id`

**File:** `frontend/src/app/human-review/[id]/page.tsx` (470 lines)  
**Route:** `/human-review/:id` (protected)  
**Purpose:** Review and act on a single escalated decision.

**Layout:**
- Breadcrumbs
- Escalation header (priority, status, SLA)
- Original decision context
- Escalation reason
- Action panel (Approve/Reject with reason)
- Comment thread

**Components Used:**
- `Card`, `Button`, `Badge`, `Breadcrumbs`, `ConfirmationDialog`, `NotFoundState`, `ErrorState` (UI)

**Data Source:**
- `useEscalation(id)` → React Query → mock fallback
- `useApproveEscalation()`, `useRejectEscalation()`, `useCommentEscalation()` → mutations

**Interactions:**
- **Approve** → confirmation dialog with reason → "Escalation approved"
- **Reject** → confirmation dialog with reason → "Escalation rejected"
- Add comment to escalation thread
- Assign to team member (dropdown)
- Navigate to original decision

**Visual Style:**
- Priority-themed header
- Decision context shown as embedded card
- Comment thread with timestamps and user avatars
- Action buttons: green (approve), red (reject)

**States:** Loading → Error → Not Found → Filled

**Issues:**
- Team member assignment is dropdown but unclear if team list is real
- Comment thread may be mock data only
- No @mention or notification system for comments

---

### 2.13 Analytics — `/analytics`

**File:** `frontend/src/app/analytics/page.tsx` (1,115 lines)  
**Route:** `/analytics` (protected)  
**Purpose:** Performance analytics dashboard with charts and calibration data.

**Layout:**
- KPI stat cards row (4 metrics)
- Tabbed sections: Overview, Accuracy, Routes, Calibration
- Charts in grid layouts within each tab
- Date range filter

**Components Used:**
- `StatCard` (domain/common)
- `Card`, `Badge`, `Button` (UI)
- Recharts components (LineChart, BarChart, PieChart, etc.)
- Custom chart wrappers

**Data Source:**
- `useAnalytics()` → React Query → V2 API → mock fallback
- Transforms backend data into chart-friendly format

**Interactions:**
- Tab navigation (Overview, Accuracy, Routes, Calibration)
- Date range picker
- Chart tooltips on hover
- Export to CSV (unclear if functional)

**Visual Style:**
- Dashboard grid layout
- Recharts with custom theme colors
- Stat cards with animated numbers
- Clean card-based sections

**States:** Loading (skeleton) → Error → Filled

**Issues:**
- 1,115 lines in a single page file — should be decomposed
- Analytics data likely mock when backend unavailable
- Calibration tab content unclear — needs manual verification
- No drill-down from charts to underlying data

---

### 2.14 Audit Trail — `/audit`

**File:** `frontend/src/app/audit/page.tsx` (584 lines)  
**Route:** `/audit` (protected)  
**Purpose:** Immutable audit log of all system actions for compliance.

**Layout:**
- Header with title, export button
- Filter bar: Event type, Date range, Actor
- Audit event list (chronological)

**Components Used:**
- `Card`, `Button`, `Badge`, `FilterDropdown` (UI)
- `FreshnessIndicator` (UI)

**Data Source:**
- `useAuditTrail()` → React Query → V2 API `/api/v2/audit` → mock fallback

**Interactions:**
- Filter by event type
- Filter by date range
- Filter by actor
- Export to CSV/PDF (buttons present)
- Click event → expand details

**Visual Style:**
- Timeline-style list
- Event type badges (color-coded)
- Expandable event detail panels
- Mono font for IDs and hashes

**States:** Loading → Error → Empty → Filled

**Issues:**
- Export functionality needs verification (may be UI-only)
- Audit integrity verification UI present but relies on client-side hash computation
- Large audit trails may have performance issues (no virtual scrolling)

---

### 2.15 Oracle Reality — `/reality`

**File:** `frontend/src/app/reality/page.tsx` (531 lines)  
**Route:** `/reality` (protected)  
**Purpose:** Real-world maritime intelligence — chokepoint health, freight rates, vessel tracking.

**Layout:**
- Header with "Oracle Reality Engine" title
- Tabs: Chokepoint Health, Freight Rates, Vessel Alerts
- Data cards/tables within each tab

**Components Used:**
- `Card`, `Badge`, `Button` (UI)
- `StatCard` (domain/common)
- Icons: Globe, Ship, Anchor, Activity, TrendingUp, AlertTriangle

**Data Source:**
- `useRealityEngine()` → React Query → signals + analytics APIs → mock fallback

**Interactions:**
- Tab switching (Chokepoints, Freight, Vessels)
- Chokepoint status indicators (clickable for details)
- Freight rate sparklines
- Vessel alert cards

**Visual Style:**
- Maritime theme — globe/ship iconography
- Status indicators: green (operational), yellow (congested), red (disrupted)
- Compact data tables
- Sparkline charts for trends

**States:** Loading → Error → Filled

**Issues:**
- Data is largely derived from signal analysis — not a real AIS integration
- No interactive map (despite "reality engine" branding)
- Vessel tracking is simulated from mock data
- Freight rate sources unclear

---

### 2.16 Settings — `/settings`

**File:** `frontend/src/app/settings/page.tsx` (2,145 lines)  
**Route:** `/settings` (protected)  
**Purpose:** User and system configuration across 7 tabs.

**Layout:**
- Tab sidebar (left) + Tab content (right)
- Responsive: tabs become horizontal scroll on mobile
- Each tab is a form with save functionality

**Components Used:**
- `Card`, `CardHeader`, `CardTitle`, `CardContent`, `CardDescription` (UI)
- `Button`, `Badge` (UI)
- `useTheme`, `useToast`, `useUser` (contexts)
- Custom `CustomSelect` dropdown (defined in-file)
- Custom `InlinePhoneInput` (defined in-file)

**Tabs:**

1. **Profile** — Name, email, phone, department, role (read-only)
2. **Company** — Company name, industry, trade routes, chokepoints
3. **Notifications** — Email/SMS/Push toggles, alert thresholds
4. **Thresholds** — Risk tolerance settings, exposure limits
5. **Team** — Team member list, invite form
6. **Appearance** — Theme toggle (Light/Dark/System), density settings, language (EN/VI)
7. **Keyboard Shortcuts** — Shortcut reference table (read-only)

**Data Source:**
- `useUser()` → user context
- `localStorage` for settings persistence
- `useCreateCustomer()` for company profile save
- Theme from `useTheme()`

**Interactions:**
- Tab navigation
- Form inputs with save buttons
- Theme toggle (Light/Dark/System with preview)
- Language selector (English/Vietnamese)
- Invite team member form
- Route/chokepoint selector dropdowns

**Visual Style:**
- Clean form layout with labeled inputs
- Theme preview cards showing light/dark
- Toggle switches for boolean settings
- Grouped settings with section headers

**States:** Each tab loads independently. Save shows toast notification.

**Issues:**
- **2,145 lines in a single file** — massive, should be split into separate tab components
- Most settings save to localStorage only — not synced to backend
- Team management is UI-only — no actual invitation system
- Keyboard shortcuts tab is read-only reference
- Company settings duplicate onboarding wizard fields

---

### 2.17 Onboarding Wizard — `/onboarding`

**File:** `frontend/src/app/onboarding/page.tsx` (1,008 lines)  
**Route:** `/onboarding` (protected — accessed after registration)  
**Purpose:** Multi-step setup wizard for new companies.

**Layout:**
- Full-page wizard with step indicator at top
- Content area for each step
- Navigation buttons (Back/Next/Skip/Complete)
- Progress bar

**Steps:**
1. **Welcome** — Introduction and overview
2. **Company Profile** — Name, industry, phone (with international prefix)
3. **Trade Routes** — Origin/destination port selection, chokepoint auto-detection
4. **Risk Preferences** — Tolerance level, notification settings
5. **Data Import** — CSV upload or manual setup
6. **Signal Scan** — First AI analysis trigger
7. **Complete** — Success message, navigate to dashboard

**Components Used:**
- `Button`, `Card`, `CardContent`, `Badge` (UI)
- Custom `OnboardingPhoneInput` (defined in-file)
- `v2Customers`, `v2Signals`, `v2Intelligence` (API)

**Data Source:**
- `v2Customers.create()` — creates customer profile
- `v2Signals.list()` — fetches initial signals
- `v2Intelligence.analyze()` — triggers AI analysis

**Interactions:**
- Step-by-step wizard navigation
- Port search/selection with dropdown
- CSV file upload (drag-and-drop zone)
- Phone number input with country code selector
- AI analysis trigger with loading state

**Visual Style:**
- Step indicator: numbered circles with connecting line
- Clean card-based step content
- Port selector: searchable list grouped by region
- File upload zone: dashed border, icon, drop area

**States:** Each step manages its own validation state.

**Issues:**
- CSV import parsing implementation unclear
- AI analysis in step 6 may timeout or fail silently
- No ability to go back to onboarding after initial completion
- 1,008 lines in a single file

---

### 2.18 Chat — `/chat`

**File:** `frontend/src/app/chat/page.tsx` (105 lines)  
**Route:** No dedicated route in router — was commented out. Chat is primarily via `ChatWidget` on every page.  
**Purpose:** Dedicated full-page chat interface (secondary to floating widget).

**Layout:**
- Horizontal split: Session sidebar (280px, collapsible) + Chat panel (flex-1)
- Toggle button between sidebar and chat area

**Components Used:**
- `ChatPanel` (domain/chat)
- `v2Chat` API for session list

**Data Source:**
- `v2Chat.sessions()` → React Query → session list
- `ChatPanel` handles individual conversation

**Interactions:**
- Session history sidebar (create new, select existing)
- Full chat functionality via `ChatPanel`

**Issues:**
- Route exists in file but chat is primarily accessed via floating `ChatWidget`
- Session management is minimal
- Sidebar only visible on large screens (`lg:flex`)

---

### 2.19 Unauthorized — `/unauthorized`

**File:** `frontend/src/app/unauthorized/page.tsx` (56 lines)  
**Route:** `/unauthorized` (protected)  
**Purpose:** Shown when user's role lacks permission for a page.

**Layout:** Centered message with icon, role display, and navigation buttons.

**Components Used:** `Button`, `ShieldAlert` icon, `useUser`

**Interactions:** "Go Back" button, "Dashboard" link

---

### 2.20 Not Found — `*` (catch-all)

**File:** `frontend/src/app/not-found/page.tsx` (67 lines)  
**Route:** `*` (catch-all for undefined routes)  
**Purpose:** 404 error page.

**Layout:** Centered 404 message with animated shield icon.

**Components Used:** `Button`, `Shield` icon, `motion`

**Interactions:** "Go Back" button, "Dashboard" link

---

## 3. Component Library

### 3.1 UI Primitives (`frontend/src/components/ui/`)

| Component | File | Lines | Props | Used In | Notes |
|---|---|---|---|---|---|
| `Button` | `button.tsx` | 222 | variant, size, isLoading, loadingText, leftIcon, rightIcon, enableHoverAnimation, enableRipple | Every page | Variants: default, destructive, outline, secondary, ghost, link, premium. Motion-enhanced. |
| `Badge` | `badge.tsx` | 245 | variant, size, animated | Every page | Variants: default, secondary, destructive, outline, success, warning, info, urgency levels. AnimatedBadge, CountBadge, DotBadge, StatusDot. |
| `Card` | `card.tsx` | 260 | variant, className + children | Every page | AnimatedCard, StaggerCard, UrgencyCard, DataCard sub-variants. |
| `AnimatedNumber` | `animated-number.tsx` | 404 | value, format, duration | Dashboard, Analytics, Decision detail | AnimatedCurrency, AnimatedPercentage, AnimatedCounter, SlotMachineNumber, DataChangeIndicator, LiveDataValue. |
| `Skeleton` | `skeleton.tsx` | 449 | className | All list/detail pages | SkeletonDashboard, SkeletonDecisionsList, SkeletonSignalsList, SkeletonHumanReview, SkeletonDecisionView, SkeletonChart, etc. |
| `Toast` | `toast.tsx` | 402 | N/A (Zustand store) | Every page (via provider) | success, error, warning, info, promise variants. Auto-dismiss with progress bar. Zustand-based store. |
| `CommandPalette` | `command-palette.tsx` | 670 | isOpen, onClose | AppLayout (global) | Cmd+K/Ctrl+K. Searches decisions, signals, customers. Quick navigation + actions. |
| `ConfirmationDialog` | `confirmation-dialog.tsx` | 223 | isOpen, onConfirm, onCancel, title, description, variant, children | Decision detail, Escalation detail | Focus trapping, Escape to close, backdrop blur. Variants: default, warning, danger. |
| `ErrorBoundary` | `error-boundary.tsx` | 163 | children, fallback, onError | AppLayout (wraps Outlet) | Class component. Dev-only stack traces. Retry/reload actions. |
| `ErrorState` | `error-state.tsx` | 81 | error, onRetry, title, variant | All pages with data | Inline or full-page variants. |
| `NotFoundState` | `not-found-state.tsx` | 61 | entity, id, backTo | Detail pages | Entity-specific 404 with back navigation. |
| `FilterDropdown` | `filter-dropdown.tsx` | 193 | label, options, value, onChange, icon | Decisions, Signals, Customers, Escalations | Full keyboard navigation, ARIA roles, checkmark for selected. |
| `ActiveFilterChip` | `active-filter-chip.tsx` | 36 | label, onRemove | Decisions, Signals | Small chip with X button. |
| `Pagination` | `pagination.tsx` | 221 | currentPage, totalPages, onPageChange, pageSize, totalItems | Decisions, Audit | First/prev/next/last, page size selector, keyboard nav. |
| `Breadcrumbs` | `breadcrumbs.tsx` | 70 | items (label + href) | All detail pages | Mono font for IDs. Chevron separators. |
| `SwipeableCard` | `swipeable-card.tsx` | 237 | leftActions, rightActions, threshold | DecisionCard (mobile) | Touch swipe with reveal actions. Keyboard accessible. |
| `FreshnessIndicator` | `FreshnessIndicator.tsx` | 64 | lastUpdated, source | Various widgets | Green/yellow/red dot with relative time. |
| `ThemeProvider` | `theme-provider.tsx` | 125 | defaultTheme, children | main.tsx (root) | Light/Dark/System. localStorage persistence. Smooth transition class. |
| `KeyboardShortcutsPanel` | `keyboard-shortcuts-panel.tsx` | 191 | N/A | AppLayout (global) | Modal with shortcut reference. Platform-aware (Mac/Windows). |
| `LoadingState` | `states.tsx` | 130 | message | Various | Vietnamese default text "Đang tải..." |
| `EmptyState` | `states.tsx` | — | icon, title, description, action | Various | Generic empty state with optional action button. |

### 3.2 Chart Components (`frontend/src/components/charts/`)

| Component | File | Lines | Purpose | Used In |
|---|---|---|---|---|
| `CausalChainDiagram` | `CausalChainDiagram.tsx` | 557 | Flowchart showing root cause → effects → impact | Q4 (Why) |
| `ConfidenceGauge` | `ConfidenceGauge.tsx` | 562 | Circular gauge with confidence score and factors | Q6 (Confidence) |
| `CostEscalationChart` | `CostEscalationChart.tsx` | 520 | Line/area chart showing cost growth over time | Q7 (If Nothing) |
| `ExposureChart` | `ExposureChart.tsx` | 433 | Bar chart of shipment exposure distribution | Q3 (How Bad) |
| `ScenarioVisualization` | `ScenarioVisualization.tsx` | 540 | Side-by-side scenario cards (best/base/worst) | Q3 (How Bad) |
| `TimelineVisualization` | `TimelineVisualization.tsx` | 481 | Horizontal timeline with milestones | Q2 (When) |
| `MiniConfidenceGauge` | `ConfidenceGauge.tsx` | — | Compact version of confidence gauge | DecisionCard |

### 3.3 Domain Components

#### Decisions (`frontend/src/components/domain/decisions/`)

| Component | File | Lines | Purpose |
|---|---|---|---|
| `DecisionCard` | `DecisionCard.tsx` | 483 | List card with urgency, exposure, action, swipe |
| `VerdictBanner` | `VerdictBanner.tsx` | 215 | Executive summary banner for detail page |
| `SevenQuestionsView` | `SevenQuestionsView.tsx` | ~300 | Accordion container for Q1-Q7 |
| `DecisionHeader` | `DecisionHeader.tsx` | ~150 | Header with status, ID, timestamps |
| `ActionButtons` | `ActionButtons.tsx` | ~200 | Acknowledge/Override/Escalate button bar |
| `AuditTrailFooter` | `AuditTrailFooter.tsx` | 365 | Metadata, linked signals, integrity hash |
| `Q1WhatIsHappening` | `Q1WhatIsHappening.tsx` | 243 | Event summary + affected shipments |
| `Q2When` | `Q2When.tsx` | 220 | Deadline + timeline visualization |
| `Q3HowBad` | `Q3HowBad.tsx` | 308 | Severity + exposure + scenarios |
| `Q4Why` | `Q4Why.tsx` | 274 | Root cause + causal chain diagram |
| `Q5WhatToDo` | `Q5WhatToDo.tsx` | 674 | Recommended action + alternatives |
| `Q6Confidence` | `Q6Confidence.tsx` | 590 | Confidence gauge + factors + calibration |
| `Q7IfNothing` | `Q7IfNothing.tsx` | 452 | Cost of inaction + PONR countdown |

#### Common (`frontend/src/components/domain/common/`)

| Component | File | Lines | Purpose |
|---|---|---|---|
| `StatCard` | `StatCard.tsx` | 344 | Metric card with icon, animated value, trend |
| `ActionBadge` | `ActionBadge.tsx` | 120 | Action type badge (REROUTE, DELAY, INSURE...) |
| `ConfidenceIndicator` | `ConfidenceIndicator.tsx` | 184 | HIGH/MEDIUM/LOW indicator (badge/bar/ring) |
| `CostDisplay` | `CostDisplay.tsx` | 242 | Cost with confidence interval + comparison |
| `CountdownTimer` | `CountdownTimer.tsx` | 272 | Live deadline countdown + urgency states |
| `SeverityBadge` | `SeverityBadge.tsx` | 103 | CRITICAL/HIGH/MEDIUM/LOW badge |
| `UrgencyBadge` | `UrgencyBadge.tsx` | 104 | IMMEDIATE/URGENT/SOON/WATCH badge |
| `QuickActions` | `QuickActions.tsx` | 119 | Pipeline flow: Signals → Decisions → Actions |
| `MorningBriefCard` | `MorningBriefCard.tsx` | 103 | Daily AI brief card |
| `SignalFeedV2` | `SignalFeedV2.tsx` | 134 | Real-time signal feed |

#### Other Domain Components

| Component | File | Lines | Purpose |
|---|---|---|---|
| `SignalCard` | `signals/SignalCard.tsx` | 363 | Signal list card with severity/probability |
| `EvidenceList` | `signals/EvidenceList.tsx` | 155 | Evidence items with confidence scores |
| `CustomerCard` | `customers/CustomerCard.tsx` | 99 | Customer list card |
| `EscalationCard` | `escalations/EscalationCard.tsx` | 211 | Escalation list card with SLA countdown |
| `ChatPanel` | `chat/ChatPanel.tsx` | 194 | Full chat interface with SSE streaming |
| `ChatWidget` | `chat/ChatWidget.tsx` | 102 | Floating chat bubble |
| `ChatInput` | `chat/ChatInput.tsx` | 80 | Auto-resizing message input |
| `ChatMessage` | `chat/ChatMessage.tsx` | 64 | User/assistant message bubble |
| `SuggestionCard` | `chat/SuggestionCard.tsx` | 116 | AI suggestion with accept/reject |

#### Layout Components (`frontend/src/components/domain/layout/`)

| Component | File | Lines | Purpose |
|---|---|---|---|
| `AppLayout` | `AppLayout.tsx` | 145 | Main shell: sidebar + topbar + content + mobile nav + chat widget |
| `Sidebar` | `Sidebar.tsx` | 557 | Left navigation with 3 sections, collapsible, badges |
| `TopBar` | `TopBar.tsx` | 796 | Top bar: search, notifications, data freshness, user menu |
| `MobileNav` | `MobileNav.tsx` | 251 | Bottom tab bar for mobile with overflow sheet |

---

## 4. Navigation & User Flow

### 4.1 Route Architecture

```
PUBLIC ROUTES (no auth):
  /                    → Landing Page
  /auth/login          → Login
  /auth/register       → Register

PROTECTED ROUTES (wrapped in ProtectedRoute + AppLayout):
  /dashboard           → Dashboard (default after login)
  /decisions           → Decisions List
  /decisions/:id       → Decision Detail (7 Questions)
  /signals             → Signals List
  /signals/:id         → Signal Detail
  /customers           → Customers List
  /customers/:id       → Customer Detail
  /human-review        → Human Review Queue
  /human-review/:id    → Escalation Detail
  /analytics           → Analytics Dashboard
  /audit               → Audit Trail
  /reality             → Oracle Reality Engine
  /onboarding          → Setup Wizard (post-registration)
  /settings            → Settings (7 tabs)
  /unauthorized        → Access Denied

CATCH-ALL:
  *                    → 404 Not Found
```

### 4.2 Navigation Structure

**Desktop:**
- **Sidebar** (left, 256px expanded / 64px collapsed):
  - Logo + collapse toggle
  - OPERATIONS section: Dashboard, Signals, Decisions, Human Review, Customers
  - INTELLIGENCE section: Analytics, Oracle Reality
  - SYSTEM section: Audit Trail, Settings
  - Footer: Role indicator, system health, version
- **TopBar** (top):
  - Mobile menu button (md:hidden)
  - Data freshness indicator
  - Search button (opens Command Palette via Cmd+K)
  - Notification bell (dropdown with pending decisions/escalations)
  - Theme toggle (Sun/Moon)
  - User menu (dropdown with profile, settings, logout)

**Tablet (768-1023px):**
- Sidebar auto-collapses to icon-only mode (64px)
- TopBar remains visible
- Content area expands

**Mobile (<768px):**
- Sidebar hidden (hamburger menu to show overlay)
- TopBar simplified
- **Bottom Navigation Bar** (fixed, 5 items):
  - Home (Dashboard), Signals, Decisions, Review, More...
  - "More" opens bottom sheet with remaining pages
  - Badge counts on Decisions and Review items

### 4.3 User Journey

```
FIRST-TIME USER:
Landing (/) → Register (/auth/register) → Onboarding Wizard (/onboarding)
  → Step 1: Welcome
  → Step 2: Company Profile
  → Step 3: Trade Routes
  → Step 4: Risk Preferences
  → Step 5: Data Import (CSV)
  → Step 6: First Signal Scan
  → Step 7: Complete → Dashboard (/dashboard)

RETURNING USER:
Landing (/) → Login (/auth/login) → Dashboard (/dashboard)

CORE WORKFLOW:
Dashboard → See urgent decisions → Click decision → Decision Detail (7Q view)
  → Read through Q1-Q7 → Choose: Acknowledge / Override / Escalate
  → If Escalate → Human Review Queue → Review → Approve/Reject

SIGNAL MONITORING:
Signals → Browse/Filter → Click signal → Signal Detail → Generate Decision

AI CHAT (accessible from any page):
Click floating chat bubble → Chat panel opens → Ask questions → Get answers/suggestions
```

### 4.4 Keyboard Navigation

| Shortcut | Action |
|---|---|
| `Cmd+K` / `Ctrl+K` | Open Command Palette |
| `?` | Open Keyboard Shortcuts Panel |
| `/` | Focus search (on list pages) |
| `j` / `k` | Navigate items (decisions list) |
| `Enter` | Open selected item |
| `Escape` | Close modal/dialog/clear search |
| `g d` | Go to Dashboard |
| `g s` | Go to Signals |
| `g c` | Go to Customers |

---

## 5. Design System Summary

### 5.1 Color Palette

**Light Mode:**
| Token | Value | Usage |
|---|---|---|
| `--color-background` | `#f8fafc` | Page background |
| `--color-foreground` | `#0f172a` | Primary text |
| `--color-card` | `#ffffff` | Card backgrounds |
| `--color-muted` | `#f1f5f9` | Muted backgrounds |
| `--color-muted-foreground` | `#64748b` | Secondary text |
| `--color-border` | `#e2e8f0` | Borders |
| `--color-accent` | `#2563eb` | Primary accent (blue) |
| `--color-accent-hover` | `#1d4ed8` | Accent hover |
| `--color-sidebar` | `#ffffff` | Sidebar background |

**Dark Mode:**
| Token | Value | Usage |
|---|---|---|
| `--color-background` | `#0b0f1a` | Page background (deep blue-gray) |
| `--color-foreground` | `#f1f3f7` | Primary text |
| `--color-card` | `#1a2236` | Card backgrounds |
| `--color-muted` | `#182030` | Muted backgrounds |
| `--color-muted-foreground` | `#8b95a8` | Secondary text |
| `--color-border` | `#2e3b54` | Borders |
| `--color-accent` | `#3b82f6` | Primary accent (brighter blue) |
| `--color-sidebar` | `#0e1424` | Sidebar background |

**Semantic Colors (both modes):**
| Category | Levels | Colors |
|---|---|---|
| Urgency | IMMEDIATE / URGENT / SOON / WATCH | Red / Orange / Yellow / Gray |
| Severity | CRITICAL / HIGH / MEDIUM / LOW | Red / Orange / Blue / Green |
| Confidence | HIGH / MEDIUM / LOW | Green / Orange / Red |
| Actions | REROUTE / DELAY / INSURE / MONITOR / NOTHING | Purple / Blue / Cyan / Green / Gray |
| Status | Success / Error / Warning / Info | Green / Red / Orange / Blue |

### 5.2 Typography

| Element | Font | Size | Weight | Tracking |
|---|---|---|---|---|
| Base | Inter, system-ui | 14px (data-dense UI) | 400 | Normal |
| H1 | Inter | 1.875rem (30px) | 600 | -0.025em |
| H2 | Inter | 1.5rem (24px) | 600 | -0.02em |
| H3 | Inter | 1.25rem (20px) | 600 | -0.01em |
| H4 | Inter | 1.125rem (18px) | 600 | -0.01em |
| Mono | JetBrains Mono, Fira Code | Various | Various | Normal |
| Labels | Inter (mono) | 10-12px | 500-700 | 0.05-0.1em (uppercase) |

**Key pattern:** Labels and metadata use `font-mono text-[10px] uppercase tracking-wider text-muted-foreground`.

### 5.3 Spacing

4px base grid system. Tailwind standard scale:
- Component padding: `p-3` to `p-6` (12-24px)
- Card padding: `p-4` to `p-8` (16-32px)
- Section gaps: `gap-4` to `gap-6` (16-24px)
- Grid gaps: `gap-3` to `gap-4` (12-16px)
- Page padding: `p-4 md:p-6` (16px mobile, 24px desktop)

### 5.4 Effects & Elevation

| Pattern | Light Mode | Dark Mode |
|---|---|---|
| Card shadow | `0 1px 3px rgba(0,0,0,0.06)` | `0 1px 3px rgba(0,0,0,0.3)` |
| Card hover | `0 8px 24px rgba(0,0,0,0.1)` | `0 8px 24px rgba(0,0,0,0.35)` |
| Border radius | `rounded-xl` (12px) for cards, `rounded-lg` (8px) for inputs | Same |
| Backdrop blur | Used on TopBar, mobile nav, modals | Same |
| Glassmorphism | `bg-white/70 + backdrop-blur-md` | `bg-gray-900/80 + backdrop-blur-md` |
| Glow effects | Very subtle: `0 0 0 1px rgba(...)` | Subtle: accent glow on hover |
| Terminal effects | Disabled (all opacity: 0) | Disabled (tasteful, no neon) |

### 5.5 Animations

| Type | Implementation | Easing |
|---|---|---|
| Page transitions | Framer Motion: fade-in + y: 10→0 | Spring (smooth) |
| Card hover | scale + y shift + shadow change | Spring (snappy) |
| Stagger lists | staggerChildren: 0.05-0.1s | Spring |
| Number animation | AnimatedNumber with spring | Spring |
| Skeleton loading | Shimmer animation (2s linear infinite) | Linear |
| Toast enter/exit | Slide from right + fade | Spring |
| Modal | Scale 0.95→1 + fade + y: 10→0 | Spring |
| Theme transition | 500ms ease on background, 350ms on colors | Ease |

**Reduced motion:** All animations respect `prefers-reduced-motion: reduce` — animations are disabled or minimized.

### 5.6 Icon Library

**lucide-react** (v0.563.0) — used exclusively throughout. No other icon library.

Common icons by domain:
- Navigation: LayoutDashboard, AlertTriangle, FileText, Bell, Users, BarChart3, Globe, FileSearch, Settings
- Actions: Shield, Zap, ArrowRight, ChevronRight, Check, X, Plus, Minus
- Risk: AlertTriangle, ShieldAlert, Activity, TrendingDown, Ship, Anchor
- Data: DollarSign, Clock, Eye, Brain, Target, Radio

### 5.7 Responsive Behavior

| Breakpoint | Sidebar | Navigation | Layout | Content |
|---|---|---|---|---|
| < 768px (mobile) | Hidden (overlay) | Bottom tab bar | Single column | `p-4 pb-20` |
| 768-1023px (tablet) | Collapsed (64px) | Top bar only | Flexible | `p-6` |
| >= 1024px (desktop) | Expanded (256px) | Top bar | Multi-column grids | `p-6` |

### 5.8 Dark/Light Mode

- **Full support:** Both modes have complete custom CSS variables
- **Persistence:** localStorage (`riskcast-theme`)
- **System detection:** `prefers-color-scheme` media query
- **Transition:** Smooth 500ms transition with `.theme-transitioning` class
- **Auth pages:** Login/Register force dark mode regardless of setting

---

## 6. State & Data Architecture

### 6.1 State Management

| Layer | Technology | Purpose |
|---|---|---|
| Server State | React Query (TanStack) | API data fetching, caching, mutations |
| Auth State | React Context (`AuthProvider`) | JWT tokens, login/logout, protected routes |
| User State | React Context (`UserProvider`) | User profile, avatar, role |
| Plan State | React Context (`PlanProvider`) | Subscription tier, limits, features |
| Theme State | React Context (`ThemeProvider`) | Light/dark/system theme |
| i18n State | React Context (`I18nProvider`) | Locale (en/vi), translations |
| Toast State | Zustand store | Toast notifications queue |
| Local UI State | React `useState` | Form inputs, toggles, modals, tabs |
| URL State | React Router + `usePagination` | Current route, page number, filters |
| Persistent Settings | `localStorage` | Theme, settings, auth tokens |

**Note:** Zustand is listed as a dependency (v5.0.11) but is ONLY used for the toast notification store. All other state uses React Context or React Query.

### 6.2 Data Flow

```
Backend (Python/FastAPI on :8002)
  ↓ HTTP REST API (proxied via Vite dev server)
  ↓
API Clients
  ├── api-v2.ts → V2 endpoints (/api/v2/*)
  │     ├── v2Auth (login, register, refresh)
  │     ├── v2Signals (list, get, dismiss)
  │     ├── v2Chat (send, sessions — SSE streaming)
  │     ├── v2Briefs (today's brief)
  │     ├── v2Feedback (submit)
  │     ├── v2Dashboard (summary, freshness)
  │     ├── v2Analytics (timeseries, categories, routes)
  │     ├── v2Audit (list, get)
  │     ├── v2Customers (CRUD)
  │     ├── v2Shipments (CRUD)
  │     └── v2Intelligence (analyze company)
  │
  └── api.ts → Legacy endpoints (/api/*)
        ├── Health check gate (checks /health first)
        └── withMockFallback() wrapper
              ↓ If API fails
              Mock Data Generators
                ├── generators/dashboard.ts
                ├── generators/customers.ts
                ├── generators/analytics.ts
                ├── generators/audit.ts
                ├── generators/reality.ts
                └── generators/escalations.ts
  ↓
React Query Hooks
  ├── useDashboard.ts → DashboardData
  ├── useDecisions.ts → Decision[] + mutations
  ├── useSignals.ts → Signal[] + mutations
  ├── useCustomers.ts → Customer[] + CRUD mutations
  ├── useEscalations.ts → Escalation[] + approve/reject
  ├── useRealityEngine.ts → RealityData
  ├── useAnalytics.ts → AnalyticsData
  ├── useAuditTrail.ts → AuditEvent[]
  ├── useChat.ts → SSE streaming messages
  └── useBrief.ts → MorningBrief
  ↓
Page Components → Render UI
```

### 6.3 API Health & Mock Fallback

The system has a dual-API architecture:
1. **V2 API** (`api-v2.ts`): Modern endpoints with JWT auth, typed responses
2. **Legacy API** (`api.ts`): Older endpoints with health-check gate

**Mock Fallback Pattern:**
```typescript
const withMockFallback = async (apiFn, mockFn) => {
  if (!isBackendHealthy) return mockFn();
  try {
    return await apiFn();
  } catch {
    return mockFn();
  }
};
```

This means: **Every page can render with mock data when the backend is unavailable.** Mock data is generated via seeded PRNG for deterministic output.

### 6.4 React Query Configuration

```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30 * 1000, // 30 seconds
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});
```

### 6.5 Provider Stack (top to bottom)

```tsx
<StrictMode>
  <QueryClientProvider>
    <I18nProvider>
      <ThemeProvider>
        <AuthProvider>
          <PlanProvider>
            <UserProvider>
              <ToastProvider>
                <RouterProvider />
              </ToastProvider>
            </UserProvider>
          </PlanProvider>
        </AuthProvider>
      </ThemeProvider>
    </I18nProvider>
  </QueryClientProvider>
</StrictMode>
```

### 6.6 Key Data Types

**Decision (7-Questions Framework):**
```typescript
interface Decision {
  decision_id: string;
  status: 'PENDING' | 'ACKNOWLEDGED' | 'OVERRIDDEN' | 'ESCALATED';
  urgency: 'IMMEDIATE' | 'URGENT' | 'SOON' | 'WATCH';
  q1_what: Q1WhatIsHappening;
  q2_when: Q2WhenWillItHappen;
  q3_severity: Q3HowBadIsIt;
  q4_why: Q4WhyIsThisHappening;
  q5_action: Q5WhatToDoNow;
  q6_confidence: Q6HowConfident;
  q7_inaction: Q7WhatIfNothing;
  affected_shipments: ShipmentExposure[];
  created_at: string;
  updated_at: string;
}
```

**Signal:**
```typescript
interface Signal {
  signal_id: string;
  status: 'ACTIVE' | 'CONFIRMED' | 'EXPIRED' | 'DISMISSED';
  event_type: EventType;
  severity_score: number;
  probability: number;
  confidence: number;
  source: SignalSource;
  evidence: EvidenceItem[];
  affected_regions: string[];
  impact_estimate: { min_usd: number; max_usd: number };
}
```

---

## 7. Feature Status Matrix

| # | Feature | Status | Notes |
|---|---|---|---|
| 1 | Landing/Marketing Page | ✅ Functional | Static content, no real pricing integration |
| 2 | User Registration | ✅ Functional | Creates V2 API account, redirects to onboarding |
| 3 | User Login | ✅ Functional | V2 API auth with JWT, demo accounts, lockout |
| 4 | Onboarding Wizard | ✅ Functional | 7-step wizard, creates customer, triggers scan |
| 5 | Dashboard Overview | ✅ Functional | Stats, urgent decisions, chokepoints, activity |
| 6 | Decision List + Filtering | ✅ Functional | Search, filter, sort, paginate, keyboard nav |
| 7 | Decision Detail (7 Questions) | ✅ Functional | Full Q1-Q7 with charts, countdown, evidence |
| 8 | Decision Acknowledge | ✅ Functional | Confirmation dialog → API mutation |
| 9 | Decision Override | ✅ Functional | Action selection + reason → API mutation |
| 10 | Decision Escalate | ✅ Functional | Priority + reason → creates escalation |
| 11 | Signal List + Filtering | ✅ Functional | Search, filter by status/severity/source |
| 12 | Signal Detail | ✅ Functional | Evidence, impact, related decisions |
| 13 | Customer List | ✅ Functional | Search, filter, add customer modal |
| 14 | Customer Detail + Edit | ✅ Functional | Profile, shipments, edit mode |
| 15 | Customer AI Analysis | 🔧 Partial | Triggers LLM but may fail/timeout |
| 16 | Human Review Queue | ✅ Functional | List with priority/status filtering |
| 17 | Escalation Approve/Reject | ✅ Functional | Confirmation dialog with reason |
| 18 | Analytics Dashboard | 🔧 Partial | Charts render but data may be mock |
| 19 | Audit Trail | 🔧 Partial | List renders, export buttons UI-only |
| 20 | Oracle Reality Engine | 🔧 Partial | Shows data but derived from signals, not real AIS |
| 21 | Settings - Profile | 🔧 Partial | UI renders, saves to localStorage only |
| 22 | Settings - Company | 🔧 Partial | Duplicates onboarding, localStorage persistence |
| 23 | Settings - Notifications | 🔧 Partial | UI toggles, no actual notification system |
| 24 | Settings - Thresholds | 🔧 Partial | UI renders, unclear backend integration |
| 25 | Settings - Team Management | ❌ UI Only | No actual invitation/team API |
| 26 | Settings - Appearance | ✅ Functional | Theme toggle, density, language |
| 27 | Settings - Keyboard Shortcuts | ✅ Functional | Read-only reference panel |
| 28 | Command Palette (Cmd+K) | ✅ Functional | Search decisions/signals/customers, quick nav |
| 29 | AI Chat Widget | ✅ Functional | SSE streaming, session management |
| 30 | AI Chat Page | 🔧 Partial | Exists but secondary to widget |
| 31 | Dark Mode / Light Mode | ✅ Functional | Full support with system detection |
| 32 | i18n (English/Vietnamese) | 🔧 Partial | Translations exist but not all strings translated |
| 33 | Mobile Navigation | ✅ Functional | Bottom tab bar + overflow sheet |
| 34 | Swipe Gestures (Mobile) | ✅ Functional | Swipe actions on decision cards |
| 35 | Toast Notifications | ✅ Functional | Success/error/warning/info with auto-dismiss |
| 36 | Error Boundary | ✅ Functional | Catches render errors with retry |
| 37 | Loading Skeletons | ✅ Functional | Page-specific skeleton screens |
| 38 | Data Freshness Indicator | ✅ Functional | Shows data age with staleness colors |
| 39 | RBAC (Role-Based Access) | 🔧 Partial | Nav filtering works, but roles are client-side |
| 40 | CSV Export | ❌ UI Only | Button present, no export implementation |
| 41 | PDF Export | ❌ UI Only | Button present, no export implementation |
| 42 | Real-time Updates (SSE) | 🔧 Partial | Chat uses SSE, other data uses polling |
| 43 | Data Integrity Verification | 🔧 Partial | Client-side SHA-256 hash, no server verification |
| 44 | Shipment Creation | ✅ Functional | Form in customer detail page |
| 45 | Signal Dismiss | ✅ Functional | API mutation with confirmation |
| 46 | Morning Brief | 🔧 Partial | Card renders, data from V2 API |
| 47 | Pricing Tiers | ❌ UI Only | Landing page shows tiers, no Stripe/payment |
| 48 | Password Reset | ❌ Not Built | No forgot password flow |
| 49 | Email Verification | ❌ Not Built | No email verification after registration |
| 50 | OAuth / SSO | ❌ Not Built | No third-party auth providers |

**Legend:** ✅ Functional (end-to-end working) | 🔧 Partial (UI exists, backend incomplete or mock) | ❌ Not Built / UI Only

---

## 8. UX Issues & Technical Debt

### CRITICAL

1. **Hardcoded credentials in UI** (`frontend/src/app/auth/login/page.tsx`, `register/page.tsx`)
   - Real email `hoangpro268@gmail.com` and password `Hoang2672004` visible to any user
   - Demo accounts with password "demo" also exposed
   - **Impact:** Security vulnerability, unprofessional appearance

2. **Mock data pervasive throughout** — Every page falls back to mock data when API unavailable
   - Mock generators in `frontend/src/lib/mock-data/generators/`
   - Users cannot distinguish real vs mock data
   - **Impact:** Data integrity concerns, false sense of functionality

3. **Settings page is 2,145 lines** — Single monolithic file
   - Mixes 7 different feature domains
   - Difficult to maintain, test, or extend
   - **Impact:** Maintainability, developer velocity

### HIGH

4. **Client-side only RBAC** — Role-based access uses `usePermissions()` hook
   - Roles checked in frontend only — no server-side enforcement visible
   - Permission gate can be bypassed via direct URL navigation
   - **Impact:** Security gap

5. **Auth lockout is client-side** — 5 failed attempts → 30-second cooldown
   - Bypassed by page refresh
   - No server-side rate limiting apparent from frontend code
   - **Impact:** Security vulnerability

6. **No actual export functionality** — CSV/PDF export buttons exist on audit page
   - Buttons render but no implementation
   - **Impact:** Broken user expectations

7. **Mixed Vietnamese/English defaults** — `states.tsx` has Vietnamese default messages
   - `LoadingState` defaults to "Đang tải..."
   - `ErrorState` defaults to "Đã xảy ra lỗi. Vui lòng thử lại."
   - i18n system exists but not consistently applied
   - **Impact:** Inconsistent UX for English-primary users

8. **Register page forces dark theme** — Uses hardcoded `dark` class and `data-theme="dark"`
   - Login page uses theme-aware `bg-background`
   - **Impact:** Inconsistent auth page behavior

### MEDIUM

9. **No form validation library** — All validation is manual `if` checks
   - No Zod/Yup schema validation
   - Inconsistent error messages across forms
   - **Impact:** Data quality, maintainability

10. **Dead code: Zustand dependency** — Listed in package.json, only used for toast store
    - Could use React Context or be removed
    - **Impact:** Bundle size (minimal)

11. **Large page components** — Several pages exceed 700 lines
    - `analytics/page.tsx` (1,115 lines)
    - `onboarding/page.tsx` (1,008 lines)
    - `customers/page.tsx` (802 lines)
    - `TopBar.tsx` (796 lines)
    - **Impact:** Maintainability, code splitting effectiveness

12. **No virtual scrolling** — Large lists (audit trail, decisions) render all items
    - Pagination mitigates but doesn't solve for large pages
    - **Impact:** Performance with large datasets

13. **Accessibility gaps:**
    - Skip-to-content link exists (good)
    - Focus visible styles exist (good)
    - ARIA roles on filter dropdowns (good)
    - Missing: aria-live regions for dynamic content
    - Missing: Screen reader announcements for toast notifications
    - Missing: Color-only severity indicators (need text labels too)
    - Contrast may be insufficient for some muted-foreground text on light backgrounds

14. **No error reporting** — ErrorBoundary has `onError` prop but no integration
    - No Sentry, LogRocket, or similar
    - **Impact:** Production debugging difficulty

### LOW

15. **Terms of Service links are dead** — `href="#"` on register page
16. **No breadcrumb on all pages** — Only detail pages have breadcrumbs
17. **Inconsistent loading states** — Some pages use `SkeletonX`, others use generic `LoadingState`
18. **Chart components are heavy** — Each chart is 400-600 lines with custom rendering
19. **No lazy loading for images** — Though few images exist in the app
20. **Google Translate compatibility hack** in `index.html` — May mask React DOM issues

---

## 9. Overall Assessment

### Architecture Quality

RISKCAST V2's frontend is a **well-structured, professionally designed React application** built with modern tooling (React 19, TypeScript 5.9, Vite 7, Tailwind 4). The codebase demonstrates strong architectural decisions: lazy-loaded routes, a comprehensive design token system, theme-aware components, and a clean separation between UI primitives, domain components, and page compositions. The **7-Questions decision framework** is the crown jewel — a deeply thought-out UX pattern that transforms complex risk data into a structured, actionable narrative through Q1-Q7 cards with rich visualizations (causal chains, confidence gauges, cost escalation charts, scenario comparisons).

### Design System Maturity

The design system is **remarkably complete** for a project at this stage. The 1,217-line `index.css` defines a full dual-theme token system with semantic colors for urgency, severity, confidence, and action types. The animation library (`animations.ts`, 703 lines) provides consistent motion patterns across the entire app. The component library spans ~70+ components from atomic primitives (Button, Badge, Card) to complex domain-specific visualizations (CausalChainDiagram, ConfidenceGauge). The visual language draws from Bloomberg terminal density + Linear/Vercel cleanness, creating a distinctive "premium enterprise intelligence" aesthetic.

### Critical Gaps

The primary gap is **backend integration maturity**. The `withMockFallback` pattern means the UI is fully functional in demo mode but the boundary between real and mock data is invisible to users. Key missing pieces include: real-time data feeds (only SSE for chat), actual AIS/vessel tracking integration, server-side RBAC enforcement, export functionality, payment processing, email verification, and password reset. The hardcoded credentials in auth pages are a **security concern that should be addressed immediately**. Several pages (settings at 2,145 lines, analytics at 1,115 lines) need decomposition. The i18n system is built but inconsistently applied, with Vietnamese strings leaking into English-mode defaults.

**In summary:** This is a sophisticated prototype-to-MVP frontend with exceptional UI polish and a strong design system, but it needs backend hardening, security cleanup, and some structural refactoring before production readiness. The 7-Questions framework and dual-theme system are significant competitive differentiators that are well-executed.

---

*End of Audit Report*
