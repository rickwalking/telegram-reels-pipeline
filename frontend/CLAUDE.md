# Frontend Dashboard — Coding Rules

## Tech Stack

React 19+ (React Compiler) | Vite 6+ | TypeScript 5.7+ (strictNullChecks) | Shadcn/ui | Tailwind CSS 4+ | TanStack Query 5+ | TanStack Form | TanStack Router | Zod 3+ | nuqs | Storybook 8+ | Vitest 2+ | Testing Library | Playwright MCP

## Commands

```bash
npm run dev          # Vite dev server (proxy /api → localhost:8000)
npm run build        # Production build → dist/
npm run test         # Vitest unit tests
npm run test:e2e     # Playwright E2E via Playwright MCP
npm run storybook    # Storybook dev server
npm run lint         # ESLint + TypeScript check
npm run typecheck    # tsc --noEmit
```

## Strict Bans

| Banned Pattern | Use Instead | Why |
|---------------|------------|-----|
| `any` type | Proper types or `unknown` (only exception for third-party library interop where the library's own types are untyped) | TypeScript strictness (`strictNullChecks: true`) |
| `useEffect` | `useMountEffect` from `core/hooks/` | Prevents cleanup bugs, clearer intent |
| `useEffect` for data fetching | TanStack Query `useSuspenseQuery` | Proper cache/stale/refetch + Suspense |
| `useState` for URL state | `nuqs` | Deep-linking, browser history |
| Barrel exports (`index.ts` re-exports) | Direct imports | Bundle size (`bundle-barrel-imports` rule) |
| `transition: all` | Explicit `transform`, `opacity` | Performance (Vercel rule) |
| `<div onClick>` / `<span onClick>` | `<button>` or `<Link>` | Semantics + accessibility |
| `outline-none` without replacement | `focus-visible:ring-*` | Accessibility |
| `console.log` in production | Structured logging service | Cleanliness |
| Promise `.then().then()` chains | `async/await` | Readability |
| `user-scalable=no` / `maximum-scale=1` | Never disable zoom | Accessibility (Vercel anti-pattern) |
| Inline styles | Tailwind classes | Consistency |
| `condition && <Component/>` | `condition ? <Component/> : null` | Avoids rendering `0`/`false` as text |
| Inline component definitions | Extract to separate file | Prevents remount on every parent render |
| `autoFocus` on mobile | Desktop only, single primary input | Prevents keyboard viewport resize |
| `Math.min(...largeArray)` | Single-loop min/max | Stack overflow on large arrays |
| Hardcoded date/number formats | `Intl.DateTimeFormat`, `Intl.NumberFormat` | Internationalization |

## Hard Limits

| Type | Max Lines | Action on Exceed |
|------|-----------|-----------------|
| Component (`.tsx`) | 200 | Extract sub-components or hooks |
| Hook (`.ts`) | 100 | Split into focused hooks |
| Service (`.ts`) | 200 | Split by responsibility |
| Interface file (`.ts`) | 50 | One interface per file |
| Function arguments | 3 max | Use destructured interface for more |
| Test file (`.test.tsx`) | 300 | Split by describe block |
| Feature file (`.feature`) | 100 | Split by user journey |

## Naming Conventions

| Element | Convention | Good Example | Bad Example |
|---------|-----------|-------------|------------|
| Components | PascalCase | `StageStepperBar.tsx` | `stagestepper.tsx` |
| Hooks | camelCase + `use` prefix | `usePipelineSse.ts` | `pipelineSSE.ts` |
| Interfaces | PascalCase + `Props`/`Interface` suffix | `StatusBadgeProps` | `IBadge` |
| Interface files | camelCase + `Interface` suffix | `statusBadgeInterface.ts` | `types.ts` |
| Services | PascalCase + `Service` suffix | `PipelineApiService.ts` | `api.ts` |
| Constants | UPPER_SNAKE_CASE | `API_BASE_URL` | `apiBaseUrl` |
| Variables | camelCase, descriptive | `pipelineRunList`, `currentStageIndex` | `data`, `x`, `temp`, `value`, `thing`, `obj` |
| Test files | `*.test.tsx` / `*.test.ts` | `StatusBadge.test.tsx` | `test-badge.tsx` |
| Story files | `*.stories.tsx` | `StatusBadge.stories.tsx` | `badge-story.tsx` |
| Feature files | kebab-case `.feature` | `trigger-pipeline-run.feature` | `triggerRun.feature` |

**Banned variable names:** `x`, `data`, `temp`, `value`, `thing`, `obj`, `aa`, `res`, `ret`, `cb`, `fn`, `val`, `el`. Use descriptive names: `customerProfile`, `llmResponse`, `processingStep`, `eventFeedItems`.

## Architecture — Atomic Design

```
src/
├── core/          # Shared component library (NEVER imports from app/ or services/implementations/)
│   ├── atoms/     # StatusBadge, CopyButton, TimeDisplay, DurationLabel, PulseIndicator, IconButton, SkipLink
│   ├── molecules/ # EventCard, StageStep, RunListItem, PayloadTab, InlineError
│   ├── organisms/ # StageStepperBar, EventFeed, DocumentCarousel, PipelineDvrTimeline, TriggerRunForm
│   ├── templates/ # SidebarLayout, RunDetailLayout, DvrLayout, ModalSheetLayout
│   ├── hooks/     # useMountEffect, useCopyToClipboard, useBreakpoint, useReducedMotion, useLatest, useWindowEvent
│   └── themes/    # Design tokens, theme definitions
├── app/           # Application-specific (composes core/, imports service INTERFACES only)
│   ├── pages/     # DashboardPage, RunDetailPage, PipelineDvrPage, TriggerRunPage
│   ├── hooks/     # usePipelineSse, usePipelineRunList, usePipelineRunDetail
│   ├── routes/    # TanStack Router route tree
│   └── providers/ # QueryProvider, ThemeProvider, ServiceProvider
├── services/      # External dependency isolation
│   ├── interfaces/       # One interface per file (pipelineApiClientInterface.ts, etc.)
│   ├── implementations/  # PipelineApiService, SseConnectionService, ClipboardService
│   └── fakes/            # FakePipelineApiService, FakeSseConnectionService (for tests)
├── schemas/       # Zod schemas for API response validation
└── utils/         # Pure utility functions (formatDuration, formatTimestamp)
```

### Import Rules (STRICT)

```typescript
// CORRECT: app imports core component
import { StatusBadge } from "@/core/atoms/StatusBadge/StatusBadge";

// CORRECT: app imports service interface
import type { PipelineApiClientInterface } from "@/services/interfaces/pipelineApiClientInterface";

// BANNED: core imports from app
import { usePipelineSse } from "@/app/hooks/usePipelineSse"; // NEVER in core/

// BANNED: core imports service implementation
import { PipelineApiService } from "@/services/implementations/PipelineApiService"; // NEVER in core/

// BANNED: barrel imports
import { StatusBadge, CopyButton } from "@/core"; // NEVER
```

### Component File Structure

Every component in `core/` must have all 5 files:

```
core/atoms/StatusBadge/
├── StatusBadge.tsx           # Implementation (max 200 lines)
├── statusBadgeInterface.ts   # Props + variant types (one interface per file)
├── StatusBadge.test.tsx      # Unit tests (Vitest + Testing Library)
├── StatusBadge.stories.tsx   # Storybook stories (all variants + themes)
└── statusBadge.feature       # Gherkin scenarios (written BEFORE implementation)
```

## State Management

| State Type | Tool | Pattern |
|-----------|------|---------|
| Server data | TanStack Query | `useSuspenseQuery` with `<Suspense>` boundary + skeleton fallback |
| Real-time SSE | Custom `usePipelineSse` hook | Updates TanStack Query cache on events via `queryClient.setQueryData` |
| URL state | nuqs | Filters, active tab, selected event, DVR position — ALL in URL params |
| Form state | TanStack Form + Zod | Type-safe, schema-validated, inline field errors |
| Local UI only | React `useState` | ONLY for ephemeral state: dropdown open, hover position |

### State Rules

- `startTransition` wraps all nuqs state updates and manual query invalidations
- `useRef` for transient high-frequency values (scroll position, hover coords, animation frames)
- `setState(prev => ...)` functional form required when new state depends on previous
- `useState(() => computeExpensiveInitial())` lazy initializer for expensive defaults
- Default prop values that are objects/arrays must be module-level constants, not inline

## Performance (Vercel React Best Practices)

### Async Patterns

- **Fire early, await late:** `PipelineApiService` starts `fetch()` before sync setup, `await` at point of use
- **`Promise.all()`:** Independent data fetches in service methods use `Promise.all()`
- **`useSuspenseQuery`:** All data-fetching organisms use Suspense-enabled queries
- **`useQueries`:** Organisms needing multiple independent resources fetch in parallel

### Bundle Optimization

- **`React.lazy()`:** Heavy organisms (DVR timeline, JSON viewer, charts) loaded dynamically with `<Suspense>`
- **Direct imports:** No barrel files, import from specific file paths
- **Prefetch on hover:** Navigation links trigger `queryClient.prefetchQuery()` on pointer-enter
- **Deferred third-party:** Analytics/monitoring scripts loaded after app shell via `requestIdleCallback`

### Rendering

- **`<Activity>`:** Toggled panels (sidebar, drawers) use React 19 `<Activity>` instead of conditional render
- **`content-visibility: auto`:** Applied to off-screen list sections (event feed, DVR timeline >50 items)
- **Static JSX hoisting:** Truly static JSX (no props/context) defined as module-level constants
- **SVG optimization:** All SVGs processed through SVGO (2 decimal precision) before inclusion
- **Theme flicker prevention:** Inline `<script>` in `index.html` reads localStorage theme, applies class to `<html>` before React mounts
- **Resource hints:** `<link rel="preconnect">` for FastAPI backend domain in `index.html`

## Testing

### Gherkin First

Every feature and component MUST have Gherkin scenarios written BEFORE implementation:

```gherkin
# statusBadge.feature
Feature: Status Badge
  Scenario: Renders correct color for completed status
    Given a StatusBadge with status "completed"
    Then the badge should display green styling
    And the badge should show a checkmark icon
    And the icon should have aria-hidden="true"

  Scenario: Renders accessible text for screen readers
    Given a StatusBadge with status "failed"
    Then the badge should have text content "Failed"
    And the color should not be the only status indicator
```

### Test Patterns

- **Unit tests:** Vitest + Testing Library, AAA pattern (`// Arrange`, `// Act`, `// Assert`)
- **E2E tests:** Playwright MCP validates full user journeys
- **Storybook:** All core components have stories showing all variants + dark mode + mobile
- **Test naming:** `describe("ComponentName") > it("should behavior when condition")`
- **Service fakes:** Every service interface has a corresponding fake in `services/fakes/`

## Accessibility (Vercel Web Interface Guidelines)

| Rule | Implementation |
|------|---------------|
| `prefers-reduced-motion` | All animations have reduced variant (media query) |
| `aria-live="polite"` | Event feed container, toast region, copy confirmations |
| `aria-label` | All icon-only buttons (FAB, theme toggle, copy button) |
| `aria-hidden="true"` | Decorative icons alongside text labels |
| ARIA tab pattern | Document Carousel uses Shadcn `Tabs` (built-in) |
| `focus-visible:ring-2` | All interactive elements (Shadcn default) |
| Skip link | `<a href="#main-content">` as first focusable DOM element |
| Touch targets | Minimum 44x44px on all interactive elements |
| `touch-action: manipulation` | Global base-layer rule on interactive elements |
| `overscroll-behavior: contain` | All modals, sheets, drawers, scrollable panels |
| `env(safe-area-inset-*)` | Bottom nav, FAB, bottom sheets (notched devices) |
| `font-variant-numeric: tabular-nums` | All numeric displays (timestamps, durations, scores) |
| Color contrast | 4.5:1 minimum WCAG AA; amber uses `amber-800`/`amber-200` |
| Color independence | Status never communicated by color alone — always text + icon |
| Semantic HTML | `<nav>`, `<main>`, `<button>`, `<a>`, `<ol>`, `<time>`, `<h1>`-`<h6>` hierarchy |
| No zoom blocking | Never `user-scalable=no` or `maximum-scale=1` |

## Responsive Breakpoints

| Breakpoint | Name | Key Layout Changes |
|-----------|------|-------------------|
| 0-767px | Mobile | Bottom nav, vertical stepper, bottom sheets, FAB, stacked layouts |
| 768-1023px | Tablet | Collapsible sidebar, horizontal stepper, side panels appear |
| 1024px+ | Desktop | Full sidebar, horizontal stepper, side-by-side panels, keyboard shortcuts |

## Dark Mode

- CSS class on `<html>` (`class="dark"`) via Shadcn convention
- `color-scheme: dark` on `<html>` for native element theming
- `<meta name="theme-color">` matches background per theme
- Theme initialization via inline `<script>` before React mounts (no flicker)
- All Shadcn components use CSS variable tokens (auto dark mode)

## External Dependency Isolation

Every external dependency accessed through a service interface:

| Dependency | Interface | Implementation | Fake (tests) |
|-----------|-----------|---------------|-------------|
| FastAPI REST | `PipelineApiClientInterface` | `PipelineApiService` | `FakePipelineApiService` |
| SSE EventSource | `SseConnectionInterface` | `SseConnectionService` | `FakeSseConnectionService` |
| Clipboard API | `ClipboardInterface` | `ClipboardService` | `FakeClipboardService` |

Services injected via React Context (`ServiceProvider`), never imported directly in components.

## Commit Rules

- Conventional commits: `feat:`, `fix:`, `refactor:`, `test:`, `chore:`, `docs:`
- Keep messages short (under 72 chars)
- Do not include `Co-Authored-By` lines
- Stage specific files, never `git add -A` or `git add .`
- Run `npm run typecheck && npm run lint && npm run test` before committing
- Author: Pedro Marins <ph.marins@hotmail.com>
