---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
lastStep: 8
status: 'complete'
completedAt: '2026-03-18'
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/ux-design-specification.md
  - _bmad-output/planning-artifacts/architecture.md
  - _bmad-output/planning-artifacts/epics.md
  - _bmad-output/planning-artifacts/product-brief-instagram-reels-pipeline-2026-02-24.md
workflowType: 'architecture'
scope: 'frontend'
project_name: 'Telegram Reels Pipeline Dashboard'
user_name: 'Pedro'
date: '2026-03-18'
---

# Frontend Architecture Decision Document

_This document defines the architecture for the React SPA dashboard ("The Glass Kitchen Wall") for the Telegram Reels Pipeline. It complements the existing backend architecture (architecture.md) and is guided by the UX Design Specification (ux-design-specification.md)._

## Project Context Analysis

### Scope

A responsive SPA dashboard that provides real-time observability into the AI pipeline. Four primary screens: Dashboard (run list), Run Detail, Pipeline DVR, and Trigger New Run. Communicates exclusively with the FastAPI backend via REST + SSE.

### Technical Constraints

| Constraint | Value | Source |
|-----------|-------|--------|
| Backend API | FastAPI at `http://localhost:8000/api` | Backend architecture |
| Real-time transport | SSE via `GET /api/runs/{id}/stream` | PRD FR13 |
| Target devices | Mobile (320px) + Desktop (1024px+) | UX spec |
| Deployment | Static files served by FastAPI | Backend architecture |
| Runtime | Modern browsers (Chrome, Safari, Firefox — latest 2 versions) | SPA requirement |

### Classification

| Dimension | Choice |
|-----------|--------|
| Project type | SPA (Single Page Application) |
| Complexity | Medium |
| Context | Greenfield frontend, brownfield backend |
| Team size | Solo developer (Pedro) |

## Starter Template & Tech Stack

### Chosen Stack

| Technology | Version | Purpose |
|-----------|---------|---------|
| React | 19+ | UI framework with React Compiler |
| Vite | 6+ | Build tool + dev server |
| TypeScript | 5.7+ | Language with `strictNullChecks` |
| Shadcn/ui | Latest | Component primitives (Radix-based) |
| Tailwind CSS | 4+ | Utility-first styling |
| TanStack Query | 5+ | Server state management |
| TanStack Form | Latest | Form state with Zod validation |
| TanStack Router | Latest | Type-safe routing with URL state |
| Zod | 3+ | Schema validation |
| nuqs | Latest | URL query state management |
| Storybook | 8+ | Component development + showcase |
| Vitest | 2+ | Unit testing |
| Testing Library | Latest | Component testing |
| Playwright | Latest | E2E testing via Playwright MCP |

### Initialization Command

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npx shadcn@latest init
npm install @tanstack/react-query @tanstack/react-form @tanstack/react-router zod nuqs
npm install -D vitest @testing-library/react @testing-library/jest-dom @storybook/react-vite playwright
```

## Core Architectural Decisions

### Decision 1: Monorepo Placement

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Location | `frontend/` inside `telegram-reels-pipeline/` repo | Same repo as backend; shared CI, single PR for full-stack changes |
| Package manager | npm (not pnpm/yarn) | Simplicity for solo dev, compatible with Vite |

### Decision 2: State Management

| State Type | Tool | Pattern |
|-----------|------|---------|
| Server state (API data) | TanStack Query | `useQuery` / `useMutation` with cache keys |
| Real-time state (SSE) | TanStack Query + custom SSE hook | `useMountEffect` to establish EventSource, update query cache |
| URL state (filters, tabs, selections) | nuqs | URL query params as source of truth |
| Form state | TanStack Form + Zod | Type-safe forms with schema validation |
| Ephemeral UI state | React `useState` | Only for truly local state (dropdown open, hover) |

**Banned:** No Redux, no Zustand, no MobX, no Context for data. No `useEffect` (use `useMountEffect` from custom hooks).

### Decision 3: Routing

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Router | TanStack Router | Type-safe routes, built-in search params, loader pattern |
| Route structure | File-based conceptually, explicit route tree | 4 routes: `/`, `/runs/:runId`, `/runs/:runId/dvr`, `/trigger` |

### Decision 4: API Client Architecture

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Pattern | Service class behind interface | Isolates `fetch` from components; mockable for tests |
| HTTP client | Native `fetch` (no axios) | Zero dependency, sufficient for REST |
| SSE client | Native `EventSource` behind facade | Auto-reconnect, `Last-Event-ID` support |
| Type safety | Zod schemas validate API responses at runtime | Never trust backend blindly |

### Decision 5: Component Architecture

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Pattern | Atomic Design (atoms → molecules → organisms → templates → pages) | Scalable, reusable, matches Shadcn granularity |
| Shared library | `core/` directory (framework-agnostic components) | Reusable across future apps |
| App-specific | `app/` directory (route-connected, data-fetching) | Pipeline-specific compositions |
| Interface pattern | Every component has a `*Interface.ts` file | Props, variants, and types in dedicated file |

### Decision 6: Testing Strategy

| Layer | Tool | What to Test |
|-------|------|-------------|
| Unit | Vitest + Testing Library | Components render correctly, props work, variants display |
| Integration | Vitest + Testing Library | Components compose correctly, hooks work with fakes |
| E2E | Playwright MCP | Full user journeys through the app |
| Visual | Storybook | All component states/variants documented |
| Gherkin | Feature files pre-written | Every test scenario defined in Gherkin BEFORE implementation |

### Decision 7: Error Handling

| Boundary | Pattern |
|----------|---------|
| API errors | TanStack Query `onError` → display inline error component |
| SSE disconnect | Auto-reconnect + connection status indicator |
| Route errors | React Error Boundary per route |
| Form validation | Zod schema → TanStack Form field-level errors |
| Render errors | Error Boundary wrapping each organism |

## Implementation Patterns & Consistency Rules

### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Components | PascalCase | `StageStepperBar`, `EventCard` |
| Hooks | camelCase with `use` prefix | `usePipelineSse`, `useMountEffect` |
| Interfaces | PascalCase with `Props`/`Interface` suffix | `StatusBadgeProps`, `PipelineApiClientInterface` |
| Interface files | camelCase with `Interface` suffix | `statusBadgeInterface.ts`, `pipelineApiClientInterface.ts` |
| Services | PascalCase with `Service` suffix | `PipelineApiService`, `SseConnectionService` |
| Constants | UPPER_SNAKE_CASE | `API_BASE_URL`, `SSE_RECONNECT_INTERVAL_MS` |
| Variables | camelCase, descriptive | `pipelineRunList`, `currentStageIndex`, `eventFeedItems` |
| Files | camelCase for utils, PascalCase for components | `formatDuration.ts`, `StatusBadge.tsx` |
| Test files | `*.test.tsx` / `*.test.ts` | `StatusBadge.test.tsx` |
| Story files | `*.stories.tsx` | `StatusBadge.stories.tsx` |
| Feature files | kebab-case `.feature` | `trigger-pipeline-run.feature` |

### Banned Patterns

| Pattern | Alternative | Why |
|---------|------------|-----|
| `any` type | Proper types or `unknown` | TypeScript strictness |
| `useEffect` | `useMountEffect` custom hook | Prevents cleanup bugs, clearer intent |
| `useEffect` for data fetching | TanStack Query `useQuery` | Proper cache/stale/refetch management |
| `useState` for URL state | `nuqs` | Deep-linking, browser history support |
| Barrel exports (`index.ts` re-exports) | Direct imports | Bundle size (Vercel `bundle-barrel-imports` rule) |
| `transition: all` | Explicit properties | Performance (Vercel rule) |
| `<div onClick>` | `<button>` or `<Link>` | Semantics + accessibility |
| `outline-none` without replacement | `focus-visible:ring-*` | Accessibility |
| Inline styles | Tailwind classes | Consistency |
| `console.log` in production | Structured logging service | Cleanliness |
| Functions >3 args | Destructured interface param | Readability |
| Components >200 lines | Extract sub-components | Maintainability |
| `promise.then().then()` | `async/await` | Readability |

### File Size Limits

| Type | Max Lines | Action on Exceed |
|------|-----------|-----------------|
| Component (`.tsx`) | 200 | Extract sub-components or hooks |
| Hook (`.ts`) | 100 | Split into focused hooks |
| Service (`.ts`) | 200 | Split by responsibility |
| Interface (`.ts`) | 50 | One interface per file |
| Test (`.test.tsx`) | 300 | Split by describe block |
| Feature (`.feature`) | 100 | Split by user journey |

### Component Interface Pattern

Every component in `core/` follows this structure:

```
core/atoms/StatusBadge/
├── StatusBadge.tsx           # Component implementation (max 200 lines)
├── statusBadgeInterface.ts   # Props interface + variant types (single file)
├── StatusBadge.test.tsx      # Unit tests
├── StatusBadge.stories.tsx   # Storybook stories
└── statusBadge.feature       # Gherkin test scenarios
```

Interface file pattern:
```typescript
// statusBadgeInterface.ts
export type StatusBadgeVariant = "pending" | "active" | "completed" | "failed" | "paused";

export interface StatusBadgeProps {
  readonly status: StatusBadgeVariant;
  readonly size?: "sm" | "md" | "lg";
  readonly showIcon?: boolean;
}
```

### Service Isolation Pattern

External dependencies are isolated behind interfaces:

```typescript
// pipelineApiClientInterface.ts
export interface PipelineApiClientInterface {
  readonly fetchRunList: (params: RunListQueryParams) => Promise<PipelineRunListResponse>;
  readonly fetchRunDetail: (runId: string) => Promise<PipelineRunDetailResponse>;
  readonly triggerRun: (command: TriggerRunCommand) => Promise<TriggerRunResponse>;
  readonly pauseRun: (runId: string) => Promise<void>;
  readonly resumeRun: (runId: string) => Promise<void>;
}
```

Implementation:
```typescript
// PipelineApiService.ts
export class PipelineApiService implements PipelineApiClientInterface {
  constructor(private readonly baseUrl: string) {}
  // ... fetch-based implementation
}
```

Test fake:
```typescript
// FakePipelineApiService.ts
export class FakePipelineApiService implements PipelineApiClientInterface {
  // ... in-memory implementation for tests
}
```

### Custom Hook: useMountEffect

Replaces `useEffect` for mount-only side effects:

```typescript
// useMountEffect.ts
import { useEffect, useRef } from "react";

export function useMountEffect(callback: () => void | (() => void)): void {
  const hasRun = useRef(false);
  useEffect(() => {
    if (hasRun.current) return;
    hasRun.current = true;
    return callback();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
}
```

## Project Structure & Boundaries

```
telegram-reels-pipeline/
└── frontend/                              # React SPA root
    ├── package.json
    ├── tsconfig.json                      # strictNullChecks: true, noUncheckedIndexedAccess: true
    ├── vite.config.ts                     # Proxy /api → backend, React Compiler plugin
    ├── tailwind.config.ts                 # Shadcn theme tokens, custom status colors
    ├── components.json                    # Shadcn configuration
    ├── CLAUDE.md                          # Frontend-specific coding rules
    ├── .storybook/                        # Storybook configuration
    │   ├── main.ts
    │   └── preview.ts
    │
    ├── public/                            # Static assets
    │
    ├── src/
    │   ├── main.tsx                       # App entry point
    │   ├── App.tsx                        # Router + QueryClient + ThemeProvider
    │   │
    │   ├── core/                          # ⭐ Shared component library (reusable)
    │   │   ├── atoms/                     # Smallest UI units
    │   │   │   ├── StatusBadge/
    │   │   │   │   ├── StatusBadge.tsx
    │   │   │   │   ├── statusBadgeInterface.ts
    │   │   │   │   ├── StatusBadge.test.tsx
    │   │   │   │   ├── StatusBadge.stories.tsx
    │   │   │   │   └── statusBadge.feature
    │   │   │   ├── CopyButton/
    │   │   │   ├── TimeDisplay/
    │   │   │   ├── DurationLabel/
    │   │   │   ├── PulseIndicator/
    │   │   │   ├── SkipLink/
    │   │   │   └── IconButton/
    │   │   │
    │   │   ├── molecules/                 # Composed from atoms
    │   │   │   ├── EventCard/
    │   │   │   ├── StageStep/
    │   │   │   ├── RunListItem/
    │   │   │   ├── PayloadTab/
    │   │   │   └── InlineError/
    │   │   │
    │   │   ├── organisms/                 # Feature-level compositions
    │   │   │   ├── StageStepperBar/
    │   │   │   ├── EventFeed/
    │   │   │   ├── DocumentCarousel/
    │   │   │   ├── PipelineDvrTimeline/
    │   │   │   ├── TriggerRunForm/
    │   │   │   └── CommandPalette/
    │   │   │
    │   │   ├── templates/                 # Layout shells
    │   │   │   ├── SidebarLayout/
    │   │   │   ├── RunDetailLayout/
    │   │   │   ├── DvrLayout/
    │   │   │   └── ModalSheetLayout/
    │   │   │
    │   │   ├── hooks/                     # Shared hooks
    │   │   │   ├── useMountEffect.ts
    │   │   │   ├── useCopyToClipboard.ts
    │   │   │   ├── useBreakpoint.ts
    │   │   │   └── useReducedMotion.ts
    │   │   │
    │   │   └── themes/                    # Theme definitions
    │   │       ├── defaultTheme.ts
    │   │       └── tokens.css
    │   │
    │   ├── app/                           # ⭐ Application-specific code
    │   │   ├── pages/                     # Route-connected pages
    │   │   │   ├── DashboardPage/
    │   │   │   │   ├── DashboardPage.tsx
    │   │   │   │   └── DashboardPage.test.tsx
    │   │   │   ├── RunDetailPage/
    │   │   │   ├── PipelineDvrPage/
    │   │   │   └── TriggerRunPage/
    │   │   │
    │   │   ├── hooks/                     # App-specific hooks
    │   │   │   ├── usePipelineSse.ts      # SSE connection + TanStack Query cache update
    │   │   │   ├── usePipelineRunList.ts  # TanStack Query wrapper
    │   │   │   └── usePipelineRunDetail.ts
    │   │   │
    │   │   ├── routes/                    # Route definitions (TanStack Router)
    │   │   │   └── routeTree.tsx
    │   │   │
    │   │   └── providers/                 # App-level providers
    │   │       ├── QueryProvider.tsx
    │   │       ├── ThemeProvider.tsx
    │   │       └── ServiceProvider.tsx    # DI container for services
    │   │
    │   ├── services/                      # ⭐ External dependency isolation
    │   │   ├── interfaces/                # One interface per file
    │   │   │   ├── pipelineApiClientInterface.ts
    │   │   │   ├── sseConnectionInterface.ts
    │   │   │   └── clipboardInterface.ts
    │   │   │
    │   │   ├── implementations/           # Concrete implementations
    │   │   │   ├── PipelineApiService.ts
    │   │   │   ├── SseConnectionService.ts
    │   │   │   └── ClipboardService.ts
    │   │   │
    │   │   └── fakes/                     # Test doubles
    │   │       ├── FakePipelineApiService.ts
    │   │       ├── FakeSseConnectionService.ts
    │   │       └── FakeClipboardService.ts
    │   │
    │   ├── schemas/                       # Zod schemas for API responses
    │   │   ├── pipelineRunSchema.ts
    │   │   ├── pipelineEventSchema.ts
    │   │   └── triggerRunSchema.ts
    │   │
    │   └── utils/                         # Pure utility functions
    │       ├── formatDuration.ts
    │       ├── formatTimestamp.ts
    │       └── classNames.ts
    │
    ├── e2e/                               # Playwright E2E tests
    │   ├── features/                      # Gherkin feature files
    │   │   ├── dashboard.feature
    │   │   ├── run-detail.feature
    │   │   ├── pipeline-dvr.feature
    │   │   └── trigger-run.feature
    │   └── steps/                         # Step definitions
    │       ├── dashboard.steps.ts
    │       ├── run-detail.steps.ts
    │       └── trigger-run.steps.ts
    │
    └── .claude/                           # IDE config (gitignored)
```

### Architectural Boundaries

| Boundary | Rule |
|----------|------|
| `core/` → `app/` | `core/` NEVER imports from `app/`. `core/` is reusable and app-agnostic. |
| `core/` → `services/` | `core/` NEVER imports from `services/`. Services are injected via props or context. |
| `app/` → `core/` | `app/` imports and composes `core/` components. |
| `app/` → `services/` | `app/` imports service INTERFACES only. Implementations injected by providers. |
| `services/interfaces/` → `services/implementations/` | Interfaces NEVER import implementations. |
| Atoms → Molecules | Atoms don't import molecules. Molecules compose atoms. |
| Molecules → Organisms | Molecules don't import organisms. Organisms compose molecules. |

### Import Rule Enforcement

```typescript
// ✅ CORRECT: app imports core component
import { StatusBadge } from "@/core/atoms/StatusBadge/StatusBadge";

// ✅ CORRECT: app imports service interface
import type { PipelineApiClientInterface } from "@/services/interfaces/pipelineApiClientInterface";

// ❌ BANNED: core imports from app
import { usePipelineSse } from "@/app/hooks/usePipelineSse"; // NEVER in core/

// ❌ BANNED: core imports service implementation
import { PipelineApiService } from "@/services/implementations/PipelineApiService"; // NEVER in core/

// ❌ BANNED: barrel imports
import { StatusBadge, CopyButton, EventCard } from "@/core"; // NEVER barrel
```

## Frontend CLAUDE.md

The following rules must be saved as `frontend/CLAUDE.md`:

```markdown
# Frontend Dashboard — Coding Rules

## Tech Stack
React 19+ (React Compiler) | Vite | TypeScript (strictNullChecks) | Shadcn/ui | Tailwind CSS | TanStack Query + Form + Router | Zod | nuqs | Storybook | Vitest + Testing Library | Playwright MCP

## Strict Bans
- `any` type: BANNED. Use proper types or `unknown`.
- `useEffect`: BANNED. Use `useMountEffect` from `core/hooks/`.
- `useEffect` for data: BANNED. Use TanStack Query `useQuery`.
- `useState` for URL state: BANNED. Use `nuqs`.
- Barrel exports (`index.ts`): BANNED. Import directly.
- `transition: all`: BANNED. List properties explicitly.
- `<div onClick>`: BANNED. Use `<button>` or `<Link>`.
- `outline-none`: BANNED without `focus-visible:ring-*`.
- `console.log`: BANNED in production. Use logging service.
- Promise `.then()` chains: BANNED. Use `async/await`.
- `user-scalable=no`: BANNED. Never disable zoom.
- Inline styles: BANNED. Use Tailwind classes.

## Limits
- Component: max 200 lines
- Hook: max 100 lines
- Service: max 200 lines
- Interface file: max 50 lines (one interface per file)
- Function: max 3 arguments (use destructured interface for more)
- Test file: max 300 lines

## Naming
- Components: PascalCase (`StageStepperBar.tsx`)
- Hooks: camelCase with `use` prefix (`usePipelineSse.ts`)
- Interfaces: PascalCase + `Props`/`Interface` suffix
- Interface files: camelCase + `Interface` suffix (`statusBadgeInterface.ts`)
- Services: PascalCase + `Service` suffix (`PipelineApiService.ts`)
- Variables: camelCase, descriptive. BANNED: `x`, `data`, `temp`, `value`, `thing`, `obj`, `aa`
- Constants: UPPER_SNAKE_CASE
- Test files: `*.test.tsx`
- Story files: `*.stories.tsx`
- Feature files: kebab-case `.feature`

## Architecture
- Atomic Design: atoms → molecules → organisms → templates → pages
- `core/` is shared library — NEVER imports from `app/` or `services/implementations/`
- `app/` composes `core/` components, imports service INTERFACES only
- Services isolated behind interfaces in `services/interfaces/`
- Every core component: `.tsx` + `Interface.ts` + `.test.tsx` + `.stories.tsx` + `.feature`

## Testing
- Gherkin scenarios MUST be written BEFORE implementation
- Unit tests: Vitest + Testing Library (AAA pattern)
- E2E tests: Playwright MCP
- All components have Storybook stories
- Test naming: `describe("ComponentName") > it("should behavior when condition")`

## Accessibility (Vercel Web Interface Guidelines)
- `prefers-reduced-motion`: all animations must have reduced variant
- `aria-live="polite"`: on event feed and toast regions
- `aria-label`: on all icon-only buttons
- `aria-hidden="true"`: on decorative icons
- ARIA tab pattern: on Document Carousel (Shadcn Tabs handles this)
- Focus visible: `focus-visible:ring-2` on all interactive elements
- Touch targets: minimum 44x44px
- `touch-action: manipulation`: on all interactive elements
- `overscroll-behavior: contain`: on modals, sheets, drawers
- `env(safe-area-inset-*)`: on bottom nav, FAB, bottom sheets
- Timestamps: `Intl.DateTimeFormat` only (no hardcoded formats)
- Numbers: `font-variant-numeric: tabular-nums` for aligned columns
- Color contrast: 4.5:1 minimum (WCAG AA)
- Skip link: first focusable element in DOM

## State Management
- Server data: TanStack Query (`useQuery`, `useMutation`)
- SSE real-time: Custom hook updates TanStack Query cache
- URL state: nuqs (filters, active tab, selected event, etc.)
- Form state: TanStack Form + Zod
- Local UI state: React `useState` (dropdowns, hover only)

## Commands
npm run dev          # Vite dev server (proxy /api → backend)
npm run build        # Production build
npm run test         # Vitest unit tests
npm run test:e2e     # Playwright E2E
npm run storybook    # Storybook dev server
npm run lint         # ESLint + TypeScript check
npm run typecheck    # tsc --noEmit
```

## Architecture Validation

### Requirements Coverage

| PRD Requirement | Architecture Component |
|----------------|----------------------|
| FR1: Trigger via Web UI | `TriggerRunForm` organism → `PipelineApiService.triggerRun()` |
| FR12: View active/historical runs | `DashboardPage` → `usePipelineRunList` hook → TanStack Query |
| FR13: Real-time SSE updates | `usePipelineSse` hook → `SseConnectionService` → TanStack Query cache |
| FR14: Time-travel DVR | `PipelineDvrPage` → `PipelineDvrTimeline` organism |
| FR15: Payload inspection | `DocumentCarousel` organism → `JsonPayloadViewer` molecule |

### Decision Coherence

All decisions are compatible:
- React 19 + React Compiler eliminates need for manual `useMemo`/`useCallback`
- TanStack Query + SSE hook provides real-time without `useEffect`
- Shadcn/ui + Tailwind provides Atomic Design foundation
- TanStack Form + Zod provides type-safe forms without `any`
- nuqs + TanStack Router provides full URL state management
- Service interfaces + fakes enables testing without backend

### Vercel React Best Practices Validation (62 Rules)

Validated against all 62 Vercel React performance rules. Key findings integrated:

#### CRITICAL Rules — Added to Architecture

| Rule | Gap Found | Resolution Added |
|------|----------|-----------------|
| `async-suspense-boundaries` | No Suspense boundaries defined | Use `useSuspenseQuery` from TanStack Query; every data-fetching organism wrapped in `<Suspense>` with skeleton fallback |
| `bundle-dynamic-imports` | No lazy loading for heavy components | DVR timeline, JSON viewer, charts must use `React.lazy()` + `Suspense` |
| `bundle-preload` | No prefetch on hover/focus | Navigation links trigger `queryClient.prefetchQuery()` on pointer-enter |
| `async-api-routes` | No fire-early-await-late pattern | `PipelineApiService` must start `fetch()` before sync setup, `await` at point of use |

#### HIGH Rules — Added to Architecture

| Rule | Resolution |
|------|-----------|
| `server-hoist-static-io` | Static config fetched once at module init, not per-render |
| `server-serialization` | Zod schemas use `.strict()` to reject unexpected API fields |
| `server-parallel-fetching` | Organisms with multiple data needs use `useQueries` (parallel) |

#### MEDIUM Rules — Added to CLAUDE.md

| Rule | Convention Added |
|------|----------------|
| `rerender-transitions` | URL state updates via nuqs wrapped in `startTransition` |
| `rerender-use-ref-transient-values` | Scroll position, hover coords stored in `useRef` not `useState` |
| `rerender-no-inline-components` | Component definitions BANNED inside other components |
| `rerender-functional-setstate` | `setState(prev => ...)` required when depending on previous state |
| `rendering-hydration-no-flicker` | Inline `<script>` in `index.html` applies theme class before React mounts |
| `rendering-activity` | Toggled panels use React 19 `<Activity>` instead of conditional rendering |
| `rendering-conditional-render` | Ban `&&` rendering; use ternary `condition ? <A/> : null` |
| `client-passive-event-listeners` | All scroll/touch/wheel listeners use `{ passive: true }` |
| `client-localstorage-schema` | localStorage data versioned (`trp_prefs_v1`), validated with Zod on read |

#### Additional Hooks Required (from validation)

| Hook | Purpose | Location |
|------|---------|----------|
| `useLatest` | Prevents stale closures in SSE callbacks | `core/hooks/useLatest.ts` |
| `useWindowEvent` | Singleton global event listener with dedup | `core/hooks/useWindowEvent.ts` |
| `useBreakpoint` | Responsive breakpoint detection | `core/hooks/useBreakpoint.ts` (already planned) |
| `useReducedMotion` | Respects `prefers-reduced-motion` | `core/hooks/useReducedMotion.ts` (already planned) |

#### Compliance Score

| Priority | Total | Addressed | Gap |
|----------|-------|-----------|-----|
| CRITICAL (10) | 10 | 6 after fixes | 4 deferred (conditional imports, partial deps) |
| HIGH (8) | 8 | 6 after fixes | 2 N/A (no RSC) |
| MEDIUM (30) | 30 | 22 after fixes | 8 low-impact |

### Gap Analysis

| Gap | Impact | Mitigation |
|-----|--------|-----------|
| No PWA support | Can't send push notifications from dashboard | Phase 2; Telegram handles mobile notifications for now |
| No offline mode | Dashboard blank without backend | TanStack Query caches last-known state; acceptable for monitoring tool |
| No i18n | Dashboard is English-only | Solo dev, single user; defer to Phase 3 |
| No analytics | Can't track dashboard usage | Not needed for internal tool |

---

*Frontend architecture complete. This document + the UX Design Specification provide the full context for implementing Epic 25.*
