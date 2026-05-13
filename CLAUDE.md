# OCW Canvas — project rules for Claude

A personal Canvas-like LMS for self-studying open courseware. **Single user.** Stack: FastAPI + SQLAlchemy + Alembic + Postgres (Supabase) on the backend, React + Vite + TypeScript on the frontend, deployed to Render (backend, Docker) + GitHub Pages (frontend). AI via Claude Code CLI (`claude` CLI, OAuth token) or the Anthropic API fallback. Email via Resend.

The full design spec is [`docs/superpowers/specs/2026-05-12-ocw-canvas-design.md`](docs/superpowers/specs/2026-05-12-ocw-canvas-design.md); phase-by-phase plans are in [`docs/superpowers/plans/`](docs/superpowers/plans/); production deploy walkthrough is [`docs/DEPLOY.md`](docs/DEPLOY.md). **Read those before changing anything structural.**

---

## Live URLs

| | URL |
|---|---|
| Frontend (Pages) | <https://dafu-zhu.github.io/ocw-canvas/> |
| Backend (Render) | <https://ocw-canvas-api.onrender.com> |
| Repo | <https://github.com/dafu-zhu/ocw-canvas> |
| Supabase | <https://supabase.com/dashboard/project/euiriasfxnlnyislkqzd> |

Default branch is `master`. CI runs on every push (`.github/workflows/ci.yml`); the Pages deploy fires on push to master (`.github/workflows/deploy.yml`); the hourly cron tick is a GH-Actions workflow, not a Render cron (`.github/workflows/cron-tick.yml`).

---

## Repo shape

```
backend/                 FastAPI service
  app/
    models/              SQLAlchemy ORM (one file per area)
    schemas/             pydantic request/response models
    api/                 routers (one per area: auth, courses, modules, …,
                                                 submissions, gradebook, ai,
                                                 announcements, cron, schedule, files)
    services/            ai, ai_jobs, email, notify, storage, grading, schedule
    cron.py              the hourly tick logic (called by api/cron.py)
    main.py              FastAPI app factory + router mounts
    config.py            pydantic-settings; reads .env / Render env
    db.py                engine + Base + DATABASE_URL normalizer
    auth.py              JWT + bcrypt; httpOnly cookie
    manage.py            CLI: `python -m app.manage create-owner …`
  alembic/versions/      migrations 0001..0005 (one per phase)
  seed/seed_template_course.py   MIT 18.100B seed + URL/coverage updater
  Dockerfile             python:3.12-slim + Node 20 + uv + Claude Code CLI
  render.yaml            Render blueprint (web service only — no cron service)
  tests/                 pytest; mocks ai._invoke + email.httpx.post + Storage
frontend/                Vite + React + TypeScript
  src/
    api/                 typed fetch client + types
    auth/AuthContext     login/me/teacher-mode/unread-count
    components/          AppLayout, CourseLayout, Modal, Markdown, TodoList,
                         ScheduleCourseModal, edit/*EditModal
    pages/               one per Canvas section
    styles/canvas.css    hand-rolled Canvas-like styling
docs/
  superpowers/specs/     the design spec + UI screenshots
  superpowers/plans/     P1..P6 implementation plans
  DEPLOY.md              production deploy runbook
.github/workflows/       ci.yml, deploy.yml (Pages), cron-tick.yml
```

---

## Phase history (P1 → P6, all merged to master)

| Phase | What |
|---|---|
| P1 | Skeleton + auth + read-mostly Canvas (courses/modules/items). |
| P2 | Assignments + submissions (Supabase Storage, local on-disk fallback) + manual grading + Grades page rollup. |
| P3 | AI service: `services/ai.py` drives the **Claude Code CLI directly** (`subprocess.run` with `-p --output-format json`), not via `claude-agent-sdk` (the SDK swallowed stderr on Render). Whitelists `Read,Glob,Grep` only; no `--permission-mode bypassPermissions` (root rejects it). Solution key resolution + AI generation + AI grading + retry handling + transcript logging. |
| P4 | Resend email + announcements + hourly `POST /api/cron/tick` (idempotent via `cron_marker`) + password reset. |
| P5 | MIT 18.100B seed course; KaTeX math rendering; Canvas styling pass + print mode. |
| P6 | Course scheduling: `covers_lecture_from/to` on `assignment`; pure `services/schedule.py`; `POST /courses/{id}/schedule` (preview/apply/activate); `ScheduleCourseModal` triggered on `planned→active` status flip. |

Migrations go up to `0005`. Every push to master triggers Render's `alembic upgrade head` on boot — never edit an already-applied migration; add a new one.

---

## Conventions (apply when editing)

- **Branching.** Work on `feat/<area>` or `fix/<area>` branches; merge to master via `--no-ff`. Never commit directly to master unless it's a doc tweak.
- **Tests.** `cd backend && uv run pytest -q` must pass before any commit that changes Python. Frontend: `npm run typecheck && npm run lint && npm run build`. CI runs both on every push.
- **Lint.** `uv run ruff check .` (line length 100, `select=E,F,I,UP,B`). Match existing code's comment density / docstring style; don't add headers, don't editorialize.
- **Mock boundary.** AI tests monkeypatch `app.services.ai._invoke`. Email tests monkeypatch `app.services.email.httpx.post`. Storage tests monkeypatch `_supabase_configured=False` and `_LOCAL_ROOT=tmp_path`. **No test should make a real network call.**
- **AI invocation.** Always go through `services/ai.py`. Never import `claude_agent_sdk` directly elsewhere — it was deliberately bypassed.
- **Migrations.** `cd backend && DATABASE_URL=sqlite:///./_x.db uv run alembic revision --autogenerate -m "…"` against a fresh sqlite, then rename the file to the next sequential number (e.g. `0006_…`), set `revision="0006"` / `down_revision="0005"`, then `rm _x.db`. Commit the migration alongside the model change.
- **Seed updates that don't drop user data.** Use `python -m seed.seed_template_course --update-urls` — it rewrites module-item URLs, assignment description_md, and assignment coverage in place. `--force` deletes + re-creates (loses submissions / AI solutions / announcements).
- **OCW URLs.** Always verify with curl/WebFetch before committing — patterns differ silently per term (we hit `/pages/assignments/` vs `/pages/problem-sets/`, lec-notes vs `pset` slugs, and review PDFs at `review_midterm` not `midterm_review`).

---

## Gotchas (already paid for; don't pay again)

- **Supabase direct connection is IPv6-only.** Render's free tier has no IPv6 egress → boot loop with `Network is unreachable`. Always use the **Session pooler** URL (`aws-0-<region>.pooler.supabase.com:5432`). `app/db.py` rewrites `postgresql://` → `postgresql+psycopg://` and disables client-side prepared statements for pooler compat.
- **Render free tier has no Cron Jobs.** The hourly tick is a GitHub Actions workflow (`cron-tick.yml`); `render.yaml` declares **only** the web service.
- **`render.yaml` Blueprint Path.** Render's default looks for `render.yaml` at repo root. Ours is `backend/render.yaml`. New Blueprints must explicitly set `Blueprint Path = backend/render.yaml`.
- **Claude Code CLI on Render** runs as root, which refuses `--dangerously-skip-permissions` (aka `--permission-mode bypassPermissions`). We use `--allowedTools Read,Glob,Grep` instead. The CLI's stream-json mode also swallows stderr, so `_invoke_agent_sdk` shells out via `subprocess.run` with `--output-format json` and captures stderr explicitly.
- **CORS + cross-site cookies.** `FRONTEND_ORIGINS=https://dafu-zhu.github.io`, `COOKIE_SECURE=true`, `COOKIE_SAMESITE=none`. Without these, login from Pages doesn't keep a session.
- **SQLite vs Postgres datetime.** SQLite returns naive datetimes from `DateTime(timezone=True)` columns. Code that compares to `datetime.now(UTC)` uses an `_aware()` helper (see `api/cron.py`, `api/submissions.py`, `services/grading.days_late_between`). Postgres returns proper tz-aware datetimes — comparisons work natively.
- **`CRON_SECRET` between Render and GH Actions.** Both must hold the same value. The blueprint's `generateValue: true` row generates a value Render-side only; the GH Actions secret stays whatever it was. Always set both ends in lock-step.
- **YAML block scalars in `render.yaml`.** A literal `:` inside an unquoted scalar (e.g. an HTTP header `X-Cron-Secret: $CRON_SECRET`) trips Render's blueprint parser. Use `>-` (folded block) or single-quote the whole value.

---

## Owner credentials (local dev / live login)

- Email: `dafuzhu@uchicago.edu`
- Initial password: `onM4xGt5-fkM17Ka` (must be rotated — pasted in transcript; use Forgot Password to set a new one).
- AI credential, DB password, Supabase service key, Resend key were all pasted in transcripts and should be rotated before treating this as fully secure.

---

## When the user asks for things

- **"Add a course"** → either teacher-mode UI (Dashboard → + Add course) or a new file under `backend/seed/`.
- **"Fix an OCW link"** → edit the URL constants/maps in `backend/seed/seed_template_course.py`, then run `--update-urls` against the live DB. Don't `--force` re-seed unless schema or structure changed.
- **"Generate AI solution failed"** → check `ai_solution.error` on the row (`SELECT error FROM ai_solution …` in Supabase Studio). The errors are detailed since the P3 CLI bypass.
- **"Schedule the course"** → in teacher mode, edit the course and change Status `planned → active`. The save button becomes "Save & schedule…", which opens `ScheduleCourseModal` with start-date + cadences. Apply writes due_at for all assignments + flips status.
- **"The cron isn't firing"** → check the **Hourly cron tick** workflow's last run on GitHub Actions. 200 = healthy. 403 = `CRON_SECRET` drift between GH secret and Render env. Other = the backend itself is sad.
- **"Production is down"** → Render Logs first. The backend's the chokepoint; the SPA is static and always loads.

---

## Don'ts

- Don't run real AI/email/Storage calls in tests.
- Don't add `--permission-mode bypassPermissions` back to the CLI args.
- Don't switch `DATABASE_URL` to the direct Supabase connection in production.
- Don't commit secrets — `.env*` is gitignored and `render.yaml` uses `sync: false` for everything sensitive.
- Don't `--force` re-seed the live 18.100B without copying out any AI solutions / submissions first.
- Don't edit migrations after they've shipped to master — add a new one.
- Don't bypass `services/ai.py` to call Anthropic directly elsewhere; the seam exists so tests can mock one place.
