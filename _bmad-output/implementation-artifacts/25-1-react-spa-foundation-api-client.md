# Story 25.1: React SPA Foundation & API Client

Status: ready-for-dev

## Story

As a UI Developer,
I want to set up the base React SPA and API client,
So that I have a clean foundation to build the dashboard views.

## Acceptance Criteria

1. **Given** a new frontend project, **When** scaffolded, **Then** it must use React 19+ with TypeScript, Vite for bundling, and Tailwind CSS for styling, **And** it must be located at `frontend/` in the project root.

2. **Given** the React app, **When** I navigate to `/`, **Then** it must render a Dashboard view with a list of pipeline runs, **And** clicking a run must navigate to `/runs/{pipeline_run_id}` (Run Detail view).

3. **Given** the API client, **When** it calls `GET /api/runs`, **Then** it must receive typed responses matching `PipelineRunListItemDTO`, **And** handle network errors gracefully with user-visible feedback.

4. **Given** the frontend dev server, **When** I run `npm run dev`, **Then** it must proxy API requests to the FastAPI backend, **And** hot module replacement must work.

## Tasks / Subtasks

- [ ] **Task 1: Scaffold React project** (AC: #1)
  - [ ] Run `npm create vite@latest frontend -- --template react-ts`
  - [ ] Install core deps: `react-router-dom`, `tailwindcss`, `@headlessui/react`
  - [ ] Install dev deps: `@types/react`, `eslint`, `prettier`
  - [ ] Configure Tailwind CSS with project design tokens
  - [ ] Configure Vite proxy for `/api` → FastAPI backend

- [ ] **Task 2: Create routing structure** (AC: #2)
  - [ ] Create `frontend/src/routes/` directory
  - [ ] Define routes:
    - `/` → `DashboardPage` (list of runs)
    - `/runs/:pipelineRunId` → `RunDetailPage` (single run detail)
    - `/runs/:pipelineRunId/dvr` → `PipelineDvrPage` (time-travel view)
  - [ ] Create `AppLayout` component with navigation header
  - [ ] Add loading and error boundary components

- [ ] **Task 3: Create typed API client** (AC: #3)
  - [ ] Create `frontend/src/api/pipeline_api_client.ts`
  - [ ] Define TypeScript interfaces matching backend DTOs:
    - `PipelineRunListItem`
    - `PipelineRunDetail`
    - `PipelineEventItem`
    - `ErrorResponse`
  - [ ] Functions: `fetchPipelineRuns()`, `fetchPipelineRunDetail(id)`, `triggerPipelineRun(payload)`
  - [ ] Use `fetch` with proper error handling (no axios — keep it simple)
  - [ ] Generic `apiRequest<T>()` helper with typed responses

- [ ] **Task 4: Create Dashboard page** (AC: #2, #3)
  - [ ] Create `frontend/src/pages/DashboardPage.tsx`
  - [ ] Fetch and display list of pipeline runs
  - [ ] Show: run ID, YouTube URL (truncated), status badge, stage, created at
  - [ ] Color-coded status badges: green (completed), blue (in progress), yellow (pending), red (failed)
  - [ ] Click row → navigate to Run Detail page
  - [ ] "New Run" button (triggers modal/form)

- [ ] **Task 5: Create Run Detail page (skeleton)** (AC: #2)
  - [ ] Create `frontend/src/pages/RunDetailPage.tsx`
  - [ ] Fetch run detail by ID from route params
  - [ ] Display: current stage, status, stage progression indicator
  - [ ] Placeholder sections for: SSE stream (Story 25-2), DVR (Story 25-3), Document Carousel (Story 25-4)

- [ ] **Task 6: Create design system components** (AC: #1)
  - [ ] `StatusBadge` — color-coded status display
  - [ ] `StageProgressBar` — visual pipeline stage progression
  - [ ] `LoadingSpinner` — async loading state
  - [ ] `ErrorAlert` — API error display
  - [ ] `PageHeader` — consistent page titles and navigation
  - [ ] All components use Tailwind utility classes

- [ ] **Task 7: Configure build and deployment** (AC: #4)
  - [ ] `vite.config.ts` with API proxy configuration
  - [ ] `npm run build` produces static assets in `frontend/dist/`
  - [ ] FastAPI serves `frontend/dist/` as static files in production
  - [ ] Create `StaticFileMiddleware` or mount in FastAPI for SPA routing

- [ ] **Task 8: Write frontend tests** (AC: #2, #3)
  - [ ] Install vitest + @testing-library/react
  - [ ] `tests/DashboardPage.test.tsx`: renders run list, handles empty state
  - [ ] `tests/pipeline_api_client.test.ts`: API client typed responses, error handling
  - [ ] `tests/StatusBadge.test.tsx`: correct colors for each status

## Dev Notes

### Frontend Architecture

```
frontend/
├── src/
│   ├── api/                    # API client and TypeScript interfaces
│   │   └── pipeline_api_client.ts
│   ├── components/             # Reusable UI components
│   │   ├── StatusBadge.tsx
│   │   ├── StageProgressBar.tsx
│   │   └── ...
│   ├── pages/                  # Page-level components
│   │   ├── DashboardPage.tsx
│   │   ├── RunDetailPage.tsx
│   │   └── PipelineDvrPage.tsx
│   ├── hooks/                  # Custom React hooks
│   │   └── use_pipeline_sse.ts (Story 25-2)
│   ├── routes/                 # React Router config
│   │   └── index.tsx
│   └── App.tsx
├── index.html
├── vite.config.ts
├── tailwind.config.js
├── tsconfig.json
└── package.json
```

### API Proxy Configuration

During development, Vite proxies API calls to FastAPI:

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    }
  }
})
```

In production, FastAPI serves the built SPA as static files.

### TypeScript DTO Alignment

TypeScript interfaces must mirror the Python Pydantic DTOs exactly. Any change to a backend DTO requires a corresponding frontend type update. Consider generating types from OpenAPI spec in the future.

### References

- [Source: prd.md#User Success] — Visual engagement, observability
- [Source: prd.md#MVP Feature Set] — React SPA frontend with SSE
- [Source: epics.md#Story 4.1] — React SPA Foundation & API Client
- [Source: implementation-readiness-report] — UX: basic, intuitive UI using modern web practices
