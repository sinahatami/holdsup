# HoldsUp — Working notes

## P1.1 Monorepo skeleton

Plan:
- Root: pnpm workspace (`apps/web`), uv workspace (`apps/api`), `Makefile`, `.env.example`, `.nvmrc` (26), `.python-version` (3.13), `engines` in both package.json files, Prettier.
- `apps/api`: FastAPI app factory, `GET /v1/health` → `{"status":"ok"}`, pydantic-settings config, pytest test.
- `apps/web`: create-next-app 16.4.5, React 19.3.1, Tailwind 4.3.5, shadcn/ui on Base UI (`base-nova` style, RTL on), home page from `src/lib/strings.ts`, Vitest + RTL placeholder test.
- Placeholders: `packages/catalog` (VERSION 0.1.0), `ml/`, `eval/` (VERSION 0.1.0).

Choices made (spec ambiguous or tools moved):
- TypeScript pinned to 5.9.3, not 7.0.x: the scaffold and eslint-config-next target 5.x; revisit when typescript-eslint supports 7.
- ESLint pinned to 9.39.5 (scaffold default; eslint-config-next 16.4 flat config).
- `shadcn init -b base` alone produced the Radix `new-york` style; `-b base -p nova` gives `base-nova` with `@base-ui/react`.
- shadcn's new `cn` package (by shadcn) replaces clsx + tailwind-merge.
- `typecheck` runs `next typegen` first, because `LayoutProps` is a generated global.
- `make lint` runs `prettier --check .` from the root; Markdown and `docs/` are excluded from Prettier.
- Starlette warns that `TestClient` with `httpx` is deprecated in favour of `httpx2`. Kept `httpx` (it is the spec's HTTP client); revisit in P1.2/Renovate.
- `make setup` does not install lefthook hooks yet; that is P1.2.
- `next dev` re-creates `apps/web/AGENTS.md`, so it is committed.
- No `/v1` route for the web yet; the home page is static text.

Result: `make setup && make dev` serves `GET /v1/health` → `{"status":"ok"}` and the home page renders "HoldsUp / Every number has a denominator."; `make lint` and `make test` green (2 pytest, 1 vitest).
