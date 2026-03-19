# Story 25.1: React SPA Foundation — Scaffolding, Core Library & API Client

Status: ready-for-dev

## Story

As a Developer,
I want to scaffold the React SPA with Vite, Shadcn/ui, TanStack stack, and the `core/` component library structure,
So that all future frontend development follows the Atomic Design architecture with strict TypeScript and accessibility rules.

## Acceptance Criteria

1. **Given** `frontend/` directory, **When** `npm run dev` is executed, **Then** Vite dev server starts with proxy to FastAPI backend at `/api`.

2. **Given** the project, **When** I inspect `tsconfig.json`, **Then** `strictNullChecks: true`, `noUncheckedIndexedAccess: true`, and `noImplicitAny: true` must be enabled.

3. **Given** Shadcn/ui is initialized, **When** I run `npx shadcn add button badge tabs`, **Then** components install into `src/core/atoms/ui/` with Tailwind CSS 4 tokens.

4. **Given** the `core/` directory, **When** I inspect it, **Then** Atomic Design layers exist: `atoms/`, `molecules/`, `organisms/`, `templates/`, `hooks/`, `themes/`.

5. **Given** `PipelineApiService`, **When** I call `fetchRunList()`, **Then** it returns Zod-validated response data from `GET /api/runs`.

6. **Given** the dark mode toggle, **When** clicked, **Then** theme switches via CSS class on `<html>` without flicker (inline script in `index.html`).

7. **Given** Storybook, **When** `npm run storybook` is executed, **Then** it starts and shows the first atom stories.

## Tasks / Subtasks

- [ ] **Task 1: Scaffold Vite + React + TypeScript project**
  - [ ] `npm create vite@latest frontend -- --template react-ts` (at monorepo root, sibling to `telegram-reels-pipeline/`)
  - [ ] Configure `tsconfig.json`: `strictNullChecks`, `noUncheckedIndexedAccess`, `noImplicitAny`, `paths` alias `@/`
  - [ ] Configure `vite.config.ts`: proxy `/api` → `http://localhost:8000`, React Compiler plugin
  - [ ] Install core deps: `@tanstack/react-query @tanstack/react-form @tanstack/react-router zod nuqs`
  - [ ] Install dev deps: `vitest @testing-library/react @testing-library/jest-dom`
  - [ ] Create `frontend/CLAUDE.md` (already exists — verify)

- [ ] **Task 2: Initialize Shadcn/ui + Tailwind CSS**
  - [ ] `npx shadcn@latest init` (configure for `src/core/atoms/ui/`)
  - [ ] Configure `tailwind.config.ts` with custom status color tokens (`--status-pending`, `--status-active`, etc.)
  - [ ] Add theme tokens from UX spec (colors, spacing, typography)
  - [ ] Create `src/core/themes/tokens.css` with CSS variables
  - [ ] Create `src/core/themes/defaultTheme.ts`

- [ ] **Task 3: Create Atomic Design directory structure**
  - [ ] Create all directories per architecture: `core/{atoms,molecules,organisms,templates,hooks,themes}`, `app/{pages,hooks,routes,providers}`, `services/{interfaces,implementations,fakes}`, `schemas/`, `utils/`
  - [ ] Create `__init__` placeholder files where needed

- [ ] **Task 4: Create core hooks**
  - [ ] `src/core/hooks/useMountEffect.ts` — mount-only effect (replaces useEffect)
  - [ ] `src/core/hooks/useLatest.ts` — stable ref to latest callback (prevents stale closures)
  - [ ] `src/core/hooks/useCopyToClipboard.ts` — clipboard API with aria-live announcement
  - [ ] `src/core/hooks/useBreakpoint.ts` — responsive breakpoint detection (mobile/tablet/desktop)
  - [ ] `src/core/hooks/useReducedMotion.ts` — `prefers-reduced-motion` detection
  - [ ] `src/core/hooks/useWindowEvent.ts` — singleton global event listener with dedup
  - [ ] Unit tests for each hook

- [ ] **Task 5: Create service interfaces + implementations**
  - [ ] `src/services/interfaces/pipelineApiClientInterface.ts` — `fetchRunList`, `fetchRunDetail`, `triggerRun`, `pauseRun`, `resumeRun`
  - [ ] `src/services/interfaces/sseConnectionInterface.ts` — `connect`, `disconnect`, `onEvent`
  - [ ] `src/services/interfaces/clipboardInterface.ts` — `copyToClipboard`
  - [ ] `src/services/implementations/PipelineApiService.ts` — native `fetch`, Zod validation on responses
  - [ ] `src/services/implementations/SseConnectionService.ts` — native `EventSource` with auto-reconnect + `Last-Event-ID`
  - [ ] `src/services/implementations/ClipboardService.ts`
  - [ ] `src/services/fakes/FakePipelineApiService.ts`
  - [ ] `src/services/fakes/FakeSseConnectionService.ts`
  - [ ] `src/services/fakes/FakeClipboardService.ts`

- [ ] **Task 6: Create Zod schemas for API responses**
  - [ ] `src/schemas/pipelineRunSchema.ts` — validates `GET /api/runs` and `GET /api/runs/:id` responses
  - [ ] `src/schemas/pipelineEventSchema.ts` — validates event stream data
  - [ ] `src/schemas/triggerRunSchema.ts` — validates `POST /api/runs` response
  - [ ] All schemas use `.strict()` to reject unexpected fields

- [ ] **Task 7: Create app providers + routing**
  - [ ] `src/app/providers/QueryProvider.tsx` — TanStack Query client (singleton, `useSuspenseQuery` default)
  - [ ] `src/app/providers/ThemeProvider.tsx` — dark/light mode via CSS class + localStorage
  - [ ] `src/app/providers/ServiceProvider.tsx` — DI container for service interfaces
  - [ ] `src/app/routes/routeTree.tsx` — TanStack Router with 4 routes: `/`, `/runs/:runId`, `/runs/:runId/dvr`, `/trigger`
  - [ ] `src/App.tsx` — compose providers + router
  - [ ] `src/main.tsx` — entry point

- [ ] **Task 8: Theme flicker prevention**
  - [ ] Inline `<script>` in `index.html` that reads `localStorage("theme")` and applies class to `<html>` before React mounts
  - [ ] `<meta name="theme-color">` set per theme
  - [ ] `color-scheme: dark` applied on `<html>` when dark

- [ ] **Task 9: Initialize Storybook**
  - [ ] `npx storybook@latest init --type react`
  - [ ] Configure `.storybook/main.ts` for Vite
  - [ ] Configure `.storybook/preview.ts` with Tailwind CSS + theme tokens
  - [ ] Create first story: `core/atoms/ui/Button.stories.tsx` (Shadcn button variants)

- [ ] **Task 10: Create first atom — StatusBadge**
  - [ ] Write `statusBadge.feature` (Gherkin scenarios FIRST)
  - [ ] Create `statusBadgeInterface.ts` — `StatusBadgeProps { status, size?, showIcon? }`, `StatusBadgeVariant`
  - [ ] Create `StatusBadge.tsx` — 5 variants (pending/active/completed/failed/paused), dark mode, icon + text
  - [ ] Create `StatusBadge.test.tsx` — all variants, dark mode, aria-hidden on icon, color contrast
  - [ ] Create `StatusBadge.stories.tsx` — all variants + sizes + dark mode

- [ ] **Task 11: Create SkipLink atom**
  - [ ] `SkipLink.tsx` — `<a href="#main-content" class="sr-only focus:not-sr-only">`
  - [ ] First focusable element in DOM
  - [ ] Unit test + story

- [ ] **Task 12: E2E test infrastructure**
  - [ ] Install Playwright: `npm install -D @playwright/test`
  - [ ] Create `e2e/` directory with `features/` and `steps/`
  - [ ] Create `playwright.config.ts` with Vite dev server
  - [ ] Create placeholder `e2e/features/dashboard.feature`

## Dev Notes

### References

- [Source: ux-design-specification.md] — Screen inventory, component list, responsive patterns
- [Source: frontend-architecture.md] — Project structure, tech stack, patterns, CLAUDE.md rules
- [Source: frontend/CLAUDE.md] — All coding rules, bans, limits, naming conventions
- [Source: Vercel React Best Practices] — 62 performance rules
- [Source: Vercel Web Interface Guidelines] — 100+ accessibility/UX rules

### Key Architecture Decisions

- `useSuspenseQuery` (not `useQuery`) — every data-fetching component inside `<Suspense>` boundary
- Service interfaces injected via React Context, never imported directly
- No barrel exports — import from specific file paths only
- React Compiler eliminates need for manual `useMemo`/`useCallback`
- Gherkin scenarios written BEFORE component implementation
