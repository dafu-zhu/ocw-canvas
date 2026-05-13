# OCW Canvas — Deployment Runbook

End-to-end, top to bottom. Each step's output feeds the next, so do them in order. About **45–60 min** total if nothing surprises you.

```
1. Supabase        → DATABASE_URL · SUPABASE_URL · SUPABASE_SERVICE_KEY · 2 private buckets
2. Resend          → RESEND_API_KEY (+ optional verified sender)
3. Claude AI       → CLAUDE_CODE_OAUTH_TOKEN  (preferred)  OR  ANTHROPIC_API_KEY  (fallback)
4. Render          → deploys backend Docker image; gives you a public URL
5. Bootstrap       → create owner + seed MIT 18.100B on the live DB
6. GitHub Pages    → publishes the frontend; gives you a public URL
7. CORS / cookies  → put the Pages URL back into Render
8. GitHub cron     → repo secrets so the hourly tick fires
9. Smoke test      → log in, generate a solution, submit, see the email
```

Repo: <https://github.com/dafu-zhu/ocw-canvas>. Default branch `master`. CI / Pages deploy / hourly cron workflows live in `.github/workflows/`.

> **What you'll keep in a scratchpad while you work:**
> a `DATABASE_URL`, a `SUPABASE_URL`, a `SUPABASE_SERVICE_KEY`, a `RESEND_API_KEY`, one of (`CLAUDE_CODE_OAUTH_TOKEN`, `ANTHROPIC_API_KEY`), a `JWT_SECRET`, a `CRON_SECRET`, the **Render backend URL**, and the **Pages URL**. Don't commit any of them.

---

## 1 — Supabase (Postgres + Storage), free

1.1. Create an account at <https://supabase.com>, then **New project**. Pick a region close to Render's region (e.g. US‑East). Save the project's **database password** somewhere — you can't view it again.

1.2. **Project Settings → Database → Connection string → URI**. Copy the value (looks like `postgresql://postgres.<ref>:<pwd>@aws-0-<region>.pooler.supabase.com:6543/postgres`). **This is `DATABASE_URL`.** The app rewrites the scheme to `postgresql+psycopg://…` automatically; both the pooler (`:6543`) and the direct connection (`db.<ref>.supabase.co:5432`) work.

1.3. **Project Settings → API**. Copy:
- **Project URL** → `SUPABASE_URL` (e.g. `https://<ref>.supabase.co`, no trailing slash)
- **`service_role` secret** → `SUPABASE_SERVICE_KEY`. Treat this like a root password — backend only, never the frontend.

1.4. **Storage → New bucket**. Create **two private buckets**:
- `submissions`
- `solutions`

Leave RLS as default — the backend uses the service key so RLS doesn't matter; the frontend never touches Storage directly.

---

## 2 — Resend (email), free

2.1. Create an account at <https://resend.com>, then **API Keys → Create API Key** with "Sending access". Copy the value → **`RESEND_API_KEY`**.

2.2. **Sender domain.** Start with `OWNER_EMAIL_FROM=onboarding@resend.dev` (the Resend onboarding domain — works immediately, fine for personal use). To use your own domain, add it under **Domains** and follow the DNS instructions; once it's *Verified*, change `OWNER_EMAIL_FROM` to a `you@yourdomain` address.

> If you skip Resend entirely, the app still runs — emails are simply not sent (an `email_log` row records the intent). You can come back and add the key later.

---

## 3 — The Claude AI credential

Two paths; **pick one**. Either one alone is enough.

**(A) Preferred — Claude subscription, no per-token billing.**

```bash
# Locally (Claude Pro/Max required):
claude setup-token
```

Copy the token. You'll set it on Render as **`CLAUDE_CODE_OAUTH_TOKEN`** in step 4. This routes the AI service through the Claude Code CLI / Agent SDK and bills against your subscription. The deployed Docker image bundles Node + `@anthropic-ai/claude-code` so this works on Render.

**(B) Fallback — Anthropic API, pay-per-token.**

Get a key at <https://console.anthropic.com>. You'll set it on Render as **`ANTHROPIC_API_KEY`**. If you want to keep cost minimal also set **`AI_SOLUTION_GENERATION_ENABLED=false`** — the AI then never *solves* a problem set from scratch (the expensive part); instead each assignment must have a key attached (`official_solution_url` or an uploaded file) before autograding runs, and the API key is only used for the cheap grading-against-a-key step.

> If you set neither, the app runs in **manual grading** mode (teacher mode → enter a score by hand). Everything else works.

---

## 4 — Render (backend Docker), free web service

Render reads `backend/render.yaml` and stands up a Docker Web Service from `backend/Dockerfile`.

4.1. Sign in at <https://dashboard.render.com> → **New → Blueprint** → connect the `dafu-zhu/ocw-canvas` repo → it detects `render.yaml` and proposes:

- a **Web Service** `ocw-canvas-api`
- a **Cron Job** `ocw-canvas-tick` (Render Cron Jobs may **not** be on the free plan — see 4.4)

4.2. **Generate two secrets locally** and keep them handy:
```bash
python -c "import secrets; print('JWT_SECRET=' + secrets.token_urlsafe(32))"
python -c "import secrets; print('CRON_SECRET=' + secrets.token_urlsafe(24))"
```
(Or let Render `generateValue` them via the blueprint; in that case open the service after deploy and copy the values it generated.)

4.3. **Fill in the env vars on the Web Service** (the blueprint marks the secret ones `sync:false` so Render prompts you). Leave the placeholders below as-is — fill them with the values from steps 1–3:

| Key | Value |
|---|---|
| `DATABASE_URL` | from 1.2 |
| `SUPABASE_URL` | from 1.3 |
| `SUPABASE_SERVICE_KEY` | from 1.3 |
| **One of:** `CLAUDE_CODE_OAUTH_TOKEN` *or* `ANTHROPIC_API_KEY` | from 3 |
| `AI_SOLUTION_GENERATION_ENABLED` | `true` (or `false` if you went path (B) and want cheap mode) |
| `AI_MODEL` | `claude-sonnet-4-6` (default; bump to a newer model later if you want) |
| `RESEND_API_KEY` | from 2.1 |
| `OWNER_EMAIL` | the address that receives graded / deadline / reset emails |
| `OWNER_EMAIL_FROM` | `onboarding@resend.dev` (or your verified sender) |
| `JWT_SECRET` | from 4.2 |
| `CRON_SECRET` | from 4.2 — **write this down**; you'll reuse it in step 8 |
| `FRONTEND_ORIGINS` | leave as `https://dafu-zhu.github.io` for now; refine in step 7 |
| `FRONTEND_BASE_URL` | leave as `https://dafu-zhu.github.io/ocw-canvas` for now; refine in step 7 |
| `COOKIE_SECURE` | `true` |
| `COOKIE_SAMESITE` | `none` |

4.4. **About the cron service.** Render Cron Jobs aren't on the free plan. Two options:

- **Cheapest path** (recommended for personal use): delete the `ocw-canvas-tick` service from the blueprint, and let the **GitHub Actions cron workflow** (`.github/workflows/cron-tick.yml`, already in the repo) fire the hourly tick. See step 8.
- **Or** keep it and accept the small monthly fee.

4.5. **Deploy.** The Docker `CMD` runs `alembic upgrade head` automatically, then `uvicorn`. Wait for the service to go green (~3–5 min on the free plan). Note the public URL Render assigns — e.g. `https://ocw-canvas-api.onrender.com`. **This is the backend URL.** Verify:

```bash
curl https://<your-service>.onrender.com/api/health
# -> {"status":"ok"}
```

If it doesn't go green: open **Logs**. Common gotchas — wrong `DATABASE_URL` (`alembic` errors), missing `JWT_SECRET` (raises at startup), wrong `SUPABASE_URL` format (must be the project URL, not the dashboard URL).

---

## 5 — First-run setup on the live DB

The migrations ran on first deploy. You still need (a) an owner account and (b) the seed course.

**Option A — Render Shell** (Web Service page → **Shell** tab):

```bash
cd /app
uv run python -m app.manage create-owner --email you@example.com --name "Your Name"
uv run python -m seed.seed_template_course
```

**Option B — Local, pointing at the prod DB.** From your machine:

```bash
cd backend
DATABASE_URL="<the Supabase URI from 1.2>" uv run python -m app.manage create-owner --email you@example.com --name "Your Name"
DATABASE_URL="<the Supabase URI from 1.2>" uv run python -m seed.seed_template_course
```

You should see:
```
Owner ready: you@example.com
Seeded MIT 18.100B — Real Analysis: 9 modules, 66 items, 12 assignments.
```

---

## 6 — GitHub Pages (frontend), free

6.1. **Tell the build where the backend is.** Repo → **Settings → Secrets and variables → Actions → Variables → New repository variable**:

- Name: `VITE_API_BASE_URL`
- Value: the Render URL from 4.5, **no trailing slash** (e.g. `https://ocw-canvas-api.onrender.com`)

6.2. **Run the deploy.** Actions tab → **Deploy frontend to GitHub Pages** → **Run workflow** → branch `master`. (It also runs automatically on every push to `master`.) On success, it pushes `frontend/dist/` to the `gh-pages` branch.

6.3. **Turn Pages on.** Repo → **Settings → Pages**:

- **Source:** Deploy from a branch
- **Branch:** `gh-pages` / `(root)`
- Save.

Wait ~30 s. Your site is at **`https://dafu-zhu.github.io/ocw-canvas/`** (Vite is configured with `base: "/ocw-canvas/"` to match). Visit it — you should see the login page. (Don't log in yet — first finish step 7 so the cookie works.)

---

## 7 — CORS / cookies — wire the two URLs together

If 4.5's URL or 6.3's URL differs from what you put in step 4.3, **update Render now** and redeploy:

| Key | Value |
|---|---|
| `FRONTEND_ORIGINS` | the **origin only** of the Pages URL — `https://dafu-zhu.github.io` (no path, no trailing slash) |
| `FRONTEND_BASE_URL` | the **full base** including the `/ocw-canvas` path — `https://dafu-zhu.github.io/ocw-canvas` (used in email links) |
| `COOKIE_SECURE` | `true` |
| `COOKIE_SAMESITE` | `none` |

Then **Manual Deploy → Deploy latest commit** on the Render service. (CORS / cookie settings are read at startup.)

---

## 8 — GitHub Actions cron (if you skipped Render's cron service)

Repo → **Settings → Secrets and variables → Actions → Secrets → New repository secret**, add **two**:

- `BACKEND_URL` — the Render URL from 4.5 (no trailing slash)
- `CRON_SECRET` — the same value you used on Render in 4.3

Then Actions tab → **Hourly cron tick** → **Run workflow** once to confirm it returns 200. It'll run automatically every hour after that (UTC). It also doubles as a free keep-warm ping against Render free-tier cold starts.

---

## 9 — Smoke test

Log in at `https://dafu-zhu.github.io/ocw-canvas/` with the owner credentials from step 5. Walk through:

1. **Dashboard** shows the MIT 18.100B course card.
2. Click in → **Modules** lists 9 modules, every `link`/`video` row opens an OCW page in a new tab.
3. **Assignments** → 10 problem sets + Midterm + Final. Open **Problem Set 1**.
4. Toggle **Teacher mode** in the Account menu → click **Generate AI solution**. Within ~10–60 s the solution panel shows `status: ready` and the worked solution. This **tests the OAuth/Agent-SDK path on Render** — see step 10.
5. Paste any text / upload any file → **Submit Assignment**. The submission auto-grades against the AI key and shows a score + rubric + feedback.
6. Open **Inbox** — there's a `Graded: Problem Set 1 — …` announcement; check the unread badge on the rail.
7. Check your `OWNER_EMAIL` inbox — the graded email should be there (if you set up Resend in step 2).
8. Actions tab → **Hourly cron tick** → **Run workflow** → it returns 200; no new announcements/emails because everything's up to date.

If all eight work: you're live.

---

## 10 — Resolve §10 open question #1: does the Claude OAuth token work on Render?

You answered this in 9.4:

| What you saw | What it means | Action |
|---|---|---|
| `status: ready`, content rendered | OAuth path works on Render. | Done. Keep `CLAUDE_CODE_OAUTH_TOKEN`. |
| `status: failed` with an error mentioning `claude`, `node`, `CLI`, or the token | The CLI / token path didn't work on the deployed image. | On Render: remove `CLAUDE_CODE_OAUTH_TOKEN`, add `ANTHROPIC_API_KEY`. Optionally also `AI_SOLUTION_GENERATION_ENABLED=false` (cheap mode). Redeploy and retry. |
| `status: pending`, `error: "… disabled …"` | Generation is intentionally off. | Either flip `AI_SOLUTION_GENERATION_ENABLED=true`, or attach an `official_solution_url`/file on the assignment yourself. |

The other §10 items: custom domain (defer — start with the subpath; add later via Pages + a `frontend/public/CNAME`); Resend sender (start with the onboarding domain); PDF rendering of AI solutions (markdown-in-app is fine, `pdf_path` exists unused); `app_user` as a table (already done); free-tier cold starts (the cron tick keeps the service warm).

---

## Day-2 operations

- **Watching the loop.** `email_log` and `announcement` are append-only — query Supabase Studio's SQL editor if anything looks off. AI prompt+response transcripts are in the `solutions` bucket under `logs/` (path stored on the row).
- **Re-seeding.** `uv run python -m seed.seed_template_course --force` deletes + re-creates `MIT 18.100B`. Cascades take care of the modules / assignments / submissions / announcements.
- **Adding another course.** Either via teacher mode in the UI (Dashboard → **+ Add course** → Modules → **+ Module / + Item** → Assignments → **+ Assignment group / + Assignment**), or write a new file under `backend/seed/`.
- **Rotating secrets.** Update on Render → Manual Deploy. For `CRON_SECRET`, also update the GitHub repo secret (step 8) at the same time.
- **Schema changes.** New migration: `cd backend && uv run alembic revision --autogenerate -m "..."`, edit the file, commit. Render runs `alembic upgrade head` on every deploy.
- **Logs.** Render service → **Logs** tab. The CI pipeline runs `pytest` + `ruff` + frontend `typecheck`/`lint`/`build` on every push.
