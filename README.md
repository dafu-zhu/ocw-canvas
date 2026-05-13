# OCW Canvas

A personal, Canvas-like LMS for self-studying open courseware (MIT OCW, etc.). Tracks course materials under **Modules** (every item links out to the university's real page — nothing is re-hosted), and runs a homework loop: an assignment has a deadline; if no official solution exists the AI writes a reference solution key; you upload your work; the AI grades it against the key, leaves written feedback and a score; you get an in-app announcement and an email.

Single user. React + Vite frontend (GitHub Pages), FastAPI backend (Render, Docker — Python + Node), Supabase Postgres + Storage, the Claude Agent SDK (Claude subscription via OAuth token; Anthropic API as fallback) for AI, Resend for email. The UI mirrors Canvas (dark left rail, course-card dashboard, per-course nav: Home · Syllabus · Modules · Assignments · Grades · Video Lectures · Announcements).

**Status:** P1–P5 complete — feature-complete per the design spec; the MIT 18.100B seed course is loaded. P1 — single-user auth; CRUD for courses / modules / module-items / assignment-groups; Dashboard, Course Home, Syllabus, Modules, Video Lectures pages; teacher-mode editing. P2 — assignment CRUD; Assignments list + Assignment detail with file/text submissions in Supabase Storage (local on-disk fallback); late flagging; manual grade entry; a Canvas-style Grades page driven by a tested rollup; To-Do widgets fed real deadlines. P3 — `services/ai.py` over the Claude Agent SDK (OAuth-token auth; Anthropic-API fallback; `AI_SOLUTION_GENERATION_ENABLED` flag); the `ai_solution` table; solution-key resolution (official URL > official file > AI solution > none); AI reference-solution generation and AI grading (rubric + score + feedback) with bounded retries + transcript logging; "awaiting solution key" state; the in-app "view reference solution" surface; the Docker image. P4 — Resend email (graded / deadline / password-reset) + `email_log`; the `announcement` feed (page + unread badge + mark-read) wired into grading; an hourly idempotent `POST /api/cron/tick` (48h/24h deadline reminders + stuck-AI-job re-drives, `cron_marker`); password reset; `render.yaml` (Web Service + Cron Job). P5 — the MIT 18.100B seed course (course record, syllabus, modules over the 23 lectures + reviews + exams, 3 weighted assignment groups, 10 problem sets + Midterm + Final) via `seed/seed_template_course.py`; a Canvas styling/print pass.

First seed course: **MIT 18.100B — Real Analysis (Spring 2025)** — <https://ocw.mit.edu/courses/18-100b-real-analysis-spring-2025/>.

## Quick start (local)

```bash
# backend
cd backend
uv sync
cp .env.example .env                       # edit JWT_SECRET; DATABASE_URL defaults to local sqlite
uv run alembic upgrade head
uv run python -m app.manage create-owner --email you@example.com --name "Your Name"
uv run python -m seed.seed_template_course # loads MIT 18.100B (idempotent; --force re-creates)
uv run uvicorn app.main:app --reload --port 8000

# frontend (in another shell)
cd frontend
npm install
cp .env.example .env                       # VITE_API_BASE_URL=http://localhost:8000
npm run dev                                # http://localhost:5173
```

Sign in with the owner credentials. Everything works without any cloud setup: file storage falls back to `backend/_local_storage/`, and with no `CLAUDE_CODE_OAUTH_TOKEN`/`ANTHROPIC_API_KEY` the AI is simply off (you grade manually in teacher mode) — likewise email is skipped (but still logged) without `RESEND_API_KEY`.

## How the homework loop works

1. **Author** an assignment (teacher mode): title, a `description_md` with the link to the source problem-set PDF, points, due date, submission types, late policy — optionally attach a published official solution (`official_solution_url` or an uploaded file).
2. **Solution key.** If an official key is attached, that's the key. Otherwise, if AI generation is enabled, "Generate AI solution" produces a complete worked solution (cached on `ai_solution`). If neither, the assignment is still usable — autograding just waits.
3. **Submit** — paste text/LaTeX and/or upload PDFs/images. If a key exists, grading kicks off immediately; otherwise the submission shows "awaiting solution key".
4. **AI grades** the submission against the key: a rubric breakdown, a score (late penalty applied per the policy), written feedback. Every prompt + response is logged to Storage.
5. **Announce + email.** A `kind=graded` announcement appears in the Inbox feed and an email goes to the owner. The hourly `/api/cron/tick` also sends 48h/24h deadline reminders and re-drives any stalled AI jobs — idempotently.

## Deployment

End-to-end runbook (Supabase → Render → Pages → cron, ~45 min): **[`docs/DEPLOY.md`](docs/DEPLOY.md)**. Short version: `backend/render.yaml` builds the Dockerfile (Python 3.12 + Node + Claude Code CLI) on Render free; the GitHub Action `.github/workflows/deploy.yml` publishes the Vite SPA to `gh-pages`; the GitHub Action `cron-tick.yml` POSTs `/api/cron/tick` hourly (free alternative to Render's paid Cron Job).

## Layout & docs

- Backend: [`backend/README.md`](backend/README.md) — run, tests, AI / email / cron / Docker config.
- Frontend: [`frontend/README.md`](frontend/README.md).
- Design spec: [`docs/superpowers/specs/2026-05-12-ocw-canvas-design.md`](docs/superpowers/specs/2026-05-12-ocw-canvas-design.md) (Canvas UI screenshots in `docs/superpowers/specs/assets/`).
- Implementation plans (one per phase): [`docs/superpowers/plans/`](docs/superpowers/plans/).
