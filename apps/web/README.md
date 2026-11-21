# HoldsUp web

The site: a Next.js App Router app in strict TypeScript, styled with Tailwind CSS. It renders checks from the [API](../api/README.md) and streams new ones live. The [root README](../../README.md) explains what HoldsUp does.

## Run it

From the repository root:

```bash
make dev-web     # next dev on localhost:3000 (make dev also starts the API on :8000)
make types       # regenerate src/lib/api/schema.ts after an API change
```

| Variable                   | Used for                                                                  |
| -------------------------- | ------------------------------------------------------------------------- |
| `NEXT_PUBLIC_API_URL`      | The API address the browser calls (default `http://localhost:8000`)       |
| `HOLDSUP_API_URL`          | The API address for server-side reads, if it differs from the public one  |
| `NEXT_PUBLIC_SITE_URL`     | The site's own address for share images (Vercel works it out by itself)   |
| `GOOGLE_SITE_VERIFICATION` | Search Console's HTML tag value (optional)                                |

## Pages (`src/app/`)

| Route            | Page                                                      |
| ---------------- | --------------------------------------------------------- |
| `/`              | The claim box and the gallery of featured checks          |
| `/check/[id]`    | A check: verdict, chart, framing checks and the receipt   |
| `/recent`        | Recent checks                                             |
| `/indicators`    | The indicator catalog                                     |
| `/methodology`   | How a verdict is reached, with the tolerances in use      |
| `/about`         | About the project                                         |
| `/embed/[id]`    | A check without the site frame, for an iframe             |

Pages with the site header and footer sit in the `(site)` route group, which does not change their URLs.

## Layout (`src/`)

- `components/` follows atomic design (atoms, molecules, organisms, templates). A layer imports only from the ones below it, and ESLint enforces it. See [its README](src/components/README.md).
- `hooks/` holds stateful React logic, such as `use-check`, which follows a check's event stream.
- `lib/` holds framework-free code: the API client (`lib/api/`, with types generated from the API's OpenAPI schema), formatting, the theme store and route paths.
- `lib/strings/` holds all interface text. `pages.ts` is for server-only pages and never reaches the browser.

Server components are the default; `"use client"` marks the few that need the browser. CSS uses logical properties only (`ms-`, `pe-`, `start`), never `left` or `right`.

## Tests

| Command          | What it runs                                                                                  |
| ---------------- | --------------------------------------------------------------------------------------------- |
| `make test-web`  | Vitest with React Testing Library                                                             |
| `make test-ui`   | The same tests in a browser window, rerun on save                                             |
| `make e2e`       | Playwright with axe accessibility checks, against a mocked API (`e2e/mock-server.mjs`), no keys |

CI also runs Lighthouse on a production build (`lighthouse/`) and fails on performance, accessibility or bundle-size budgets.

## Deploy

Vercel builds this folder on every push (`vercel.json`); `main` is the live site. [DEPLOY.md](../../DEPLOY.md) has the one-time setup.
