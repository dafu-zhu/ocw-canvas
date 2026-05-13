# OCW Canvas — backend

FastAPI + SQLAlchemy + Alembic. Single-user; JWT in an httpOnly cookie.

## Run locally

```bash
cd backend
uv sync
cp .env.example .env          # edit JWT_SECRET; DATABASE_URL defaults to local sqlite
uv run alembic upgrade head
uv run python -m app.manage create-owner --email you@example.com --name "Your Name"
uv run python -m seed.seed_template_course   # loads the MIT 18.100B seed course (idempotent; --force re-creates)
uv run uvicorn app.main:app --reload --port 8000
```

API at <http://localhost:8000>; interactive docs at <http://localhost:8000/docs>.

## Tests / lint

```bash
uv run pytest -q
uv run ruff check .
```

All tests mock the AI model call (`app.services.ai._invoke`) and use Storage's local on-disk
fallback — nothing in the suite touches Anthropic or Supabase.

## AI configuration (P3+)

The AI does two jobs through `app/services/ai.py`: generate a reference solution when an
assignment has no published key, and grade a submission against the key.

Pick **one** credential:

- `CLAUDE_CODE_OAUTH_TOKEN` — preferred. Produced once by `claude setup-token` (needs a Claude
  Pro/Max subscription). Drives the Claude Code CLI via the Agent SDK; all model usage is billed
  to your subscription. The Docker image installs Node + `@anthropic-ai/claude-code` for this.
- `ANTHROPIC_API_KEY` — fallback (per-token billing). In this mode set
  `AI_SOLUTION_GENERATION_ENABLED=false` to skip the token-expensive "solve the whole problem set"
  step — then an assignment must carry a key (`official_solution_url` or an uploaded file) before
  autograding runs; the API key is used only for the cheap grading-against-a-key step.
- neither — AI is off; submissions are still recorded and you grade manually in teacher mode.

Other knobs: `AI_MODEL` (default `claude-sonnet-4-6`). Solution generation runs at most once per
assignment (cached on `ai_solution`); grading runs once per submission attempt. Prompt+response
transcripts are written to Storage (`solutions/logs/...`) and the path stored on the row.

## Email & cron (P4+)

Outbound email goes through Resend (`app/services/email.py`). Set `RESEND_API_KEY` and
`OWNER_EMAIL_FROM` (a verified sender, or Resend's `onboarding@resend.dev` to start). If
`RESEND_API_KEY` is unset the app still runs — emails are skipped but an `email_log` row is
written recording the intent. Three templates: graded results, deadline reminders, password reset.
Every graded submission (AI or manual) also creates an in-app `announcement`; the Announcements
page mirrors them and the Inbox rail icon shows an unread count.

`POST /api/cron/tick` is the hourly job. It is **not** behind the login cookie — it's guarded by
an `X-Cron-Secret: <CRON_SECRET>` header (wrong/missing → 403). It (1) sends 48h/24h deadline
reminders for published, dated, unsubmitted assignments — idempotently, via `cron_marker` rows
keyed `deadline-<48|24>h:<assignment_id>` — and (2) re-drives stalled AI work (solutions stuck
`generating`/`failed` with `attempts<3`; submissions that are `submitted` and now have a key;
submissions stuck `grading`). Running it twice produces no duplicate emails/announcements.

Password reset: `POST /api/auth/forgot-password {email}` → emails a one-hour signed token →
`POST /api/auth/reset-password {token, new_password}` sets the password and logs in.

## Docker / deploy

`Dockerfile` builds a Python 3.12 + Node image (Node is only needed for the OAuth/Agent-SDK path).
It runs `alembic upgrade head` then `uvicorn`. `render.yaml` declares a Docker **Web Service** and
a Docker **Cron Job** (`schedule: "0 * * * *"`, curls `/api/cron/tick` with the shared secret).
Set the dashboard env vars: `DATABASE_URL`, `SUPABASE_*`, one AI credential, `RESEND_API_KEY`,
`OWNER_EMAIL`, `OWNER_EMAIL_FROM`, `JWT_SECRET`, `CRON_SECRET`, `FRONTEND_ORIGINS`,
`FRONTEND_BASE_URL`, and `SELF_URL` (on the cron job).
