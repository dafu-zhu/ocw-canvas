# OCW Canvas — backend

FastAPI + SQLAlchemy + Alembic. Single-user; JWT in an httpOnly cookie.

## Run locally

```bash
cd backend
uv sync
cp .env.example .env          # edit JWT_SECRET; DATABASE_URL defaults to local sqlite
uv run alembic upgrade head
uv run python -m app.manage create-owner --email you@example.com --name "Your Name"
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

## Docker / deploy

`Dockerfile` builds a Python 3.12 + Node image (Node is only needed for the OAuth/Agent-SDK path).
It runs `alembic upgrade head` then `uvicorn`. Set the env vars (`DATABASE_URL`, `SUPABASE_*`,
the AI credential, `RESEND_API_KEY`, `JWT_SECRET`, `CRON_SECRET`, `FRONTEND_ORIGIN`, …) in the
host dashboard.
