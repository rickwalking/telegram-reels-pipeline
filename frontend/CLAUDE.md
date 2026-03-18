# Frontend — Pipeline Dashboard

React SPA built with Vite, TypeScript, TanStack Router/Query, Shadcn/ui, and Tailwind CSS v4.

## Commands

```bash
npm run dev          # Start dev server (proxies /api -> localhost:8000)
npm run build        # Type-check + production build
npm run typecheck    # TypeScript only
npm run test         # Vitest (run once)
npm run test:watch   # Vitest (watch mode)
npm run lint         # ESLint
```

## Architecture

Atomic Design with strict layering:

| Layer | Path | Purpose |
|-------|------|---------|
| Atoms | `src/core/atoms/` | Smallest UI primitives (StatusBadge, etc.) |
| Molecules | `src/core/molecules/` | Composed atoms (search bars, form fields) |
| Organisms | `src/core/organisms/` | Complex UI sections (run list, stage timeline) |
| Templates | `src/core/templates/` | Page layout skeletons |
| Core Hooks | `src/core/hooks/` | Reusable hooks (useMountEffect, useBreakpoint) |
| App | `src/app/` | Pages, providers, routes, app-level hooks |
| Services | `src/services/` | Interfaces, implementations, fakes |
| Schemas | `src/schemas/` | Zod validation schemas for API responses |
| Utils | `src/utils/` | Pure utility functions |
| Components/UI | `src/components/ui/` | Shadcn/ui generated components (do not edit) |

## Coding Rules

- **No `any` type** — strict TypeScript everywhere
- **No `useEffect`** — use `useMountEffect`, `useSyncExternalStore`, or TanStack Query
- **No barrel exports** — import directly from the source file
- **Max 200 lines per component file**
- **Max 3 function arguments** — use interface/object for more
- **Max 20 lines per function**
- **No nested `if`** — use early returns or dictionary dispatch
- **Interfaces over abstract classes** — always use TypeScript interfaces
- **Frozen/readonly types** — use `readonly` on all interface properties
- **Fakes over mocks** — use fake service implementations for testing
- **AAA test pattern** — comment `// Arrange`, `// Act`, `// Assert` in every test
- **Gherkin feature files** — every atom/molecule gets a `.feature` file
- **5-file atom structure** — `feature`, `interface`, `component`, `test`, (storybook later)

## Service Pattern

All external I/O goes through service interfaces:
1. Define interface in `services/interfaces/`
2. Create real implementation in `services/implementations/`
3. Create fake for tests in `services/fakes/`
4. Inject via `ServiceProvider` context

## Theme

- Dark/light via CSS class on `<html>` + localStorage
- Flicker prevention via inline `<script>` in `index.html`
- Custom status color tokens: `--status-{pending,active,completed,failed,paused}`

## Path Alias

`@/*` maps to `src/*` — configured in both `tsconfig.app.json` and `vite.config.ts`.
