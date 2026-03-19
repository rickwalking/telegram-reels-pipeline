---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
lastStep: 14
workflowCompleted: true
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/product-brief-instagram-reels-pipeline-2026-02-24.md
  - _bmad-output/planning-artifacts/architecture.md
  - _bmad-output/planning-artifacts/epics.md
  - _bmad-output/brainstorming/brainstorming-session-2026-02-24.md
techStack:
  framework: React 19+ (with React Compiler)
  bundler: Vite
  language: TypeScript (strictNullChecks)
  styling: Shadcn/ui + Tailwind CSS
  stateManagement: TanStack Query
  testing: Testing Library + Playwright MCP
  storybook: true
  architecture: Atomic Design
  componentLibrary: core/ (shared across future apps)
designReferences:
  - https://ui.shadcn.com/blocks
  - https://github.com/vercel-labs/agent-skills
  - Atomic Design: https://medium.com/rd-shipit/como-criar-componentes-react-com-uma-arquitetura-escalavel-usando-atomic-design
---

# UX Design Specification — Telegram Reels Pipeline Dashboard

**Author:** Pedro
**Date:** 2026-03-18

---

## Executive Summary

### Project Vision

A real-time observability dashboard ("The Glass Kitchen Wall") for the Telegram Reels Pipeline. The SPA replaces SSH/terminal debugging with a visual interface that streams pipeline state changes via SSE, enables time-travel debugging through an event-sourced Pipeline DVR, and provides direct inspection of AI agent outputs through a Document Carousel. Built with React 19 + Vite + Shadcn/ui + TanStack Query, following Atomic Design principles with a shared `core/` component library.

### Target Users

| User | Context | Device | Tech Level |
|------|---------|--------|------------|
| Pedro (Operator) | Triggers pipeline runs, monitors progress, debugs failures, reviews/publishes Reels | Desktop (dashboard) + Mobile (Telegram notifications) | High — developer, comfortable with JSON payloads |
| Future Contributors | Extend the pipeline with new adapters (Discord, CI) or new agents | Desktop only | Medium-High — developers familiar with React/TypeScript |

### Key Design Challenges

1. **Information Density** — 7 pipeline stages × QA cycles × events per stage = potentially 50-100 events per run. Must present hierarchically (stage → events → payloads) without overwhelming.
2. **Real-Time Streaming UX** — SSE events arrive continuously during active runs. The UI must update smoothly (optimistic rendering, transition animations) without layout thrash or focus loss.
3. **Time-Travel Interaction Design** — The Pipeline DVR must support scrubbing through events chronologically, clicking into individual events for payload inspection, and comparing QA rework cycles. This is the core differentiator.
4. **Dual-Channel Experience** — Operators trigger from Telegram (mobile) and monitor from the dashboard (desktop). State must be consistent across channels with no stale data.

### Design Opportunities

1. **Shadcn Blocks Sidebar Layout** — Dashboard navigation pattern with collapsible sidebar (run list) + main content area (run detail). Matches the established Shadcn design language.
2. **Pipeline Stage Stepper** — Horizontal multi-step progress indicator with color-coded status (green/blue/yellow/red), QA rework loop indicators, and duration labels.
3. **Atomic Component Library** — The `core/` library can establish a reusable design system: StatusBadge, JsonViewer, Timeline, CopyButton, EventCard. These atoms/molecules are valuable for any future pipeline tool.
4. **Storybook-Driven Development** — Build and validate components in isolation before integration, ensuring consistency and enabling design review without running the full pipeline.

## Core User Experience

### Defining Experience

The dashboard's core interaction is **monitoring and inspecting pipeline runs**. Pedro's primary loop:

1. **Trigger** — Send YouTube URL via Telegram (or POST /api/runs from the dashboard)
2. **Watch** — See real-time stage progression via SSE stream (phone or desktop)
3. **Inspect** — Tap/click into any completed stage to view agent outputs (JSON/markdown)
4. **Debug** — If a run fails, scrub through the Pipeline DVR event timeline to find the root cause
5. **Act** — Pause/resume runs, re-trigger with adjustments

The run detail view is the gravity center — it must load instantly, stream events in real-time, and provide one-tap access to every agent artifact on any device.

### Platform Strategy

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Platform | Responsive SPA (mobile + desktop) | Operators check status on phone (Telegram → dashboard) and debug on desktop |
| Layout | Adaptive: sidebar (desktop) / bottom nav (mobile) | Shadcn Blocks sidebar collapses; mobile gets bottom tab navigation |
| Input | Touch (mobile) + mouse/keyboard (desktop) | 44px+ touch targets, swipe gestures for DVR, keyboard shortcuts on desktop |
| Offline | Limited — last-known state cached | TanStack Query caches recent data; SSE reconnects automatically on network recovery |
| Breakpoints | 320px (mobile) → 768px (tablet) → 1024px+ (desktop) | Three layout tiers with progressive feature density |
| State | TanStack Query | Server state with background refetch + offline cache |
| Real-time | EventSource (SSE) | Auto-reconnect with `Last-Event-ID` replay on mobile network drops |
| PWA | Considered for Phase 2 | Service worker for offline shell, push notifications to replace Telegram alerts |

### Responsive Interaction Patterns

| Interaction | Mobile | Desktop |
|-------------|--------|---------|
| Run list | Full-screen list, swipe between runs | Sidebar with collapsible panel |
| Stage stepper | Vertical progress (scrollable) | Horizontal stepper bar |
| Event feed | Scrolling card list | Scrolling table with columns |
| Payload inspection | Bottom sheet (slide up) | Side panel (slide right) |
| DVR timeline | Vertical timeline, swipe to navigate | Horizontal timeline, mouse scrub |
| Pause/resume | Floating action button (FAB) | Prominent header button |
| Copy | Long-press → share sheet | Click → clipboard with toast |
| JSON viewer | Collapsible accordion sections | Full syntax-highlighted panel |

### Effortless Interactions

1. **Auto-refreshing run list** — New runs appear without page reload. Active run's stage updates in real-time. TanStack Query handles staleness.
2. **Visual stage progression** — Stepper with color-coded status replaces reading log output. One glance shows where the pipeline is. Adapts orientation by screen size.
3. **Live event feed** — Events stream in with subtle slide-in animation. Most recent always visible. No manual polling.
4. **One-tap payload inspection** — Tap any stage in the stepper → Document Carousel shows all artifacts. Bottom sheet on mobile, side panel on desktop.
5. **Universal copy** — Every JSON payload, every artifact path, every error message has a copy button with visual confirmation. Share sheet on mobile.
6. **Direct pipeline control** — Pause/resume as FAB (mobile) or header button (desktop). Confirmation dialog prevents accidents. SSE reflects state change within 1 second.

### Critical Success Moments

| Moment | Scenario | Success Criteria |
|--------|----------|-----------------|
| "It's alive" | Pedro opens the dashboard during an active run | Stage stepper is moving, events are streaming, no loading spinners after initial load — works on phone and desktop |
| "Found it" | A run fails and Pedro needs to debug | Open DVR → scrub to error → tap event → see exact agent output. Under 1 minute. Works from any device. |
| "Smooth recovery" | Pedro pauses, fixes config, resumes | Pause FAB → confirmation → status updates via SSE → resume → pipeline continues. Possible from phone. |
| "Clean overview" | Pedro checks morning dashboard for overnight runs | Run list shows all runs with color-coded status badges. Completed = green, failed = red, active = blue pulse. Scannable on mobile. |

### Experience Principles

1. **Show, Don't Tell** — Replace text-based status with visual indicators. Stage stepper > "Currently in transcript stage". Color badges > "Status: completed".
2. **Progressive Disclosure** — Dashboard (high-level) → Run Detail (stages + events) → Document Carousel (payloads) → JSON Viewer (raw data). Each tap goes deeper.
3. **Real-Time by Default** — The UI should never feel stale. SSE keeps everything current. TanStack Query handles background refetching. No "Refresh" buttons.
4. **Debugger-First** — The Pipeline DVR is not a nice-to-have — it's the core differentiator. Optimize the timeline scrubbing, event inspection, and payload comparison interactions.
5. **Zero Configuration** — The dashboard should work out of the box. No settings pages, no config files, no onboarding flow. Open the URL → see your runs.
6. **Device Agnostic** — Every core interaction must work on mobile and desktop. Same data, adapted presentation. Phone for monitoring, desktop for deep debugging.

## Desired Emotional Response

### Primary Emotional Goals

The dashboard should make Pedro feel like a **mission control operator** — calm, informed, in charge. The primary emotion is **confidence and control**: full visibility into what the AI pipeline is doing at every moment, with the tools to intervene when needed.

| Priority | Emotion | Description |
|----------|---------|-------------|
| 1 | **Confidence** | "I can see exactly what's happening — no mysteries" |
| 2 | **Empowerment** | "When something breaks, I know exactly where and why" |
| 3 | **Trust** | "The system does what I tell it — pause means pause, resume means resume" |
| 4 | **Satisfaction** | "Clean run, well done" — quiet accomplishment on success |

### Emotional Journey Mapping

| Stage | Desired Emotion | Anti-Emotion (Avoid) |
|-------|----------------|---------------------|
| First open | **Clarity** — "I immediately understand what's happening" | Confusion — "What am I looking at?" |
| Active run monitoring | **Confidence** — "I can see it working" | Anxiety — "Is it stuck? Did it crash?" |
| Successful completion | **Satisfaction** — "Clean run, nice" | Indifference — "Whatever" |
| Failure/error | **Empowerment** — "I know exactly what went wrong and can fix it" | Frustration — "Why did it break? Where?" |
| DVR debugging | **Detective thrill** — "Found it!" | Overwhelm — "Too many events, can't find anything" |
| Pause/resume | **Trust** — "The system did what I asked" | Doubt — "Did it actually pause? Is it safe to resume?" |
| Morning check (overnight runs) | **Relief** — "Everything ran fine" OR **Alertness** — "Two failed, let me check" | Dread — "I bet something broke" |

### Micro-Emotions

| Emotion Pair | Target State | Design Implication |
|-------------|-------------|-------------------|
| Confidence vs. Confusion | Confidence | Every UI element self-explanatory, no ambiguous icons |
| Trust vs. Skepticism | Trust | SSE confirms every state change instantly, no stale data |
| Accomplishment vs. Frustration | Accomplishment | DVR makes debugging feel like solving a puzzle, not searching for a needle |
| Excitement vs. Anxiety | Calm excitement | Live indicators show progress without creating "is it stuck?" anxiety |

### Design Implications

| Emotion | UX Design Approach |
|---------|-------------------|
| Confidence | Live SSE indicators (pulsing dot, stage animation), clear status badges, event count per stage |
| Empowerment | DVR with one-click event inspection, payload search, QA score comparison across attempts |
| Trust | Immediate SSE feedback on pause/resume, confirmation dialogs, state consistency across views |
| Satisfaction | Subtle success animation when run completes (green checkmark cascade through stages) |
| Alertness (not dread) | Failed runs show red badge with reason preview — not just "FAILED" but "QA exhausted at transcript stage" |
| Detective thrill | DVR timeline highlights anomalies (errors, rework cycles), payload diff between attempts |

### Emotional Design Principles

1. **No Ambiguity** — Every state has a distinct visual. Active = blue pulse. Completed = green check. Failed = red with reason. Paused = amber with pause icon.
2. **Instant Feedback** — Every user action (trigger, pause, resume) shows immediate visual confirmation via SSE. No "processing..." spinners longer than 1 second.
3. **Failure is Not Scary** — Errors are presented as debugging opportunities, not disasters. The DVR makes the "Found it!" moment accessible.
4. **Quiet Success** — Completed runs don't demand attention. A green badge in the sidebar is enough. Save the drama for failures that need action.
5. **Progressive Trust** — The more Pedro uses the dashboard, the more he trusts it. Consistent behavior, no stale data, no ghost states.

## UX Pattern Analysis & Inspiration

### Inspiring Products Analysis

| Product | Strength | Key UX Pattern | Relevance |
|---------|----------|---------------|-----------|
| **Vercel Dashboard** | Deployment status at a glance — build logs stream live, status transitions instant, errors actionable | Streaming log output, collapsible build steps, one-click re-deploy | Build step visualization maps to our pipeline stage stepper |
| **GitHub Actions** | Multi-step workflow visualization — each job collapsible, logs stream per step, re-run from failed | Workflow graph, step-by-step logs, timing labels, status badges | "Re-run from failed" maps to our "resume from checkpoint" |
| **Linear** | Information density without overwhelm — keyboard shortcuts, fast search, clean hierarchy, responsive mobile | Command palette (Cmd+K), list→detail, status badges, real-time sync | Mobile-to-desktop consistency, command palette for power users |
| **Shadcn Blocks** | Pre-built dashboard layouts that feel professional immediately | Sidebar + stats cards + data table | Direct starting point for our dashboard layout |

### Transferable UX Patterns

| Category | Pattern | Source | Our Application |
|----------|---------|--------|----------------|
| Navigation | Collapsible sidebar + main content | Shadcn Blocks | Run list sidebar + run detail area |
| Real-time | Streaming log output with auto-scroll | Vercel | Live event feed with SSE |
| Workflow | Expandable step visualization with timing | GitHub Actions | Pipeline stage stepper with duration |
| Status | Color-coded badges with reason text | All three | Run status badges (pending/active/done/failed) |
| Mobile | Responsive list → detail with bottom sheet | Linear | Run list → run detail with payload bottom sheet |
| Power user | Command palette (Cmd+K) | Linear | Quick search for runs, jump to stage, trigger new run |
| Recovery | Re-run from failed step | GitHub Actions | Resume from checkpoint button |

### Anti-Patterns to Avoid

| Anti-Pattern | Source | Problem | Our Approach Instead |
|-------------|--------|---------|---------------------|
| Wall of text logs | Jenkins | Raw log output useless for debugging | Structured EventCard components with metadata |
| Polling spinners | Old CI tools | "Checking status..." destroys confidence | SSE means UI is always current |
| Deep navigation (3+ clicks) | JIRA | Too many clicks to see a payload | Progressive disclosure, max 2 clicks to any data |
| Desktop-only dashboards | Grafana default | Tiny text, hover-only interactions fail on mobile | Touch-first responsive design |
| Undifferentiated event lists | Generic logs | All events look identical | Visual weight hierarchy: stages big, QA medium, heartbeats hidden |

### Design Inspiration Strategy

| Strategy | Pattern | Adaptation |
|----------|---------|-----------|
| **Adopt** | Shadcn Blocks sidebar layout | Use directly as base template |
| **Adopt** | Color-coded status badges | Green/blue/amber/red consistent across all views |
| **Adapt** | Vercel streaming logs | Replace raw text with structured EventCard components |
| **Adapt** | GitHub Actions step graph | Horizontal stepper (desktop) / vertical (mobile) with QA rework indicators |
| **Adapt** | Linear command palette | Cmd+K for run search, stage jump, quick trigger |
| **Avoid** | Jenkins log walls | Never show raw unstructured text |
| **Avoid** | Polling spinners | SSE-first, TanStack Query for cache |

## Design System Foundation

### Design System Choice

**Shadcn/ui + Tailwind CSS** — Themeable component system with Atomic Design architecture.

Shadcn provides copy-paste source code (not a dependency), giving full ownership of every component. Combined with Tailwind's utility-first CSS and design token system, this enables a shared `core/` component library that is themeable, testable, and reusable across future applications.

### Rationale for Selection

| Factor | Decision | Why |
|--------|----------|-----|
| Speed vs. Uniqueness | Balance | Shadcn provides fast, professional defaults; Tailwind enables customization |
| Component Ownership | Full ownership | Shadcn components are source code, not npm dependencies |
| Responsive | Built-in | Tailwind mobile-first breakpoints |
| Dark Mode | Built-in | Shadcn + next-themes pattern |
| Accessibility | Strong foundation | Shadcn built on Radix UI primitives (ARIA-compliant) |
| Storybook | Compatible | Components are plain React — Storybook integration trivial |
| Atomic Design | Natural fit | Shadcn primitives = atoms, compose into molecules/organisms |

### Implementation Approach — Atomic Design Layers

| Layer | Purpose | Examples | Location |
|-------|---------|----------|----------|
| Atoms | Smallest UI units, generic, themeable | StatusBadge, CopyButton, JsonViewer, Tooltip | `core/atoms/` |
| Molecules | Composed from atoms, single responsibility | EventCard, StageStep, PayloadTab | `core/molecules/` |
| Organisms | Feature-level compositions | StageStepperBar, EventFeed, DocumentCarousel, PipelineDvrTimeline | `core/organisms/` |
| Templates | Layout shells with slots | SidebarLayout, RunDetailLayout, DvrLayout | `core/templates/` |
| Pages | Route-bound, data-connected | DashboardPage, RunDetailPage, PipelineDvrPage | `app/pages/` |

### Customization Strategy

**Design Tokens (Tailwind CSS Variables):**
- Colors: `--primary`, `--destructive`, `--success`, `--warning`, `--muted`
- Spacing: consistent 4px grid
- Typography: system font stack (Inter or Geist)
- Border-radius: `--radius` token (Shadcn convention)

**Theme Support:**
- Light and dark mode via CSS class toggle
- Theme provider at app root
- Every core component accepts theme variants

**Component Interface Pattern:**
Every component in `core/` exposes a TypeScript interface:
- Props interface (e.g., `StatusBadgeProps`)
- Variant type (e.g., `StatusBadgeVariant`)
- Exported from a dedicated interface file (e.g., `statusBadgeInterface.ts`)

### External Dependency Isolation

| External Dependency | Isolation Pattern | Interface File |
|--------------------|-------------------|---------------|
| FastAPI REST API | `PipelineApiClient` service class | `pipelineApiClientInterface.ts` |
| SSE (EventSource) | `SseConnectionService` facade | `sseConnectionInterface.ts` |
| Clipboard API | `ClipboardService` utility | `clipboardInterface.ts` |
| TanStack Query | Direct usage (React primitive) | — |
| React Router | Direct usage (React primitive) | — |

### Web Design Guidelines Validation (Vercel)

Validated against Vercel Web Interface Guidelines (100+ rules). Key findings integrated into component requirements:

#### Cross-Cutting Accessibility Rules

| Rule | Applies To | Implementation |
|------|-----------|---------------|
| `prefers-reduced-motion` | Pulse animation, slide-in, DVR scrub | Reduced-motion media query on all animations |
| URL state via `nuqs` | Selected run, active tab, DVR position | Never `useState` for navigable state — always URL params |
| `aria-live="polite"` | Event feed, copy confirmations | Screen reader announcements for async updates |
| ARIA tab pattern | Document Carousel tabs | `role="tablist"`, `aria-selected`, `aria-labelledby` |
| `<button>` not `<div onClick>` | Stepper steps, DVR markers, toggle buttons | Semantic HTML for all interactive elements |
| `touch-action: manipulation` | All interactive elements | Global Tailwind base-layer rule to eliminate tap delay |
| `overscroll-behavior: contain` | Bottom sheets, modals, drawers | Prevent parent scroll bleed on mobile |
| `env(safe-area-inset-bottom)` | Bottom nav, FAB, bottom sheets | iPhone notch/home indicator safe areas |
| No `transition: all` | All animations | Explicit `transform`/`opacity` only |
| Virtualize lists >50 items | Event feed, DVR timeline | `virtua` or `content-visibility: auto` |
| Skip link | Dashboard layout | `<a href="#main-content">` as first focusable element |

#### Component-Specific Validation Results

| Component | Status | Key Actions Required |
|-----------|--------|---------------------|
| Sidebar Layout | NEEDS_WORK | `<a>`/`<Link>` for nav items, URL state for selected run, `<nav aria-label>`, skip link |
| Stage Stepper | NEEDS_WORK | `<button>` for steps, `aria-expanded`/`aria-controls`, `<ol>` container, `aria-current="step"` |
| Event Feed | NEEDS_WORK | `aria-live`, virtualization, `Intl.DateTimeFormat`, "new events" resume-scroll button |
| Payload Inspector | NEEDS_WORK | ARIA tab pattern, URL tab state, `overscroll-behavior`, dark-mode JSON theme |
| DVR Timeline | NEEDS_WORK | `<button>` markers, keyboard arrow navigation, `overscroll-behavior`, URL state |
| Status Badges | PASS | Amber contrast check (`amber-800`/`amber-200`), dark mode token pairing |
| Action Buttons | NEEDS_WORK | `role="alertdialog"` on pause confirm, `aria-label` on FAB, Cancel as default focus |
| Responsive | NEEDS_WORK | No `user-scalable=no`, safe-area insets, no `autoFocus` on mobile |

#### Color Contrast Requirements

| Status | Light Mode | Dark Mode | Minimum Ratio |
|--------|-----------|-----------|---------------|
| PENDING (gray) | `text-gray-700 bg-gray-100` | `text-gray-300 bg-gray-800` | 4.5:1 |
| IN_PROGRESS (blue) | `text-blue-700 bg-blue-100` | `text-blue-300 bg-blue-900` | 4.5:1 |
| COMPLETED (green) | `text-green-700 bg-green-100` | `text-green-300 bg-green-900` | 4.5:1 |
| FAILED (red) | `text-red-700 bg-red-100` | `text-red-300 bg-red-900` | 4.5:1 |
| PAUSED (amber) | `text-amber-800 bg-amber-100` | `text-amber-200 bg-amber-900` | 4.5:1 |

## Defining Core Experience — Screen Inventory

### Form Stack

| Tool | Purpose | Why |
|------|---------|-----|
| TanStack Form | Form state management | Type-safe, no `any`, React Compiler compatible, no `useEffect` internals |
| Zod | Schema validation | Inferred TypeScript types, runtime validation, no `any` leakage |

### Screen 1: Dashboard (Run List)

**Shadcn Base:** `sidebar-07` (collapses to icons) + `dashboard-01` (stats cards)

**Layout:** Collapsible sidebar with run list + main content area for selected run preview or overview stats.

**Components Required:**

| Component | Shadcn Source | Atomic Layer | Notes |
|-----------|-------------|-------------|-------|
| `Sidebar` + `SidebarMenu` | Shadcn Sidebar | Template | Collapsible, icons-only mode |
| `RunListItem` | Custom (Card-based) | Molecule | `<Link>` to `/runs/:runId`, status badge, timestamp |
| `StatusBadge` | Badge | Atom | Color-coded, text + icon, `aria-hidden` on icon |
| `CommandPalette` | Command (Cmd+K) | Organism | Search runs, jump to stage, trigger new run |
| `ThemeToggle` | Custom | Atom | `aria-label="Toggle dark mode"` |
| Bottom Nav (mobile) | Custom | Molecule | `env(safe-area-inset-bottom)`, `<Link>` items |

**Validation Rules Applied:**
- Run list items are `<Link>` (supports Cmd+click, middle-click)
- Run list virtualized from day one (`virtua`, >50 items expected)
- Empty state: show overview stats, not passive "Select a run" text
- Search input: `autocomplete="off"`, `spellCheck={false}`
- Bottom nav: safe-area insets for notched devices

### Screen 2: Run Detail (Gravity Center)

**Shadcn Base:** `Tabs` + `ScrollArea` + `AlertDialog`

**Layout:** Header (run ID, status, actions) → Stage Stepper → Document Carousel (tabs) → Live Event Feed.

**Components Required:**

| Component | Shadcn Source | Atomic Layer | Notes |
|-----------|-------------|-------------|-------|
| `StageStepperBar` | Custom (ordered list) | Organism | `<ol>` container, `<button>` per step, `aria-current="step"` on active |
| `StageStep` | Custom | Molecule | Color-coded circle + label + duration, `aria-expanded`, `aria-controls` |
| `DocumentCarousel` | Tabs | Organism | ARIA tab pattern built into Shadcn Tabs |
| `JsonPayloadViewer` | Custom | Molecule | Syntax highlighting, collapsible sections, dark-mode aware |
| `MarkdownViewer` | Custom | Molecule | Rendered markdown with code blocks |
| `CopyButton` | Button | Atom | `aria-label="Copy {name}"`, `aria-live` success announcement |
| `EventFeed` | ScrollArea | Organism | `aria-live="polite"`, auto-scroll with pause detection |
| `EventCard` | Card | Molecule | Event type icon (`aria-hidden`), timestamp (`<time>`), stage badge |
| `PauseResumeButton` | AlertDialog + Button | Molecule | Destructive confirmation, Cancel as default focus |

**Validation Rules Applied:**
- Active stage synced to URL: `?stage=transcript` via `nuqs`
- Duration labels use `font-variant-numeric: tabular-nums`
- Loading text ends with `…`: "running…"
- Pulse animation honors `prefers-reduced-motion`
- Touch targets ≥ 44px on stepper steps
- "← Back" is `<Link to="/runs">`, not `<button>`

### Screen 3: Pipeline DVR

**Shadcn Base:** `ResizablePanel` + `ScrollArea` + `Card`

**Layout:** Resizable split — timeline panel (left/top) + event detail panel (right/bottom).

**Components Required:**

| Component | Shadcn Source | Atomic Layer | Notes |
|-----------|-------------|-------------|-------|
| `PipelineDvrTimeline` | Custom (ResizablePanel) | Organism | Vertical timeline, keyboard arrow navigation, virtualized |
| `TimelineEventMarker` | Custom | Atom | `<button>` with `aria-label`, ≥44px touch target |
| `StageBoundaryMarker` | Custom | Atom | `aria-hidden="true"` (decorative), duration label with `tabular-nums` |
| `EventDetailPanel` | Card | Organism | Full payload display, copy button, diff button |
| `PayloadDiffViewer` | Custom | Molecule | Compare QA rework attempts side-by-side |

**Validation Rules Applied:**
- Selected event in URL: `?event=evt-abc123` via `nuqs`
- Timeline markers are `<button>` elements, not `<div onClick>`
- Keyboard: Left/Right arrow keys navigate events (roving `tabindex`)
- Timestamps use `<time datetime="...">` + `Intl.DateTimeFormat`
- `touch-action: pan-x` on horizontal timeline (desktop), `pan-y` on vertical (mobile)
- `overscroll-behavior: contain` to prevent browser back gesture
- Virtualize if >50 events

### Screen 4: Trigger New Run (Modal/Sheet)

**Shadcn Base:** `Dialog` (desktop) / `Drawer` (mobile) + `Input` + `Label` + `Button`

**Layout:** Modal with URL input, optional topic field, cancel/submit buttons.

**Form Validation (TanStack Form + Zod):**

```typescript
const triggerRunSchema = z.object({
  youtubeUrl: z.string().url().regex(/youtube\.com\/watch|youtu\.be\//),
  topicFocus: z.string().optional().default(""),
});
```

**Components Required:**

| Component | Shadcn Source | Atomic Layer | Notes |
|-----------|-------------|-------------|-------|
| `TriggerRunDialog` | Dialog / Drawer | Organism | Desktop=Dialog, Mobile=Drawer (bottom sheet) |
| URL Input | Input + Label | Atom | `type="url"`, `autocomplete="off"`, `spellCheck={false}`, placeholder ends with `…` |
| Topic Input | Input + Label | Atom | `autocomplete="off"` |
| Submit Button | Button | Atom | Loading spinner, `aria-label="Starting pipeline…"` during submit |
| Inline Error | Custom | Atom | Appears below field, not as toast. Focus first error on submit. |

**Validation Rules Applied:**
- `autoFocus` on URL input only on desktop, NOT on mobile
- Submit button stays enabled until request starts, then shows spinner
- Validation errors inline next to fields (Zod schema errors mapped to field positions)
- Escape key dismisses dialog (built into Shadcn Dialog)
- Mobile bottom sheet: `overscroll-behavior: contain`
- `aria-required="true"` on URL input

### Mobile Layout Adaptations

| Screen | Desktop | Mobile |
|--------|---------|--------|
| Dashboard | Sidebar + main content | Full-screen run list → tap → full-screen detail |
| Run Detail | Horizontal stepper + side-by-side carousel + feed | Vertical stepper → carousel (bottom sheet) → feed (scrollable) |
| DVR | Resizable side-by-side panels | Vertical timeline → event detail bottom sheet |
| Trigger | Centered dialog modal | Full-screen bottom drawer |

### Complete Shadcn Component Registry

| Shadcn Component | Usage | Customization |
|-----------------|-------|---------------|
| `Sidebar` | Dashboard navigation | Collapsible, icon-only mode, safe-area bottom |
| `Tabs` | Document Carousel | ARIA tab pattern, URL-synced active tab |
| `Card` | EventCard, RunListItem, EventDetail | Themed variants |
| `Badge` | StatusBadge across all views | 5 color variants with dark mode pairs |
| `Button` | All actions (trigger, pause, resume, copy) | Variants: default, destructive, ghost, outline |
| `AlertDialog` | Pause confirmation | Cancel as default focus, `role="alertdialog"` |
| `Dialog` | Trigger New Run (desktop) | Form inside, Escape to close |
| `Drawer` | Trigger New Run + payloads (mobile) | Bottom sheet, `overscroll-behavior: contain` |
| `Command` | Cmd+K palette | Search runs, jump to stage |
| `ScrollArea` | Event feed, timeline, run list | With virtualization wrapper |
| `ResizablePanel` | DVR split view | Timeline + detail |
| `Input` + `Label` | Form fields | TanStack Form + Zod integration |
| `Tooltip` | Stage duration, badge details | Hover on desktop, long-press on mobile |
| `Separator` | Section dividers | Semantic `<hr>` |
| `Collapsible` | JSON viewer sections, stage details | `aria-expanded` + `aria-controls` |

## Visual Foundation

### Color System

Built on Shadcn/Tailwind CSS variables. All colors defined as HSL tokens for theme flexibility.

**Semantic Colors:**

| Token | Light Mode | Dark Mode | Usage |
|-------|-----------|-----------|-------|
| `--primary` | Shadcn default (blue-ish) | Adjusted for dark | Primary CTA buttons, active indicators |
| `--destructive` | `red-600` | `red-400` | Pause button, failed status, errors |
| `--success` | `green-600` | `green-400` | Completed status, QA pass |
| `--warning` | `amber-600` | `amber-400` | Paused status, rework indicators |
| `--muted` | `gray-500` | `gray-400` | Pending status, disabled states |
| `--accent` | `blue-500` | `blue-400` | Active/in-progress status, pulse animation |
| `--background` | `white` | `gray-950` | Page background |
| `--card` | `gray-50` | `gray-900` | Card surfaces |
| `--border` | `gray-200` | `gray-800` | Borders, separators |

**Status Color Tokens (reused across all components):**

| Status | Token | Badge Light | Badge Dark |
|--------|-------|------------|-----------|
| PENDING | `--status-pending` | `text-gray-700 bg-gray-100` | `text-gray-300 bg-gray-800` |
| IN_PROGRESS | `--status-active` | `text-blue-700 bg-blue-100` | `text-blue-300 bg-blue-900` |
| COMPLETED | `--status-success` | `text-green-700 bg-green-100` | `text-green-300 bg-green-900` |
| FAILED | `--status-error` | `text-red-700 bg-red-100` | `text-red-300 bg-red-900` |
| PAUSED | `--status-warning` | `text-amber-800 bg-amber-100` | `text-amber-200 bg-amber-900` |

### Typography

| Element | Font | Size | Weight | Notes |
|---------|------|------|--------|-------|
| Page title | Geist Sans / Inter | `text-2xl` (1.5rem) | `font-bold` | `text-wrap: balance` |
| Section heading | Geist Sans / Inter | `text-lg` (1.125rem) | `font-semibold` | — |
| Body text | Geist Sans / Inter | `text-sm` (0.875rem) | `font-normal` | Default for dashboard density |
| Monospace (JSON) | Geist Mono / JetBrains Mono | `text-xs` (0.75rem) | `font-normal` | JSON viewer, code blocks |
| Badge text | System | `text-xs` | `font-medium` | — |
| Timestamps | System | `text-xs` | `font-normal` | `font-variant-numeric: tabular-nums` |
| Duration labels | System | `text-xs` | `font-medium` | `font-variant-numeric: tabular-nums` |

### Spacing System

Consistent 4px grid. Shadcn uses `space-*` utilities mapped to 4px increments:

| Token | Value | Usage |
|-------|-------|-------|
| `gap-1` | 4px | Tight spacing (icon + label) |
| `gap-2` | 8px | Default component internal padding |
| `gap-3` | 12px | Card padding, list item gaps |
| `gap-4` | 16px | Section spacing |
| `gap-6` | 24px | Major section separation |
| `gap-8` | 32px | Page-level spacing |

### Animation Tokens

| Animation | Duration | Easing | Properties | Reduced Motion |
|-----------|----------|--------|-----------|----------------|
| Stage pulse | 2s | `ease-in-out` | `opacity`, `transform` (scale) | `animation: none` |
| Event slide-in | 200ms | `ease-out` | `transform` (translateY), `opacity` | Instant appear |
| Tab switch | 150ms | `ease` | `opacity` | Instant switch |
| Bottom sheet | 300ms | `cubic-bezier(0.32, 0.72, 0, 1)` | `transform` (translateY) | Instant appear |
| Status badge color | 200ms | `ease` | `background-color`, `color` | Instant change |

All animations: never `transition: all`, always explicit properties, always `prefers-reduced-motion` variant.

## User Journey Flows

### Journey 1: Happy Path — Trigger and Monitor

```
[Telegram] → Send YouTube URL
     ↓
[Dashboard - Mobile] → See new run appear in list (SSE)
     ↓ tap
[Run Detail - Mobile] → Watch stage stepper progress
     ↓ stages complete
[Run Detail] → Tap completed stage → Bottom sheet with payload
     ↓ all stages done
[Run Detail] → Status badge = green "Completed"
     ↓
[Telegram] → Receive final reel + content options
```

**Key UX Moments:**
- Run appears in list within 1 second of Telegram trigger (SSE)
- Stage stepper updates without page reload
- Completed run shows green cascade animation

### Journey 2: Time-Travel Debugger

```
[Dashboard] → See red "Failed" badge on run
     ↓ tap
[Run Detail] → Stage stepper shows red on "transcript" stage
     ↓ tap "View DVR"
[DVR Timeline] → Scrub through events
     ↓ tap error event (red marker)
[Event Detail Panel] → See exact error: "QA exhausted at transcript"
     ↓ tap "View QA History"
[QA History] → Compare 3 attempts side-by-side (scores: 72, 78, 81)
     ↓ identify issue
[Back to Run Detail] → Tap "Resume from Transcript"
     ↓
[Run Detail] → Pipeline resumes, stepper updates live
```

**Key UX Moments:**
- Error reason visible in badge preview (not just "FAILED")
- DVR timeline highlights error events with visual weight
- QA attempt comparison enables root cause analysis

### Journey 3: Quick Morning Check

```
[Dashboard - Mobile] → Open app
     ↓ glance
[Run List] → 3 green, 1 red, 1 blue (active)
     ↓ tap red
[Run Detail] → See failure reason in header
     ↓ decide: fix later or now
[Back] → Continue with day
```

**Key UX Moments:**
- Run list is scannable in <3 seconds
- Color badges communicate status without reading text
- No loading spinners — TanStack Query has cached data from last visit

## Component Strategy — Full Inventory

### Atoms (core/atoms/)

| Component | Props Interface | Variants | Tests Required |
|-----------|----------------|----------|---------------|
| `StatusBadge` | `StatusBadgeProps { status, size?, showIcon? }` | pending, active, completed, failed, paused | Unit: all variants render, dark mode, aria-hidden on icon |
| `CopyButton` | `CopyButtonProps { content, label }` | default, ghost | Unit: copies to clipboard, shows confirmation, aria-live announcement |
| `TimeDisplay` | `TimeDisplayProps { timestamp, format? }` | relative, absolute | Unit: uses Intl.DateTimeFormat, tabular-nums |
| `DurationLabel` | `DurationLabelProps { seconds }` | compact, verbose | Unit: formats correctly, tabular-nums |
| `PulseIndicator` | `PulseIndicatorProps { active }` | active, inactive | Unit: respects prefers-reduced-motion |
| `SkipLink` | `SkipLinkProps { targetId }` | — | Unit: visible on focus, links to #main-content |
| `IconButton` | `IconButtonProps { icon, ariaLabel, onClick }` | default, ghost, destructive | Unit: renders aria-label, focus-visible ring |

### Molecules (core/molecules/)

| Component | Composed From | Props Interface | Tests Required |
|-----------|-------------|----------------|---------------|
| `EventCard` | StatusBadge + TimeDisplay + CopyButton | `EventCardProps { event }` | Unit: renders type/stage/time, copy works |
| `StageStep` | StatusBadge + DurationLabel + PulseIndicator | `StageStepProps { stage, status, duration?, active? }` | Unit: all states, aria-expanded, aria-current |
| `RunListItem` | StatusBadge + TimeDisplay | `RunListItemProps { run }` | Unit: renders as Link, Cmd+click works |
| `PayloadTab` | CopyButton | `PayloadTabProps { name, type, active? }` | Unit: ARIA tab attributes |
| `InlineError` | — | `InlineErrorProps { message, fieldName }` | Unit: renders below field, aria-describedby |

### Organisms (core/organisms/)

| Component | Composed From | Props Interface | Tests Required |
|-----------|-------------|----------------|---------------|
| `StageStepperBar` | StageStep[] | `StageStepperBarProps { stages, activeStage }` | Unit: renders ordered list, horizontal/vertical, keyboard nav |
| `EventFeed` | EventCard[] + ScrollArea | `EventFeedProps { events, isLive? }` | Unit: aria-live, auto-scroll, pause on user scroll, virtualization |
| `DocumentCarousel` | PayloadTab[] + JsonViewer/MarkdownViewer | `DocumentCarouselProps { artifacts, activeTab }` | Unit: ARIA tab pattern, URL sync |
| `PipelineDvrTimeline` | TimelineEventMarker[] + StageBoundaryMarker[] | `PipelineDvrTimelineProps { events, selectedEventId }` | Unit: keyboard arrow nav, virtualization, URL sync |
| `TriggerRunForm` | Input + Label + Button (TanStack Form + Zod) | `TriggerRunFormProps { onSubmit }` | Unit: validation, inline errors, loading state |
| `CommandPalette` | Command (Shadcn) | `CommandPaletteProps { commands }` | Unit: Cmd+K opens, search filters, keyboard nav |

### Templates (core/templates/)

| Component | Layout | Breakpoints |
|-----------|--------|-------------|
| `SidebarLayout` | Sidebar (desktop) + bottom nav (mobile) + main content | 320px / 768px / 1024px |
| `RunDetailLayout` | Header + stepper + carousel + feed | Stacks vertically on mobile |
| `DvrLayout` | Resizable split (timeline + detail) | Side-by-side (desktop) / stacked (mobile) |
| `ModalSheetLayout` | Dialog (desktop) / Drawer bottom sheet (mobile) | Adaptive by breakpoint |

## UX Consistency Patterns

### Loading States

| Context | Pattern | Implementation |
|---------|---------|---------------|
| Initial page load | Skeleton screens (Shadcn Skeleton) | Show layout structure immediately, fill with data |
| Data refetch | Stale data visible + subtle refresh indicator | TanStack Query `isFetching` indicator in header |
| Action pending | Button spinner + `aria-label="Processing…"` | Disable button after click, show spinner |
| SSE connecting | Connection status dot in header | Green = connected, amber = reconnecting, red = disconnected |

### Error States

| Context | Pattern | Implementation |
|---------|---------|---------------|
| API error | Inline error banner in affected section | Red border + error message + retry button |
| Form validation | Inline errors below each field | Zod schema → field-level error mapping |
| SSE disconnect | Auto-reconnect + "Reconnecting…" banner | `EventSource` reconnect with exponential backoff |
| Empty state | Helpful message + primary action | "No runs yet. Trigger your first pipeline run." + CTA |
| 404 run | Friendly message + back to dashboard | "Run not found. It may have been cleaned up." |

### Confirmation Patterns

| Action | Pattern | Default Focus |
|--------|---------|---------------|
| Pause pipeline | AlertDialog with reason input | Cancel button |
| Delete/cancel run | AlertDialog with destructive button | Cancel button |
| Trigger new run | Form submission (no extra confirmation) | — |
| Copy to clipboard | Instant + toast confirmation | — |
| Resume pipeline | Button click (no confirmation needed — safe action) | — |

### Navigation Patterns

| Pattern | Desktop | Mobile |
|---------|---------|--------|
| Primary nav | Sidebar (collapsible) | Bottom tab bar |
| Back navigation | Breadcrumbs + browser back | `← Back` header link + system back |
| Deep linking | All state in URL via `nuqs` | Same |
| Cmd+K search | Command palette overlay | Not available (bottom nav search) |
| Tab switching | Click tab | Swipe or tap tab |

## Responsive Design & Accessibility

### Breakpoint Strategy

| Breakpoint | Name | Layout Changes |
|-----------|------|---------------|
| 0-767px | Mobile | Bottom nav, vertical stepper, bottom sheets, stacked layouts, FAB for actions |
| 768-1023px | Tablet | Sidebar (collapsible), horizontal stepper, side panels begin appearing |
| 1024px+ | Desktop | Full sidebar, horizontal stepper, side-by-side panels, keyboard shortcuts active |

### Accessibility Checklist

| Category | Requirement | Implementation |
|----------|------------|----------------|
| **Semantic HTML** | Use correct elements | `<nav>`, `<main>`, `<button>`, `<a>`, `<ol>`, `<time>` |
| **Skip link** | First focusable element | `<a href="#main-content" class="sr-only focus:not-sr-only">` |
| **Focus visible** | All interactive elements | `focus-visible:ring-2 focus-visible:ring-ring` (Shadcn default) |
| **ARIA labels** | Icon-only buttons, badges | `aria-label` on every icon button, `aria-hidden` on decorative icons |
| **ARIA live** | Event feed, copy confirmations | `aria-live="polite"` on feed container and toast region |
| **ARIA tabs** | Document Carousel | `role="tablist"` + `role="tab"` + `role="tabpanel"` (Shadcn Tabs built-in) |
| **Keyboard nav** | All interactive elements | Tab order, arrow keys for stepper/timeline (roving tabindex) |
| **Reduced motion** | All animations | `prefers-reduced-motion: reduce` → `animation: none` / instant |
| **Color contrast** | All text on backgrounds | 4.5:1 minimum for normal text, 3:1 for large text (WCAG AA) |
| **Color independence** | Status indicators | Never color-only — always text + icon alongside color |
| **Touch targets** | All interactive elements | Minimum 44×44px, `touch-action: manipulation` |
| **Safe areas** | Bottom nav, FAB, sheets | `env(safe-area-inset-*)` for notched devices |
| **No zoom blocking** | Viewport meta | Never `user-scalable=no` or `maximum-scale=1` |
| **Internationalization** | Dates, numbers | `Intl.DateTimeFormat`, `Intl.NumberFormat` — no hardcoded formats |

### Dark Mode Strategy

| Element | Approach |
|---------|----------|
| Theme toggle | CSS class on `<html>` (`class="dark"`) via Shadcn pattern |
| Color scheme | `color-scheme: dark` on `<html>` for native element theming |
| Meta theme-color | `<meta name="theme-color">` matches page background per theme |
| JSON syntax highlight | Dark-mode aware theme via CSS variables |
| Status badge colors | Paired light/dark tokens (see Color System) |
| Form inputs | Explicit `background-color` + `color` for Windows dark mode |

---

*UX Design Specification complete. This document serves as the source of truth for all frontend development decisions.*
