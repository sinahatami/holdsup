# Deploying HoldsUp

The site runs on three free tiers: the web app on **Vercel**, the API as a Docker **Hugging Face Space**, and Postgres with pgvector on **Neon**. You set every key on the platform that uses it. Keys never go in the repository, a commit or a Space file.

Order: database, then API, then web. The web build reads the gallery from the API, and the API refuses to start without the site's address.

## 0. One decision first, one thing to know

**Which database the site uses.** The simplest safe choice is a Neon **branch** of the database you develop against, called `production`. It starts with everything already there (catalog, the 20 featured checks, the ledger). After that, local runs (`make dev`, seeding, evals) stay on the development branch and never touch live data. Sharing one database also works, but then everything you do locally shows up on the site.

**The smoke run shares Groq's quota on Sundays.** `eval.yml` runs 30 claims once a week, on Sunday at 03:43 UTC, with the `GROQ_API_KEY` GitHub secret. Pull requests replay saved replies, so they rarely ask a model. If that key belongs to the same Groq account as the Space's key, the Sunday run uses most of that day's Groq quota (about 25 new checks) before visitors arrive. After Groq, checks fall back to Cerebras (5 a minute) and then to Mistral, which extracts claims less well. When every provider is out, the site says "HoldsUp is at capacity" and offers the gallery. Ledger hits and gallery receipts never use a model. A run you start by hand (Run workflow) spends the same quota on the day you start it.

## 1. Database (Neon)

1. In the Neon console, create a branch `production` from your development branch and copy its connection string. Paste it as Neon shows it (`postgresql://…neon.tech/neondb?sslmode=require`). The API converts it to asyncpg with SSL.
2. Check the branch is at the latest migration (`0007`). A branch of an up-to-date database already is. Otherwise:

   ```bash
   make db-migrate DATABASE_URL='<production url>'
   ```

   Put the address after the target, as here. Written before `make` (`DATABASE_URL=… make …`), it loses to the one in `.env`.

## 2. API (Hugging Face Space)

1. Create a Space: SDK **Docker**, blank template, free CPU hardware, public. Its address is `https://<owner>-<space>.hf.space`.
2. In the Space's **Settings → Variables and secrets**, add:

   | Name | Kind | Value |
   | --- | --- | --- |
   | `DATABASE_URL` | secret | the production connection string |
   | `GROQ_API_KEY` | secret | Groq key |
   | `CEREBRAS_API_KEY` | secret | Cerebras key (second host of the same model) |
   | `MISTRAL_API_KEY` | secret | Mistral key |
   | `OPENROUTER_API_KEY` | secret | OpenRouter key (no credits) |
   | `WEB_ORIGIN` | variable | the site's exact origin, e.g. `https://holdsup.vercel.app` (no trailing slash) |
   | `TRUSTED_PROXIES` | variable | `1` to start with (step 6) |

   Never add `GEMINI_API_KEY`: Gemini is for offline evaluation only, and the router refuses it for live calls anyway. `APP_ENV` is `production` in the image already.

3. Write the Space's files from an up-to-date `main`:

   ```bash
   make space-bundle
   ```

   This puts committed files only (never `.env` or local edits) into `.cache/space-<commit>`: the API, the catalog, the eval reports, a `Dockerfile` at the root with the commit stamped in for receipts, and the Space card.

4. Push that folder to the Space. Each deploy replaces the Space's history, because the Space is a build output and the repository is the source:

   ```bash
   cd .cache/space-<commit>
   git init -b main && git add -A && git commit -m "Deploy <commit>"
   git push --force https://huggingface.co/spaces/<owner>/<space> main
   ```

   Git asks for your Hugging Face username and a token with **write** access (Settings → Access Tokens) as the password.

5. Watch the build in the Space's **Logs** tab. If a setting is missing, the API refuses to start and the log names each one (`Refusing to start in production: …`). When it runs:

   ```bash
   curl https://<owner>-<space>.hf.space/v1/health
   ```

   should print `{"status":"ok"}`, and `/v1/status` lists each provider as ready.

6. **Set `TRUSTED_PROXIES` from the logs.** After the first check from the site, search the Space log for `client_address`. Its `forwarded_entries` field is the number of proxies in front of the API (browsers send none). If it is more than 1, set `TRUSTED_PROXIES` to that number and restart the Space. If it is 0, every visitor shares one rate limit, so tell me. A visitor behind their own proxy can show a higher count, so take the smallest one you see. Setting the value too high lets callers choose their own address. Setting it too low only puts everyone in one shared limit.

## 3. Web (Vercel)

1. Import the GitHub repository and set **Root Directory** to `apps/web`. `vercel.json` there sets Next.js and `pnpm install --frozen-lockfile`. Use Node 26 (`.nvmrc`) if Vercel offers it.
2. Add these environment variables for Production:

   | Name | Value |
   | --- | --- |
   | `NEXT_PUBLIC_API_URL` | `https://<owner>-<space>.hf.space` (the browser calls it) |
   | `HOLDSUP_API_URL` | the same address (server-side reads: gallery, catalog, eval) |

   `NEXT_PUBLIC_SITE_URL` is only needed if the site uses a custom domain. On Vercel, share-picture links are worked out from the deployment. `NEXT_PUBLIC_*` values are built into the pages, so redeploy after changing one.
3. Deploy. If the home page shows an empty gallery, the API was asleep or not up during the build: redeploy once it answers.
4. If the final address differs from the `WEB_ORIGIN` you set on the Space, update it there and restart the Space. Otherwise browsers get CORS errors. Preview deployments have other addresses, so they can show pages but can't run checks.

## 4. GitHub

- Repository **variable** `API_BASE_URL` = the Space address. The keep-alive workflow pings `/v1/health` twice a day, because Spaces sleep after about 48 hours idle.
- Repository **secret** `DATABASE_URL` = the production connection string. The daily claim watch (`watch.yml`) uses no model and marks or updates checks whose figures were revised.

## 5. After launch

- Run the claim-watch backfill against the production database once Groq's daily quota has reset. It makes about one plan call per featured claim (your `.env` keys) and keeps only plans that reproduce the figures:

  ```bash
  make watch ARGS=--backfill DATABASE_URL='<production url>'
  ```

- To deploy a new version, merge to `main`, then repeat steps 2.3 and 2.4. Vercel deploys the web app from `main` by itself.
- To roll back the API, check out the earlier commit or tag, run `make space-bundle` and push that folder the same way.

## What CI checks

`.github/workflows/image.yml` runs on every pull request that touches the API, the catalog or the reports. It builds the image from `make space-bundle` the way the Space does, then checks two things. With incomplete production settings, the image must refuse to start. With complete (dummy) settings, it must serve `/v1/health`, the catalog and the eval page. `make docker-api` builds the same image locally and runs it as development.
