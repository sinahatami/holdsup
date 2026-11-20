# Deploying HoldsUp

The site runs on three free tiers: the web app on **Vercel**, the API as a Docker container on **Google Cloud Run**, and Postgres with pgvector on **Neon**. You set every key on the platform that uses it. Keys never go in the repository, a commit or an image.

Order: database, then API, then web. The web build reads the gallery from the API, and the API refuses to start without the site's address.

## 0. One decision first, one thing to know

**Which database the site uses.** The simplest safe choice is a Neon **branch** of the database you develop against, called `live` (Neon may already call your development branch `production`). It starts with everything already there (catalog, the 20 featured checks, the ledger). After that, local runs (`make dev`, seeding, evals) stay on the development branch and never touch live data. Sharing one database also works, but then everything you do locally shows up on the site.

**The smoke run shares Groq's quota on Sundays.** `eval.yml` runs 30 claims once a week, on Sunday at 03:43 UTC, with the `GROQ_API_KEY` GitHub secret. Pull requests replay saved replies, so they rarely ask a model. If that key belongs to the same Groq account as the API's key on Cloud Run, the Sunday run uses most of that day's Groq quota (about 25 new checks) before visitors arrive. After Groq, checks fall back to Cerebras (5 a minute) and then to Mistral, which extracts claims less well. When every provider is out, the site says "HoldsUp is at capacity" and offers the gallery. Ledger hits and gallery receipts never use a model. A run you start by hand (Run workflow) spends the same quota on the day you start it.

## 1. Database (Neon)

1. In the Neon console, create a branch `live` from your development branch, with **Branch data and schema** and auto-delete set to **Never** (the default may delete it after a day). Copy its connection string. Paste it as Neon shows it (`postgresql://…neon.tech/neondb?sslmode=require`). The API converts it to asyncpg with SSL.
2. Check the branch is at the latest migration (`0007`). A branch of an up-to-date database already is. Otherwise:

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

   should print `{"status":"ok"}`, and `/v1/status` lists each provider as ready.

6. **Set `TRUSTED_PROXIES` from the logs.** After the first check from the site, search the service's **Logs** for `client_address`. Its `forwarded_entries` field is the number of proxies in front of the API (browsers send none). If it is more than 1, set `TRUSTED_PROXIES` to that number (**Edit & deploy new revision → Variables & secrets**). If it is 0, every visitor shares one rate limit, so tell me. A visitor behind their own proxy can show a higher count, so take the smallest one you see. Setting the value too high lets callers choose their own address. Setting it too low only puts everyone in one shared limit.

## 3. Web (Vercel)

1. Import the GitHub repository and set **Root Directory** to `apps/web`. `vercel.json` there sets Next.js, `pnpm install --frozen-lockfile`, and the region the server-side code runs in: `iad1` (Washington, D.C.), next to the database. If yours is elsewhere, change `regions` there to the Vercel region in the table in section 2. The web app needs Node 26 (`engines` in `package.json`); if the build log rejects the Node version, set **Settings → Build and Deployment → Node.js Version** to 26.x.
2. Add these environment variables for Production:

   | Name | Value |
   | --- | --- |
   | `NEXT_PUBLIC_API_URL` | the Cloud Run address (the browser calls it) |
   | `HOLDSUP_API_URL` | the same address (server-side reads: gallery, catalog, eval) |

   `NEXT_PUBLIC_SITE_URL` is only needed if the site uses a custom domain. On Vercel, share-picture links are worked out from the deployment. `NEXT_PUBLIC_*` values are built into the pages, so redeploy after changing one.
3. Deploy. If the home page shows an empty gallery, the API was still starting during the build: redeploy once it answers.
4. If the final address differs from the `WEB_ORIGIN` you set on Cloud Run, update it there (**Edit & deploy new revision**). Otherwise browsers get CORS errors. Preview deployments have other addresses, so they can show pages but can't run checks.

## 4. GitHub

- Repository **secret** `DATABASE_URL` = the connection string of the Neon branch the site uses. The daily claim watch (`watch.yml`) uses no model and marks or updates checks whose figures were revised.

Cloud Run wakes on the first request, so nothing needs to keep the API awake.

## 5. After launch

- Run the claim-watch backfill against the site's database once Groq's daily quota has reset. It makes about one plan call per featured claim (your `.env` keys) and keeps only plans that reproduce the figures:

  ```bash
  make watch ARGS=--backfill DATABASE_URL='<the site database url>'
  ```

- To deploy a new version, merge to `main`, then from an up-to-date `main`:

  ```bash
  make deploy-api GCP_PROJECT=<project id> GCP_REGION=<region>
  ```

  It builds and pushes the image, then switches the service to it. The settings from step 2.4 carry over. Vercel deploys the web app from `main` by itself.
- To roll back the API, open the service's **Revisions** tab and send all traffic to an earlier revision.
- To move the API to another region (for example next to the database), set up the new one before taking the old one down:
  1. Run the three `gcloud artifacts …` commands from section 2, step 2, with the new region, then `make api-image GCP_PROJECT=<project id> GCP_REGION=<new region>`.
  2. Create the service in the new region as in section 2, step 4: same name, settings and variables (including the `TRUSTED_PROXIES` value you settled on). Check `/v1/health` and `/v1/status` at its new address.
  3. In Vercel, set `NEXT_PUBLIC_API_URL` and `HOLDSUP_API_URL` to the new address and redeploy. Check that a gallery receipt opens and `/status` lists the providers.
  4. Delete the old service, then the old image repository (`gcloud artifacts repositories delete holdsup --location=<old region>`). Images kept in two regions would pass the 0.5 GB of free storage.
  5. After the first check through the new service, look at `client_address` in its logs again (section 2, step 6).

## What CI checks

`.github/workflows/image.yml` runs on every pull request that touches the API, the catalog or the reports. It builds the image from `make api-bundle` the way a deploy does, then checks two things. With incomplete production settings, the image must refuse to start. With complete (dummy) settings, it must serve `/v1/health`, the catalog and the eval page. `make docker-api` builds the same image locally and runs it as development.
