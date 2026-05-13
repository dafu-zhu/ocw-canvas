# OCW Canvas — Phase 2 (Assignments & Submissions) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the full homework *tracking* loop (no AI yet): assignments under assignment groups, file/text submissions stored in Supabase Storage, late flagging, manual grade entry, and a Canvas-style Grades page driven by a tested rollup function.

**Architecture:** Builds on P1. New backend: `assignment` CRUD, `submission` + `grade` models (migration 0002), a `services/storage.py` Supabase-Storage client (REST via httpx; signed URLs), a `services/grading.py` of pure rollup/late-penalty functions, and a gradebook endpoint. New frontend: Assignments list + Assignment detail (with submit panel + file upload), the Grades page, assignment + assignment-group edit modals, and the To-Do widgets fed real data.

**Tech Stack:** unchanged from P1 (FastAPI/SQLAlchemy/Alembic/httpx; React/Vite/TS). Supabase Storage is reached over its REST API with the service key.

**Conventions:** same as the P1 plan. Work on branch `feat/p2-assignments` (already created). Backend cmds from `backend/`, frontend cmds from `frontend/`. Commit after each task. `tmpdb` env trick for alembic: `DATABASE_URL=sqlite:///./_x.db uv run alembic ...`.

---

### Task 1: `submission` + `grade` models and migration 0002

**Files:**
- Create: `backend/app/models/submission.py`
- Modify: `backend/app/models/__init__.py` (export `Submission`, `Grade`)
- Modify: `backend/app/models/assignment.py` (add `submissions` relationship to `Assignment`)
- Create: `backend/alembic/versions/0002_submissions_grades.py`
- Test: `backend/tests/test_submission_models.py`

- [ ] **Step 1: Write `backend/app/models/submission.py`**

```python
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.base import TimestampMixin, _uuid

if TYPE_CHECKING:
    from app.models.assignment import Assignment


class Submission(Base, TimestampMixin):
    __tablename__ = "submission"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    assignment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assignment.id", ondelete="CASCADE"), nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_late: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    text_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_paths: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="me")  # me | ai_demo
    # submitted | grading | graded | grading_failed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="submitted")

    assignment: Mapped["Assignment"] = relationship(back_populates="submissions")
    grade: Mapped["Grade | None"] = relationship(
        back_populates="submission", uselist=False, cascade="all, delete-orphan"
    )


class Grade(Base, TimestampMixin):
    __tablename__ = "grade"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    submission_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("submission.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    score: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    score_out_of: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False, default=100)
    late_penalty_applied: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    final_score: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    percentage: Mapped[float] = mapped_column(Numeric(8, 3), nullable=False, default=0)
    feedback_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    rubric_breakdown: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    graded_by: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")  # manual | ai
    model: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    prompt_log_path: Mapped[str] = mapped_column(Text, nullable=False, default="")
    graded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    submission: Mapped["Submission"] = relationship(back_populates="grade")
```

- [ ] **Step 2: Add the `submissions` relationship to `Assignment` in `backend/app/models/assignment.py`** — inside the `Assignment` class, after the `group` relationship, add:

```python
    submissions: Mapped[list["Submission"]] = relationship(
        back_populates="assignment", cascade="all, delete-orphan", order_by="Submission.attempt_number"
    )
```

And in the `TYPE_CHECKING` block of that file add `from app.models.submission import Submission`. (The `if TYPE_CHECKING:` block currently imports only `Course`; add the line.)

- [ ] **Step 3: Update `backend/app/models/__init__.py`**

```python
from app.models.assignment import Assignment, AssignmentGroup
from app.models.course import Course
from app.models.module import Module, ModuleItem
from app.models.submission import Grade, Submission
from app.models.user import AppUser

__all__ = [
    "AppUser",
    "Course",
    "Module",
    "ModuleItem",
    "AssignmentGroup",
    "Assignment",
    "Submission",
    "Grade",
]
```

- [ ] **Step 4: Autogenerate migration 0002**

```bash
cd backend
rm -f _ag.db
DATABASE_URL="sqlite:///./_ag.db" uv run alembic upgrade head            # apply 0001
DATABASE_URL="sqlite:///./_ag.db" uv run alembic revision --autogenerate -m "submissions and grades"
rm -f _ag.db
```
Rename the new file to `alembic/versions/0002_submissions_grades.py`; set `revision = "0002"`, `down_revision = "0001"`. Verify it has `op.create_table("submission", ...)` and `op.create_table("grade", ...)`.

- [ ] **Step 5: Verify the chain applies**

```bash
rm -f _v.db
DATABASE_URL="sqlite:///./_v.db" uv run alembic upgrade head
DATABASE_URL="sqlite:///./_v.db" uv run python -c "import sqlite3; print(sorted(r[0] for r in sqlite3.connect('_v.db').execute(\"select name from sqlite_master where type='table'\")))"
rm -f _v.db
```
Expected list includes `grade` and `submission` alongside the P1 tables and `alembic_version`.

- [ ] **Step 6: Write `backend/tests/test_submission_models.py`**

```python
from datetime import UTC, datetime

from app.models import Assignment, Course, Grade, Submission


def test_submission_grade_cascade(db):
    c = Course(code="X", title="X")
    db.add(c)
    db.flush()
    a = Assignment(course_id=c.id, title="PS1", points_possible=100)
    db.add(a)
    db.flush()
    s = Submission(assignment_id=a.id, submitted_at=datetime.now(UTC), file_paths=["p/x.pdf"])
    db.add(s)
    db.flush()
    db.add(Grade(submission_id=s.id, score=90, score_out_of=100, final_score=90, percentage=90))
    db.commit()

    db.delete(a)
    db.commit()
    assert db.query(Submission).count() == 0
    assert db.query(Grade).count() == 0
```

- [ ] **Step 7: Run tests + ruff**

Run: `cd backend && uv run pytest -q && uv run ruff check .`
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
cd ..
git add backend/app/models backend/alembic backend/tests/test_submission_models.py
git commit -m "feat: submission + grade models and migration 0002"
```

---

### Task 2: Grading math (`services/grading.py`) — pure, tested

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/grading.py`
- Test: `backend/tests/test_grading.py`

- [ ] **Step 1: Write `backend/app/services/__init__.py`** (empty)

```python
```

- [ ] **Step 2: Write the failing test `backend/tests/test_grading.py`**

```python
from datetime import UTC, datetime, timedelta

from app.services.grading import (
    GradeRow,
    GroupSpec,
    apply_late_penalty,
    course_total,
    group_percentage,
)


def test_apply_late_penalty_none_and_flag_only_keep_full_score():
    assert apply_late_penalty(score=80, points=100, is_late=True, policy="none", value=None) == (80, 0)
    assert apply_late_penalty(score=80, points=100, is_late=True, policy="flag_only", value=None) == (80, 0)
    assert apply_late_penalty(score=80, points=100, is_late=False, policy="percent_per_day", value=10, days_late=3) == (80, 0)


def test_apply_late_penalty_percent_per_day():
    # 3 days late at 10%/day on a 100-pt assignment = 30 pts off; clamp at 0
    assert apply_late_penalty(score=80, points=100, is_late=True, policy="percent_per_day", value=10, days_late=3) == (80, 30)
    assert apply_late_penalty(score=20, points=100, is_late=True, policy="percent_per_day", value=50, days_late=3) == (20, 100)


def test_group_percentage_drops_lowest():
    rows = [
        GradeRow(final_score=100, points=100),
        GradeRow(final_score=80, points=100),
        GradeRow(final_score=40, points=100),  # dropped
    ]
    # without drop: 220/300 = 73.33...
    assert round(group_percentage(rows, drop_lowest_n=0), 2) == 73.33
    # drop 1 lowest (the 40): 180/200 = 90.0
    assert group_percentage(rows, drop_lowest_n=1) == 90.0
    # empty group -> None (no graded work)
    assert group_percentage([], drop_lowest_n=0) is None


def test_course_total_weighted_normalizes_over_graded_groups():
    groups = [
        GroupSpec(name="Problem Sets", weight=50, drop_lowest_n=1, rows=[GradeRow(100, 100), GradeRow(80, 100), GradeRow(40, 100)]),  # pct 90
        GroupSpec(name="Midterm", weight=20, drop_lowest_n=0, rows=[GradeRow(70, 100)]),  # pct 70
        GroupSpec(name="Final", weight=30, drop_lowest_n=0, rows=[]),  # ungraded
    ]
    # only PS (50) + Midterm (20) have work -> renormalize: (90*50 + 70*20) / 70 = (4500+1400)/70 = 84.2857
    assert round(course_total(groups, only_graded=True), 2) == 84.29
    # if every group must count, ungraded counts as 0%: (90*50 + 70*20 + 0*30)/100 = 59.0
    assert round(course_total(groups, only_graded=False), 2) == 59.0


def test_course_total_unweighted_is_flat_points():
    groups = [
        GroupSpec(name="A", weight=None, drop_lowest_n=0, rows=[GradeRow(90, 100)]),
        GroupSpec(name="B", weight=None, drop_lowest_n=0, rows=[GradeRow(40, 50)]),
    ]
    # flat: (90+40) / (100+50) = 130/150 = 86.67
    assert round(course_total(groups, only_graded=True), 2) == 86.67


def test_days_late_helper_floor():
    from app.services.grading import days_late
    due = datetime(2026, 4, 1, 23, 59, tzinfo=UTC)
    assert days_late(due, due + timedelta(hours=1)) == 1
    assert days_late(due, due + timedelta(days=2, hours=1)) == 3
    assert days_late(due, due - timedelta(hours=1)) == 0
```

- [ ] **Step 3: Run it to confirm it fails**

Run: `cd backend && uv run pytest tests/test_grading.py -q`
Expected: FAIL (module `app.services.grading` doesn't exist).

- [ ] **Step 4: Write `backend/app/services/grading.py`**

```python
"""Pure grading math: late penalties, per-group percentages with drop rules, and the course rollup.

No I/O — everything takes plain data so it is exhaustively unit-tested.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class GradeRow:
    final_score: float
    points: float


@dataclass
class GroupSpec:
    name: str
    weight: float | None
    drop_lowest_n: int
    rows: list[GradeRow] = field(default_factory=list)


def days_late(due_at: datetime, submitted_at: datetime) -> int:
    """Whole days late (1-based: any time past the deadline counts as day 1). 0 if on time."""
    if submitted_at <= due_at:
        return 0
    delta = submitted_at - due_at
    return int(math.floor(delta.total_seconds() / 86400)) + 1


def apply_late_penalty(
    *,
    score: float,
    points: float,
    is_late: bool,
    policy: str,
    value: float | None,
    days_late: int = 0,
) -> tuple[float, float]:
    """Return (score_unchanged, penalty_points). `score` itself is never altered here;
    the caller computes final_score = max(0, score - penalty)."""
    if not is_late or policy in ("none", "flag_only"):
        return score, 0.0
    if policy == "percent_per_day":
        pct = (value or 0) * max(days_late, 1)
        penalty = min(points, points * pct / 100.0)
        return score, penalty
    return score, 0.0


def group_percentage(rows: list[GradeRow], drop_lowest_n: int) -> float | None:
    """Σ final_score / Σ points over the group's graded rows, after dropping the N
    lowest-by-percentage. None if there are no graded rows."""
    graded = [r for r in rows if r.points > 0]
    if not graded:
        return None
    if drop_lowest_n > 0:
        graded = sorted(graded, key=lambda r: r.final_score / r.points)[drop_lowest_n:]
    if not graded:
        return None
    total_pts = sum(r.points for r in graded)
    if total_pts == 0:
        return None
    return sum(r.final_score for r in graded) / total_pts * 100.0


def course_total(groups: list[GroupSpec], *, only_graded: bool) -> float | None:
    """Weighted sum of group percentages if every group has a weight; otherwise a flat
    points total. With only_graded=True, ungraded groups are excluded and the weights of
    the remaining groups are renormalized; with only_graded=False, an ungraded weighted
    group contributes 0%."""
    weighted = bool(groups) and all(g.weight is not None for g in groups)
    if not weighted:
        rows = [r for g in groups for r in g.rows if r.points > 0]
        if not rows:
            return None
        total_pts = sum(r.points for r in rows)
        if total_pts == 0:
            return None
        return sum(r.final_score for r in rows) / total_pts * 100.0

    contributions: list[tuple[float, float]] = []  # (weight, percentage)
    for g in groups:
        pct = group_percentage(g.rows, g.drop_lowest_n)
        if pct is None:
            if only_graded:
                continue
            pct = 0.0
        contributions.append((g.weight or 0.0, pct))
    if not contributions:
        return None
    weight_sum = sum(w for w, _ in contributions)
    if weight_sum == 0:
        return None
    return sum(w * p for w, p in contributions) / weight_sum
```

- [ ] **Step 5: Run the test until green**

Run: `cd backend && uv run pytest tests/test_grading.py -q`
Expected: PASS (all 6 tests).

- [ ] **Step 6: Run full suite + ruff**

Run: `cd backend && uv run pytest -q && uv run ruff check .`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
cd ..
git add backend/app/services backend/tests/test_grading.py
git commit -m "feat: pure grading math (late penalty, group %, course rollup) + tests"
```

---

### Task 3: Supabase Storage service

**Files:**
- Create: `backend/app/services/storage.py`
- Test: `backend/tests/test_storage.py`

> Design: a thin wrapper over Supabase Storage's REST API (`/storage/v1/object/...`). When `SUPABASE_URL`/`SUPABASE_SERVICE_KEY` are unset (local dev / CI / tests), it falls back to a **local on-disk store** under `backend/_local_storage/` so the app is fully runnable without a Supabase project. Path construction is pure and tested.

- [ ] **Step 1: Write `backend/app/services/storage.py`**

```python
"""File storage for submissions and AI solutions.

Backend = Supabase Storage REST API when configured, else a local on-disk store
(so the app runs without any cloud setup). All paths are bucket-relative.
"""
from __future__ import annotations

import os
from pathlib import Path

import httpx

from app.config import get_settings

_settings = get_settings()
_LOCAL_ROOT = Path(__file__).resolve().parents[2] / "_local_storage"


def _supabase_configured() -> bool:
    return bool(_settings.supabase_url and _settings.supabase_service_key)


def submission_path(assignment_id: str, submission_id: str, filename: str) -> str:
    safe = os.path.basename(filename).replace("/", "_").replace("\\", "_")
    return f"submissions/{assignment_id}/{submission_id}/{safe}"


def solution_path(assignment_id: str) -> str:
    return f"solutions/{assignment_id}.md"


def upload_bytes(bucket: str, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    """Store `data` at bucket/key. Returns the bucket-relative key."""
    if _supabase_configured():
        url = f"{_settings.supabase_url}/storage/v1/object/{bucket}/{key}"
        headers = {
            "Authorization": f"Bearer {_settings.supabase_service_key}",
            "Content-Type": content_type,
            "x-upsert": "true",
        }
        resp = httpx.post(url, headers=headers, content=data, timeout=30)
        resp.raise_for_status()
    else:
        dest = _LOCAL_ROOT / bucket / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    return key


def read_bytes(bucket: str, key: str) -> bytes:
    if _supabase_configured():
        url = f"{_settings.supabase_url}/storage/v1/object/{bucket}/{key}"
        headers = {"Authorization": f"Bearer {_settings.supabase_service_key}"}
        resp = httpx.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.content
    return (_LOCAL_ROOT / bucket / key).read_bytes()


def signed_url(bucket: str, key: str, expires_in: int = 3600) -> str:
    """A short-lived download URL. For the local backend, returns an /api route the app serves."""
    if _supabase_configured():
        url = f"{_settings.supabase_url}/storage/v1/object/sign/{bucket}/{key}"
        headers = {
            "Authorization": f"Bearer {_settings.supabase_service_key}",
            "Content-Type": "application/json",
        }
        resp = httpx.post(url, headers=headers, json={"expiresIn": expires_in}, timeout=30)
        resp.raise_for_status()
        signed = resp.json()["signedURL"]
        return f"{_settings.supabase_url}/storage/v1{signed}"
    # local: served by the backend (see api/files.py)
    return f"/api/files/{bucket}/{key}"
```

- [ ] **Step 2: Write `backend/tests/test_storage.py`**

```python
from app.services import storage


def test_path_builders():
    assert storage.submission_path("a1", "s1", "proof.pdf") == "submissions/a1/s1/proof.pdf"
    assert storage.submission_path("a1", "s1", "../etc/passwd") == "submissions/a1/s1/passwd"
    assert storage.submission_path("a1", "s1", "x\\y.png") == "submissions/a1/s1/x_y.png"
    assert storage.solution_path("a1") == "solutions/a1.md"


def test_local_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "_LOCAL_ROOT", tmp_path)
    monkeypatch.setattr(storage, "_supabase_configured", lambda: False)
    key = storage.upload_bytes("submissions", "submissions/a/s/x.txt", b"hello", "text/plain")
    assert key == "submissions/a/s/x.txt"
    assert storage.read_bytes("submissions", key) == b"hello"
    assert storage.signed_url("submissions", key).startswith("/api/files/")
```

- [ ] **Step 3: Add `_local_storage/` to `.gitignore`** — append to repo-root `.gitignore`:

```
# Local file-storage fallback
backend/_local_storage/
```

- [ ] **Step 4: Run tests + ruff**

Run: `cd backend && uv run pytest -q && uv run ruff check .`
Expected: pass.

- [ ] **Step 5: Commit**

```bash
cd ..
git add backend/app/services/storage.py backend/tests/test_storage.py .gitignore
git commit -m "feat: storage service (Supabase Storage REST, local on-disk fallback)"
```

---

### Task 4: Assignment CRUD API + schemas

**Files:**
- Create: `backend/app/schemas/assignment.py`
- Create: `backend/app/api/assignments.py`
- Modify: `backend/app/main.py` (mount the `assignments` router)
- Modify: `backend/app/schemas/course.py` (extend `AssignmentSummaryOut`? — no; leave it, the detail tree already returns summaries)
- Test: `backend/tests/test_assignments_api.py`

- [ ] **Step 1: Write `backend/app/schemas/assignment.py`**

```python
from datetime import datetime

from app.schemas.common import ORMModel


class AssignmentBase(ORMModel):
    assignment_group_id: str | None = None
    title: str
    description_md: str = ""
    points_possible: float = 100
    due_at: datetime | None = None
    available_at: datetime | None = None
    accepts_files: bool = True
    accepts_text: bool = True
    official_solution_url: str = ""
    official_solution_file_path: str = ""
    late_policy: str = "flag_only"  # none | flag_only | percent_per_day
    late_value: float | None = None
    position: int = 0
    published: bool = True


class AssignmentCreate(AssignmentBase):
    pass


class AssignmentUpdate(AssignmentBase):
    pass


class AssignmentOut(AssignmentBase):
    id: str
    course_id: str


class RubricItem(ORMModel):
    criterion: str
    points_awarded: float
    points_possible: float
    note: str = ""


class GradeOut(ORMModel):
    id: str
    submission_id: str
    score: float
    score_out_of: float
    late_penalty_applied: float
    final_score: float
    percentage: float
    feedback_md: str
    rubric_breakdown: list[RubricItem] = []
    graded_by: str
    model: str
    graded_at: datetime | None = None


class SubmissionOut(ORMModel):
    id: str
    assignment_id: str
    attempt_number: int
    submitted_at: datetime | None = None
    is_late: bool
    text_body: str | None = None
    file_paths: list[str] = []
    source: str
    status: str
    grade: GradeOut | None = None


class AssignmentDetailOut(AssignmentOut):
    submissions: list[SubmissionOut] = []
```

- [ ] **Step 2: Write `backend/app/api/assignments.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import Assignment, Course
from app.schemas.assignment import AssignmentCreate, AssignmentDetailOut, AssignmentOut, AssignmentUpdate

router = APIRouter(tags=["assignments"], dependencies=[Depends(get_current_user)])

_VALID_LATE = {"none", "flag_only", "percent_per_day"}


def _validate(payload: AssignmentBase) -> None:  # noqa: F821 (AssignmentBase imported below)
    if payload.late_policy not in _VALID_LATE:
        raise HTTPException(422, f"invalid late_policy {payload.late_policy!r}")


from app.schemas.assignment import AssignmentBase  # noqa: E402


@router.get("/courses/{course_id}/assignments", response_model=list[AssignmentOut])
def list_assignments(course_id: str, db: Session = Depends(get_db)) -> list[Assignment]:
    if db.get(Course, course_id) is None:
        raise HTTPException(404, "course not found")
    return (
        db.query(Assignment)
        .filter(Assignment.course_id == course_id)
        .order_by(Assignment.position, Assignment.title)
        .all()
    )


@router.post("/courses/{course_id}/assignments", response_model=AssignmentOut, status_code=201)
def create_assignment(
    course_id: str, payload: AssignmentCreate, db: Session = Depends(get_db)
) -> Assignment:
    if db.get(Course, course_id) is None:
        raise HTTPException(404, "course not found")
    _validate(payload)
    a = Assignment(course_id=course_id, **payload.model_dump())
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def _get(db: Session, assignment_id: str) -> Assignment:
    a = db.get(Assignment, assignment_id)
    if a is None:
        raise HTTPException(404, "assignment not found")
    return a


@router.get("/assignments/{assignment_id}", response_model=AssignmentDetailOut)
def get_assignment(assignment_id: str, db: Session = Depends(get_db)) -> Assignment:
    return _get(db, assignment_id)


@router.put("/assignments/{assignment_id}", response_model=AssignmentOut)
def update_assignment(
    assignment_id: str, payload: AssignmentUpdate, db: Session = Depends(get_db)
) -> Assignment:
    a = _get(db, assignment_id)
    _validate(payload)
    for k, v in payload.model_dump().items():
        setattr(a, k, v)
    db.commit()
    db.refresh(a)
    return a


@router.delete("/assignments/{assignment_id}", status_code=204)
def delete_assignment(assignment_id: str, db: Session = Depends(get_db)) -> None:
    db.delete(_get(db, assignment_id))
    db.commit()
```

> Clean up the `_validate` / late-`from ... import AssignmentBase` ordering so ruff is happy — put `from app.schemas.assignment import AssignmentBase, AssignmentCreate, ...` all at the top with the other imports; the `# noqa` hints above are only there because the snippet shows the function before that import. Final file: imports at top, then router, then `_validate`, then the endpoints.

- [ ] **Step 3: Mount in `backend/app/main.py`** — add `assignments` to the import line and `app.include_router(assignments.router, prefix="/api")` after the others.

- [ ] **Step 4: Write `backend/tests/test_assignments_api.py`**

```python
def _course(client):
    return client.post("/api/courses", json={"code": "X", "title": "X"}).json()["id"]


def test_assignment_crud(logged_in_client):
    client = logged_in_client
    cid = _course(client)
    g = client.post(f"/api/courses/{cid}/assignment-groups", json={"name": "PS", "weight": 100}).json()

    r = client.post(
        f"/api/courses/{cid}/assignments",
        json={"title": "Problem Set 1", "points_possible": 100, "assignment_group_id": g["id"]},
    )
    assert r.status_code == 201
    aid = r.json()["id"]

    bad = client.post(f"/api/courses/{cid}/assignments", json={"title": "bad", "late_policy": "weird"})
    assert bad.status_code == 422

    assert [a["title"] for a in client.get(f"/api/courses/{cid}/assignments").json()] == ["Problem Set 1"]
    detail = client.get(f"/api/assignments/{aid}").json()
    assert detail["title"] == "Problem Set 1"
    assert detail["submissions"] == []

    client.put(f"/api/assignments/{aid}", json={"title": "Problem Set 1 — Sequences", "points_possible": 100})
    assert client.get(f"/api/assignments/{aid}").json()["title"] == "Problem Set 1 — Sequences"
    assert client.delete(f"/api/assignments/{aid}").status_code == 204
    assert client.get(f"/api/assignments/{aid}").status_code == 404
```

- [ ] **Step 5: Run tests + ruff**

Run: `cd backend && uv run pytest -q && uv run ruff check .`
Expected: pass.

- [ ] **Step 6: Commit**

```bash
cd ..
git add backend/app/schemas/assignment.py backend/app/api/assignments.py backend/app/main.py backend/tests/test_assignments_api.py
git commit -m "feat: assignment CRUD API + schemas"
```

---

### Task 5: Submissions API + file upload + local file serving

**Files:**
- Create: `backend/app/api/submissions.py`
- Create: `backend/app/api/files.py` (serves the local-storage fallback; no-op route shape when Supabase is configured — it still works, just unused)
- Modify: `backend/app/main.py` (mount both routers)
- Test: `backend/tests/test_submissions_api.py`

- [ ] **Step 1: Write `backend/app/api/submissions.py`**

```python
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import Assignment, Grade, Submission
from app.schemas.assignment import GradeOut, SubmissionOut
from app.services import storage
from app.services.grading import apply_late_penalty, days_late

router = APIRouter(tags=["submissions"], dependencies=[Depends(get_current_user)])


def _next_attempt(db: Session, assignment_id: str) -> int:
    n = (
        db.query(Submission)
        .filter(Submission.assignment_id == assignment_id)
        .order_by(Submission.attempt_number.desc())
        .first()
    )
    return (n.attempt_number + 1) if n else 1


@router.post("/assignments/{assignment_id}/submissions", response_model=SubmissionOut, status_code=201)
async def create_submission(
    assignment_id: str,
    text_body: str | None = Form(default=None),
    files: list[UploadFile] | None = None,
    db: Session = Depends(get_db),
) -> Submission:
    a = db.get(Assignment, assignment_id)
    if a is None:
        raise HTTPException(404, "assignment not found")
    now = datetime.now(UTC)
    is_late = a.due_at is not None and now > a.due_at
    sub = Submission(
        assignment_id=assignment_id,
        attempt_number=_next_attempt(db, assignment_id),
        submitted_at=now,
        is_late=is_late,
        text_body=text_body,
        file_paths=[],
        status="submitted",
    )
    db.add(sub)
    db.flush()  # need sub.id for file paths
    paths: list[str] = []
    for f in files or []:
        data = await f.read()
        key = storage.submission_path(assignment_id, sub.id, f.filename or "file")
        storage.upload_bytes("submissions", key, data, f.content_type or "application/octet-stream")
        paths.append(key)
    sub.file_paths = paths
    db.commit()
    db.refresh(sub)
    return sub


@router.get("/assignments/{assignment_id}/submissions", response_model=list[SubmissionOut])
def list_submissions(assignment_id: str, db: Session = Depends(get_db)) -> list[Submission]:
    return (
        db.query(Submission)
        .filter(Submission.assignment_id == assignment_id)
        .order_by(Submission.attempt_number)
        .all()
    )


@router.post("/submissions/{submission_id}/grade", response_model=GradeOut)
def manual_grade(
    submission_id: str,
    score: float = Form(...),
    feedback_md: str = Form(default=""),
    db: Session = Depends(get_db),
) -> Grade:
    sub = db.get(Submission, submission_id)
    if sub is None:
        raise HTTPException(404, "submission not found")
    a = db.get(Assignment, sub.assignment_id)
    points = float(a.points_possible)
    dl = days_late(a.due_at, sub.submitted_at) if (a.due_at and sub.submitted_at) else 0
    _, penalty = apply_late_penalty(
        score=score,
        points=points,
        is_late=sub.is_late,
        policy=a.late_policy,
        value=float(a.late_value) if a.late_value is not None else None,
        days_late=dl,
    )
    final = max(0.0, score - penalty)
    g = sub.grade or Grade(submission_id=sub.id)
    g.score = score
    g.score_out_of = points
    g.late_penalty_applied = penalty
    g.final_score = final
    g.percentage = (final / points * 100.0) if points else 0.0
    g.feedback_md = feedback_md
    g.graded_by = "manual"
    g.graded_at = datetime.now(UTC)
    if sub.grade is None:
        db.add(g)
    sub.status = "graded"
    db.commit()
    db.refresh(g)
    return g
```

- [ ] **Step 2: Write `backend/app/api/files.py`** (local-storage download route; harmless when Supabase is used)

```python
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.auth import get_current_user
from app.services import storage

router = APIRouter(prefix="/files", tags=["files"], dependencies=[Depends(get_current_user)])


@router.get("/{bucket}/{key:path}")
def get_file(bucket: str, key: str) -> Response:
    if bucket not in ("submissions", "solutions"):
        raise HTTPException(404, "unknown bucket")
    try:
        data = storage.read_bytes(bucket, key)
    except FileNotFoundError as exc:
        raise HTTPException(404, "file not found") from exc
    return Response(content=data, media_type="application/octet-stream")
```

- [ ] **Step 3: Mount both in `backend/app/main.py`** — add `files`, `submissions` to the import and `include_router` lines.

- [ ] **Step 4: Write `backend/tests/test_submissions_api.py`**

```python
import io


def _setup(client):
    cid = client.post("/api/courses", json={"code": "X", "title": "X"}).json()["id"]
    g = client.post(f"/api/courses/{cid}/assignment-groups", json={"name": "PS", "weight": 100}).json()
    aid = client.post(
        f"/api/courses/{cid}/assignments",
        json={"title": "PS1", "points_possible": 100, "assignment_group_id": g["id"]},
    ).json()["id"]
    return aid


def test_submit_and_manual_grade(logged_in_client, tmp_path, monkeypatch):
    from app.services import storage

    monkeypatch.setattr(storage, "_LOCAL_ROOT", tmp_path)
    monkeypatch.setattr(storage, "_supabase_configured", lambda: False)
    client = logged_in_client
    aid = _setup(client)

    # submit with text + a file
    r = client.post(
        f"/api/assignments/{aid}/submissions",
        data={"text_body": "see attached"},
        files={"files": ("proof.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
    )
    assert r.status_code == 201
    sub = r.json()
    assert sub["attempt_number"] == 1
    assert sub["text_body"] == "see attached"
    assert sub["file_paths"][0].endswith("proof.pdf")

    # the file is downloadable via the local route
    fr = client.get(f"/api/files/submissions/{sub['file_paths'][0]}")
    assert fr.status_code == 200 and fr.content == b"%PDF-1.4 fake"

    # manual grade
    gr = client.post(f"/api/submissions/{sub['id']}/grade", data={"score": "92", "feedback_md": "Nice."})
    assert gr.status_code == 200
    assert gr.json()["final_score"] == 92.0 and gr.json()["percentage"] == 92.0

    # detail tree shows the graded submission
    detail = client.get(f"/api/assignments/{aid}").json()
    assert detail["submissions"][0]["status"] == "graded"
    assert detail["submissions"][0]["grade"]["feedback_md"] == "Nice."
```

> Note: `files={"files": (...)}` with FastAPI `files: list[UploadFile]` — sending one file under the `files` field name works; for multiple, repeat the field. If the TestClient/Starlette form parsing complains about `list[UploadFile] | None`, change the param to `files: list[UploadFile] = File(default=[])` (import `File` from fastapi) — adjust until the test passes.

- [ ] **Step 5: Run tests + ruff**

Run: `cd backend && uv run pytest -q && uv run ruff check .`
Expected: pass. If multipart isn't installed it is — `python-multipart` is already a dep.

- [ ] **Step 6: Commit**

```bash
cd ..
git add backend/app/api/submissions.py backend/app/api/files.py backend/app/main.py backend/tests/test_submissions_api.py
git commit -m "feat: submissions API (file upload, local file serving) + manual grading"
```

---

### Task 6: Gradebook endpoint

**Files:**
- Create: `backend/app/api/gradebook.py`
- Modify: `backend/app/main.py` (mount)
- Create: `backend/app/schemas/gradebook.py`
- Test: `backend/tests/test_gradebook_api.py`

- [ ] **Step 1: Write `backend/app/schemas/gradebook.py`**

```python
from datetime import datetime

from app.schemas.common import ORMModel


class GradebookRow(ORMModel):
    assignment_id: str
    title: str
    group_name: str
    points_possible: float
    due_at: datetime | None = None
    submitted_at: datetime | None = None
    status: str  # not_submitted | submitted | graded | missing | late
    score: float | None = None
    feedback_md: str = ""
    rubric_breakdown: list = []


class GradebookGroup(ORMModel):
    name: str
    weight: float | None
    drop_lowest_n: int
    percentage: float | None
    earned: float
    possible: float


class GradebookOut(ORMModel):
    course_id: str
    rows: list[GradebookRow]
    groups: list[GradebookGroup]
    total_percentage: float | None
    only_graded: bool
```

- [ ] **Step 2: Write `backend/app/api/gradebook.py`**

```python
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import Assignment, AssignmentGroup, Course, Submission
from app.schemas.gradebook import GradebookGroup, GradebookOut, GradebookRow
from app.services.grading import GradeRow, GroupSpec, course_total, group_percentage

router = APIRouter(tags=["gradebook"], dependencies=[Depends(get_current_user)])


def _current_grade(sub: Submission | None):
    return sub.grade if (sub and sub.grade) else None


@router.get("/courses/{course_id}/gradebook", response_model=GradebookOut)
def gradebook(course_id: str, only_graded: bool = True, db: Session = Depends(get_db)) -> GradebookOut:
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(404, "course not found")
    groups = {
        g.id: g
        for g in db.query(AssignmentGroup).filter(AssignmentGroup.course_id == course_id).all()
    }
    assignments = (
        db.query(Assignment)
        .filter(Assignment.course_id == course_id, Assignment.published == True)  # noqa: E712
        .order_by(Assignment.position, Assignment.title)
        .all()
    )
    now = datetime.now(UTC)

    rows: list[GradebookRow] = []
    group_rows: dict[str, list[GradeRow]] = {gid: [] for gid in groups}
    group_rows[None] = []  # type: ignore[index]
    for a in assignments:
        latest = (
            db.query(Submission)
            .filter(Submission.assignment_id == a.id)
            .order_by(Submission.attempt_number.desc())
            .first()
        )
        grade = _current_grade(latest)
        if grade is not None:
            status = "graded"
            score: float | None = float(grade.final_score)
        elif latest is not None:
            status = "submitted"
            score = None
        elif a.due_at is not None and now > a.due_at:
            status = "missing"
            score = None
        else:
            status = "not_submitted"
            score = None
        if latest is not None and latest.is_late and status not in ("missing",):
            # keep status but the row carries is_late info via submitted_at; UI shows "late"
            pass
        gname = groups[a.assignment_group_id].name if a.assignment_group_id in groups else ""
        rows.append(
            GradebookRow(
                assignment_id=a.id,
                title=a.title,
                group_name=gname,
                points_possible=float(a.points_possible),
                due_at=a.due_at,
                submitted_at=latest.submitted_at if latest else None,
                status="late" if (latest and latest.is_late and grade is not None) else status,
                score=score,
                feedback_md=grade.feedback_md if grade else "",
                rubric_breakdown=list(grade.rubric_breakdown) if grade else [],
            )
        )
        if grade is not None:
            group_rows.setdefault(a.assignment_group_id, []).append(
                GradeRow(final_score=float(grade.final_score), points=float(a.points_possible))
            )

    gb_groups: list[GradebookGroup] = []
    specs: list[GroupSpec] = []
    for gid, g in groups.items():
        gr = group_rows.get(gid, [])
        pct = group_percentage(gr, g.drop_lowest_n)
        gb_groups.append(
            GradebookGroup(
                name=g.name,
                weight=float(g.weight) if g.weight is not None else None,
                drop_lowest_n=g.drop_lowest_n,
                percentage=pct,
                earned=sum(r.final_score for r in gr),
                possible=sum(r.points for r in gr),
            )
        )
        specs.append(GroupSpec(name=g.name, weight=float(g.weight) if g.weight is not None else None, drop_lowest_n=g.drop_lowest_n, rows=gr))

    # ungrouped assignments form an implicit unweighted bucket only if there are no weighted groups
    ungrouped = group_rows.get(None, [])
    if ungrouped and all(s.weight is None for s in specs):
        specs.append(GroupSpec(name="(ungrouped)", weight=None, drop_lowest_n=0, rows=ungrouped))

    total = course_total(specs, only_graded=only_graded) if specs else None
    return GradebookOut(
        course_id=course_id,
        rows=rows,
        groups=gb_groups,
        total_percentage=total,
        only_graded=only_graded,
    )
```

> If SQLAlchemy complains about `group_rows[None]` typing, just keep it — at runtime `None` is a valid dict key. Adjust the `# type:` comment as needed; ruff won't flag it.

- [ ] **Step 3: Mount in `backend/app/main.py`** (`gradebook` router).

- [ ] **Step 4: Write `backend/tests/test_gradebook_api.py`**

```python
def test_gradebook_rollup(logged_in_client, tmp_path, monkeypatch):
    from app.services import storage

    monkeypatch.setattr(storage, "_LOCAL_ROOT", tmp_path)
    monkeypatch.setattr(storage, "_supabase_configured", lambda: False)
    client = logged_in_client

    cid = client.post("/api/courses", json={"code": "X", "title": "X"}).json()["id"]
    ps = client.post(f"/api/courses/{cid}/assignment-groups", json={"name": "Problem Sets", "weight": 50, "drop_lowest_n": 1}).json()
    mid = client.post(f"/api/courses/{cid}/assignment-groups", json={"name": "Midterm", "weight": 50}).json()

    # 3 problem sets, scores 100/80/40 (the 40 is dropped) -> PS pct = 90
    ps_ids = []
    for i, _ in enumerate([1, 2, 3]):
        aid = client.post(f"/api/courses/{cid}/assignments", json={"title": f"PS{i+1}", "points_possible": 100, "assignment_group_id": ps["id"]}).json()["id"]
        ps_ids.append(aid)
    for aid, sc in zip(ps_ids, [100, 80, 40]):
        sid = client.post(f"/api/assignments/{aid}/submissions", data={"text_body": "x"}).json()["id"]
        client.post(f"/api/submissions/{sid}/grade", data={"score": str(sc)})

    # midterm scored 70
    maid = client.post(f"/api/courses/{cid}/assignments", json={"title": "Midterm", "points_possible": 100, "assignment_group_id": mid["id"]}).json()["id"]
    msid = client.post(f"/api/assignments/{maid}/submissions", data={"text_body": "x"}).json()["id"]
    client.post(f"/api/submissions/{msid}/grade", data={"score": "70"})

    gb = client.get(f"/api/courses/{cid}/gradebook").json()
    # PS 50% @ 90, Midterm 50% @ 70 -> 80.0
    assert round(gb["total_percentage"], 2) == 80.0
    ps_group = next(g for g in gb["groups"] if g["name"] == "Problem Sets")
    assert round(ps_group["percentage"], 2) == 90.0
    assert len(gb["rows"]) == 4
```

- [ ] **Step 5: Run tests + ruff**

Run: `cd backend && uv run pytest -q && uv run ruff check .`
Expected: pass.

- [ ] **Step 6: Commit**

```bash
cd ..
git add backend/app/api/gradebook.py backend/app/schemas/gradebook.py backend/app/main.py backend/tests/test_gradebook_api.py
git commit -m "feat: gradebook endpoint (per-group % + course rollup)"
```

---

### Task 7: Frontend — API client + types for assignments/submissions/gradebook

**Files:**
- Modify: `frontend/src/api/types.ts` (add `Assignment`, `Submission`, `Grade`, `RubricItem`, `AssignmentDetail`, `Gradebook*`)
- Modify: `frontend/src/api/client.ts` (add the new endpoints + a `submit` that posts FormData)

- [ ] **Step 1: Append to `frontend/src/api/types.ts`**

```ts
export type LatePolicy = "none" | "flag_only" | "percent_per_day";

export interface Assignment {
  id: string;
  course_id: string;
  assignment_group_id: string | null;
  title: string;
  description_md: string;
  points_possible: number;
  due_at: string | null;
  available_at: string | null;
  accepts_files: boolean;
  accepts_text: boolean;
  official_solution_url: string;
  official_solution_file_path: string;
  late_policy: LatePolicy;
  late_value: number | null;
  position: number;
  published: boolean;
}

export interface RubricItem {
  criterion: string;
  points_awarded: number;
  points_possible: number;
  note: string;
}

export interface Grade {
  id: string;
  submission_id: string;
  score: number;
  score_out_of: number;
  late_penalty_applied: number;
  final_score: number;
  percentage: number;
  feedback_md: string;
  rubric_breakdown: RubricItem[];
  graded_by: string;
  model: string;
  graded_at: string | null;
}

export interface Submission {
  id: string;
  assignment_id: string;
  attempt_number: number;
  submitted_at: string | null;
  is_late: boolean;
  text_body: string | null;
  file_paths: string[];
  source: string;
  status: string;
  grade: Grade | null;
}

export interface AssignmentDetail extends Assignment {
  submissions: Submission[];
}

export interface GradebookRow {
  assignment_id: string;
  title: string;
  group_name: string;
  points_possible: number;
  due_at: string | null;
  submitted_at: string | null;
  status: string;
  score: number | null;
  feedback_md: string;
  rubric_breakdown: RubricItem[];
}

export interface GradebookGroup {
  name: string;
  weight: number | null;
  drop_lowest_n: number;
  percentage: number | null;
  earned: number;
  possible: number;
}

export interface Gradebook {
  course_id: string;
  rows: GradebookRow[];
  groups: GradebookGroup[];
  total_percentage: number | null;
  only_graded: boolean;
}
```

- [ ] **Step 2: Append the new endpoints to `frontend/src/api/client.ts`'s `api` object** (and a raw `apiBase` export for building file URLs)

```ts
// add near the top, after `const BASE = ...`
export const apiBase = BASE;

// add a helper used for multipart submit (above the `api` object)
async function reqForm<T>(method: string, path: string, form: FormData): Promise<T> {
  const res = await fetch(`${BASE}/api${path}`, { method, credentials: "include", body: form });
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  const data = text ? JSON.parse(text) : undefined;
  if (!res.ok) throw new ApiError(res.status, (data && data.detail) || res.statusText);
  return data as T;
}

// add these entries inside the `api` object:
  // assignments
  listAssignments: (courseId: string) =>
    req<import("./types").Assignment[]>("GET", `/courses/${courseId}/assignments`),
  getAssignment: (id: string) => req<import("./types").AssignmentDetail>("GET", `/assignments/${id}`),
  createAssignment: (courseId: string, a: Partial<import("./types").Assignment> & { title: string }) =>
    req<import("./types").Assignment>("POST", `/courses/${courseId}/assignments`, a),
  updateAssignment: (id: string, a: Partial<import("./types").Assignment> & { title: string }) =>
    req<import("./types").Assignment>("PUT", `/assignments/${id}`, a),
  deleteAssignment: (id: string) => req<void>("DELETE", `/assignments/${id}`),

  // submissions
  submit: (assignmentId: string, opts: { text?: string; files: File[] }) => {
    const fd = new FormData();
    if (opts.text) fd.append("text_body", opts.text);
    for (const f of opts.files) fd.append("files", f);
    return reqForm<import("./types").Submission>("POST", `/assignments/${assignmentId}/submissions`, fd);
  },
  manualGrade: (submissionId: string, score: number, feedback: string) => {
    const fd = new FormData();
    fd.append("score", String(score));
    fd.append("feedback_md", feedback);
    return reqForm<import("./types").Grade>("POST", `/submissions/${submissionId}/grade`, fd);
  },

  // gradebook
  getGradebook: (courseId: string, onlyGraded = true) =>
    req<import("./types").Gradebook>("GET", `/courses/${courseId}/gradebook?only_graded=${onlyGraded}`),
```

> Tidy the imports: instead of `import("./types").X` inline, add `Assignment, AssignmentDetail, Submission, Grade, Gradebook` to the top `import type { ... } from "./types";`. The inline form is shown only so the diff is self-contained.

- [ ] **Step 3: Typecheck**

Run: `cd frontend && npm run typecheck`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
cd ..
git add frontend/src/api/types.ts frontend/src/api/client.ts
git commit -m "feat(frontend): API client for assignments, submissions, gradebook"
```

---

### Task 8: Frontend — Assignments list + Assignment detail pages

**Files:**
- Create: `frontend/src/pages/CourseAssignmentsPage.tsx`
- Create: `frontend/src/pages/AssignmentDetailPage.tsx`
- Create: `frontend/src/components/edit/AssignmentEditModal.tsx`
- Modify: `frontend/src/App.tsx` (route `/courses/:courseId/assignments` → `CourseAssignmentsPage`; `/courses/:courseId/assignments/:assignmentId` → `AssignmentDetailPage`)
- Delete: nothing (the `CoursePlaceholderPage` is still used by `/grades` until Task 9)

- [ ] **Step 1: Write `frontend/src/components/edit/AssignmentEditModal.tsx`** — fields per the `Assignment` model; `due_at` as a `datetime-local` input (convert to/from ISO).

```tsx
import { useState } from "react";
import { api } from "../../api/client";
import type { Assignment, AssignmentGroup, LatePolicy } from "../../api/types";
import { Modal } from "../Modal";

function toLocalInput(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
function fromLocalInput(v: string): string | null {
  return v ? new Date(v).toISOString() : null;
}

export function AssignmentEditModal({
  courseId,
  assignment,
  groups,
  nextPosition,
  onClose,
  onSaved,
}: {
  courseId: string;
  assignment: Assignment | null;
  groups: AssignmentGroup[];
  nextPosition: number;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [title, setTitle] = useState(assignment?.title ?? "");
  const [groupId, setGroupId] = useState(assignment?.assignment_group_id ?? "");
  const [desc, setDesc] = useState(assignment?.description_md ?? "");
  const [points, setPoints] = useState(assignment?.points_possible ?? 100);
  const [due, setDue] = useState(toLocalInput(assignment?.due_at ?? null));
  const [acceptsFiles, setAcceptsFiles] = useState(assignment?.accepts_files ?? true);
  const [acceptsText, setAcceptsText] = useState(assignment?.accepts_text ?? true);
  const [solUrl, setSolUrl] = useState(assignment?.official_solution_url ?? "");
  const [latePolicy, setLatePolicy] = useState<LatePolicy>(assignment?.late_policy ?? "flag_only");
  const [lateValue, setLateValue] = useState<string>(
    assignment?.late_value != null ? String(assignment.late_value) : "",
  );
  const [position, setPosition] = useState(assignment?.position ?? nextPosition);
  const [published, setPublished] = useState(assignment?.published ?? true);

  async function save() {
    const payload = {
      title,
      assignment_group_id: groupId || null,
      description_md: desc,
      points_possible: points,
      due_at: fromLocalInput(due),
      accepts_files: acceptsFiles,
      accepts_text: acceptsText,
      official_solution_url: solUrl,
      late_policy: latePolicy,
      late_value: lateValue === "" ? null : Number(lateValue),
      position,
      published,
    };
    if (assignment) await api.updateAssignment(assignment.id, payload);
    else await api.createAssignment(courseId, payload);
    onSaved();
  }
  async function del() {
    if (!assignment || !confirm("Delete this assignment and its submissions?")) return;
    await api.deleteAssignment(assignment.id);
    onSaved();
  }

  return (
    <Modal
      title={assignment ? "Edit assignment" : "Add assignment"}
      onClose={onClose}
      footer={
        <>
          {assignment ? <button className="btn" onClick={del}>Delete</button> : <span />}
          <span>
            <button className="btn" onClick={onClose}>Cancel</button>
            <button className="btn primary" style={{ marginLeft: 8 }} onClick={save}>Save</button>
          </span>
        </>
      }
    >
      <label className="req">Title</label>
      <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Problem Set 1 — Sequences" />
      <label>Assignment group</label>
      <select value={groupId} onChange={(e) => setGroupId(e.target.value)}>
        <option value="">(ungrouped)</option>
        {groups.map((g) => <option key={g.id} value={g.id}>{g.name}{g.weight != null ? ` (${g.weight}%)` : ""}</option>)}
      </select>
      <label>Description (markdown — put the link to the source problem-set PDF here)</label>
      <textarea rows={5} value={desc} onChange={(e) => setDesc(e.target.value)} />
      <label>Points possible</label>
      <input type="number" value={points} onChange={(e) => setPoints(Number(e.target.value))} />
      <label>Due (local time)</label>
      <input type="datetime-local" value={due} onChange={(e) => setDue(e.target.value)} />
      <label><input type="checkbox" checked={acceptsFiles} onChange={(e) => setAcceptsFiles(e.target.checked)} /> Accept file uploads</label>
      <label><input type="checkbox" checked={acceptsText} onChange={(e) => setAcceptsText(e.target.checked)} /> Accept text / LaTeX entry</label>
      <label>Official solution URL (optional — if set, this is the answer key)</label>
      <input value={solUrl} onChange={(e) => setSolUrl(e.target.value)} />
      <label>Late policy</label>
      <select value={latePolicy} onChange={(e) => setLatePolicy(e.target.value as LatePolicy)}>
        <option value="none">none</option>
        <option value="flag_only">flag only</option>
        <option value="percent_per_day">percent per day</option>
      </select>
      {latePolicy === "percent_per_day" && (
        <>
          <label>% off per day late</label>
          <input value={lateValue} onChange={(e) => setLateValue(e.target.value)} placeholder="10" />
        </>
      )}
      <label>Position</label>
      <input type="number" value={position} onChange={(e) => setPosition(Number(e.target.value))} />
      <label><input type="checkbox" checked={published} onChange={(e) => setPublished(e.target.checked)} /> Published</label>
    </Modal>
  );
}
```

- [ ] **Step 2: Write `frontend/src/pages/CourseAssignmentsPage.tsx`** — Show By Date / Show By Type toggle; rows show `Due … | <score>/<pts> pts | <status>`.

```tsx
import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { Assignment, AssignmentGroup, AssignmentSummary } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { CourseLayout } from "../components/CourseLayout";
import { Spinner } from "../components/Spinner";
import { AssignmentEditModal } from "../components/edit/AssignmentEditModal";
import { useCourse } from "../lib/useCourse";

type Mode = "date" | "type";

function dateBucket(a: AssignmentSummary): "Overdue Assignments" | "Upcoming Assignments" | "Undated Assignments" {
  if (!a.due_at) return "Undated Assignments";
  return new Date(a.due_at) < new Date() ? "Overdue Assignments" : "Upcoming Assignments";
}

export function CourseAssignmentsPage() {
  const { courseId } = useParams();
  const { course, reload } = useCourse(courseId);
  const { teacherMode } = useAuth();
  const [mode, setMode] = useState<Mode>("date");
  const [editing, setEditing] = useState<Assignment | "new" | null>(null);

  const grouped = useMemo(() => {
    if (!course) return new Map<string, AssignmentSummary[]>();
    const m = new Map<string, AssignmentSummary[]>();
    const byId = new Map<string, AssignmentGroup>(course.assignment_groups.map((g) => [g.id, g]));
    for (const a of course.assignments) {
      const key =
        mode === "date"
          ? dateBucket(a)
          : a.assignment_group_id && byId.has(a.assignment_group_id)
            ? byId.get(a.assignment_group_id)!.name
            : "(ungrouped)";
      if (!m.has(key)) m.set(key, []);
      m.get(key)!.push(a);
    }
    return m;
  }, [course, mode]);

  if (!course) return <Spinner />;
  const order =
    mode === "date"
      ? ["Overdue Assignments", "Upcoming Assignments", "Undated Assignments"]
      : [...course.assignment_groups.map((g) => g.name), "(ungrouped)"];

  return (
    <CourseLayout course={course} section="Assignments">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1 className="page-title">Assignments</h1>
        <div>
          <button className={"btn" + (mode === "date" ? " primary" : "")} onClick={() => setMode("date")}>Show by date</button>
          <button className={"btn" + (mode === "type" ? " primary" : "")} style={{ marginLeft: 6 }} onClick={() => setMode("type")}>Show by type</button>
          {teacherMode && <button className="btn primary" style={{ marginLeft: 12 }} onClick={() => setEditing("new")}>+ Assignment</button>}
        </div>
      </div>
      {course.assignments.length === 0 && <div className="center-empty">No assignments yet.</div>}
      {order.filter((k) => grouped.has(k)).map((k) => (
        <div className="module" key={k}>
          <div className="module-head">{k}</div>
          {grouped.get(k)!.map((a) => (
            <div className="module-item" key={a.id}>
              <span className="mi-icon">📝</span>
              <span style={{ flex: 1 }}>
                <Link to={`/courses/${course.id}/assignments/${a.id}`}>{a.title}</Link>
                <div className="mi-sub">
                  {a.due_at ? `Due ${new Date(a.due_at).toLocaleString()} | ` : ""}–/{a.points_possible} pts
                </div>
              </span>
              {teacherMode && (
                <span className="row-actions">
                  <button className="btn small" onClick={() => setEditing(course.assignments.find((x) => x.id === a.id) as unknown as Assignment)}>Edit</button>
                </span>
              )}
            </div>
          ))}
        </div>
      ))}
      {editing && (
        <AssignmentEditModal
          courseId={course.id}
          assignment={editing === "new" ? null : (editing as Assignment)}
          groups={course.assignment_groups}
          nextPosition={course.assignments.length}
          onClose={() => setEditing(null)}
          onSaved={() => { setEditing(null); reload(); }}
        />
      )}
    </CourseLayout>
  );
}
```

> Note: `course.assignments` items are `AssignmentSummary`, not full `Assignment`. For the edit modal you need the full assignment — fetch it: when "Edit" is clicked, `api.getAssignment(id).then(setEditing)`. Adjust: make `editing` hold `Assignment | "new" | null` and on edit do `api.getAssignment(a.id).then((full) => setEditing(full))`. (Implement that instead of the `as unknown as` cast above.)

- [ ] **Step 3: Write `frontend/src/pages/AssignmentDetailPage.tsx`** — header (title, due, points), Details collapsible, submit panel (file dropzone + text box), submission history, grade display + "view reference solution" toggle (official URL only in P2; AI solution in P3), and a teacher-mode manual-grade form.

```tsx
import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { api, apiBase } from "../api/client";
import type { AssignmentDetail, CourseDetail } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { CourseLayout } from "../components/CourseLayout";
import { Markdown } from "../components/Markdown";
import { Spinner } from "../components/Spinner";
import { useCourse } from "../lib/useCourse";

export function AssignmentDetailPage() {
  const { courseId, assignmentId } = useParams();
  const { course } = useCourse(courseId);
  const { teacherMode } = useAuth();
  const [a, setA] = useState<AssignmentDetail | null>(null);
  const [text, setText] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [showRef, setShowRef] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  function reloadA() {
    if (assignmentId) api.getAssignment(assignmentId).then(setA);
  }
  useEffect(reloadA, [assignmentId]);

  if (!course || !a) return <Spinner />;
  const latest = a.submissions[a.submissions.length - 1];

  async function submit() {
    setBusy(true);
    try {
      await api.submit(a!.id, { text: text || undefined, files });
      setText("");
      setFiles([]);
      if (fileRef.current) fileRef.current.value = "";
      reloadA();
    } finally {
      setBusy(false);
    }
  }

  return (
    <CourseLayout course={course as CourseDetail} section="Assignments">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h1 className="page-title">{a.title}</h1>
          {a.due_at && <div className="muted">Due: {new Date(a.due_at).toLocaleString()}</div>}
        </div>
        <div style={{ fontSize: 22, fontWeight: 300 }}>{a.points_possible} Points Possible</div>
      </div>

      <details open style={{ margin: "16px 0" }}>
        <summary style={{ cursor: "pointer", fontWeight: 700 }}>Details</summary>
        <div style={{ marginTop: 8 }}>
          {a.description_md ? <Markdown>{a.description_md}</Markdown> : <span className="muted">No description.</span>}
        </div>
      </details>

      {/* Submit panel */}
      <h2 style={{ fontWeight: 400 }}>{latest && latest.status === "graded" ? "Resubmit" : "Submit"}</h2>
      {a.accepts_text && (
        <>
          <label className="muted">Text / LaTeX</label>
          <textarea rows={4} style={{ width: "100%" }} value={text} onChange={(e) => setText(e.target.value)} />
        </>
      )}
      {a.accepts_files && (
        <div style={{ margin: "10px 0" }}>
          <input ref={fileRef} type="file" multiple onChange={(e) => setFiles(Array.from(e.target.files ?? []))} />
        </div>
      )}
      <button className="btn primary" disabled={busy || (!text && files.length === 0)} onClick={submit}>
        {busy ? "Submitting…" : "Submit Assignment"}
      </button>

      {/* Submission history */}
      {a.submissions.length > 0 && (
        <>
          <h2 style={{ fontWeight: 400, marginTop: 24 }}>Submissions</h2>
          {a.submissions.map((s) => (
            <div className="module" key={s.id}>
              <div className="module-head">
                Attempt {s.attempt_number}
                {s.is_late && <span className="badge-pill late" style={{ marginLeft: 8 }}>late</span>}
                <span style={{ marginLeft: 8 }} className="muted">{s.submitted_at && new Date(s.submitted_at).toLocaleString()}</span>
              </div>
              <div className="module-item">
                <div style={{ flex: 1 }}>
                  {s.text_body && <Markdown>{s.text_body}</Markdown>}
                  {s.file_paths.map((p) => (
                    <div key={p}>
                      <a href={`${apiBase}/api/files/submissions/${p}`} target="_blank" rel="noreferrer">{p.split("/").pop()}</a>
                    </div>
                  ))}
                  {s.grade ? (
                    <div style={{ marginTop: 10 }}>
                      <strong>Score: {s.grade.final_score} / {s.grade.score_out_of}</strong>
                      {s.grade.late_penalty_applied > 0 && <span className="muted"> (late penalty −{s.grade.late_penalty_applied})</span>}
                      {s.grade.rubric_breakdown.length > 0 && (
                        <table className="data" style={{ marginTop: 8 }}>
                          <thead><tr><th>Criterion</th><th>Awarded</th><th>Out of</th><th>Note</th></tr></thead>
                          <tbody>
                            {s.grade.rubric_breakdown.map((r, i) => (
                              <tr key={i}><td>{r.criterion}</td><td>{r.points_awarded}</td><td>{r.points_possible}</td><td>{r.note}</td></tr>
                            ))}
                          </tbody>
                        </table>
                      )}
                      {s.grade.feedback_md && <div style={{ marginTop: 8 }}><Markdown>{s.grade.feedback_md}</Markdown></div>}
                    </div>
                  ) : (
                    <div className="muted" style={{ marginTop: 8 }}>
                      {s.status === "submitted" ? "Submitted — not yet graded." : s.status}
                    </div>
                  )}
                  {teacherMode && (
                    <ManualGradeForm submissionId={s.id} onGraded={reloadA} />
                  )}
                </div>
              </div>
            </div>
          ))}
        </>
      )}

      {/* Reference solution */}
      <div style={{ marginTop: 24 }}>
        <button className="btn" onClick={() => setShowRef(!showRef)}>
          {showRef ? "Hide" : "View"} reference solution
        </button>
        {showRef && (
          <div style={{ marginTop: 10 }}>
            {a.official_solution_url ? (
              <a href={a.official_solution_url} target="_blank" rel="noreferrer" className="external-arrow">Official solution</a>
            ) : (
              <span className="muted">No solution available yet. (AI-generated solutions arrive in a later phase.)</span>
            )}
          </div>
        )}
      </div>
    </CourseLayout>
  );
}

function ManualGradeForm({ submissionId, onGraded }: { submissionId: string; onGraded: () => void }) {
  const [score, setScore] = useState("");
  const [fb, setFb] = useState("");
  return (
    <div style={{ marginTop: 12, borderTop: "1px solid #eee", paddingTop: 10 }}>
      <strong>Teacher: manual grade</strong>
      <div style={{ display: "flex", gap: 8, marginTop: 6, alignItems: "center" }}>
        <input style={{ width: 80 }} placeholder="score" value={score} onChange={(e) => setScore(e.target.value)} />
        <input style={{ flex: 1 }} placeholder="feedback (markdown)" value={fb} onChange={(e) => setFb(e.target.value)} />
        <button
          className="btn small primary"
          onClick={async () => {
            await api.manualGrade(submissionId, Number(score), fb);
            onGraded();
          }}
        >
          Save grade
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Wire routes in `frontend/src/App.tsx`** — replace the two `CoursePlaceholderPage section="Assignments"` routes:

```tsx
import { CourseAssignmentsPage } from "./pages/CourseAssignmentsPage";
import { AssignmentDetailPage } from "./pages/AssignmentDetailPage";
// ...
<Route path="/courses/:courseId/assignments" element={<Auth><CourseAssignmentsPage /></Auth>} />
<Route path="/courses/:courseId/assignments/:assignmentId" element={<Auth><AssignmentDetailPage /></Auth>} />
```
(`/grades` still uses `CoursePlaceholderPage` until Task 9.)

- [ ] **Step 5: Typecheck + lint + build**

Run: `cd frontend && npm run typecheck && npm run lint && npm run build`
Expected: pass (warnings ok). Fix the `editing` state typing in `CourseAssignmentsPage` per Step 2's note (fetch the full assignment on edit).

- [ ] **Step 6: Commit**

```bash
cd ..
git add frontend/src/pages/CourseAssignmentsPage.tsx frontend/src/pages/AssignmentDetailPage.tsx frontend/src/components/edit/AssignmentEditModal.tsx frontend/src/App.tsx
git commit -m "feat(frontend): assignments list + assignment detail (submit, history, manual grade)"
```

---

### Task 9: Frontend — Grades page + assignment-group management + To-Do widgets

**Files:**
- Create: `frontend/src/pages/CourseGradesPage.tsx`
- Modify: `frontend/src/App.tsx` (route `/courses/:courseId/grades` → `CourseGradesPage`)
- Modify: `frontend/src/pages/CourseAssignmentsPage.tsx` (add a teacher-mode "Assignment groups" panel using `AssignmentGroupEditModal`)
- Modify: `frontend/src/components/CourseSidebar.tsx` and `frontend/src/pages/DashboardPage.tsx` (fill the "To Do" widgets with real upcoming-due-date data)
- Delete: `frontend/src/pages/CoursePlaceholderPage.tsx` (no longer referenced) — and remove its import from `App.tsx`

- [ ] **Step 1: Write `frontend/src/pages/CourseGradesPage.tsx`** — match the Canvas Grades layout (see `docs/superpowers/specs/assets/canvas-grades-page-*.png`): "Grades for &lt;name&gt;", Print Grades, the table (Name/Due/Submitted/Status/Score), group subtotals, Total row, and the right-sidebar weighted-by-group mini-table + "only graded" checkbox.

```tsx
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { Gradebook } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { CourseLayout } from "../components/CourseLayout";
import { Markdown } from "../components/Markdown";
import { Spinner } from "../components/Spinner";
import { useCourse } from "../lib/useCourse";

export function CourseGradesPage() {
  const { courseId } = useParams();
  const { course } = useCourse(courseId);
  const { user } = useAuth();
  const [gb, setGb] = useState<Gradebook | null>(null);
  const [onlyGraded, setOnlyGraded] = useState(true);
  const [showDetails, setShowDetails] = useState(false);

  useEffect(() => {
    if (courseId) api.getGradebook(courseId, onlyGraded).then(setGb);
  }, [courseId, onlyGraded]);

  if (!course || !gb) return <Spinner />;
  const pct = gb.total_percentage;

  return (
    <CourseLayout course={course} section="Grades">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1 className="page-title">Grades for {user?.display_name ?? "you"}</h1>
        <button className="btn" onClick={() => window.print()}>🖨 Print Grades</button>
      </div>
      <div className="page-with-sidebar">
        <div className="col-main">
          <table className="data">
            <thead>
              <tr><th>Name</th><th>Due</th><th>Submitted</th><th>Status</th><th>Score</th></tr>
            </thead>
            <tbody>
              {gb.rows.map((r) => (
                <>
                  <tr key={r.assignment_id}>
                    <td>
                      <Link to={`/courses/${course.id}/assignments/${r.assignment_id}`}>{r.title}</Link>
                      <div className="muted" style={{ fontSize: 12 }}>{r.group_name}</div>
                    </td>
                    <td>{r.due_at ? new Date(r.due_at).toLocaleString() : ""}</td>
                    <td>{r.submitted_at ? new Date(r.submitted_at).toLocaleString() : ""}</td>
                    <td>
                      {r.status === "missing" && <span className="badge-pill missing">missing</span>}
                      {r.status === "late" && <span className="badge-pill late">late</span>}
                    </td>
                    <td>{r.score != null ? `${r.score} / ${r.points_possible}` : `⊘ / ${r.points_possible}`}</td>
                  </tr>
                  {showDetails && (r.feedback_md || r.rubric_breakdown.length > 0) && (
                    <tr key={r.assignment_id + "-d"}>
                      <td colSpan={5} style={{ background: "#fafafa" }}>
                        {r.rubric_breakdown.length > 0 && (
                          <table className="data" style={{ marginBottom: 8 }}>
                            <tbody>
                              {r.rubric_breakdown.map((rb, i) => (
                                <tr key={i}><td>{rb.criterion}</td><td>{rb.points_awarded}/{rb.points_possible}</td><td>{rb.note}</td></tr>
                              ))}
                            </tbody>
                          </table>
                        )}
                        {r.feedback_md && <Markdown>{r.feedback_md}</Markdown>}
                      </td>
                    </tr>
                  )}
                </>
              ))}
              {gb.groups.map((g) => (
                <tr key={"g-" + g.name} style={{ fontWeight: 700 }}>
                  <td colSpan={3}>{g.name}</td>
                  <td>{g.percentage != null ? `${g.percentage.toFixed(1)}%` : "N/A"}</td>
                  <td>{g.earned.toFixed(2)} / {g.possible.toFixed(2)}</td>
                </tr>
              ))}
              <tr style={{ fontWeight: 700, fontSize: 18 }}>
                <td colSpan={4}>Total</td>
                <td>{pct != null ? `${pct.toFixed(2)}%` : "N/A"}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div className="col-side">
          <div className="widget">
            <h2>Total: {pct != null ? `${pct.toFixed(0)}%` : "N/A"}</h2>
            <button className="btn small" onClick={() => setShowDetails(!showDetails)}>
              {showDetails ? "Hide" : "Show"} all details
            </button>
          </div>
          {gb.groups.some((g) => g.weight != null) && (
            <div className="widget">
              <strong>Assignments are weighted by group:</strong>
              <table className="data" style={{ marginTop: 6 }}>
                <thead><tr><th>Group</th><th>Weight</th></tr></thead>
                <tbody>
                  {gb.groups.map((g) => (
                    <tr key={g.name}><td>{g.name}</td><td>{g.weight != null ? `${g.weight}%` : "—"}</td></tr>
                  ))}
                  <tr style={{ fontWeight: 700 }}>
                    <td>Total</td>
                    <td>{gb.groups.reduce((s, g) => s + (g.weight ?? 0), 0)}%</td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}
          <div className="widget">
            <label>
              <input type="checkbox" checked={onlyGraded} onChange={(e) => setOnlyGraded(e.target.checked)} />{" "}
              Calculate based only on graded assignments
            </label>
            <p className="muted" style={{ fontSize: 12, marginTop: 8 }}>
              The total above reflects only assignments that have a grade. Editable "what-if" scores
              are not supported.
            </p>
          </div>
        </div>
      </div>
    </CourseLayout>
  );
}
```

> If React complains about `<>...</>` fragments needing keys inside `.map`, wrap each row pair in a keyed `<Fragment key={...}>` (`import { Fragment } from "react"`). Do that.

- [ ] **Step 2: Wire the route + drop the placeholder in `frontend/src/App.tsx`** — replace the `/grades` route with `<CourseGradesPage />`, remove `CoursePlaceholderPage` import and its remaining usages (there should be none left), then delete `frontend/src/pages/CoursePlaceholderPage.tsx`.

- [ ] **Step 3: Add an "Assignment groups" teacher-mode panel to `CourseAssignmentsPage.tsx`** — above the assignment list, when `teacherMode`, render a small box listing `course.assignment_groups` with Edit buttons and an "+ Add group" button, each opening `AssignmentGroupEditModal` (already exists from P1, file `components/edit/AssignmentGroupEditModal.tsx`). On save, `reload()`.

- [ ] **Step 4: Feed the To-Do widgets** — in `CourseSidebar.tsx`, replace the placeholder text with the course's upcoming assignments (`course.assignments.filter(a => a.due_at && new Date(a.due_at) > new Date()).sort(...).slice(0,5)`), each a `<Link>` to the assignment with its due date. In `DashboardPage.tsx`, load each course's detail (or add a small `/api/todo` endpoint — simpler to just fetch details since there are few courses) and show the soonest few upcoming due dates across all courses. Keep "Recent Feedback" as a stub (P3 fills it once AI grading exists; or list recently-graded submissions if easy).

- [ ] **Step 5: Typecheck + lint + build**

Run: `cd frontend && npm run typecheck && npm run lint && npm run build`
Expected: pass.

- [ ] **Step 6: Commit**

```bash
cd ..
git add frontend/src
git commit -m "feat(frontend): Grades page; assignment-group management; To-Do widgets"
```

---

### Task 10: Wire teacher-mode "module item → assignment" creation shortcut + manual verification

**Files:**
- Modify: `frontend/src/components/edit/ModuleEditModals.tsx` (in `ModuleItemEditModal`, when `kind=assignment` and there are no assignments yet, show a hint linking to the Assignments page) — small polish, optional.
- (No new backend.)

- [ ] **Step 1: Manual smoke (run once)**

1. `cd backend && uv run alembic upgrade head && uv run python -m app.manage create-owner --email a@b.c --password test --name Tester && uv run uvicorn app.main:app --reload --port 8000`
2. `cd frontend && npm run dev`; sign in.
3. Teacher mode → open a course → Assignments → add an assignment group "Problem Sets" weight 50, then "Midterm" weight 50.
4. Add an assignment "Problem Set 1" in Problem Sets, points 100, due tomorrow, with a description containing an OCW link.
5. As the student: open the assignment → type some text + attach a small PDF → Submit. The submission appears in history with the file downloadable.
6. Teacher mode on the same submission → enter score 92 → Save grade. Reload: score shows, status `graded`.
7. Grades page → the gradebook shows the row with 92/100, the Problem Sets group at 92% (one assignment), Total reflects the weighting; toggle "only graded" — Total changes.
8. Modules → add a `module_item kind=assignment` pointing at "Problem Set 1" — it appears with the due/points subtitle and links to the assignment page.

- [ ] **Step 2: Commit any polish**

```bash
cd ..
git add -A
git commit -m "chore(frontend): module-item assignment hint; P2 polish" || echo "nothing to commit"
```

---

### Task 11: Merge P2 to the default branch

- [ ] **Step 1: Full check**

```bash
cd backend && uv run pytest -q && uv run ruff check . && cd ..
cd frontend && npm run typecheck && npm run lint && npm run build && cd ..
```
Expected: all green.

- [ ] **Step 2: Merge**

```bash
git checkout master   # or `main` — check `git branch`
git merge --no-ff feat/p2-assignments -m "feat: P2 — assignments & submissions"
```

- [ ] **Step 3: Update root README "Status:" line** to mention P2 (assignments, submissions, manual grading, Grades page) is complete; commit on the default branch.

- [ ] **Step 4: Confirm** `git log --oneline -8` and `git status`. (Push only if asked.)

---

## Self-Review notes

- **Spec coverage (P2 slice):** `submission` + `grade` tables (§3) → Task 1; group `drop_lowest_n` + weighted/flat rollup math (§3) → Task 2 (tested); Supabase Storage for submissions (§3) → Task 3 (with local fallback so it runs without cloud); assignment CRUD (§4 8a) → Task 4; submit panel — file upload + text, late flagging, submission history (§4 8b, §5 step 3) → Tasks 5, 8; manual score entry "no AI yet" (§7-P2) → Task 5; Grades page matching the screenshots (§4 #9) → Task 9; To-Do widgets fed real data (§4 Dashboard) → Task 9. Not in P2: AI solution/grading (P3), email/announcements/cron (P4), the 18.100B seed (P5), `ai_solution` table (added in P3's migration), `available_at` gating (deferred — the field exists; enforcing the lock is a small P3/P5 polish).
- **Placeholder scan:** intentional stubs called out in-task — "Recent Feedback" stays a stub until P3; "view reference solution" only shows the official URL until P3; `ai_demo` submission source is reserved. No `TODO`/`TBD` in code.
- **Type consistency:** backend `schemas/assignment.py` (`AssignmentOut`, `SubmissionOut`, `GradeOut`) ↔ frontend `types.ts` field names match; `schemas/gradebook.py` ↔ frontend `Gradebook*` match; `services/grading.py` exports `GradeRow`, `GroupSpec`, `apply_late_penalty`, `group_percentage`, `course_total`, `days_late` and they're imported under those names in `submissions.py`, `gradebook.py`, and the tests; `storage.py` exports `submission_path`, `solution_path`, `upload_bytes`, `read_bytes`, `signed_url`, `_LOCAL_ROOT`, `_supabase_configured` and tests/`submissions.py` use those names.
