# Story 25.4: Document Carousel, Run Detail Page & Dashboard Assembly

Status: ready-for-dev

## Story

As a System Operator,
I want to inspect agent outputs per stage, see pipeline stage progression, and have a complete working dashboard,
So that I can monitor runs, debug issues, and trigger new runs from a single interface.

## Acceptance Criteria

1. **Given** a run with completed stages, **When** I select a stage in the stepper, **Then** the Document Carousel shows all artifacts for that stage with JSON/markdown rendering.

2. **Given** the Dashboard page, **When** loaded, **Then** I see the run list (sidebar on desktop, full-screen on mobile) with status badges and a "Trigger New Run" button.

3. **Given** the Run Detail page, **When** loaded, **Then** I see: stage stepper (with progression), Document Carousel (artifacts), event feed (live), and pause/resume controls.

4. **Given** the "Trigger New Run" button, **When** clicked, **Then** a Dialog (desktop) or Drawer (mobile) opens with a TanStack Form + Zod validated form for YouTube URL and topic.

5. **Given** the full application, **When** I navigate between pages, **Then** TanStack Router handles transitions with `startTransition` and URL state is preserved.

## Tasks / Subtasks

- [ ] **Task 1: Create `StageStep` molecule**
  - [ ] Write `stageStep.feature` (Gherkin FIRST)
  - [ ] `stageStepInterface.ts` — props: `stageName`, `status`, `durationSeconds?`, `isActive?`, `onClick`
  - [ ] `StageStep.tsx` — `<button>` element, color-coded circle + label + duration, `aria-expanded`, `aria-controls`
  - [ ] Active stage: pulse animation with `prefers-reduced-motion` variant
  - [ ] Duration: `font-variant-numeric: tabular-nums`, `<time>` element
  - [ ] Touch target: min 44x44px
  - [ ] Tests + stories (all 5 status variants)

- [ ] **Task 2: Create `StageStepperBar` organism**
  - [ ] Write `stageStepperBar.feature` (Gherkin FIRST)
  - [ ] `stageStepperBarInterface.ts` — props: `stages`, `activeStageIndex`, `onStageClick`
  - [ ] `StageStepperBar.tsx` — `<ol>` container, horizontal (desktop) / vertical (mobile)
  - [ ] `aria-current="step"` on active step
  - [ ] QA rework indicators (loop icon on stages with multiple attempts)
  - [ ] URL state: active stage synced via nuqs `?stage=transcript`
  - [ ] Tests + stories (horizontal + vertical + various stage states)

- [ ] **Task 3: Create `DocumentCarousel` organism**
  - [ ] Write `documentCarousel.feature` (Gherkin FIRST)
  - [ ] `documentCarouselInterface.ts` — props: `artifacts`, `activeTab`, `onTabChange`
  - [ ] Uses Shadcn `Tabs` (ARIA tab pattern built-in: `role="tablist"`, `aria-selected`, etc.)
  - [ ] Active tab synced to URL via nuqs `?artifact=router-output`
  - [ ] JSON artifacts: rendered in `JsonPayloadViewer` (from story 25-3)
  - [ ] Markdown artifacts: rendered with `react-markdown` or `marked`
  - [ ] Binary artifacts: download link
  - [ ] CopyButton on every payload
  - [ ] Tests + stories

- [ ] **Task 4: Create `RunListItem` molecule**
  - [ ] Write Gherkin scenarios FIRST
  - [ ] `runListItemInterface.ts` — props: `run` (id, url, status, stage, createdAt)
  - [ ] `RunListItem.tsx` — `<Link to="/runs/$runId">` (supports Cmd+click), StatusBadge, truncated URL, timestamp
  - [ ] Tests + stories

- [ ] **Task 5: Create `TriggerRunForm` organism**
  - [ ] Write `triggerRunForm.feature` (Gherkin FIRST)
  - [ ] `triggerRunFormInterface.ts` — props: `onSubmit`, `isSubmitting`
  - [ ] TanStack Form + Zod schema (`youtubeUrl: z.string().url().regex(...)`, `topicFocus: z.string().optional()`)
  - [ ] URL input: `type="url"`, `autocomplete="off"`, `spellCheck={false}`, placeholder ends with `…`
  - [ ] `autoFocus` on URL input: desktop only (not mobile)
  - [ ] Submit button: enabled until request starts, then spinner with `aria-label="Starting pipeline…"`
  - [ ] Inline field errors (not toast)
  - [ ] `aria-required="true"` on URL input
  - [ ] Tests + stories

- [ ] **Task 6: Create `DashboardPage` page**
  - [ ] Write `dashboard.feature` (Gherkin FIRST for E2E)
  - [ ] `src/app/pages/DashboardPage/DashboardPage.tsx`
  - [ ] `SidebarLayout` template: sidebar (run list) + main (selected run preview or stats)
  - [ ] `usePipelineRunList` hook: `useSuspenseQuery` + `<Suspense>` + skeleton
  - [ ] Run list virtualized via `virtua` (>50 runs expected over time)
  - [ ] "Trigger New Run" button opens `TriggerRunForm` in `Dialog` (desktop) / `Drawer` (mobile)
  - [ ] `CommandPalette` (Cmd+K): search runs, jump to stage
  - [ ] Empty state: "No pipeline runs yet. Trigger your first run." + CTA
  - [ ] Bottom nav on mobile with `env(safe-area-inset-bottom)`

- [ ] **Task 7: Create `RunDetailPage` page**
  - [ ] Write `runDetail.feature` (Gherkin FIRST for E2E)
  - [ ] `src/app/pages/RunDetailPage/RunDetailPage.tsx`
  - [ ] Header: run ID, StatusBadge, back link (`<Link>`), pause/resume button
  - [ ] `StageStepperBar` with stage progression
  - [ ] `DocumentCarousel` showing artifacts for selected stage
  - [ ] `EventFeed` (from story 25-2) showing live events
  - [ ] Pause button: `AlertDialog` confirmation, Cancel as default focus, `role="alertdialog"`
  - [ ] Resume button: direct action (no confirmation needed)
  - [ ] `usePipelineSse` hook for real-time updates
  - [ ] `useSuspenseQuery` for initial data + `<Suspense>` boundary

- [ ] **Task 8: Create `TriggerRunPage` page (mobile route)**
  - [ ] Full-screen bottom drawer with `TriggerRunForm`
  - [ ] `overscroll-behavior: contain`
  - [ ] On success: navigate to new run's detail page

- [ ] **Task 9: Create `MarkdownViewer` molecule**
  - [ ] `markdownViewerInterface.ts` — props: `content`, `maxHeight?`
  - [ ] Renders markdown to HTML (headings, code blocks, lists, tables, links)
  - [ ] CopyButton for raw markdown
  - [ ] Dark mode support for code blocks
  - [ ] Tests + stories

- [ ] **Task 10: Create `CopyButton` atom**
  - [ ] Write `copyButton.feature` (Gherkin FIRST)
  - [ ] `copyButtonInterface.ts` — props: `content`, `label`, `variant?`
  - [ ] Uses `ClipboardService` via `ServiceProvider` context
  - [ ] Success: checkmark animation + `aria-live="polite"` announcement
  - [ ] Tests + stories

- [ ] **Task 11: Write E2E tests (Playwright MCP)**
  - [ ] `e2e/features/dashboard.feature`:
    - Scenario: View run list with status badges
    - Scenario: Trigger new run via dialog
    - Scenario: Navigate to run detail
  - [ ] `e2e/features/run-detail.feature`:
    - Scenario: See stage stepper progression
    - Scenario: Click stage to view artifacts in carousel
    - Scenario: Pause and resume pipeline
    - Scenario: Copy payload from JSON viewer

## Dev Notes

### Page → Component Composition

```
DashboardPage
├── SidebarLayout (template)
│   ├── RunListItem[] (molecule, virtualized)
│   ├── CommandPalette (organism)
│   └── TriggerRunForm in Dialog/Drawer
│
RunDetailPage
├── RunDetailLayout (template)
│   ├── StageStepperBar (organism)
│   │   └── StageStep[] (molecule)
│   ├── DocumentCarousel (organism, Shadcn Tabs)
│   │   ├── JsonPayloadViewer (molecule)
│   │   └── MarkdownViewer (molecule)
│   ├── EventFeed (organism, from 25-2)
│   │   └── EventCard[] (molecule)
│   └── PauseResumeButton (molecule, AlertDialog)
```

### Prefetch on Hover (Vercel `bundle-preload`)

Run list items trigger `queryClient.prefetchQuery()` on pointer-enter so run detail loads instantly on click.

### References

- [Source: ux-design-specification.md#Screen 1-4] — all screen wireframes
- [Source: ux-design-specification.md#Complete Shadcn Component Registry] — component mapping
- [Source: frontend-architecture.md#Project Structure] — file locations
- [Source: frontend/CLAUDE.md] — all rules apply
