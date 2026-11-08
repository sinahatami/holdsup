# Components: atomic design

Each layer may import only from layers below it. ESLint enforces this
(`no-restricted-imports` in `eslint.config.mjs`).

| Layer        | What belongs here                                                               | Examples                                        |
| ------------ | ------------------------------------------------------------------------------- | ----------------------------------------------- |
| `ui/`        | Vendored shadcn/Base UI primitives. Leave as generated.                         | `button`                                        |
| `atoms/`     | One element or one style: no layout of other components, no data fetching.      | `verdict-badge`, `eyebrow`, `logo`, `pill`      |
| `molecules/` | A few atoms forming one small unit with one job.                                | `field-list`, `trace-step`, `theme-toggle`      |
| `organisms/` | A self-contained region of a page made of molecules and atoms.                  | `check-form`, `receipt`, `trace`, `site-header` |
| `templates/` | Page layout with slots and no data of its own.                                  | `page-shell`, `check-template`                  |
| `app/`       | Pages: routes that fetch or bind data and fill a template (Next.js App Router). | `app/page.tsx`, `app/check/[id]/check-live.tsx` |

Logic lives outside `components/`:

- `src/hooks/` holds stateful React logic (`use-check`, `use-submit-check`, `use-theme`, `use-custom-cursor`).
- `src/lib/` holds framework-free code: the API client factory (`createApiClient`), the theme store, the trace reducer, formatting, and route paths. It never imports components or hooks.
- All interface text lives in `src/lib/strings.ts`.

Rules of thumb:

- Components are presentational and take data as props. Data comes from a page or a hook.
- Pick visuals from lookup tables keyed by state (`verdictIcon`, the trace status `LOOK`), not `if`/ternary chains. A new state is then one new entry.
- Put shared class sets in `cva` variants (`pill`, `PageShell`'s `layout`) instead of copying class strings.
- Import each file directly. There are no barrel `index.ts` files, so the `"use client"` boundaries stay explicit.
