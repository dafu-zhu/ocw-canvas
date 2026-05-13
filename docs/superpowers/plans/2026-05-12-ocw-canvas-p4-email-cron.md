# OCW Canvas — Phase 4 (Email, Announcements & Cron) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or superpowers:executing-plans. Checkbox steps.

**Goal:** "The AI announces you." Add Resend email (graded / deadline / password-reset), the `announcement` feed (page + unread badge + mark-read), an hourly `POST /cron/tick` (48h/24h deadline reminders + stuck-AI-job re-drives, idempotent via `cron_marker`), the password-reset flow, and `render.yaml` (Web Service + Cron Job). Hook graded-submission events into an announcement + email.

**Architecture:** Builds on P3. New backend: `app/models/notifications.py` (`Announcement`, `EmailLog`, `CronMarker`; migration 0004), `app/services/email.py` (Resend REST via httpx; templates; writes `email_log`; no-op-but-logs when `RESEND_API_KEY` unset), `app/services/notify.py` (the "submission graded → announcement + email" + "deadline → announcement + email" helpers — pure-ish, uses `email`), `app/api/announcements.py` (list/get/mark-read/mark-all-read + unread count), `app/cron.py` + `app/api/cron.py` (`POST /cron/tick`, `X-Cron-Secret`), password-reset added to `app/api/auth.py`. `ai_jobs.grade_with_ai` and `api/submissions.manual_grade` call `notify.announce_graded`. New frontend: real `AnnouncementsPage` (global + course-scoped), unread badge on the Inbox rail item, a `/reset` set-new-password page, "Forgot password?" wired. New ops: `render.yaml`.

**Tech Stack:** unchanged (httpx for Resend; itsdangerous-free signed reset token = a short random token stored on `app_user.reset_token` + `reset_expires`). Tests mock the Resend HTTP call; cron tested as a plain endpoint.

**Conventions:** branch `feat/p4-email-cron` (from `master`). Commit per task. Tests mock all network.

---

### Task 1: `Announcement` / `EmailLog` / `CronMarker` models + migration 0004

**Files:** Create `backend/app/models/notifications.py`; modify `backend/app/models/__init__.py`; create `backend/alembic/versions/0004_notifications.py`; test `backend/tests/test_notification_models.py`.

```python
# notifications.py
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.base import TimestampMixin, _uuid

if TYPE_CHECKING:
    from app.models.course import Course


class Announcement(Base, TimestampMixin):
    __tablename__ = "announcement"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    course_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("course.id", ondelete="CASCADE"), nullable=True
    )  # null = global
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")  # graded|deadline|manual|system
    title: Mapped[str] = mapped_column(String(400), nullable=False)
    body_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    related_assignment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    emailed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    course: Mapped["Course | None"] = relationship()


class EmailLog(Base, TimestampMixin):
    __tablename__ = "email_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    to: Mapped[str] = mapped_column(String(320), nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    template: Mapped[str] = mapped_column(String(40), nullable=False)  # graded|deadline|password_reset
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    resend_id: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="sent")  # sent|failed
    error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CronMarker(Base):
    __tablename__ = "cron_marker"

    key: Mapped[str] = mapped_column(String(200), primary_key=True)  # e.g. "deadline-48h:<assignment_id>"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
```

> `Course` needs no back-ref for announcements (one-directional relationship is fine — keep `relationship()` without `back_populates`).

- [ ] **Step 1–3:** Write `notifications.py`; export `Announcement`, `EmailLog`, `CronMarker` from `models/__init__.py`.
- [ ] **Step 4:** Autogenerate migration 0004 (`alembic upgrade head` → `revision --autogenerate -m "notifications"`), rename to `0004_notifications.py`, `revision="0004"`, `down_revision="0003"`. Verify the three `op.create_table` calls.
- [ ] **Step 5:** Verify chain applies on a throwaway sqlite db.
- [ ] **Step 6:** `tests/test_notification_models.py` — create an announcement (global + course-scoped), an email_log row, a cron_marker; deleting a course cascades its announcements; cron_marker PK uniqueness.
- [ ] **Step 7:** `uv run pytest -q && uv run ruff check .`.
- [ ] **Step 8:** Commit `feat: announcement / email_log / cron_marker models + migration 0004`.

---

### Task 2: `services/email.py` — Resend client + templates + email_log

**Files:** Create `backend/app/services/email.py`; test `backend/tests/test_email_service.py`.

- `email_configured() -> bool` — `bool(settings.resend_api_key)`.
- `send(db, *, to, subject, template, html, text, payload) -> EmailLog` — if configured, POST to `https://api.resend.com/emails` (`Authorization: Bearer …`, JSON `{from, to, subject, html, text}`) with a short timeout + one retry; on 2xx capture `resend_id` and `status="sent"`; on error `status="failed"`, `error=…`. If **not** configured, skip the HTTP call (still write the log row with `status="sent"`, `resend_id=""`, and a `payload` note `"(email not sent — RESEND_API_KEY unset)"`). Always write & commit an `EmailLog` row; return it. Wrap so it never raises.
- Template renderers (pure → `(subject, html, text)`):
  - `render_graded(*, course_code, assignment_title, final_score, points, feedback_excerpt, link) -> tuple[str,str,str]` — subject `[<course_code>] <assignment_title> graded — <final_score>/<points>`.
  - `render_deadline(*, course_code, assignment_title, due_at, hours, link) -> tuple[str,str,str]` — subject `[<course_code>] <assignment_title> due in ~<hours>h`.
  - `render_password_reset(*, name, reset_link) -> tuple[str,str,str]` — subject `Reset your OCW Canvas password`.
- The `from` address is `settings.owner_email_from` (default `onboarding@resend.dev`).

- [ ] **Step 1:** Write `services/email.py`.
- [ ] **Step 2:** `tests/test_email_service.py`:
  - templates produce the expected subjects and include the key facts in `text`.
  - `send` with `email_configured()` false → writes a log row, no HTTP call (monkeypatch `httpx.post` to fail loudly to prove it's not called), returns row with `status="sent"`.
  - `send` with `resend_api_key` set + `httpx.post` monkeypatched to return a 200 with `{"id": "re_x"}` → log row `status="sent"`, `resend_id="re_x"`.
  - `send` with `httpx.post` raising → log row `status="failed"`, `error` set; no exception escapes.
- [ ] **Step 3:** `uv run pytest -q && uv run ruff check .`.
- [ ] **Step 4:** Commit `feat: services/email.py — Resend client + templates + email_log`.

---

### Task 3: `services/notify.py` — graded & deadline announcements + emails

**Files:** Create `backend/app/services/notify.py`; modify `backend/app/services/ai_jobs.py` (`grade_with_ai` calls `notify.announce_graded` after a successful grade) and `backend/app/api/submissions.py` (`manual_grade` likewise); test `backend/tests/test_notify.py`.

- `frontend_link(path: str) -> str` — `settings.frontend_base_url.rstrip('/') + path`.
- `announce_graded(db, submission, assignment, grade) -> Announcement` — create `Announcement(course_id=assignment.course_id, kind="graded", related_assignment_id=assignment.id, title=f"Graded: {assignment.title}", body_md=…summary with score + first ~2 sentences of feedback + link…)`; render+send the graded email to `app_user.email` (look up the single `AppUser`); set `announcement.emailed_at = email_log.sent_at or now`; commit; return it. Never raises (email failure already swallowed in `email.send`; wrap the whole thing too).
- `announce_deadline(db, assignment, hours) -> Announcement | None` — create `Announcement(course_id=…, kind="deadline", related_assignment_id=…, title=f"Reminder: {assignment.title} due in ~{hours}h", body_md=…)`; render+send the deadline email; set `emailed_at`; commit; return it.
- Hook points: in `ai_jobs.grade_with_ai`, after `db.refresh(g)` on success → `notify.announce_graded(db, sub, a, g)`. In `api/submissions.manual_grade`, after `db.refresh(g)` → same. (Import `notify` lazily inside the function in `ai_jobs` to avoid any import-order surprises, or just top-level — there's no cycle: `notify` imports `email`, `models`, `config`; nothing imports `notify` except these two call sites.)

- [ ] **Step 1:** Write `services/notify.py`.
- [ ] **Step 2:** Wire the two call sites; keep all existing tests green (they don't assert on announcements, but now an `AppUser` may not exist in some unit tests that use `db` directly — `announce_graded` must tolerate "no owner row" by skipping the email but still creating the announcement; in the API tests `logged_in_client` always has the owner).
- [ ] **Step 3:** `tests/test_notify.py` (mock `email.send` or `httpx.post`; storage local; AI `_invoke` mocked):
  - submitting against an AI-keyed assignment (via `logged_in_client`) → afterwards `GET /api/announcements` shows a `kind="graded"` row whose `related_assignment_id` matches and `emailed_at` is set; an `email_log` row with `template="graded"` exists.
  - `announce_graded` called with no `AppUser` present → still creates the announcement, no email, no crash.
  - manual grading also produces a `graded` announcement.
- [ ] **Step 4:** `uv run pytest -q && uv run ruff check .`.
- [ ] **Step 5:** Commit `feat: notify — graded/deadline announcements + emails; hook into grading`.

---

### Task 4: Announcements API

**Files:** Create `backend/app/api/announcements.py`; modify `backend/app/main.py` (mount); create `backend/app/schemas/announcement.py`; test `backend/tests/test_announcements_api.py`.

```python
# schemas/announcement.py
from datetime import datetime
from app.schemas.common import ORMModel

class AnnouncementOut(ORMModel):
    id: str
    course_id: str | None
    kind: str
    title: str
    body_md: str
    related_assignment_id: str | None
    read_at: datetime | None
    emailed_at: datetime | None
    created_at: datetime
```

Endpoints (all behind `get_current_user`):
- `GET /announcements?course_id=<optional>` → `list[AnnouncementOut]`, newest first (filter by `course_id` if given).
- `GET /announcements/unread-count` → `{"count": int}`.
- `GET /announcements/{id}` → `AnnouncementOut` **and** sets `read_at = now` if it was null (so opening marks read).
- `POST /announcements/{id}/read` → mark read; returns `AnnouncementOut`.
- `POST /announcements/mark-all-read?course_id=<optional>` → marks every unread (optionally course-scoped) read; returns `{"count": int}` (how many flipped).

- [ ] **Step 1:** Schema + router; mount in `main.py`.
- [ ] **Step 2:** `tests/test_announcements_api.py` — seed a couple of announcements directly via the test `db`, then through the client: list (newest first; course filter), unread-count, GET marks read, mark-all-read flips the rest, unread-count goes to 0.
- [ ] **Step 3:** `uv run pytest -q && uv run ruff check .`.
- [ ] **Step 4:** Commit `feat: announcements API (list, unread count, mark-read, mark-all-read)`.

---

### Task 5: Password reset (backend)

**Files:** modify `backend/app/api/auth.py`; modify `backend/app/services/email.py` already done; test `backend/tests/test_password_reset.py`.

- `POST /auth/forgot-password {email}` → if a user with that email exists: generate `token = secrets.token_urlsafe(32)`, set `user.reset_token=token`, `user.reset_expires = now + 1h`, commit; `email.send(... template="password_reset", html/text from render_password_reset(name, reset_link=frontend_base_url + "/reset?token=" + token) ...)`. **Always** return `{"ok": true}` (don't leak whether the email exists).
- `POST /auth/reset-password {token, new_password}` → find the user with that `reset_token` and `reset_expires > now`; if none → 400 `"invalid or expired token"`; else `user.password_hash = hash_password(new_password)`, clear `reset_token`/`reset_expires`, commit; set the session cookie (log them in) and return `UserOut`.

- [ ] **Step 1:** Add both endpoints to `api/auth.py` (import `secrets`, `hash_password`, `email` service, `datetime`).
- [ ] **Step 2:** `tests/test_password_reset.py` (mock `email.send` / `httpx.post`): forgot-password for an unknown email → 200, no log/no token; for the known owner → 200, `reset_token` set, an `email_log` `template="password_reset"` row exists; reset-password with that token → 200, can now log in with the new password; reset-password with a bad token → 400; reset-password with an expired token → 400.
- [ ] **Step 3:** `uv run pytest -q && uv run ruff check .`.
- [ ] **Step 4:** Commit `feat: password reset (forgot-password / reset-password) via emailed token`.

---

### Task 6: Cron tick — `POST /cron/tick`

**Files:** Create `backend/app/cron.py` (the logic) and `backend/app/api/cron.py` (the route); modify `backend/app/main.py` (mount, no auth dep — guarded by header); test `backend/tests/test_cron.py`.

- `app/cron.py`:
  - `_marker_exists(db, key) -> bool`; `_set_marker(db, key)`.
  - `run_tick(db) -> dict` — returns a counts dict. Steps:
    1. **Deadline reminders:** for each published `Assignment` with `due_at` set and no submission at all, for each threshold in `(48, 24)`: if `due_at` is within the next `threshold` hours (and still in the future) and no `cron_marker` `f"deadline-{threshold}h:{a.id}"` → `notify.announce_deadline(db, a, threshold)`, `_set_marker`. (Use `days_late_between`-style tz tolerance for `due_at`.)
    2. **Re-drive stuck AI work:** `ai_jobs.retry_stuck(db)` — re-drives `generating`/`failed` solutions (attempts<3), grades now-keyed `submitted` submissions, retries stuck `grading` ones.
    Idempotent: running it twice in a row produces zero new announcements/emails (markers already set) and re-drives nothing new.
- `app/api/cron.py`: `POST /cron/tick` reading `x_cron_secret: str | None = Header(default=None)`; if `x_cron_secret != settings.cron_secret` → 403; else `return run_tick(db)`.

- [ ] **Step 1:** Write `cron.py` + `api/cron.py`; mount in `main.py` (`app.include_router(cron.router, prefix="/api")` — path `/api/cron/tick`; **render.yaml** curls `${SELF_URL}/api/cron/tick`).
- [ ] **Step 2:** `tests/test_cron.py` (mock `email.send`/`httpx.post`; storage local; AI `_invoke` mocked):
  - wrong / missing `X-Cron-Secret` → 403.
  - an assignment due in ~30h with no submission: first tick → one `deadline-48h:` marker + one `kind="deadline"` announcement + one `email_log`; second tick → no new announcement/email/marker (idempotent). (24h marker only appears once `due_at` is within 24h — optionally a second test advancing nothing; the 48h one is enough to prove the mechanism.)
  - an assignment with a submission → no deadline reminder.
  - a `submitted` submission on an AI-keyed assignment → tick grades it (`status="graded"`), and produces a `graded` announcement.
  - running the tick on an empty DB → 200, all-zero counts.
- [ ] **Step 3:** `uv run pytest -q && uv run ruff check .`.
- [ ] **Step 4:** Commit `feat: POST /cron/tick — deadline reminders + stuck-job re-drive, idempotent`.

---

### Task 7: Frontend — Announcements page, unread badge, reset page

**Files:** modify `frontend/src/api/types.ts` (`Announcement`), `frontend/src/api/client.ts` (announcements + auth methods), `frontend/src/pages/AnnouncementsPage.tsx` (real list, course filter via route, mark-all-read, click → mark read + show body + link), `frontend/src/components/AppLayout.tsx` (unread badge on the Inbox rail item — poll `getUnreadCount` on mount and after navigation), create `frontend/src/pages/ResetPasswordPage.tsx`, modify `frontend/src/App.tsx` (route `/reset`), `frontend/src/pages/LoginPage.tsx` ("Forgot password?" → small inline email prompt → `forgotPassword`).

- `AnnouncementsPage`: used at both `/announcements` (global) and `/courses/:courseId/announcements` (course-scoped — pass `courseId` from `useParams`). Filter dropdown `All` (only on the global view), search box (client-side filter on title/body), "Mark All as Read". A reverse-chron list of rows: a round avatar with initials ("AI"), bold title, truncated `body_md` preview, "Posted on: <date>", an unread dot. Click → expands the full `body_md` (rendered) + a link to the related assignment if any, and `api.markRead(id)` then refresh + refresh the badge.
- `ResetPasswordPage` (`/reset?token=…`): read `token` from the query string; a "new password" + "confirm" form → `api.resetPassword(token, pw)` → on success it's logged in (cookie set) → `nav("/")`; on error show the message.

- [ ] **Step 1:** Types + client (`listAnnouncements(courseId?)`, `getUnreadCount`, `getAnnouncement(id)`, `markRead(id)`, `markAllRead(courseId?)`, `forgotPassword(email)`, `resetPassword(token, pw)`).
- [ ] **Step 2:** Real `AnnouncementsPage` (global + course-scoped).
- [ ] **Step 3:** Unread badge on the Inbox rail item.
- [ ] **Step 4:** `ResetPasswordPage` + route + "Forgot password?" wiring on the login page.
- [ ] **Step 5:** `npm run typecheck && npm run lint && npm run build`.
- [ ] **Step 6:** Commit `feat(frontend): Announcements feed + unread badge + password-reset page`.

---

### Task 8: `render.yaml` (Web Service + Cron Job) + docs + merge

**Files:** Create `backend/render.yaml`; update `.env.example` + `backend/README.md` + root README; merge.

```yaml
services:
  - type: web
    name: ocw-canvas-api
    runtime: docker
    dockerfilePath: backend/Dockerfile
    dockerContext: backend
    plan: free
    healthCheckPath: /api/health
    autoDeploy: true
    envVars:
      - key: DATABASE_URL          ;  sync: false
      - key: SUPABASE_URL          ;  sync: false
      - key: SUPABASE_SERVICE_KEY  ;  sync: false
      - key: CLAUDE_CODE_OAUTH_TOKEN ; sync: false   # or ANTHROPIC_API_KEY
      - key: AI_SOLUTION_GENERATION_ENABLED ; value: "true"
      - key: RESEND_API_KEY        ;  sync: false
      - key: OWNER_EMAIL           ;  sync: false
      - key: OWNER_EMAIL_FROM      ;  value: "onboarding@resend.dev"
      - key: JWT_SECRET            ;  generateValue: true
      - key: CRON_SECRET           ;  generateValue: true
      - key: FRONTEND_ORIGINS      ;  sync: false   # the GitHub Pages origin
      - key: FRONTEND_BASE_URL     ;  sync: false
  - type: cron
    name: ocw-canvas-tick
    runtime: docker
    dockerfilePath: backend/Dockerfile
    dockerContext: backend
    plan: free
    schedule: "0 * * * *"
    envVars:
      - key: SELF_URL              ;  sync: false   # the web service's URL
      - key: CRON_SECRET           ;  fromService: { name: ocw-canvas-api, type: web, envVarKey: CRON_SECRET }
    dockerCommand: sh -c 'curl -fsS -X POST "$SELF_URL/api/cron/tick" -H "X-Cron-Secret: $CRON_SECRET"'
```

> (YAML comment style above is shorthand — write proper `render.yaml` with each `envVars` entry as a real list item with `key:`/`sync:`/`value:`/`generateValue:`/`fromService:` keys. Don't ship secrets; `sync: false` means "set in the dashboard".)

- [ ] **Step 1:** Write `backend/render.yaml`. Update `backend/.env.example` (add `RESEND_API_KEY`, `OWNER_EMAIL_FROM`, `FRONTEND_BASE_URL`, `CRON_SECRET`) — and `frontend/.env.example` is unchanged. Update `backend/README.md` (email + cron section: how the tick works, the `X-Cron-Secret` header, idempotency).
- [ ] **Step 2:** Full check: `cd backend && uv run pytest -q && uv run ruff check .`; `cd frontend && npm run typecheck && npm run lint && npm run build`.
- [ ] **Step 3:** `git checkout master && git merge --no-ff feat/p4-email-cron -m "feat: P4 — email, announcements & cron"`.
- [ ] **Step 4:** Update root README "Status:" → P4 complete; commit on `master`.

---

## Self-Review notes
- **Spec coverage (P4 slice):** Resend graded/deadline/password-reset emails (§2, §5 step 5, §6 env) → Tasks 2, 3, 5; `email_log` (§3) → Task 1; `announcement` table + Announcements page + unread badge + mark-read (§3, §4 #4) → Tasks 1, 4, 7; `POST /cron/tick` 48h/24h deadline reminders + stuck-job re-drives + `cron_marker` idempotency (§3, §5 step 6, §6 render.yaml) → Tasks 1, 6; "AI announces you" hooked into grading (§5 step 5) → Task 3; password reset flow (§2 auth, §4 #1 login) → Tasks 5, 7; `render.yaml` Web Service + Cron Job (§6) → Task 8. Deferred: rich announcement avatars beyond initials (cosmetic); the "Recent Feedback" dashboard widget can now be filled from `kind=graded` announcements — light pass in Task 7 or left for P5 polish.
- **Mock boundary:** `email.send` ultimately calls `httpx.post` — tests monkeypatch one of them. Cron is a plain endpoint. AI seam still `ai._invoke`. No test makes a real network call.
- **Idempotency:** `cron_marker` keyed `deadline-<48|24>h:<assignment_id>`; `run_tick` twice ⇒ zero new side effects. Graded announcements are created once per grading event (each manual/AI grade), which is itself bounded (once per attempt; re-grade creates a new "Graded:" announcement on purpose).
- **One owner row:** `notify.announce_graded` looks up `db.query(AppUser).first()`; tolerates absence (announcement still created, email skipped).
