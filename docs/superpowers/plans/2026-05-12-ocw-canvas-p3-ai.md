# OCW Canvas — Phase 3 (AI: reference solutions & grading) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Close the homework loop's brain. Add `services/ai.py` (a single interface backed by the Claude Agent SDK with an Anthropic-API fallback, gated by env), the `ai_solution` table, solution-key resolution (official URL > official file > AI solution > none), AI reference-solution generation, AI submission grading (rubric + score + feedback), the "awaiting solution key" submission state, Retry handling, transcript logging, the "view reference solution" surface in the UI, and the Docker image (Python + Node) for the Render host.

**Architecture:** Builds on P2. New backend: `app/models/ai_solution.py` (migration 0003), `app/services/ai.py` (pure prompt builders + parsers + a thin `_invoke` that is the *only* code that talks to the SDK/API; everything mockable), `app/services/ai_jobs.py` (DB-side orchestration: create/refresh `ai_solution`, grade a submission, bounded retries, transcript logging via `storage`), `app/api/ai.py` (teacher-mode endpoints: generate-solution, regrade, get-solution). `create_submission` is extended to auto-kick grading when a key exists. New frontend: assignment-detail "Reference solution" panel renders `ai_solution.content_md` / shows `generating`/`failed`+Retry; submit panel shows "awaiting solution key" when none; teacher-mode "Generate solution" / "Re-grade" buttons. New ops: `backend/Dockerfile` (python:3.12-slim + Node + uv + Claude Code CLI).

**Tech Stack:** unchanged + two **optional** runtime deps: `anthropic` (Anthropic API fallback) and `claude-agent-sdk` (Agent SDK / OAuth path). Both imported lazily inside `_invoke`; their absence only matters when that exact backend is selected — tests never import them (they monkeypatch `_invoke`).

**Conventions:** branch `feat/p3-ai` (created from `master`). Backend cmds from `backend/`. Commit after each task. Tests mock all model + network calls.

---

### Task 1: `ai_solution` model + migration 0003

**Files:** Create `backend/app/models/ai_solution.py`; modify `backend/app/models/__init__.py`, `backend/app/models/assignment.py` (1:1 `ai_solution` relationship); create `backend/alembic/versions/0003_ai_solution.py`; test `backend/tests/test_ai_solution_models.py`.

- [ ] **Step 1:** `backend/app/models/ai_solution.py`

```python
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.base import TimestampMixin, _uuid

if TYPE_CHECKING:
    from app.models.assignment import Assignment


class AiSolution(Base, TimestampMixin):
    __tablename__ = "ai_solution"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    assignment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assignment.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    # pending | generating | ready | failed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    content_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    pdf_path: Mapped[str] = mapped_column(Text, nullable=False, default="")
    model: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    prompt_log_path: Mapped[str] = mapped_column(Text, nullable=False, default="")
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    attempts: Mapped[int] = mapped_column(String(0), nullable=False, default=0)  # see note

    assignment: Mapped["Assignment"] = relationship(back_populates="ai_solution")
```

> Note: `attempts` should be an `Integer`, not `String(0)` — that line is a placeholder; write `from sqlalchemy import Integer` and `Mapped[int] = mapped_column(Integer, nullable=False, default=0)`. It bounds retries from the cron tick (P4).

- [ ] **Step 2:** In `assignment.py` add to the `TYPE_CHECKING` block `from app.models.ai_solution import AiSolution` and on `Assignment` a `ai_solution: Mapped["AiSolution | None"] = relationship(back_populates="assignment", uselist=False, cascade="all, delete-orphan")`.

- [ ] **Step 3:** Update `models/__init__.py` to import & export `AiSolution`.

- [ ] **Step 4:** Migration 0003 — autogenerate (`DATABASE_URL=sqlite:///./_ag.db uv run alembic upgrade head` then `revision --autogenerate -m "ai_solution"`), rename to `0003_ai_solution.py`, `revision="0003"`, `down_revision="0002"`. Verify it `op.create_table('ai_solution', ...)`.

- [ ] **Step 5:** Verify chain applies (`alembic upgrade head` on a throwaway sqlite db lists `ai_solution`).

- [ ] **Step 6:** `backend/tests/test_ai_solution_models.py` — create a course+assignment, attach an `AiSolution(status="ready", content_md="...")`, commit; delete assignment → solution gone (cascade); uniqueness of `assignment_id` enforced (adding a 2nd raises on flush).

- [ ] **Step 7:** `uv run pytest -q && uv run ruff check .` → pass.

- [ ] **Step 8:** Commit `feat: ai_solution model + migration 0003`.

---

### Task 2: `services/ai.py` — backend selection, prompt builders, parsers, thin `_invoke`

**Files:** Create `backend/app/services/ai.py`; test `backend/tests/test_ai_service.py`.

Design contract:
- `ai_available() -> bool` — `True` iff `claude_code_oauth_token` or `anthropic_api_key` is set.
- `solution_generation_available() -> bool` — `ai_available() and settings.ai_solution_generation_enabled`.
- `model_id() -> str` — `"claude-sonnet-4-6"` (sensible default; configurable later).
- `SOLUTION_SYSTEM_PROMPT`, `GRADING_SYSTEM_PROMPT` — fixed role + strict JSON-output contract strings.
- `build_solution_prompt(*, title, description_md, points_possible) -> str`
- `build_grading_prompt(*, title, description_md, points_possible, key_text, key_note, submission_text, submission_files: list[str]) -> str` — `key_text` is the answer key markdown (AI solution or pasted official text) or `""`; `key_note` is e.g. `"The official solution is published at <url>; grade against standard real-analysis rigor."`; `submission_files` are the *names* placed in the work dir.
- `parse_json_block(text: str) -> dict` — strips ```json … ``` fences / leading prose, `json.loads`, raises `AiResponseError` on failure.
- `validate_solution(d: dict) -> dict` — requires `content_md: str` (non-empty), returns `{"content_md": ...}`.
- `validate_grading(d: dict, points_possible: float) -> dict` — requires `score` (clamps to `[0, points_possible]`), `feedback_md: str`, `rubric_breakdown: list[{criterion, points_awarded, points_possible, note}]` (each coerced; missing → `[]`); returns the normalized dict.
- `class AiUnavailable(RuntimeError)`, `class AiResponseError(RuntimeError)`.
- `_invoke(system_prompt: str, user_prompt: str, files: dict[str, bytes]) -> tuple[str, str]` — **the only impure function.** Returns `(response_text, transcript)`. Selects backend by env: OAuth token → `claude_agent_sdk` (write `files` into a temp cwd, run a one-shot query with most tools disabled, read the final message); else Anthropic key → `anthropic` client (`files` that are text are inlined; PDFs/images are sent as document/image blocks; `model_id()`, `max_tokens` generous). Raises `AiUnavailable` if neither credential. Imports of `claude_agent_sdk` / `anthropic` happen *inside* this function so the module imports cleanly without them.
- `generate_reference_solution(*, title, description_md, points_possible) -> tuple[dict, str]` — builds prompt, `_invoke`, parse+validate; returns `(solution_dict, transcript)`.
- `grade_submission(*, title, description_md, points_possible, key_text, key_note, submission_text, submission_files: dict[str,bytes]) -> tuple[dict, str]` — builds prompt with the file names, `_invoke(system, prompt, files=submission_files)`, parse+validate; returns `(grading_dict, transcript)`.

- [ ] **Step 1:** Write `services/ai.py` per the contract above (lazy SDK imports; pure builders/parsers; `_invoke` the single seam).

- [ ] **Step 2:** Write `tests/test_ai_service.py`:
  - `parse_json_block` handles plain JSON, fenced ```json blocks, and leading prose; raises `AiResponseError` on garbage.
  - `validate_grading` clamps `score` to `[0, points]`, defaults `rubric_breakdown` to `[]`, coerces rubric item floats; rejects missing `feedback_md`.
  - `validate_solution` rejects empty `content_md`.
  - `ai_available()` / `solution_generation_available()` reflect monkeypatched settings.
  - `generate_reference_solution` and `grade_submission` with `_invoke` monkeypatched to return canned JSON → return the validated dicts; the grading prompt mentions each submission filename and the points possible.

- [ ] **Step 3:** `uv run pytest -q && uv run ruff check .` → pass.

- [ ] **Step 4:** Commit `feat: services/ai.py — prompt builders, parsers, backend-selecting invoke`.

---

### Task 3: `services/ai_jobs.py` — DB-side orchestration (solution gen, grading, retries, transcripts)

**Files:** Create `backend/app/services/ai_jobs.py`; test `backend/tests/test_ai_jobs.py`.

- `resolve_key(db, assignment) -> tuple[str, str | None]` — returns `(kind, ref)`:
  - `("official_url", url)` if `official_solution_url`
  - `("official_file", storage_key)` if `official_solution_file_path`
  - `("ai", ai_solution_id)` if an `ai_solution` row with `status=="ready"` and non-empty `content_md`
  - `("none", None)` otherwise
- `has_key(db, assignment) -> bool` — `resolve_key(...)[0] != "none"`.
- `ensure_ai_solution(db, assignment_id) -> AiSolution` — get-or-create the 1:1 row (status `pending`).
- `run_solution_generation(db, assignment_id) -> AiSolution` — if `not ai.solution_generation_available()` leave/return the row as `pending` (no-op, with `error="AI solution generation disabled"`); else set `status=generating`, `attempts+=1`, commit; call `ai.generate_reference_solution(...)`; on success set `content_md`, `model`, `generated_at`, `status=ready`, `error=""`, write the transcript to Storage (`solutions/logs/<assignment_id>-solution.txt`) and store `prompt_log_path`; on `AiUnavailable`/`AiResponseError`/`Exception` set `status=failed`, `error=str(e)`; commit; return the row. Wrapped so it never raises.
- `grade_with_ai(db, submission_id) -> Grade | None` — load submission + assignment; `kind, ref = resolve_key(...)`; if `kind=="none"` → leave `submission.status="submitted"` and return `None`; set `submission.status="grading"`, commit; build `key_text`/`key_note`/`submission_files`:
  - `kind=="ai"` → `key_text = ai_solution.content_md`, `key_note=""`
  - `kind=="official_file"` → `key_text=""`, place the file bytes (`storage.read_bytes("solutions", ref)`) into `submission_files` under `solution<ext>`; `key_note="The attached file solution<ext> is the official answer key."`
  - `kind=="official_url"` → `key_text=""`, `key_note=f"The official solution is published at {ref}; grade against standard real-analysis rigor."`
  - submission files: for each `submission.file_paths` → `storage.read_bytes("submissions", p)` keyed by basename
  - call `ai.grade_submission(...)`; on success compute late penalty via `services.grading` (reuse the exact logic from `api/submissions.manual_grade`: `days_late`, `apply_late_penalty`, `final=max(0,score-penalty)`), upsert the `Grade` row (`graded_by="ai"`, `model=ai.model_id()`, `rubric_breakdown`, `feedback_md`, `graded_at`), write transcript to `solutions/logs/<submission_id>-grade.txt` → `prompt_log_path`, `submission.status="graded"`; on failure `submission.status="grading_failed"` (record nothing else); commit; return the grade or `None`. Never raises.
- `retry_stuck(db) -> dict` — (used by P4 cron) re-drive: `ai_solution` rows in `generating`/`failed` with `attempts < 3` → `run_solution_generation`; `submission` rows `status=="submitted"` where `has_key` → `grade_with_ai`; `submission` rows stuck `status=="grading"` → `grade_with_ai`. Returns counts.

Refactor: extract the late-penalty computation in `api/submissions.py` into `services/grading.py` as `compute_final(score, points, is_late, policy, value, due_at, submitted_at) -> tuple[penalty, final, pct]` (or a small helper in `ai_jobs` reused by both). Keep `manual_grade` calling the same helper so there's one code path.

- [ ] **Step 1:** Add the shared late-penalty helper (extend `services/grading.py` with `finalize_score(...)` — pure) and have `api/submissions.manual_grade` use it; keep its tests green.
- [ ] **Step 2:** Write `services/ai_jobs.py` per the contract.
- [ ] **Step 3:** Write `tests/test_ai_jobs.py` (monkeypatch `app.services.ai._invoke` and `storage._supabase_configured=False`, `storage._LOCAL_ROOT=tmp_path`):
  - `resolve_key` priority: official URL beats official file beats ready AI solution beats none.
  - `run_solution_generation` with `_invoke` returning good JSON → `status=ready`, `content_md` set, transcript file exists at the recorded `prompt_log_path`.
  - `run_solution_generation` with `solution_generation_available()` false → `status=pending`, `error` set, `_invoke` never called.
  - `run_solution_generation` with `_invoke` raising → `status=failed`, `error` set.
  - `grade_with_ai` against an AI key → `Grade` row with `graded_by="ai"`, `final_score`, `percentage`; `submission.status="graded"`; transcript file exists.
  - `grade_with_ai` with no key → returns `None`, submission stays `submitted`.
  - `grade_with_ai` with a late submission + `percent_per_day` policy → penalty applied (matches `services/grading`).
  - `retry_stuck` re-drives a now-keyed `submitted` submission to `graded`, and a `failed` solution with `attempts<3`.
- [ ] **Step 4:** `uv run pytest -q && uv run ruff check .` → pass.
- [ ] **Step 5:** Commit `feat: ai_jobs orchestration (solution gen, AI grading, retries, transcripts)`.

---

### Task 4: API — AI endpoints + auto-grade-on-submit

**Files:** Create `backend/app/api/ai.py`; modify `backend/app/main.py` (mount), `backend/app/api/submissions.py` (auto-kick grading), `backend/app/schemas/assignment.py` (add `AiSolutionOut`, `SolutionInfoOut`); test `backend/tests/test_ai_api.py`.

Endpoints (all behind `get_current_user`; the generate/regrade ones are "teacher" actions but auth is single-user so no extra guard):
- `GET /assignments/{id}/solution` → `SolutionInfoOut { key_kind: str, official_solution_url: str, ai_solution: AiSolutionOut | None, ai_available: bool, generation_available: bool }`.
- `POST /assignments/{id}/generate-solution` → calls `ai_jobs.ensure_ai_solution` then `ai_jobs.run_solution_generation`; returns `AiSolutionOut`. (If `generation_available()` is false, the row comes back `pending` with the `error` explaining why — 200, not an error, so the UI can show it.)
- `POST /submissions/{id}/regrade` → `ai_jobs.grade_with_ai`; returns the `GradeOut` if produced else 409 with detail `"no solution key — attach one or generate the AI solution first"`.

`AiSolutionOut` (ORMModel): `id, assignment_id, status, content_md, model, prompt_log_path, generated_at, error`.

In `api/submissions.create_submission`: after committing the submission, if `ai_jobs.has_key(db, a)` → call `ai_jobs.grade_with_ai(db, sub.id)` and `db.refresh(sub)` before returning (so the response already shows `grading`/`graded`). If no key, leave it `submitted` (the UI shows "awaiting solution key"). Wrap the grading call so a model failure doesn't 500 the submit (the submission is already saved).

- [ ] **Step 1:** Add `AiSolutionOut` + `SolutionInfoOut` to `schemas/assignment.py`.
- [ ] **Step 2:** Write `api/ai.py`; mount in `main.py`.
- [ ] **Step 3:** Extend `api/submissions.create_submission` to auto-grade when a key exists (mock-safe).
- [ ] **Step 4:** `tests/test_ai_api.py` (monkeypatch `ai._invoke`, storage local):
  - `GET .../solution` on a fresh assignment → `key_kind="none"`, `ai_solution=None`.
  - `POST .../generate-solution` with a fake `_invoke` → `status="ready"`, `content_md` non-empty; `GET .../solution` now `key_kind="ai"`.
  - submit on that assignment → response submission `status="graded"` with an AI `grade` (`graded_by="ai"`).
  - submit on a key-less assignment → `status="submitted"`, no grade.
  - `POST /submissions/{id}/regrade` on the key-less one → 409.
  - with `generation_available()` monkeypatched false: `POST .../generate-solution` → `status="pending"`, `error` mentions disabled; `_invoke` not called.
- [ ] **Step 5:** `uv run pytest -q && uv run ruff check .` → pass.
- [ ] **Step 6:** Commit `feat: AI endpoints + auto-grade-on-submit`.

---

### Task 5: Frontend — solution panel, awaiting-key state, teacher actions

**Files:** modify `frontend/src/api/types.ts` (`AiSolution`, `SolutionInfo`), `frontend/src/api/client.ts` (`getSolution`, `generateSolution`, `regrade`), `frontend/src/pages/AssignmentDetailPage.tsx` (use them), `frontend/src/pages/CourseAssignmentsPage.tsx` (teacher-mode per-row "Generate solution" / "Re-grade" — optional, can be on the detail page only).

- `AssignmentDetailPage`: on load also `api.getSolution(assignmentId)` → `info`. Submit panel: if `info.key_kind === "none"` show a note "No solution key yet — your submission will be recorded and graded once a key is attached or the AI solution is generated." Submit still works. The "Reference solution" toggle: if `info.ai_solution?.status === "ready"` render `<Markdown>{content_md}</Markdown>`; if `"generating"` show "Generating…"; if `"failed"` show the `error` + (teacher) a "Retry" button → `generateSolution` again; if `info.official_solution_url` show the link; else "No solution available." Teacher-mode: a "Generate AI solution" button (disabled / explanatory text if `!info.generation_available`) and per-submission "Re-grade with AI" button (calls `regrade`, then `reloadA`). After any of these, refresh `info` + the assignment.
- Recent Feedback (Dashboard): now that AI grades exist, optionally list recently graded submissions — keep it a light pass or leave as the P2 stub; not required for P3 sign-off.

- [ ] **Step 1:** Types + client methods.
- [ ] **Step 2:** Wire into `AssignmentDetailPage` (solution info, awaiting-key note, Retry, Generate, Re-grade).
- [ ] **Step 3:** `npm run typecheck && npm run lint && npm run build` → pass.
- [ ] **Step 4:** Commit `feat(frontend): AI solution panel, awaiting-key state, generate/re-grade actions`.

---

### Task 6: Dockerfile (Python 3.12 + Node + Claude Code CLI)

**Files:** Create `backend/Dockerfile`, `backend/.dockerignore`.

```dockerfile
FROM python:3.12-slim

# Node (for the Claude Code CLI that the Agent SDK drives) + curl
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates gnupg \
 && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && rm -rf /var/lib/apt/lists/*

# uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Claude Code CLI (the Agent SDK shells out to it); harmless if the API-key fallback is used instead
RUN npm install -g @anthropic-ai/claude-code || true

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY . .

ENV PORT=8000
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
```

`.dockerignore`: `_local_storage/`, `*.db`, `.venv/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `tests/`.

> Add `anthropic` and `claude-agent-sdk` to `pyproject.toml` `dependencies` so `uv sync` installs them in the image. They're optional at *import* time (lazy in `_invoke`) but present at *runtime* in the deployed image. If `uv lock` can't resolve `claude-agent-sdk` for some reason, keep it out of the lock and `pip install` it in the Dockerfile instead — but try the clean path first.

- [ ] **Step 1:** Add `anthropic>=0.40` and `claude-agent-sdk>=0.1` to `backend/pyproject.toml` dependencies; `uv lock` (or `uv sync`) to refresh `uv.lock`. If resolution fails for `claude-agent-sdk`, drop it from deps and install it via the Dockerfile `npm`/`pip` line instead; note the decision in `backend/README.md`.
- [ ] **Step 2:** Write `backend/Dockerfile` and `backend/.dockerignore`.
- [ ] **Step 3:** `uv run pytest -q && uv run ruff check .` → still pass (new deps don't break anything; tests don't import them).
- [ ] **Step 4:** Commit `feat: backend Dockerfile (python+node+claude-code) + AI deps`.

---

### Task 7: Docs + merge

- [ ] **Step 1:** Update `backend/README.md` with the AI env vars (`CLAUDE_CODE_OAUTH_TOKEN` *or* `ANTHROPIC_API_KEY`, `AI_SOLUTION_GENERATION_ENABLED`) and how the fallback works; note the optional smoke script idea (gated, not in CI).
- [ ] **Step 2:** Full check: `cd backend && uv run pytest -q && uv run ruff check .`; `cd frontend && npm run typecheck && npm run lint && npm run build`.
- [ ] **Step 3:** `git checkout master && git merge --no-ff feat/p3-ai -m "feat: P3 — AI reference solutions & grading"`.
- [ ] **Step 4:** Update root README "Status:" to mention P3 complete; commit on `master`.

---

## Self-Review notes
- **Spec coverage (P3 slice):** `services/ai.py` over Agent SDK with API-key fallback + `AI_SOLUTION_GENERATION_ENABLED` (§2, §5) → Tasks 2, 6; `ai_solution` table (§3) → Task 1; solution-key resolution official-url > official-file > AI > none (§5 step 2) → Task 3 (`resolve_key`); AI generation + AI grading producing rubric/score/feedback (§5 steps 2,4) → Tasks 3, 4; "awaiting solution key" submission state (§5 step 3) → Task 4 (`create_submission` leaves `submitted`) + Task 5 (UI note); Retry handling + bounded retries + transcripts (§5 "Failure handling", §8) → Task 3 (`attempts`, `retry_stuck`, log paths); "view reference solution" toggle (§4 8b) → Task 5; Docker image python+node (§2, §6, P3 outcome) → Task 6. Deferred: PDF rendering of AI solutions (§10 — markdown-only for now; `pdf_path` exists, unused); `available_at` lock enforcement (small P5 polish); the cron re-drive that *calls* `retry_stuck` lands in P4.
- **Mock boundary:** the *only* impure model/network seam is `ai._invoke`; every test monkeypatches it (plus `storage._supabase_configured`/`_LOCAL_ROOT`). `anthropic`/`claude-agent-sdk` are never imported by the test suite.
- **One grading code path:** `services/grading.finalize_score` (new pure helper) is used by both `api/submissions.manual_grade` and `ai_jobs.grade_with_ai`.
