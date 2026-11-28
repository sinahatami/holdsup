# Deploying HoldsUp

The site runs on three free tiers: the web app on **Vercel**, the API as a Docker container on **Google Cloud Run**, and Postgres with pgvector on **Neon**. You set every key on the platform that uses it. Keys never go in the repository, a commit or an image.

Order: database, then API, then web. The web build reads the gallery from the API, and the API refuses to start without the site's address.

## 0. One decision first, one thing to know

**Which database the site uses.** The simplest safe choice is a Neon **branch** of the database you develop against, called `live` (Neon names your first branch `production`; renaming it `dev` in the branch's settings avoids mixing the two up, and changes no connection string). It starts with everything already there (catalog, the 20 featured checks, the ledger). After that, local runs (`make dev`, seeding, evals) stay on the development branch and never touch live data. Sharing one database also works, but then everything you do locally shows up on the site.

**The smoke run shares Groq's quota on Sundays.** `eval.yml` runs 30 claims once a week, on Sunday at 03:43 UTC, with the `GROQ_API_KEY` GitHub secret. Pull requests replay saved replies, so they rarely ask a model. If that key belongs to the same Groq account as the API's key on Cloud Run, the Sunday run uses most of that day's Groq quota (about 25 new checks) before visitors arrive. After Groq, checks fall back to Cerebras (5 a minute) and then to Mistral, which extracts claims less well. When every provider is out, the site says "HoldsUp is at capacity" and offers the gallery. Ledger hits and gallery receipts never use a model. A run you start by hand (Run workflow) spends the same quota on the day you start it.

## 1. Database (Neon)

1. In the Neon console, create a branch `live` from your development branch, with **Branch data and schema** and auto-delete set to **Never** (the default may delete it after a day).
2. **Give `live` its own password.** A new branch copies the roles of its parent with their passwords, so the address in your `.env` would reach the site's data by changing only the host. On the `live` branch open **Roles**, then **Reset password** for the database's owner (for example `holdsup_owner`). Only `live` changes; your development branch keeps its password.
3. Copy the `live` connection string (**Connect**, branch `live`). Paste it as Neon shows it (`postgresql://…neon.tech/neondb?sslmode=require`). The API converts it to asyncpg with SSL.
4. Check the branch is at the latest migration (`0007`). A branch of an up-to-date database already is. Otherwise:

   ```bash
   make db-migrate DATABASE_URL='<live branch url>'
   ```

   Put the address after the target, as here. Written before `make` (`DATABASE_URL=… make …`), it loses to the one in `.env`.

## 2. API (Google Cloud Run)

Cloud Run runs the API's Docker image and stops it when nobody is using it. Its monthly free tier (requests, CPU time and memory time) is far more than this site needs, and Artifact Registry stores up to 0.5 GB of images for free (one image is about 0.2 GB compressed; the cleanup policy below keeps only the newest two). Google asks for a card when you set up billing. Nothing is charged within those limits, and the budget alert in step 1 tells you before anything is.

The first visit after a quiet spell waits a few seconds while the container starts and loads its models.

### One-time setup

1. In the [Google Cloud console](https://console.cloud.google.com), create a project (for example `holdsup`) and note its **project ID**. Link a billing account when asked. Then open **Billing → Budgets & alerts** and create a budget of 1 (in your currency) with email alerts.
2. Install the [gcloud CLI](https://cloud.google.com/sdk/docs/install) and Docker, then run these once. Pick the region next to your Neon database, and use it everywhere below. A check lookup makes several round trips to the database, so an ocean between them adds about half a second to every page that reads data (measured: 0.6 s per lookup with the API in Belgium and the database in Virginia).

   | Neon region | Cloud Run region | Vercel function region |
   | --- | --- | --- |
   | AWS us-east-1 (N. Virginia), Neon's default | `us-east4` (N. Virginia) | `iad1` |
   | AWS us-east-2 (Ohio) | `us-east5` (Columbus) | `cle1` |
   | AWS eu-central-1 (Frankfurt) | `europe-west4` (Netherlands) | `fra1` |

   All three Cloud Run regions are Tier 1, with the same free tier.

   ```bash
   gcloud auth login
   gcloud config set project <project id>
   gcloud services enable run.googleapis.com artifactregistry.googleapis.com
   gcloud artifacts repositories create holdsup --repository-format=docker --location=<region>
   gcloud artifacts repositories set-cleanup-policies holdsup --location=<region> --policy=apps/api/cloudrun/cleanup-policy.json
   gcloud auth configure-docker <region>-docker.pkg.dev
   ```

3. Build the image from an up-to-date `main` and push it:

   ```bash
   make api-image GCP_PROJECT=<project id> GCP_REGION=<region>
   ```

   This writes committed files only (never `.env` or local edits) into `.cache/api-<commit>`, with the commit stamped in for receipts, builds the image from that folder and pushes it as `<region>-docker.pkg.dev/<project id>/holdsup/api:<commit>`.

4. In the console, open **Cloud Run → Deploy container → Service** and fill in:

   | Field | Value |
   | --- | --- |
   | Container image URL | **Select** → `holdsup` → `api` → the tag you just pushed |
   | Service name | `holdsup-api` |
   | Region | your region |
   | Authentication | **Allow public access** (unauthenticated invocations) |
   | Billing | **Request-based** |
   | Scaling | minimum **0**, maximum **1** instance (the rate limits live in one process) |
   | Container → Resources | memory **2 GiB**, CPU **2** |
   | Container → Variables & secrets | the table below |

   | Name | Value |
   | --- | --- |
   | `DATABASE_URL` | the connection string of the Neon branch the site uses |
   | `GROQ_API_KEY` | Groq key |
   | `CEREBRAS_API_KEY` | Cerebras key (second host of the same model) |
   | `MISTRAL_API_KEY` | Mistral key |
   | `OPENROUTER_API_KEY` | OpenRouter key (no credits) |
   | `WEB_ORIGIN` | the site's exact origin, e.g. `https://holdsup.vercel.app` (no trailing slash) |
   | `TRUSTED_PROXIES` | `1` to start with (step 6) |

   Leave the container port at 8080: Cloud Run passes it to the image as `PORT`. Never add `GEMINI_API_KEY`: Gemini is for offline evaluation only, and the router refuses it for live calls anyway. `APP_ENV` is `production` in the image already. Then click **Create**.

5. Cloud Run shows the service's address, `https://holdsup-api-<…>.run.app`. If a setting is missing, the API refuses to start and the service's **Logs** tab names each one (`Refusing to start in production: …`). When it runs:

   ```bash
   curl https://holdsup-api-<…>.run.app/v1/health
   ```

   should print `{"status":"ok"}`.

6. **Set `TRUSTED_PROXIES` from the logs.** After the first check from the site, search the service's **Logs** for `client_address`. Its `forwarded_entries` field is the number of proxies in front of the API (browsers send none). If it is more than 1, set `TRUSTED_PROXIES` to that number (**Edit & deploy new revision → Variables & secrets**). If it is 0, every visitor shares one rate limit, so tell me. A visitor behind their own proxy can show a higher count, so take the smallest one you see. Setting the value too high lets callers choose their own address. Setting it too low only puts everyone in one shared limit.

## 3. Web (Vercel)

1. Import the GitHub repository and set **Root Directory** to `apps/web`. `vercel.json` there sets Next.js, `pnpm install --frozen-lockfile`, and the region the server-side code runs in: `iad1` (Washington, D.C.), next to the database. If yours is elsewhere, change `regions` there to the Vercel region in the table in section 2. The web app needs Node 26 (`engines` in `package.json`); if the build log rejects the Node version, set **Settings → Build and Deployment → Node.js Version** to 26.x.
2. Add these environment variables for Production:

   | Name | Value |
   | --- | --- |
   | `NEXT_PUBLIC_API_URL` | the Cloud Run address (the browser calls it) |
   | `HOLDSUP_API_URL` | the same address (server-side reads: gallery, catalog) |

   `NEXT_PUBLIC_SITE_URL` is only needed if the site uses a custom domain. On Vercel, share-picture links are worked out from the deployment. `NEXT_PUBLIC_*` values are built into the pages, so redeploy after changing one.

   To list the site in Google: in [Search Console](https://search.google.com/search-console) add a **URL prefix** property for the site's address, pick the **HTML tag** check, and copy only the `content` value into a `GOOGLE_SITE_VERIFICATION` variable (Production). Redeploy, click **Verify**, then submit `sitemap.xml` under **Sitemaps**.
3. Deploy. If the home page shows an empty gallery, the API was still starting during the build: redeploy once it answers.
4. If the final address differs from the `WEB_ORIGIN` you set on Cloud Run, update it there (**Edit & deploy new revision**). Otherwise browsers get CORS errors. Preview deployments have other addresses, so they can show pages but can't run checks.

## 4. GitHub

- Repository **secret** `DATABASE_URL` = the connection string of the Neon branch the site uses. Each automatic API deploy (`cd.yml`) first runs the database migrations against it. The daily claim watch (`watch.yml`) uses no model and marks or updates checks whose figures were revised. Its backfill (section 5) also reads `GROQ_API_KEY`, `MISTRAL_API_KEY` and `OPENROUTER_API_KEY`, the development keys the smoke evaluation uses.

Cloud Run wakes on the first request, so nothing needs to keep the API awake.

### Automatic API deploys

Vercel deploys the web app from `main` by itself. With this one-time setup, the API follows: after a merge to `main` that changes the API, the **API image** workflow builds and starts the image as usual, and if that passes it runs `cd.yml`, which brings the site's database up to that commit's migrations (`make db-migrate`) and then deploys the commit with `make deploy-api`. Without it, the deploy job is skipped and you deploy by hand (section 5).

GitHub holds no Google key. Each run trades its own short-lived GitHub token for one of a service account, `holdsup-deployer`. That account can only push images to the `holdsup` repository and deploy `holdsup-api`, and Google accepts the trade only from `cd.yml` on this repository's `main`. The service's settings and API keys stay on Cloud Run and never pass through GitHub.

1. Run once, with `gcloud` signed in as the project's owner and `gh` signed in to the repository:

   ```bash
   make deploy-setup GCP_PROJECT=<project id> GCP_REGION=<region>
   ```

   It enables Google's token exchange, creates the Workload Identity pool `github` with its provider `holdsup`, creates the service account with those three permissions, and sets four repository **variables** (`GCP_PROJECT`, `GCP_REGION`, `GCP_DEPLOY_SERVICE_ACCOUNT`, `GCP_WORKLOAD_IDENTITY_PROVIDER`). They are variables, not secrets: none of them is a key. Running it again is safe.
2. On GitHub, open **Actions → Deploy API → Run workflow** on `main`. It deploys `main`'s latest commit, then checks that the service runs that commit's image, that the new revision takes all traffic, and that `/v1/health` answers.

## 5. After launch

- Run the claim-watch backfill once Groq's daily quota has reset, so checks made before plans were stored are watched too. It makes about one plan call per watched claim and keeps only plans that reproduce the figures. On GitHub, open **Actions → Claim watch → Run workflow**, tick **backfill** and run it. It uses the repository's `DATABASE_URL` and provider key secrets (the same names as in `eval.yml`), so the site's address never leaves GitHub. To run it from your machine instead, with your `.env` keys:

  ```bash
  make watch ARGS=--backfill DATABASE_URL='<the site database url>'
  ```

- To deploy a new version, merge to `main`. Vercel deploys the web app by itself, and so does `cd.yml` for the API once section 4's automatic deploys are set up. To deploy the API by hand instead (or before that setup), from an up-to-date `main`:

  ```bash
  make deploy-api GCP_PROJECT=<project id> GCP_REGION=<region>
  ```

  It builds and pushes the image, then switches the service to it. The settings from step 2.4 carry over. If the commit adds a migration, run `make db-migrate DATABASE_URL='<the site database url>'` first, as `cd.yml` does.
- To roll back the API, open the service's **Revisions** tab and send all traffic to an earlier revision. Traffic then stays pinned there: the next deploy creates a revision, but `cd.yml` reports that it gets no traffic. When the fix is in, send all traffic to the latest revision again under **Manage traffic**, or run `gcloud run services update-traffic holdsup-api --to-latest --region <region>`.
- To move the API to another region (for example next to the database), set up the new one before taking the old one down:
  1. Run the three `gcloud artifacts …` commands from section 2, step 2, with the new region, then `make api-image GCP_PROJECT=<project id> GCP_REGION=<new region>`.
  2. Create the service in the new region as in section 2, step 4: same name, settings and variables (including the `TRUSTED_PROXIES` value you settled on). Check `/v1/health` at its new address.
  3. In Vercel, set `NEXT_PUBLIC_API_URL` and `HOLDSUP_API_URL` to the new address and redeploy. Check that a gallery receipt opens.
  4. Delete the old service, then the old image repository (`gcloud artifacts repositories delete holdsup --location=<old region>`). Images kept in two regions would pass the 0.5 GB of free storage.
  5. After the first check through the new service, look at `client_address` in its logs again (section 2, step 6).

## 6. Telegram bot (optional)

The bot lives in the API (`apps/api/holdsup/telegram/`). Telegram posts each message to `/v1/telegram/webhook`, and the API answers in the chat. The webhook stays off (404) until both variables below are set. Every new claim sent to the bot spends the same daily model quota as the site; claims checked before cost nothing.

1. In Telegram, open [@BotFather](https://t.me/BotFather) and send `/newbot`. Give it a name (`HoldsUp`) and a username ending in `bot`. BotFather replies with the bot's **token**. Then, for that bot:
   - `/setdescription` and `/setabouttext`: one line on what it does, for example "Checks the numbers in a claim against official statistics."
   - `/setcommands`: `start - What HoldsUp is` and `help - How to use it`.
   - In the bot's settings, set its privacy policy to `https://holdsup.vercel.app/privacy` if BotFather offers it.
2. Make a second bot the same way for development (for example `HoldsUpDevBot`). Put its token in `.env` as `TELEGRAM_BOT_TOKEN` and run `make telegram-poll`: the bot then answers from your machine, with no webhook. Never use the production bot's token here.
3. Make the webhook secret: `openssl rand -hex 32`.
4. In the Cloud Run console, open the service → **Edit & deploy new revision**:
   - **Variables & secrets**: add `TELEGRAM_BOT_TOKEN` (the production bot's token) and `TELEGRAM_WEBHOOK_SECRET` (step 3). A malformed value (a stray space or line break) makes the API refuse to start, and the **Logs** tab says which one.
   - **Settings → Request timeout**: keep it at 300 seconds. The API holds Telegram's request open until the answer is sent, because Cloud Run gives the container CPU only while a request is open; a slow check takes up to about two and a half minutes.

   Deploys from `cd.yml` keep these variables.
5. Point Telegram at the API, typing the production token and the secret when asked (they are hidden, and a pasted line break is removed):

   ```bash
   make telegram-webhook ARGS="set https://holdsup-api-<…>.run.app --ask"
   ```

   It prints the webhook's state. `url` should end in `/v1/telegram/webhook`.
6. Send the bot `/start`, then a claim from the home page's gallery (checked before, so no quota). Then run `make telegram-webhook ARGS="info --ask"`: `pending_update_count` should be 0, with no `last_error_message`.

To turn the bot off, run `make telegram-webhook ARGS="delete --ask"` and remove `TELEGRAM_BOT_TOKEN` from the service.

## What CI checks

`.github/workflows/image.yml` runs on every pull request that touches the API or the catalog. It builds the image from `make api-bundle` the way a deploy does, then checks two things. With incomplete production settings, the image must refuse to start. With complete (dummy) settings, it must serve `/v1/health` and the catalog. `make docker-api` builds the same image locally and runs it as development. On a push to `main` the same workflow then deploys the commit (`cd.yml`, section 4), so an image that fails these checks is never deployed.
