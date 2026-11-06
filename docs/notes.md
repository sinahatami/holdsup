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

## P1.2 Tooling

Plan: lefthook (pre-commit ruff/eslint/prettier on staged files, commit-msg commitlint, pre-push mypy + `make test`), commitlint with `@commitlint/config-conventional`, release-please (single version for the repo), Renovate (grouped weekly). `make setup` installs the hooks.

Config files:
- `lefthook.yml`: hooks above. Installed by `make setup` (`pnpm exec lefthook install`). Skip once with `LEFTHOOK=0 git commit ...` (avoid).
- `commitlint.config.mjs`: Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`, `ci:` ...).
- `release-please-config.json` + `.release-please-manifest.json`: one `simple` release for the whole repo at `.`, tags `vX.Y.Z`, writes `CHANGELOG.md`, and bumps the version in `package.json`, `apps/web/package.json`, and `apps/api/pyproject.toml`. Starts at 0.0.0; minor bumps for features before 1.0. The GitHub Action that runs it comes with CI (P1.3/P5.2).
- `renovate.json`: weekly (Monday before 6am UTC), pinned versions, 3-day minimum release age, groups: Python, web minor/patch, GitHub Actions; web majors separate; weekly lockfile maintenance. The human must install the Renovate GitHub App on the repo.

Choices:
- Tailwind pinned to 4.3.4, not 4.3.5: 4.3.5 was published today and pnpm 12's default `minimumReleaseAge` (1 day) rejects it. The lockfile was rebuilt without the exemptions pnpm had added.
- ESLint stays on 9.39.5 (pnpm marks it deprecated): eslint-plugin-react, -jsx-a11y and -import (via eslint-config-next 16.4.5) don't declare ESLint 10 support.
- `lefthook` is allowed to run its postinstall in `pnpm-workspace.yaml` (`allowBuilds`).

Result: `git commit -m "updated some stuff"` is rejected by commitlint (2 problems: subject-empty, type-empty); conventional messages pass. Lint and tests green.

## P1.3 CI

Plan: `.github/workflows/ci.yml` (quality job = `make lint`; unit-tests job = `make test` with pytest-cov XML + Vitest v8 coverage, uploaded as an artifact), `gitleaks.yml` (PRs, main, weekly), `codeql.yml` (python, javascript-typescript, actions; PRs, main, weekly). Actions pinned to current majors (checkout v7, setup-node v7, setup-uv v7, pnpm/action-setup v6, codeql-action v4, gitleaks-action v3, upload-artifact v7); Renovate keeps them current.

Choices:
- `make test` now enforces backend coverage ≥ 85% (`--cov-fail-under=85`) and runs Vitest with `--coverage` (new dev dep `@vitest/coverage-v8`, D013).
- gitleaks-action is free for personal accounts; an organisation would need a `GITLEAKS_LICENSE` secret.

Branch protection (human, GitHub → Settings → Branches → Add rule for `main`):
1. Require a pull request before merging (0 approvals is fine for a solo repo); allow squash merging only (Settings → General → Pull Requests) and use the PR title as the commit message.
2. Require status checks to pass, and require branches to be up to date. Required checks: `Quality (ruff, mypy, eslint, tsc, prettier)`, `Unit tests with coverage`, `gitleaks`, `CodeQL (python)`, `CodeQL (javascript-typescript)`, `CodeQL (actions)`. They appear in the picker after the first CI run.
3. Block force pushes and deletions; include administrators.
4. Settings → Code security: enable CodeQL alerts view, secret scanning, and push protection.

Status: workflows committed and the branch is pushed; P1.3 is NOT ticked. Its "Done when" (a PR runs all jobs green) needs a pull request, and `gh` is not installed here. Waiting for the human to open the PR and report the CI result.
