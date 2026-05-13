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

1.1. Create an account at <https://supabase.com>, then **New project**. Pick a region close to Render's region (US‑East‑2 / Ohio is the safe pick on Render's free tier). Save the project's **database password** somewhere — you can't view it again.

1.2. **Settings → Database → Connect** (or **Connection string** on older UI). You'll see three connection-string variants. **Pick "Session pooler"**, not "Direct connection":

| Variant | When to use |
|---|---|
| Direct connection (`db.<ref>.supabase.co:5432`) | ❌ Do **not** use. Resolves to **IPv6 only**, and Render's free containers have no IPv6 egress → boot loop with `Network is unreachable` |
| **Session pooler (`aws-0-<region>.pooler.supabase.com:5432`)** | ✅ **Use this.** IPv4 endpoint; supports prepared statements; matches SQLAlchemy's long-lived pool model |
| Transaction pooler (`:6543`) | Also IPv4 and works (the code disables client-side prepared statements via `prepare_threshold=None` for compatibility); session is preferable for our use case |

Copy the Session pooler URI — looks like `postgresql://postgres.<ref>:<pwd>@aws-0-<region>.pooler.supabase.com:5432/postgres` — and replace `[YOUR-PASSWORD]` with the password from 1.1. **This is `DATABASE_URL`.** The app rewrites the scheme to `postgresql+psycopg://…` automatically.

1.3. **Project Settings → API**. Copy:
- **Project URL** → `SUPABASE_URL` (e.g. `https://<ref>.supabase.co`, no trailing slash, **no `/rest/v1/`** path — the bare project URL only)
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

4.1. Sign in at <https://dashboard.render.com> → **New → Blueprint** → connect the `dafu-zhu/ocw-canvas` repo. The blueprint form asks for:

| Field | Value |
|---|---|
| Blueprint Name | anything (e.g. `ocw-canvas`) |
| Branch | `master` |
| **Blueprint Path** | **`backend/render.yaml`** ← the YAML lives under `backend/`, not the repo root. Render's default of bare `render.yaml` won't find it. |

Click **Retry** if you initially got "not found". The blueprint declares one **Web Service** `ocw-canvas-api`. (Render's paid plan also supports a Cron Job; the `render.yaml` intentionally doesn't declare one — see 4.4.)

4.2. **Generate two secrets locally** and keep them handy:
```bash
python -c "import secrets; print('JWT_SECRET=' + secrets.token_urlsafe(32))"
python -c "import secrets; print('CRON_SECRET=' + secrets.token_urlsafe(24))"
```
*Don't* rely on Render's `generateValue: true` for `CRON_SECRET` — you need the value to match a GitHub Actions secret in step 8, and if Render generates it independently the two diverge silently. If the blueprint preview shows an auto-generated row for `JWT_SECRET` / `CRON_SECRET`, **delete those rows before pasting the values below**.

4.3. **Fill in the env vars on the Web Service.** Use Render's **bulk edit** ("Add from .env" / `…` menu in the env-var table) and paste the whole block:

```
DATABASE_URL=postgresql://postgres.<ref>:<pwd>@aws-0-<region>.pooler.supabase.com:5432/postgres
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_SERVICE_KEY=<from 1.3>
CLAUDE_CODE_OAUTH_TOKEN=<from 3A — or use ANTHROPIC_API_KEY from 3B>
AI_SOLUTION_GENERATION_ENABLED=true
AI_MODEL=claude-sonnet-4-6
RESEND_API_KEY=<from 2.1>
OWNER_EMAIL=<recipient of graded/deadline/reset emails>
OWNER_EMAIL_FROM=onboarding@resend.dev
JWT_SECRET=<from 4.2>
CRON_SECRET=<from 4.2 — also used in step 8>
FRONTEND_ORIGINS=https://dafu-zhu.github.io
FRONTEND_BASE_URL=https://dafu-zhu.github.io/ocw-canvas
COOKIE_SECURE=true
COOKIE_SAMESITE=none
```

> Notes: `DATABASE_URL` is the **Session pooler** URL (port 5432) — not the direct one, see 1.2. `SUPABASE_URL` is the bare project URL (no `/rest/v1/`). Refine `FRONTEND_*` in step 7 if your Pages URL differs.

4.4. **No Render cron job.** `render.yaml` intentionally declares only the web service — Render Cron Jobs require a paid plan, and the **GitHub Actions cron workflow** (`.github/workflows/cron-tick.yml`) does the same thing for free. See step 8.

4.5. **Deploy.** The Docker `CMD` runs `alembic upgrade head` automatically, then `uvicorn`. Wait for the service to go green (~5–8 min on the free plan — building the Python + Node + Claude Code CLI image takes a few minutes). Note the public URL Render assigns — e.g. `https://ocw-canvas-api.onrender.com`. **This is the backend URL.** Verify:

```bash
curl https://<your-service>.onrender.com/api/health
# -> {"status":"ok"}
```

If the deploy fails, open **Events / Logs** and look for the first red line. The ones we've seen:

| Symptom in Render logs | Cause | Fix |
|---|---|---|
| `Network is unreachable` connecting to Postgres on IPv6 (`2600:1f16:…`) | You used the **direct** Supabase connection (1.2). Render free is IPv4-only. | Use the **Session pooler** URL (1.2). |
| `prepared statement … already exists` | Behind transaction pooler without `prepare_threshold=None`. | Already fixed in `app/db.py` (we ship this). Confirm you're on master. |
| `services[N].plan: free not a valid plan for service type cron` (during blueprint parse) | `render.yaml` declares a cron service on the free plan. | The shipped `render.yaml` doesn't declare a cron service. If you forked it, drop the `type: cron` block. |
| `mapping values are not allowed in this context` (during blueprint parse) | YAML scalar with a literal `:` (e.g. an HTTP header). | Wrap the value in a `>-` block scalar or quote it. |
| `claude CLI exited 1 … --dangerously-skip-permissions cannot be used with root/sudo privileges` | Earlier version of the AI service. | Already fixed (we ship `--allowedTools Read,Glob,Grep` instead of bypass mode). Pull master. |

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

## 10 — §10 open questions — resolved

| Question | Resolution shipped on `master` |
|---|---|
| **Does the Claude OAuth token work on Render?** | **Yes — with the fixes we ship.** The Python `claude-agent-sdk` wrapper failed inside Render's container (stream-json mode swallowed stderr; `--permission-mode bypassPermissions` triggered the CLI's safety check against running `--dangerously-skip-permissions` as root). `services/ai.py` now invokes the CLI **directly** via `subprocess.run` with `--output-format json`, only whitelists read-only tools (`Read,Glob,Grep`), and sets `HOME=/tmp` / `CI=1` / `DISABLE_AUTOUPDATER=1` defensively. The OAuth path works end-to-end with `CLAUDE_CODE_OAUTH_TOKEN`. |
| Custom domain vs `dafu-zhu.github.io/ocw-canvas/` | Start with the subpath; Vite's `base` is already `/ocw-canvas/`. Add a domain later via Pages + a `frontend/public/CNAME`. |
| Resend sender | Onboarding domain (`onboarding@resend.dev`) for now; verify your own domain later if deliverability matters. |
| PDF rendering of AI solutions | Markdown-in-app via KaTeX (LaTeX renders as math). `ai_solution.pdf_path` exists but is unused. |
| `app_user` as a table vs env | Already a table; password reset works against it. |
| Free-tier cold starts | The hourly GitHub Actions cron-tick doubles as a keep-warm ping. |

**If the AI fails on you anyway** (different CLI version, future regression): switch the env on Render — remove `CLAUDE_CODE_OAUTH_TOKEN`, add `ANTHROPIC_API_KEY` (from <https://console.anthropic.com>). Optionally set `AI_SOLUTION_GENERATION_ENABLED=false` for the bring-your-own-key cheap mode. Same code path, different backend.

---

## Day-2 operations

- **Watching the loop.** `email_log` and `announcement` are append-only — query Supabase Studio's SQL editor if anything looks off. AI prompt+response transcripts are in the `solutions` bucket under `logs/` (path stored on the row).
- **Updating OCW link data only (no destructive re-seed).** When OCW publishes a new lecture page or you want to refresh per-lecture video / notes URLs:
  ```bash
  DATABASE_URL="<session pooler URI>" uv run python -m seed.seed_template_course --update-urls
  ```
  This rewrites `module_item.external_url` for every "Lecture N (video)" / "Lecture N notes" / "Midterm review" / "Final review" / "Video lectures (all)" item — **in place**, preserving submissions, AI solutions, and announcements.
- **Re-seeding.** `uv run python -m seed.seed_template_course --force` deletes + re-creates `MIT 18.100B` (destroys cascaded submissions / AI solutions / announcements). Prefer `--update-urls` for content fixes; reserve `--force` for structural overhauls.
- **Adding another course.** Either via teacher mode in the UI (Dashboard → **+ Add course** → Modules → **+ Module / + Item** → Assignments → **+ Assignment group / + Assignment**), or write a new file under `backend/seed/`.
- **Rotating secrets.** Update on Render → it auto-redeploys. For `CRON_SECRET`, update the GitHub Actions secret (step 8) **at the same time** — they must match or the cron returns 403.
- **Schema changes.** New migration: `cd backend && uv run alembic revision --autogenerate -m "..."`, edit the file, commit. Render runs `alembic upgrade head` on every deploy.
- **Math / LaTeX.** Solution and feedback markdown is rendered with KaTeX (`remark-math` + `rehype-katex`); `$inline$` and `$$block$$` work everywhere `<Markdown>` is used.
- **Logs.** Render service → **Logs** tab. The CI pipeline runs `pytest` + `ruff` + frontend `typecheck`/`lint`/`build` on every push.
