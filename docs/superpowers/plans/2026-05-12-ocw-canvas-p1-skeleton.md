# OCW Canvas — Phase 1 (Skeleton + Read-Mostly Canvas) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the OCW Canvas repo as a runnable full-stack app — a "Canvas without homework": FastAPI backend (single-user auth + CRUD for courses/modules/module-items/assignment-groups), React+Vite frontend with the Canvas chrome (left rail, breadcrumb, course-nav), and the read-mostly pages (Dashboard, Course Home, Syllabus, Modules, Video Lectures), with teacher-mode editing of those entities.

**Architecture:** Python 3.12 / FastAPI / SQLAlchemy 2.0 / Alembic / Postgres (Supabase in prod, SQLite for tests), JWT-in-httpOnly-cookie auth for a single account. React 18 / Vite / TypeScript / react-router SPA, hand-rolled Canvas-like CSS, hosted on GitHub Pages. The spec is `docs/superpowers/specs/2026-05-12-ocw-canvas-design.md` — read §2, §3, §4, §6 before starting; the screenshots in `docs/superpowers/specs/assets/canvas-*.png` are the visual source of truth.

**Tech Stack:** fastapi, uvicorn, sqlalchemy, alembic, pydantic-settings, pyjwt, passlib[bcrypt], python-multipart, httpx, pytest, ruff (managed by `uv`); react, react-dom, react-router-dom, react-markdown, remark-gfm, vite, typescript, eslint.

**Conventions for this plan:**
- All backend commands run from `backend/`. All frontend commands run from `frontend/`.
- Commit messages use `type: description` (`feat`/`fix`/`docs`/`refactor`/`chore`/`test`).
- Work happens on a branch `feat/p1-skeleton` (created in Task 0); commit after every task.
- Where a step shows code, write exactly that (adapt obvious things like import order to satisfy ruff).
- "Run: …" steps state the command and the expected result; if the result differs, stop and fix before moving on.

---

### Task 0: Branch + repo skeleton dirs

**Files:**
- Create: `backend/.gitkeep`, `frontend/.gitkeep`, `.github/workflows/.gitkeep` (placeholders, removed as real files land)

- [ ] **Step 1: Create the working branch**

Run (from repo root `D:\GitHub\ocw-canvas`): `git checkout -b feat/p1-skeleton`
Expected: `Switched to a new branch 'feat/p1-skeleton'`

- [ ] **Step 2: Ensure the top-level dirs exist and are tracked**

The repo already has empty `backend/`, `frontend/`, `seed/`, `docs/`. Git won't track empty dirs; create keep-files where needed:

```bash
mkdir -p .github/workflows
printf '' > backend/.gitkeep
printf '' > frontend/.gitkeep
printf '' > .github/workflows/.gitkeep
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "chore: scaffold top-level directories for P1"
```

---

### Task 1: Backend project + config + DB session

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/db.py`
- Create: `backend/.env.example`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Delete: `backend/.gitkeep`

- [ ] **Step 1: Write `backend/pyproject.toml`**

```toml
[project]
name = "ocw-canvas-backend"
version = "0.1.0"
description = "OCW Canvas backend — single-user Canvas-like LMS for self-studying open courseware"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "sqlalchemy>=2.0",
    "alembic>=1.13",
    "pydantic-settings>=2.5",
    "pyjwt>=2.9",
    "passlib[bcrypt]>=1.7.4",
    "python-multipart>=0.0.12",
    "httpx>=0.27",
]

[dependency-groups]
dev = [
    "pytest>=8.3",
    "ruff>=0.7",
]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Step 2: Write `backend/app/__init__.py`** (empty file)

```python
```

- [ ] **Step 3: Write `backend/app/config.py`**

```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "sqlite:///./ocw_canvas.db"

    # Auth
    jwt_secret: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    jwt_ttl_days: int = 30
    cookie_name: str = "ocw_session"
    cookie_secure: bool = False  # True in production (HTTPS); False for local http
    cookie_samesite: str = "lax"  # "none" in production for cross-site frontend

    # CORS — comma-separated list of allowed frontend origins
    frontend_origins: str = "http://localhost:5173"

    # Owner bootstrap (used by `python -m app.manage create-owner` when env-driven)
    owner_email: str = "owner@example.com"

    # Supabase Storage (used from P2 onward)
    supabase_url: str = ""
    supabase_service_key: str = ""

    # AI (used from P3 onward)
    claude_code_oauth_token: str = ""
    anthropic_api_key: str = ""
    ai_solution_generation_enabled: bool = True

    # Email (used from P4 onward)
    resend_api_key: str = ""

    # Cron (used from P4 onward)
    cron_secret: str = "dev-cron-secret"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.frontend_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: Write `backend/app/db.py`**

```python
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()

_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=_connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 5: Write `backend/.env.example`**

```dotenv
# Database — Supabase Postgres connection string in production
DATABASE_URL=sqlite:///./ocw_canvas.db

# Auth
JWT_SECRET=change-me-to-a-long-random-string
COOKIE_SECURE=false
COOKIE_SAMESITE=lax

# CORS — your frontend origin(s), comma-separated
FRONTEND_ORIGINS=http://localhost:5173

# Owner
OWNER_EMAIL=you@example.com

# Supabase Storage (P2+)
SUPABASE_URL=
SUPABASE_SERVICE_KEY=

# AI (P3+) — prefer the Claude Code OAuth token (subscription billing). Fallback: ANTHROPIC_API_KEY + AI_SOLUTION_GENERATION_ENABLED=false
CLAUDE_CODE_OAUTH_TOKEN=
ANTHROPIC_API_KEY=
AI_SOLUTION_GENERATION_ENABLED=true

# Email (P4+)
RESEND_API_KEY=

# Cron (P4+)
CRON_SECRET=change-me
```

- [ ] **Step 6: Write `backend/tests/__init__.py`** (empty file)

```python
```

- [ ] **Step 7: Write `backend/tests/conftest.py`**

```python
import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Force a throwaway sqlite db before app modules import settings.
_tmp_db_fd, _tmp_db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_db_path}"
os.environ["JWT_SECRET"] = "test-secret"

from app.db import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app import models  # noqa: E402,F401  (import side effect: register all models on Base)

_engine = create_engine(os.environ["DATABASE_URL"], connect_args={"check_same_thread": False}, future=True)
_TestSession = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)


@pytest.fixture(autouse=True)
def _fresh_schema():
    Base.metadata.drop_all(_engine)
    Base.metadata.create_all(_engine)
    yield
    Base.metadata.drop_all(_engine)


@pytest.fixture
def db():
    session = _TestSession()
    try:
        yield session
    finally:
        session.close()


def _override_get_db():
    session = _TestSession()
    try:
        yield session
    finally:
        session.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture
def client():
    return TestClient(app)
```

- [ ] **Step 8: Initialise uv and install**

```bash
cd backend
rm -f .gitkeep
uv sync
```
Expected: `uv` creates `.venv/` and `uv.lock`, installs deps without error. (If `uv` is unavailable, `python -m venv .venv && .venv/Scripts/pip install -e . && .venv/Scripts/pip install pytest ruff` is the fallback — but `uv` is the project standard.)

- [ ] **Step 9: Commit**

```bash
cd ..
git add -A
git commit -m "feat: backend project skeleton (config, db session, test harness)"
```

---

### Task 2: SQLAlchemy models (full P1 schema)

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/base.py`
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/course.py`
- Create: `backend/app/models/module.py`
- Create: `backend/app/models/assignment.py`
- Test: `backend/tests/test_models.py`

> Note: this task defines **all P1-relevant tables**: `app_user`, `course`, `module`, `module_item`, `assignment_group`, `assignment`. (`assignment`/`assignment_group` tables exist now because `module_item.assignment_id` FKs `assignment` and the Syllabus "Course Summary" lists assignments; their REST API + UI come in P2.) Later phases add `ai_solution`, `submission`, `grade`, `announcement`, `email_log`, `cron_marker` in their own migrations.

- [ ] **Step 1: Write `backend/app/models/base.py`** (shared mixin)

```python
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


def _uuid() -> str:
    return str(uuid.uuid4())


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
```

- [ ] **Step 2: Write `backend/app/models/user.py`**

```python
from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.base import TimestampMixin, _uuid


class AppUser(Base, TimestampMixin):
    __tablename__ = "app_user"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False, default="Owner")
    reset_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    reset_expires: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

- [ ] **Step 3: Write `backend/app/models/course.py`**

```python
from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.base import TimestampMixin, _uuid


class Course(Base, TimestampMixin):
    __tablename__ = "course"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    institution: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    term_label: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    instructor: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    external_home_url: Mapped[str] = mapped_column(Text, nullable=False, default="")
    textbook: Mapped[str] = mapped_column(Text, nullable=False, default="")
    home_page_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    syllabus_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    color: Mapped[str] = mapped_column(String(9), nullable=False, default="#394B58")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")  # active|completed|planned
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    modules: Mapped[list["Module"]] = relationship(
        back_populates="course", cascade="all, delete-orphan", order_by="Module.position"
    )
    assignment_groups: Mapped[list["AssignmentGroup"]] = relationship(
        back_populates="course", cascade="all, delete-orphan", order_by="AssignmentGroup.position"
    )
    assignments: Mapped[list["Assignment"]] = relationship(
        back_populates="course", cascade="all, delete-orphan", order_by="Assignment.position"
    )


from app.models.assignment import Assignment, AssignmentGroup  # noqa: E402
from app.models.module import Module  # noqa: E402
```

- [ ] **Step 4: Write `backend/app/models/module.py`**

```python
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.base import TimestampMixin, _uuid


class Module(Base, TimestampMixin):
    __tablename__ = "module"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    course_id: Mapped[str] = mapped_column(String(36), ForeignKey("course.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    course: Mapped["Course"] = relationship(back_populates="modules")
    items: Mapped[list["ModuleItem"]] = relationship(
        back_populates="module", cascade="all, delete-orphan", order_by="ModuleItem.position"
    )


class ModuleItem(Base, TimestampMixin):
    __tablename__ = "module_item"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    module_id: Mapped[str] = mapped_column(String(36), ForeignKey("module.id", ondelete="CASCADE"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    indent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # link|video|assignment|note|header
    title: Mapped[str] = mapped_column(String(400), nullable=False)
    external_url: Mapped[str] = mapped_column(Text, nullable=False, default="")
    assignment_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("assignment.id", ondelete="SET NULL"), nullable=True
    )
    text_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    module: Mapped["Module"] = relationship(back_populates="items")


from app.models.course import Course  # noqa: E402
```

- [ ] **Step 5: Write `backend/app/models/assignment.py`**

```python
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.base import TimestampMixin, _uuid


class AssignmentGroup(Base, TimestampMixin):
    __tablename__ = "assignment_group"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    course_id: Mapped[str] = mapped_column(String(36), ForeignKey("course.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    weight: Mapped[float | None] = mapped_column(Numeric(6, 3), nullable=True)
    drop_lowest_n: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    course: Mapped["Course"] = relationship(back_populates="assignment_groups")
    assignments: Mapped[list["Assignment"]] = relationship(
        back_populates="group", order_by="Assignment.position"
    )


class Assignment(Base, TimestampMixin):
    __tablename__ = "assignment"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    course_id: Mapped[str] = mapped_column(String(36), ForeignKey("course.id", ondelete="CASCADE"), nullable=False)
    assignment_group_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("assignment_group.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(400), nullable=False)
    description_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    points_possible: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False, default=100)
    due_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    available_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accepts_files: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    accepts_text: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    official_solution_url: Mapped[str] = mapped_column(Text, nullable=False, default="")
    official_solution_file_path: Mapped[str] = mapped_column(Text, nullable=False, default="")
    late_policy: Mapped[str] = mapped_column(String(20), nullable=False, default="flag_only")  # none|flag_only|percent_per_day
    late_value: Mapped[float | None] = mapped_column(Numeric(6, 3), nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    course: Mapped["Course"] = relationship(back_populates="assignments")
    group: Mapped["AssignmentGroup | None"] = relationship(back_populates="assignments")


from app.models.course import Course  # noqa: E402
```

- [ ] **Step 6: Write `backend/app/models/__init__.py`** (re-export everything so `from app import models` registers all tables on `Base`)

```python
from app.models.assignment import Assignment, AssignmentGroup
from app.models.course import Course
from app.models.module import Module, ModuleItem
from app.models.user import AppUser

__all__ = ["AppUser", "Course", "Module", "ModuleItem", "AssignmentGroup", "Assignment"]
```

- [ ] **Step 7: Write `backend/tests/test_models.py`**

```python
from app.models import Assignment, AssignmentGroup, Course, Module, ModuleItem


def test_course_module_item_cascade(db):
    course = Course(code="MIT 18.100B", title="Real Analysis")
    db.add(course)
    db.flush()
    module = Module(course_id=course.id, title="Unit 1", position=0)
    db.add(module)
    db.flush()
    db.add(ModuleItem(module_id=module.id, kind="link", title="OCW page", external_url="https://ocw.mit.edu", position=0))
    db.commit()

    db.delete(course)
    db.commit()
    assert db.query(Module).count() == 0
    assert db.query(ModuleItem).count() == 0


def test_assignment_belongs_to_group_and_course(db):
    course = Course(code="MIT 18.100B", title="Real Analysis")
    db.add(course)
    db.flush()
    group = AssignmentGroup(course_id=course.id, name="Problem Sets", weight=50, drop_lowest_n=1, position=0)
    db.add(group)
    db.flush()
    a = Assignment(course_id=course.id, assignment_group_id=group.id, title="Problem Set 1", points_possible=100)
    db.add(a)
    db.commit()
    assert a.group.name == "Problem Sets"
    assert a.course.code == "MIT 18.100B"
```

- [ ] **Step 8: Run the model tests** — they'll only pass once `app/main.py` exists (conftest imports it). This task ends here; the test run happens in Task 4 after `main.py` lands. For now, just verify imports compile:

Run: `cd backend && uv run python -c "from app import models; print(sorted(models.__all__))"`
Expected: `['AppUser', 'Assignment', 'AssignmentGroup', 'Course', 'Module', 'ModuleItem']`

- [ ] **Step 9: Commit**

```bash
cd ..
git add -A
git commit -m "feat: SQLAlchemy models for users, courses, modules, assignments"
```

---

### Task 3: Alembic + initial migration

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/versions/0001_initial_schema.py`

- [ ] **Step 1: Add alembic config `backend/alembic.ini`** (minimal)

```ini
[alembic]
script_location = alembic
prepend_sys_path = .

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARNING
handlers = console
qualname =

[logger_sqlalchemy]
level = WARNING
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 2: Write `backend/alembic/env.py`**

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app import models  # noqa: F401  (registers all tables on Base)
from app.config import get_settings
from app.db import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(url=config.get_main_option("sqlalchemy.url"), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 3: Write `backend/alembic/script.py.mako`** (standard alembic template)

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 4: Autogenerate the initial migration**

```bash
cd backend
DATABASE_URL=sqlite:///./_tmp_autogen.db uv run alembic revision --autogenerate -m "initial schema"
rm -f _tmp_autogen.db
```
Expected: a new file under `alembic/versions/` (rename it to `0001_initial_schema.py` and set `revision = "0001"`, `down_revision = None` if not already). It should contain `op.create_table("app_user", ...)`, `course`, `module`, `module_item`, `assignment_group`, `assignment`. Verify all six tables are present; if autogenerate produced a different filename/revision id, that's fine — just ensure it's the only migration and `down_revision = None`.

- [ ] **Step 5: Apply the migration to a fresh sqlite db and verify**

```bash
DATABASE_URL=sqlite:///./_verify.db uv run alembic upgrade head
DATABASE_URL=sqlite:///./_verify.db uv run python -c "import sqlite3; print(sorted(r[0] for r in sqlite3.connect('_verify.db').execute(\"select name from sqlite_master where type='table'\")))"
rm -f _verify.db
```
Expected output includes: `['alembic_version', 'app_user', 'assignment', 'assignment_group', 'course', 'module', 'module_item']`

- [ ] **Step 6: Commit**

```bash
cd ..
git add -A
git commit -m "feat: alembic setup + initial schema migration"
```

---

### Task 4: Auth core + owner bootstrap CLI + FastAPI app

**Files:**
- Create: `backend/app/auth.py`
- Create: `backend/app/manage.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/auth.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/test_auth.py`

- [ ] **Step 1: Write `backend/app/auth.py`**

```python
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Cookie, Depends, HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import AppUser

settings = get_settings()
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(raw: str) -> str:
    return _pwd.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    return _pwd.verify(raw, hashed)


def create_token(user_id: str) -> str:
    now = datetime.now(UTC)
    payload = {"sub": user_id, "iat": now, "exp": now + timedelta(days=settings.jwt_ttl_days)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or expired token") from exc
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="malformed token")
    return sub


def get_current_user(
    db: Session = Depends(get_db),
    session_cookie: str | None = Cookie(default=None, alias=settings.cookie_name),
) -> AppUser:
    if not session_cookie:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not authenticated")
    user_id = decode_token(session_cookie)
    user = db.get(AppUser, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user not found")
    return user
```

- [ ] **Step 2: Write `backend/app/manage.py`** (owner bootstrap CLI)

```python
"""Small management CLI. Usage: python -m app.manage create-owner [--email X] [--password Y] [--name Z]"""
import argparse
import getpass
import sys

from app.auth import hash_password
from app.config import get_settings
from app.db import SessionLocal
from app.models import AppUser


def create_owner(email: str | None, password: str | None, name: str | None) -> None:
    settings = get_settings()
    email = email or settings.owner_email
    if not password:
        password = getpass.getpass("Owner password: ")
    name = name or "Owner"
    db = SessionLocal()
    try:
        existing = db.query(AppUser).first()
        if existing is not None:
            print(f"An owner already exists ({existing.email}); updating its credentials.", file=sys.stderr)
            existing.email = email
            existing.password_hash = hash_password(password)
            existing.display_name = name
        else:
            db.add(AppUser(email=email, password_hash=hash_password(password), display_name=name))
        db.commit()
        print(f"Owner ready: {email}")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("create-owner")
    p.add_argument("--email")
    p.add_argument("--password")
    p.add_argument("--name")
    args = parser.parse_args()
    if args.cmd == "create-owner":
        create_owner(args.email, args.password, args.name)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Write `backend/app/api/__init__.py`** (empty)

```python
```

- [ ] **Step 4: Write `backend/app/api/auth.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.auth import create_token, get_current_user, verify_password
from app.config import get_settings
from app.db import get_db
from app.models import AppUser

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    display_name: str


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.jwt_ttl_days * 24 * 3600,
        path="/",
    )


@router.post("/login", response_model=UserOut)
def login(payload: LoginIn, response: Response, db: Session = Depends(get_db)) -> AppUser:
    user = db.query(AppUser).filter(AppUser.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid email or password")
    _set_session_cookie(response, create_token(user.id))
    return user


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(settings.cookie_name, path="/")
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user: AppUser = Depends(get_current_user)) -> AppUser:
    return user
```

> Note: `request-reset` / `reset` endpoints are added in P4 (they need Resend). The frontend's "Forgot password?" link is present but its submit is wired in P4.

- [ ] **Step 5: Write `backend/app/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth
from app.config import get_settings

settings = get_settings()

app = FastAPI(title="OCW Canvas API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 6: Write `backend/tests/test_auth.py`**

```python
from app.auth import create_token, decode_token, hash_password, verify_password
from app.models import AppUser


def test_password_hash_roundtrip():
    h = hash_password("hunter2")
    assert h != "hunter2"
    assert verify_password("hunter2", h)
    assert not verify_password("wrong", h)


def test_token_roundtrip():
    token = create_token("user-123")
    assert decode_token(token) == "user-123"


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_login_me_logout_flow(client, db):
    db.add(AppUser(id="u1", email="me@example.com", password_hash=hash_password("pw"), display_name="Me"))
    db.commit()

    # unauthenticated /me
    assert client.get("/api/auth/me").status_code == 401

    # bad password
    assert client.post("/api/auth/login", json={"email": "me@example.com", "password": "nope"}).status_code == 401

    # good login sets cookie
    r = client.post("/api/auth/login", json={"email": "me@example.com", "password": "pw"})
    assert r.status_code == 200
    assert r.json()["email"] == "me@example.com"

    # now /me works (TestClient persists cookies on the same instance)
    r2 = client.get("/api/auth/me")
    assert r2.status_code == 200
    assert r2.json()["display_name"] == "Me"

    # logout clears it
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401
```

- [ ] **Step 7: Run all backend tests**

Run: `cd backend && uv run pytest -q`
Expected: all tests pass (test_models.py, test_auth.py). If `test_models` fails on import, check that `app/main.py` exists and `app/models/__init__.py` imports every model module.

- [ ] **Step 8: Run ruff**

Run: `cd backend && uv run ruff check .`
Expected: `All checks passed!` (fix anything it flags).

- [ ] **Step 9: Commit**

```bash
cd ..
git add -A
git commit -m "feat: native JWT-cookie auth, owner CLI, FastAPI app + health"
```

---

### Task 5: CRUD API — courses, modules, module-items, assignment-groups

**Files:**
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/common.py`
- Create: `backend/app/schemas/course.py`
- Create: `backend/app/api/courses.py`
- Create: `backend/app/api/modules.py`
- Create: `backend/app/api/module_items.py`
- Create: `backend/app/api/assignment_groups.py`
- Modify: `backend/app/main.py` (mount the new routers)
- Test: `backend/tests/test_courses_api.py`

> Design note: all read endpoints and all write endpoints sit behind `get_current_user` (single user — no separate "teacher" role; the frontend's "teacher mode" just hides/shows the write affordances client-side). Routers are split by resource so each file stays small.

- [ ] **Step 1: Write `backend/app/schemas/__init__.py`** (empty)

```python
```

- [ ] **Step 2: Write `backend/app/schemas/common.py`**

```python
from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
```

- [ ] **Step 3: Write `backend/app/schemas/course.py`** (request/response models for course, module, module_item, assignment_group, and a "course detail" tree)

```python
from app.schemas.common import ORMModel


# ---- Course ----
class CourseBase(ORMModel):
    code: str
    title: str
    institution: str = ""
    term_label: str = ""
    instructor: str = ""
    external_home_url: str = ""
    textbook: str = ""
    home_page_md: str = ""
    syllabus_md: str = ""
    description: str = ""
    color: str = "#394B58"
    status: str = "active"
    display_order: int = 0


class CourseCreate(CourseBase):
    pass


class CourseUpdate(CourseBase):
    pass


class CourseOut(CourseBase):
    id: str


# ---- Module ----
class ModuleBase(ORMModel):
    title: str
    position: int = 0
    published: bool = True


class ModuleCreate(ModuleBase):
    pass


class ModuleUpdate(ModuleBase):
    pass


class ModuleItemBase(ORMModel):
    position: int = 0
    indent: int = 0
    kind: str  # link|video|assignment|note|header
    title: str
    external_url: str = ""
    assignment_id: str | None = None
    text_md: str = ""
    published: bool = True


class ModuleItemCreate(ModuleItemBase):
    pass


class ModuleItemUpdate(ModuleItemBase):
    pass


class ModuleItemOut(ModuleItemBase):
    id: str
    module_id: str


class ModuleOut(ModuleBase):
    id: str
    course_id: str
    items: list[ModuleItemOut] = []


# ---- Assignment group ----
class AssignmentGroupBase(ORMModel):
    name: str
    weight: float | None = None
    drop_lowest_n: int = 0
    position: int = 0


class AssignmentGroupCreate(AssignmentGroupBase):
    pass


class AssignmentGroupUpdate(AssignmentGroupBase):
    pass


class AssignmentGroupOut(AssignmentGroupBase):
    id: str
    course_id: str


# ---- Composite ----
class AssignmentSummaryOut(ORMModel):
    id: str
    title: str
    points_possible: float
    due_at: object | None = None
    assignment_group_id: str | None = None
    published: bool = True


class CourseDetailOut(CourseOut):
    modules: list[ModuleOut] = []
    assignment_groups: list[AssignmentGroupOut] = []
    assignments: list[AssignmentSummaryOut] = []
```

- [ ] **Step 4: Write `backend/app/api/courses.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import AppUser, Course
from app.schemas.course import CourseCreate, CourseDetailOut, CourseOut, CourseUpdate

router = APIRouter(prefix="/courses", tags=["courses"], dependencies=[Depends(get_current_user)])


def _get_course(db: Session, course_id: str) -> Course:
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="course not found")
    return course


@router.get("", response_model=list[CourseOut])
def list_courses(db: Session = Depends(get_db)) -> list[Course]:
    return db.query(Course).order_by(Course.display_order, Course.code).all()


@router.post("", response_model=CourseOut, status_code=201)
def create_course(payload: CourseCreate, db: Session = Depends(get_db)) -> Course:
    course = Course(**payload.model_dump())
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@router.get("/{course_id}", response_model=CourseDetailOut)
def get_course(course_id: str, db: Session = Depends(get_db)) -> Course:
    return _get_course(db, course_id)


@router.put("/{course_id}", response_model=CourseOut)
def update_course(course_id: str, payload: CourseUpdate, db: Session = Depends(get_db)) -> Course:
    course = _get_course(db, course_id)
    for k, v in payload.model_dump().items():
        setattr(course, k, v)
    db.commit()
    db.refresh(course)
    return course


@router.delete("/{course_id}", status_code=204)
def delete_course(course_id: str, db: Session = Depends(get_db)) -> None:
    course = _get_course(db, course_id)
    db.delete(course)
    db.commit()


# silence unused-import lint on AppUser (it's referenced via the dependency)
_ = AppUser
```

(Remove the `_ = AppUser` line if `AppUser` isn't imported — only import what you use; `get_current_user` returns it but this module doesn't need the symbol. Clean up imports to satisfy ruff.)

- [ ] **Step 5: Write `backend/app/api/modules.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import Course, Module
from app.schemas.course import ModuleCreate, ModuleOut, ModuleUpdate

router = APIRouter(tags=["modules"], dependencies=[Depends(get_current_user)])


@router.get("/courses/{course_id}/modules", response_model=list[ModuleOut])
def list_modules(course_id: str, db: Session = Depends(get_db)) -> list[Module]:
    if db.get(Course, course_id) is None:
        raise HTTPException(404, "course not found")
    return db.query(Module).filter(Module.course_id == course_id).order_by(Module.position).all()


@router.post("/courses/{course_id}/modules", response_model=ModuleOut, status_code=201)
def create_module(course_id: str, payload: ModuleCreate, db: Session = Depends(get_db)) -> Module:
    if db.get(Course, course_id) is None:
        raise HTTPException(404, "course not found")
    module = Module(course_id=course_id, **payload.model_dump())
    db.add(module)
    db.commit()
    db.refresh(module)
    return module


def _get_module(db: Session, module_id: str) -> Module:
    module = db.get(Module, module_id)
    if module is None:
        raise HTTPException(404, "module not found")
    return module


@router.put("/modules/{module_id}", response_model=ModuleOut)
def update_module(module_id: str, payload: ModuleUpdate, db: Session = Depends(get_db)) -> Module:
    module = _get_module(db, module_id)
    for k, v in payload.model_dump().items():
        setattr(module, k, v)
    db.commit()
    db.refresh(module)
    return module


@router.delete("/modules/{module_id}", status_code=204)
def delete_module(module_id: str, db: Session = Depends(get_db)) -> None:
    db.delete(_get_module(db, module_id))
    db.commit()
```

- [ ] **Step 6: Write `backend/app/api/module_items.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import Module, ModuleItem
from app.schemas.course import ModuleItemCreate, ModuleItemOut, ModuleItemUpdate

router = APIRouter(tags=["module-items"], dependencies=[Depends(get_current_user)])

_VALID_KINDS = {"link", "video", "assignment", "note", "header"}


def _validate_kind(kind: str) -> None:
    if kind not in _VALID_KINDS:
        raise HTTPException(422, f"invalid module item kind {kind!r}")


@router.post("/modules/{module_id}/items", response_model=ModuleItemOut, status_code=201)
def create_item(module_id: str, payload: ModuleItemCreate, db: Session = Depends(get_db)) -> ModuleItem:
    if db.get(Module, module_id) is None:
        raise HTTPException(404, "module not found")
    _validate_kind(payload.kind)
    item = ModuleItem(module_id=module_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def _get_item(db: Session, item_id: str) -> ModuleItem:
    item = db.get(ModuleItem, item_id)
    if item is None:
        raise HTTPException(404, "module item not found")
    return item


@router.put("/module-items/{item_id}", response_model=ModuleItemOut)
def update_item(item_id: str, payload: ModuleItemUpdate, db: Session = Depends(get_db)) -> ModuleItem:
    item = _get_item(db, item_id)
    _validate_kind(payload.kind)
    for k, v in payload.model_dump().items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/module-items/{item_id}", status_code=204)
def delete_item(item_id: str, db: Session = Depends(get_db)) -> None:
    db.delete(_get_item(db, item_id))
    db.commit()
```

- [ ] **Step 7: Write `backend/app/api/assignment_groups.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import AssignmentGroup, Course
from app.schemas.course import AssignmentGroupCreate, AssignmentGroupOut, AssignmentGroupUpdate

router = APIRouter(tags=["assignment-groups"], dependencies=[Depends(get_current_user)])


@router.get("/courses/{course_id}/assignment-groups", response_model=list[AssignmentGroupOut])
def list_groups(course_id: str, db: Session = Depends(get_db)) -> list[AssignmentGroup]:
    if db.get(Course, course_id) is None:
        raise HTTPException(404, "course not found")
    return db.query(AssignmentGroup).filter(AssignmentGroup.course_id == course_id).order_by(AssignmentGroup.position).all()


@router.post("/courses/{course_id}/assignment-groups", response_model=AssignmentGroupOut, status_code=201)
def create_group(course_id: str, payload: AssignmentGroupCreate, db: Session = Depends(get_db)) -> AssignmentGroup:
    if db.get(Course, course_id) is None:
        raise HTTPException(404, "course not found")
    group = AssignmentGroup(course_id=course_id, **payload.model_dump())
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


def _get_group(db: Session, group_id: str) -> AssignmentGroup:
    group = db.get(AssignmentGroup, group_id)
    if group is None:
        raise HTTPException(404, "assignment group not found")
    return group


@router.put("/assignment-groups/{group_id}", response_model=AssignmentGroupOut)
def update_group(group_id: str, payload: AssignmentGroupUpdate, db: Session = Depends(get_db)) -> AssignmentGroup:
    group = _get_group(db, group_id)
    for k, v in payload.model_dump().items():
        setattr(group, k, v)
    db.commit()
    db.refresh(group)
    return group


@router.delete("/assignment-groups/{group_id}", status_code=204)
def delete_group(group_id: str, db: Session = Depends(get_db)) -> None:
    db.delete(_get_group(db, group_id))
    db.commit()
```

- [ ] **Step 8: Mount the routers in `backend/app/main.py`** — replace the router section so it reads:

```python
from app.api import assignment_groups, auth, courses, module_items, modules

# ... (app + CORS unchanged) ...

app.include_router(auth.router, prefix="/api")
app.include_router(courses.router, prefix="/api")
app.include_router(modules.router, prefix="/api")
app.include_router(module_items.router, prefix="/api")
app.include_router(assignment_groups.router, prefix="/api")
```

- [ ] **Step 9: Write `backend/tests/test_courses_api.py`**

```python
from app.auth import hash_password
from app.models import AppUser


def _login(client, db):
    db.add(AppUser(id="u1", email="me@example.com", password_hash=hash_password("pw"), display_name="Me"))
    db.commit()
    assert client.post("/api/auth/login", json={"email": "me@example.com", "password": "pw"}).status_code == 200


def test_course_crud_and_tree(client, db):
    _login(client, db)

    # requires auth
    fresh = client.__class__(client.app)
    assert fresh.get("/api/courses").status_code == 401

    # create
    r = client.post("/api/courses", json={"code": "MIT 18.100B", "title": "Real Analysis", "color": "#8B0000"})
    assert r.status_code == 201
    cid = r.json()["id"]

    # list
    assert [c["code"] for c in client.get("/api/courses").json()] == ["MIT 18.100B"]

    # add a module + items
    m = client.post(f"/api/courses/{cid}/modules", json={"title": "Unit 1", "position": 0}).json()
    client.post(f"/api/modules/{m['id']}/items", json={"kind": "link", "title": "OCW", "external_url": "https://ocw.mit.edu", "position": 0})
    bad = client.post(f"/api/modules/{m['id']}/items", json={"kind": "bogus", "title": "x", "position": 1})
    assert bad.status_code == 422

    # add an assignment group
    g = client.post(f"/api/courses/{cid}/assignment-groups", json={"name": "Problem Sets", "weight": 50, "drop_lowest_n": 1, "position": 0})
    assert g.status_code == 201

    # detail tree
    detail = client.get(f"/api/courses/{cid}").json()
    assert detail["title"] == "Real Analysis"
    assert detail["modules"][0]["items"][0]["title"] == "OCW"
    assert detail["assignment_groups"][0]["name"] == "Problem Sets"

    # update + delete course
    client.put(f"/api/courses/{cid}", json={"code": "MIT 18.100B", "title": "Real Analysis (Spring 2025)"})
    assert client.get(f"/api/courses/{cid}").json()["title"] == "Real Analysis (Spring 2025)"
    assert client.delete(f"/api/courses/{cid}").status_code == 204
    assert client.get(f"/api/courses/{cid}").status_code == 404
```

- [ ] **Step 10: Run tests + ruff**

Run: `cd backend && uv run pytest -q && uv run ruff check .`
Expected: all pass, ruff clean.

- [ ] **Step 11: Commit**

```bash
cd ..
git add -A
git commit -m "feat: CRUD API for courses, modules, module items, assignment groups"
```

---

### Task 6: Frontend project skeleton + Vite config for GitHub Pages

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/.env.example`
- Create: `frontend/.eslintrc.cjs`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/vite-env.d.ts`
- Create: `frontend/public/404.html`
- Delete: `frontend/.gitkeep`

- [ ] **Step 1: Write `frontend/package.json`**

```json
{
  "name": "ocw-canvas-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "lint": "eslint . --ext ts,tsx",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.26.2",
    "react-markdown": "^9.0.1",
    "remark-gfm": "^4.0.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.5",
    "@types/react-dom": "^18.3.0",
    "@typescript-eslint/eslint-plugin": "^8.6.0",
    "@typescript-eslint/parser": "^8.6.0",
    "@vitejs/plugin-react": "^4.3.1",
    "eslint": "^8.57.0",
    "eslint-plugin-react-hooks": "^4.6.2",
    "eslint-plugin-react-refresh": "^0.4.11",
    "typescript": "^5.5.4",
    "vite": "^5.4.6"
  }
}
```

- [ ] **Step 2: Write `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 3: Write `frontend/tsconfig.node.json`**

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 4: Write `frontend/vite.config.ts`** — base path = `/ocw-canvas/` so it works on GitHub Pages; in dev it stays `/`.

```ts
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig(({ command }) => ({
  plugins: [react()],
  base: command === "build" ? "/ocw-canvas/" : "/",
  server: { port: 5173 },
}));
```

- [ ] **Step 5: Write `frontend/index.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>OCW Canvas</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 6: Write `frontend/public/404.html`** — GitHub Pages SPA fallback (redirects deep links back into the SPA, preserving the path).

```html
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <script>
      // GitHub Pages SPA redirect: rewrite /ocw-canvas/foo/bar -> /ocw-canvas/?/foo/bar
      var seg = 1; // number of path segments to keep (the repo name)
      var l = window.location;
      var path = l.pathname.split("/").slice(0, 1 + seg).join("/");
      var rest = l.pathname.slice(path.length).replace(/^\//, "");
      l.replace(path + "/?/" + rest + (l.search ? "&" + l.search.slice(1) : "") + l.hash);
    </script>
  </head>
  <body></body>
</html>
```

- [ ] **Step 7: Write `frontend/.env.example`**

```dotenv
# Base URL of the FastAPI backend (no trailing slash). In dev: http://localhost:8000
VITE_API_BASE_URL=http://localhost:8000
```

- [ ] **Step 8: Write `frontend/.eslintrc.cjs`**

```js
module.exports = {
  root: true,
  env: { browser: true, es2022: true },
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react-hooks/recommended",
  ],
  parser: "@typescript-eslint/parser",
  parserOptions: { ecmaVersion: "latest", sourceType: "module" },
  plugins: ["react-refresh"],
  rules: {
    "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
    "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
  },
  ignorePatterns: ["dist", ".eslintrc.cjs"],
};
```

- [ ] **Step 9: Write `frontend/src/vite-env.d.ts`**

```ts
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
}
interface ImportMeta {
  readonly env: ImportMetaEnv;
}
```

- [ ] **Step 10: Write `frontend/src/main.tsx`** (App component itself is created in Task 9; for now a placeholder that the build can compile — it'll be replaced)

```tsx
import React from "react";
import ReactDOM from "react-dom/client";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <div>OCW Canvas — bootstrapping…</div>
  </React.StrictMode>,
);
```

- [ ] **Step 11: Install + verify the build**

```bash
cd frontend
rm -f .gitkeep
npm install
npm run build
```
Expected: `npm install` succeeds; `npm run build` produces `dist/` with `index.html` and assets. (If `tsc -b` complains about `tsconfig.node.json` references, ensure both tsconfig files exist as written.)

- [ ] **Step 12: Add `frontend/.gitignore`** entries (the repo root `.gitignore` already ignores `node_modules`, `dist`; nothing more needed — skip if so). Then commit:

```bash
cd ..
git add -A
git commit -m "feat: frontend project skeleton (Vite + React + TS, GH Pages base + SPA fallback)"
```

---

### Task 7: Frontend API client + auth context + types

**Files:**
- Create: `frontend/src/api/types.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/auth/AuthContext.tsx`
- Test: (no unit tests for the frontend in P1 — verified via typecheck + manual browser pass per the spec)

- [ ] **Step 1: Write `frontend/src/api/types.ts`** — mirrors the backend response models

```ts
export interface User {
  id: string;
  email: string;
  display_name: string;
}

export type CourseStatus = "active" | "completed" | "planned";
export type ModuleItemKind = "link" | "video" | "assignment" | "note" | "header";

export interface Course {
  id: string;
  code: string;
  title: string;
  institution: string;
  term_label: string;
  instructor: string;
  external_home_url: string;
  textbook: string;
  home_page_md: string;
  syllabus_md: string;
  description: string;
  color: string;
  status: CourseStatus;
  display_order: number;
}

export interface ModuleItem {
  id: string;
  module_id: string;
  position: number;
  indent: number;
  kind: ModuleItemKind;
  title: string;
  external_url: string;
  assignment_id: string | null;
  text_md: string;
  published: boolean;
}

export interface Module {
  id: string;
  course_id: string;
  title: string;
  position: number;
  published: boolean;
  items: ModuleItem[];
}

export interface AssignmentGroup {
  id: string;
  course_id: string;
  name: string;
  weight: number | null;
  drop_lowest_n: number;
  position: number;
}

export interface AssignmentSummary {
  id: string;
  title: string;
  points_possible: number;
  due_at: string | null;
  assignment_group_id: string | null;
  published: boolean;
}

export interface CourseDetail extends Course {
  modules: Module[];
  assignment_groups: AssignmentGroup[];
  assignments: AssignmentSummary[];
}
```

- [ ] **Step 2: Write `frontend/src/api/client.ts`** — a tiny typed fetch wrapper that always sends/accepts cookies

```ts
import type {
  AssignmentGroup,
  Course,
  CourseDetail,
  Module,
  ModuleItem,
  User,
} from "./types";

const BASE = import.meta.env.VITE_API_BASE_URL.replace(/\/$/, "");

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}/api${path}`, {
    method,
    credentials: "include",
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  const data = text ? JSON.parse(text) : undefined;
  if (!res.ok) throw new ApiError(res.status, (data && data.detail) || res.statusText);
  return data as T;
}

export const api = {
  // auth
  login: (email: string, password: string) => req<User>("POST", "/auth/login", { email, password }),
  logout: () => req<{ ok: boolean }>("POST", "/auth/logout"),
  me: () => req<User>("GET", "/auth/me"),

  // courses
  listCourses: () => req<Course[]>("GET", "/courses"),
  getCourse: (id: string) => req<CourseDetail>("GET", `/courses/${id}`),
  createCourse: (c: Partial<Course>) => req<Course>("POST", "/courses", c),
  updateCourse: (id: string, c: Partial<Course>) => req<Course>("PUT", `/courses/${id}`, c),
  deleteCourse: (id: string) => req<void>("DELETE", `/courses/${id}`),

  // modules
  createModule: (courseId: string, m: { title: string; position: number; published?: boolean }) =>
    req<Module>("POST", `/courses/${courseId}/modules`, m),
  updateModule: (id: string, m: { title: string; position: number; published?: boolean }) =>
    req<Module>("PUT", `/modules/${id}`, m),
  deleteModule: (id: string) => req<void>("DELETE", `/modules/${id}`),

  // module items
  createItem: (moduleId: string, it: Partial<ModuleItem> & { kind: string; title: string }) =>
    req<ModuleItem>("POST", `/modules/${moduleId}/items`, it),
  updateItem: (id: string, it: Partial<ModuleItem> & { kind: string; title: string }) =>
    req<ModuleItem>("PUT", `/module-items/${id}`, it),
  deleteItem: (id: string) => req<void>("DELETE", `/module-items/${id}`),

  // assignment groups
  createGroup: (courseId: string, g: Partial<AssignmentGroup> & { name: string }) =>
    req<AssignmentGroup>("POST", `/courses/${courseId}/assignment-groups`, g),
  updateGroup: (id: string, g: Partial<AssignmentGroup> & { name: string }) =>
    req<AssignmentGroup>("PUT", `/assignment-groups/${id}`, g),
  deleteGroup: (id: string) => req<void>("DELETE", `/assignment-groups/${id}`),
};
```

- [ ] **Step 3: Write `frontend/src/auth/AuthContext.tsx`**

```tsx
import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { ApiError, api } from "../api/client";
import type { User } from "../api/types";

interface AuthState {
  user: User | null;
  loading: boolean;
  teacherMode: boolean;
  setTeacherMode: (v: boolean) => void;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthCtx = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [teacherMode, setTeacherModeState] = useState(() => localStorage.getItem("teacherMode") === "1");

  useEffect(() => {
    api
      .me()
      .then(setUser)
      .catch((e) => {
        if (!(e instanceof ApiError && e.status === 401)) console.error(e);
      })
      .finally(() => setLoading(false));
  }, []);

  function setTeacherMode(v: boolean) {
    setTeacherModeState(v);
    localStorage.setItem("teacherMode", v ? "1" : "0");
  }

  async function login(email: string, password: string) {
    setUser(await api.login(email, password));
  }
  async function logout() {
    await api.logout();
    setUser(null);
  }

  const value = useMemo(
    () => ({ user, loading, teacherMode, setTeacherMode, login, logout }),
    [user, loading, teacherMode],
  );
  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
```

- [ ] **Step 4: Typecheck**

Run: `cd frontend && npm run typecheck`
Expected: no errors. (Some imports are unused until Task 9 wires them; if `noUnusedLocals` complains, that's fine to leave for now only if they're *referenced* — here everything exported is used by exports, so it should pass. If not, add a temporary `// eslint-disable` is NOT acceptable — instead ensure Task 9 lands before the final P1 verification. For this task's checkpoint, `npm run build` may report unused-locals; accept it and proceed.)

- [ ] **Step 5: Commit**

```bash
cd ..
git add -A
git commit -m "feat: frontend API client, types, and auth context"
```

---

### Task 8: Canvas-like CSS + shared UI primitives

**Files:**
- Create: `frontend/src/styles/canvas.css`
- Create: `frontend/src/components/Markdown.tsx`
- Create: `frontend/src/components/Spinner.tsx`
- Create: `frontend/src/components/Modal.tsx`

- [ ] **Step 1: Write `frontend/src/styles/canvas.css`** — the Canvas look. Match the screenshots: dark narrow left rail, white content, breadcrumb bar, course-nav rail, module cards, course cards.

```css
:root {
  --rail-bg: #2d3b45;
  --rail-bg-active: #394b58;
  --link: #0374b5;
  --link-hover: #02567d;
  --text: #2d3b45;
  --text-muted: #6b7780;
  --border: #d7dade;
  --bg: #f5f5f5;
  --card-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
  --brand: #8b0000; /* maroon accent, matches the reference screenshots */
  font-family: "Lato", "Helvetica Neue", Helvetica, Arial, sans-serif;
}

* { box-sizing: border-box; }
body { margin: 0; color: var(--text); background: #fff; font-size: 14px; }
a { color: var(--link); text-decoration: none; }
a:hover { color: var(--link-hover); text-decoration: underline; }

/* ---- App shell ---- */
.app { display: flex; min-height: 100vh; }
.left-rail {
  width: 84px; background: var(--rail-bg); color: #fff; flex: 0 0 84px;
  display: flex; flex-direction: column; align-items: stretch; position: sticky; top: 0; height: 100vh;
}
.left-rail .brand { background: var(--brand); height: 54px; display: flex; align-items: center; justify-content: center; font-weight: 700; }
.left-rail .rail-item {
  color: #fff; opacity: 0.85; padding: 12px 4px; text-align: center; font-size: 11px; line-height: 1.3; cursor: pointer;
  display: flex; flex-direction: column; align-items: center; gap: 4px; border: none; background: none;
}
.left-rail .rail-item:hover { opacity: 1; text-decoration: none; }
.left-rail .rail-item.active { opacity: 1; background: var(--rail-bg-active); }
.left-rail .rail-item .glyph { font-size: 20px; line-height: 1; }
.left-rail .rail-badge { background: var(--brand); color: #fff; border-radius: 999px; font-size: 10px; padding: 0 5px; margin-top: 2px; }
.left-rail .spacer { flex: 1; }

.main { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.breadcrumb { border-bottom: 1px solid var(--border); padding: 14px 24px; font-size: 14px; }
.breadcrumb a { color: var(--link); }
.breadcrumb .sep { color: var(--text-muted); margin: 0 6px; }
.breadcrumb .leaf { color: var(--text); }

.content-wrap { display: flex; flex: 1; }
.course-nav { width: 200px; flex: 0 0 200px; padding: 12px 0; border-right: 1px solid var(--border); }
.course-nav .term { font-size: 12px; color: var(--text-muted); padding: 0 16px 8px; }
.course-nav a { display: block; padding: 8px 16px; color: var(--link); border-left: 3px solid transparent; }
.course-nav a.active { color: var(--text); font-weight: 700; border-left-color: var(--brand); background: #fff; }
.content { flex: 1; min-width: 0; padding: 24px 32px; }
.page-with-sidebar { display: flex; gap: 24px; }
.page-with-sidebar .col-main { flex: 1; min-width: 0; }
.page-with-sidebar .col-side { width: 280px; flex: 0 0 280px; }

h1.page-title { font-weight: 300; font-size: 28px; margin: 0 0 18px; }
.muted { color: var(--text-muted); }
.btn { display: inline-flex; align-items: center; gap: 6px; padding: 7px 14px; border: 1px solid var(--border); background: #fff; border-radius: 4px; cursor: pointer; color: var(--text); font-size: 14px; }
.btn:hover { background: #f0f0f0; }
.btn.primary { background: var(--brand); color: #fff; border-color: var(--brand); }
.btn.primary:hover { background: #6f0000; }
.btn.small { padding: 3px 8px; font-size: 12px; }
.row-actions { float: right; display: inline-flex; gap: 6px; }

/* ---- Dashboard course cards ---- */
.dashboard-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 18px; }
.course-card { border: 1px solid var(--border); border-radius: 6px; overflow: hidden; box-shadow: var(--card-shadow); background: #fff; }
.course-card .band { height: 140px; position: relative; }
.course-card .band .menu { position: absolute; top: 6px; right: 8px; color: #fff; opacity: 0.85; cursor: pointer; }
.course-card .body { padding: 12px 14px 14px; }
.course-card .body .ctitle { font-weight: 700; }
.course-card .body .csub { color: var(--text-muted); font-size: 13px; margin-top: 2px; }
.course-card .body .cterm { color: var(--text-muted); font-size: 12px; margin-top: 2px; }
.course-card .footer-icons { display: flex; gap: 16px; padding: 10px 14px; border-top: 1px solid #eee; color: var(--text-muted); font-size: 18px; }

/* ---- "To Do" / sidebar widgets ---- */
.widget { margin-bottom: 22px; }
.widget h2 { font-size: 17px; font-weight: 400; border-bottom: 1px solid var(--border); padding-bottom: 6px; margin: 0 0 8px; }
.todo-item { display: flex; gap: 8px; padding: 8px 0; border-bottom: 1px solid #eee; font-size: 13px; }
.todo-item .glyph { color: var(--text-muted); }
.todo-item .meta { color: var(--text-muted); }

/* ---- Modules ---- */
.module { border: 1px solid var(--border); border-radius: 4px; margin-bottom: 16px; }
.module > .module-head { background: #f5f5f5; padding: 10px 14px; font-weight: 700; display: flex; align-items: center; gap: 8px; cursor: pointer; }
.module .module-item { display: flex; align-items: center; gap: 10px; padding: 10px 14px; border-top: 1px solid #eee; }
.module .module-item .mi-icon { color: var(--text-muted); width: 18px; text-align: center; }
.module .module-item.indent-1 { padding-left: 38px; }
.module .module-item.indent-2 { padding-left: 62px; }
.module .module-item .mi-sub { color: var(--text-muted); font-size: 12px; }
.module .module-item.header-row { font-weight: 700; background: #fafafa; }

/* ---- Calendar mini ---- */
.minical { border: 1px solid var(--border); border-radius: 4px; padding: 8px; font-size: 12px; }
.minical table { width: 100%; border-collapse: collapse; }
.minical td { text-align: center; padding: 4px 2px; }
.minical td.today { background: #fde8e8; border-radius: 4px; }
.minical td.has-event { background: #eee; border-radius: 4px; font-weight: 700; }
.minical .cal-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; font-weight: 700; }

/* ---- Tables ---- */
table.data { width: 100%; border-collapse: collapse; }
table.data th, table.data td { text-align: left; padding: 10px 8px; border-bottom: 1px solid var(--border); }
table.data th { color: var(--text-muted); font-weight: 700; font-size: 12px; text-transform: none; }

/* ---- Login ---- */
.login-wrap { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: var(--bg); }
.login-card { background: #fff; border: 1px solid var(--border); border-radius: 6px; padding: 28px 32px; width: 360px; box-shadow: var(--card-shadow); }
.login-card h1 { font-weight: 300; font-size: 24px; text-align: center; margin: 0 0 18px; }
.login-card label { display: block; font-size: 13px; margin: 12px 0 4px; }
.login-card input { width: 100%; padding: 8px; border: 1px solid var(--border); border-radius: 4px; }
.login-card .err { color: #b00020; font-size: 13px; margin-top: 10px; }
.login-card .actions { margin-top: 18px; display: flex; flex-direction: column; gap: 10px; align-items: center; }

/* ---- Modal ---- */
.modal-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: flex-start; justify-content: center; padding-top: 8vh; z-index: 50; }
.modal { background: #fff; border-radius: 6px; width: 520px; max-width: 92vw; max-height: 80vh; overflow: auto; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
.modal .modal-head { padding: 16px 20px; border-bottom: 1px solid var(--border); font-weight: 700; }
.modal .modal-body { padding: 16px 20px; }
.modal .modal-body label { display: block; font-size: 13px; margin: 12px 0 4px; }
.modal .modal-body input, .modal .modal-body textarea, .modal .modal-body select { width: 100%; padding: 7px; border: 1px solid var(--border); border-radius: 4px; font-family: inherit; font-size: 14px; }
.modal .modal-body .req::after { content: " *"; color: #b00020; }
.modal .modal-foot { padding: 14px 20px; border-top: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }

/* ---- Markdown content ---- */
.md { line-height: 1.6; }
.md h1, .md h2, .md h3 { font-weight: 700; margin-top: 1.2em; }
.md pre { background: #f5f5f5; padding: 12px; border-radius: 4px; overflow: auto; }
.md code { background: #f5f5f5; padding: 1px 4px; border-radius: 3px; }
.md table { border-collapse: collapse; }
.md table th, .md table td { border: 1px solid var(--border); padding: 6px 10px; }

.center-empty { text-align: center; color: var(--text-muted); padding: 60px 20px; }
.external-arrow::after { content: " ↗"; font-size: 11px; color: var(--text-muted); }
.badge-pill { display: inline-block; padding: 1px 8px; border-radius: 999px; font-size: 11px; font-weight: 700; }
.badge-pill.missing { color: #b00020; border: 1px solid #b00020; }
.badge-pill.late { color: #b45309; border: 1px solid #b45309; }
```

- [ ] **Step 2: Write `frontend/src/components/Markdown.tsx`**

```tsx
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function Markdown({ children }: { children: string }) {
  return (
    <div className="md">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </div>
  );
}
```

- [ ] **Step 3: Write `frontend/src/components/Spinner.tsx`**

```tsx
export function Spinner({ label = "Loading…" }: { label?: string }) {
  return <div className="center-empty">{label}</div>;
}
```

- [ ] **Step 4: Write `frontend/src/components/Modal.tsx`**

```tsx
import type { ReactNode } from "react";

export function Modal({
  title,
  children,
  footer,
  onClose,
}: {
  title: string;
  children: ReactNode;
  footer?: ReactNode;
  onClose: () => void;
}) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">{title}</div>
        <div className="modal-body">{children}</div>
        {footer !== undefined && <div className="modal-foot">{footer}</div>}
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Commit**

```bash
cd ..
git add -A
git commit -m "feat: Canvas-like CSS + shared UI primitives (Markdown, Modal, Spinner)"
```

---

### Task 9: App shell, router, login page, dashboard

**Files:**
- Create: `frontend/src/App.tsx`
- Modify: `frontend/src/main.tsx` (render `<App/>` inside `<AuthProvider>` + `<BrowserRouter basename>`)
- Create: `frontend/src/components/AppLayout.tsx`
- Create: `frontend/src/components/RequireAuth.tsx`
- Create: `frontend/src/pages/LoginPage.tsx`
- Create: `frontend/src/pages/DashboardPage.tsx`
- Create: `frontend/src/lib/spaRedirect.ts`

- [ ] **Step 1: Write `frontend/src/lib/spaRedirect.ts`** — companion to `public/404.html`: if the URL is `…/ocw-canvas/?/foo/bar`, rewrite it back to `…/ocw-canvas/foo/bar` before the router boots.

```ts
export function applySpaRedirect(): void {
  const { search } = window.location;
  if (search.startsWith("?/")) {
    const rest = search.slice(2);
    const path = rest.replace(/&/g, "?").replace(/~and~/g, "&");
    window.history.replaceState(null, "", import.meta.env.BASE_URL.replace(/\/$/, "") + "/" + path + window.location.hash);
  }
}
```

- [ ] **Step 2: Replace `frontend/src/main.tsx`**

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { AuthProvider } from "./auth/AuthContext";
import { applySpaRedirect } from "./lib/spaRedirect";
import "./styles/canvas.css";

applySpaRedirect();

const basename = import.meta.env.BASE_URL.replace(/\/$/, "") || "/";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter basename={basename}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
```

- [ ] **Step 3: Write `frontend/src/components/AppLayout.tsx`** — the dark left rail + breadcrumb + content slot. Uses simple emoji glyphs for icons (placeholder — fine for v1).

```tsx
import type { ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

interface Crumb {
  label: string;
  to?: string;
}

export function AppLayout({ crumbs, children }: { crumbs: Crumb[]; children: ReactNode }) {
  const { user, teacherMode, setTeacherMode, logout } = useAuth();
  const nav = useNavigate();

  async function doLogout() {
    await logout();
    nav("/login");
  }

  return (
    <div className="app">
      <nav className="left-rail">
        <div className="brand">OCW</div>
        <button className="rail-item" onClick={() => setTeacherMode(!teacherMode)} title="Toggle teacher mode">
          <span className="glyph">{teacherMode ? "🛠" : "👤"}</span>
          {user ? user.display_name.split(" ")[0] : "Account"}
        </button>
        <RailLink to="/" glyph="🏠" label="Dashboard" />
        <RailLink to="/courses" glyph="📚" label="Courses" />
        <RailLink to="/calendar" glyph="📅" label="Calendar" />
        <RailLink to="/announcements" glyph="📨" label="Inbox" />
        <div className="spacer" />
        <button className="rail-item" onClick={doLogout}>
          <span className="glyph">⎋</span>Log out
        </button>
      </nav>
      <div className="main">
        <div className="breadcrumb">
          {crumbs.map((c, i) => (
            <span key={i}>
              {i > 0 && <span className="sep">›</span>}
              {c.to ? <NavLink to={c.to}>{c.label}</NavLink> : <span className="leaf">{c.label}</span>}
            </span>
          ))}
        </div>
        {children}
      </div>
    </div>
  );
}

function RailLink({ to, glyph, label }: { to: string; glyph: string; label: string }) {
  return (
    <NavLink to={to} className={({ isActive }) => "rail-item" + (isActive ? " active" : "")} end={to === "/"}>
      <span className="glyph">{glyph}</span>
      {label}
    </NavLink>
  );
}
```

- [ ] **Step 4: Write `frontend/src/components/RequireAuth.tsx`**

```tsx
import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { Spinner } from "./Spinner";

export function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <Spinner label="Loading OCW Canvas…" />;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}
```

- [ ] **Step 5: Write `frontend/src/pages/LoginPage.tsx`**

```tsx
import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export function LoginPage() {
  const { user, loading, login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  if (!loading && user) return <Navigate to="/" replace />;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      await login(email, password);
      nav("/");
    } catch {
      setErr("Invalid email or password.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <form className="login-card" onSubmit={submit}>
        <h1>OCW Canvas</h1>
        <label htmlFor="email">Email</label>
        <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoFocus />
        <label htmlFor="pw">Password</label>
        <input id="pw" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        {err && <div className="err">{err}</div>}
        <div className="actions">
          <button className="btn primary" disabled={busy} style={{ width: "100%" }}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
          <span className="muted" title="Available once email is configured (later phase)">Forgot password?</span>
        </div>
      </form>
    </div>
  );
}
```

- [ ] **Step 6: Write `frontend/src/pages/DashboardPage.tsx`** — course-card grid + a stub "To Do" sidebar. (To-Do real data needs assignments → P2; in P1 it just shows recent courses / a placeholder.)

```tsx
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { Course } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { AppLayout } from "../components/AppLayout";
import { Spinner } from "../components/Spinner";
import { CourseEditModal } from "../components/edit/CourseEditModal";

export function DashboardPage() {
  const { teacherMode } = useAuth();
  const [courses, setCourses] = useState<Course[] | null>(null);
  const [editing, setEditing] = useState<Course | "new" | null>(null);

  function reload() {
    api.listCourses().then(setCourses);
  }
  useEffect(reload, []);

  return (
    <AppLayout crumbs={[{ label: "Dashboard" }]}>
      <div className="content">
        <div className="page-with-sidebar">
          <div className="col-main">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h1 className="page-title">Dashboard</h1>
              {teacherMode && (
                <button className="btn primary" onClick={() => setEditing("new")}>
                  + Add course
                </button>
              )}
            </div>
            {courses === null ? (
              <Spinner />
            ) : courses.length === 0 ? (
              <div className="center-empty">Add your first course to get started.</div>
            ) : (
              <div className="dashboard-grid">
                {courses.map((c) => (
                  <div className="course-card" key={c.id}>
                    <div className="band" style={{ background: c.color }}>
                      {teacherMode && (
                        <span className="menu" onClick={() => setEditing(c)} title="Edit course">
                          ⋮
                        </span>
                      )}
                    </div>
                    <div className="body">
                      <Link to={`/courses/${c.id}`} className="ctitle">
                        {c.code} {c.term_label && `(${c.term_label})`} {c.title}
                      </Link>
                      <div className="csub">{c.title}</div>
                      <div className="cterm">{c.institution || c.term_label}</div>
                    </div>
                    <div className="footer-icons">
                      <Link to={`/courses/${c.id}/announcements`} title="Announcements">📣</Link>
                      <Link to={`/courses/${c.id}/modules`} title="Modules">📂</Link>
                      <Link to={`/courses/${c.id}/assignments`} title="Assignments">📝</Link>
                      <Link to={`/courses/${c.id}/grades`} title="Grades">📊</Link>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
          <div className="col-side">
            <div className="widget">
              <h2>To Do</h2>
              <div className="muted" style={{ fontSize: 13 }}>
                Upcoming assignment deadlines will appear here.
              </div>
            </div>
            <div className="widget">
              <h2>Recent Feedback</h2>
              <div className="muted" style={{ fontSize: 13 }}>
                Graded work will appear here.
              </div>
            </div>
          </div>
        </div>
      </div>
      {editing && (
        <CourseEditModal
          course={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            reload();
          }}
        />
      )}
    </AppLayout>
  );
}
```

- [ ] **Step 7: Write `frontend/src/App.tsx`** — the route table (course pages + edit modal land in Tasks 10–11; reference them now so the import graph is complete, then create them)

```tsx
import { Navigate, Route, Routes } from "react-router-dom";
import { LoginPage } from "./pages/LoginPage";
import { DashboardPage } from "./pages/DashboardPage";
import { CalendarPage } from "./pages/CalendarPage";
import { AnnouncementsPage } from "./pages/AnnouncementsPage";
import { CoursesListPage } from "./pages/CoursesListPage";
import { CourseHomePage } from "./pages/CourseHomePage";
import { CourseSyllabusPage } from "./pages/CourseSyllabusPage";
import { CourseModulesPage } from "./pages/CourseModulesPage";
import { CourseVideosPage } from "./pages/CourseVideosPage";
import { RequireAuth } from "./components/RequireAuth";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <DashboardPage />
          </RequireAuth>
        }
      />
      <Route path="/courses" element={<RequireAuth><CoursesListPage /></RequireAuth>} />
      <Route path="/calendar" element={<RequireAuth><CalendarPage /></RequireAuth>} />
      <Route path="/announcements" element={<RequireAuth><AnnouncementsPage /></RequireAuth>} />
      <Route path="/courses/:courseId" element={<RequireAuth><CourseHomePage /></RequireAuth>} />
      <Route path="/courses/:courseId/syllabus" element={<RequireAuth><CourseSyllabusPage /></RequireAuth>} />
      <Route path="/courses/:courseId/modules" element={<RequireAuth><CourseModulesPage /></RequireAuth>} />
      <Route path="/courses/:courseId/videos" element={<RequireAuth><CourseVideosPage /></RequireAuth>} />
      {/* assignments + grades pages arrive in P2; route stubs avoid dead links from the course nav */}
      <Route path="/courses/:courseId/assignments" element={<RequireAuth><CourseModulesPage /></RequireAuth>} />
      <Route path="/courses/:courseId/grades" element={<RequireAuth><CourseModulesPage /></RequireAuth>} />
      <Route path="/courses/:courseId/announcements" element={<RequireAuth><AnnouncementsPage /></RequireAuth>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
```

> The assignments/grades routes temporarily render `CourseModulesPage`; P2 replaces them. (Better: render a small "Coming in a later phase" placeholder — acceptable either way.)

- [ ] **Step 8: Commit (will not build yet — pages referenced in App.tsx are created next)**

```bash
cd ..
git add -A
git commit -m "feat: app shell, router, login page, dashboard"
```

---

### Task 10: Course pages — Course layout, Home, Syllabus, Modules, Videos; Calendar; Courses list; Announcements stub

**Files:**
- Create: `frontend/src/components/CourseLayout.tsx`
- Create: `frontend/src/pages/CourseHomePage.tsx`
- Create: `frontend/src/pages/CourseSyllabusPage.tsx`
- Create: `frontend/src/pages/CourseModulesPage.tsx`
- Create: `frontend/src/pages/CourseVideosPage.tsx`
- Create: `frontend/src/pages/CalendarPage.tsx`
- Create: `frontend/src/pages/CoursesListPage.tsx`
- Create: `frontend/src/pages/AnnouncementsPage.tsx`
- Create: `frontend/src/lib/useCourse.ts`
- Create: `frontend/src/components/MiniCalendar.tsx`

- [ ] **Step 1: Write `frontend/src/lib/useCourse.ts`** — loads a course detail tree, with reload

```ts
import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { CourseDetail } from "../api/types";

export function useCourse(courseId: string | undefined) {
  const [course, setCourse] = useState<CourseDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const reload = useCallback(() => {
    if (!courseId) return;
    api.getCourse(courseId).then(setCourse).catch((e) => setError(String(e)));
  }, [courseId]);
  useEffect(reload, [reload]);
  return { course, error, reload };
}
```

> If `useCallback` import name differs in your React version, it's `import { useCallback, useEffect, useState } from "react";` — React 18 exports `useCallback`. Keep as written.

- [ ] **Step 2: Write `frontend/src/components/MiniCalendar.tsx`** — month grid; highlights today and days that have an assignment due

```tsx
import { useState } from "react";

export function MiniCalendar({ eventDays }: { eventDays: Set<string> }) {
  const [cursor, setCursor] = useState(() => {
    const n = new Date();
    return new Date(n.getFullYear(), n.getMonth(), 1);
  });
  const todayKey = new Date().toISOString().slice(0, 10);
  const year = cursor.getFullYear();
  const month = cursor.getMonth();
  const first = new Date(year, month, 1);
  const startDow = first.getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells: (number | null)[] = [];
  for (let i = 0; i < startDow; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);
  while (cells.length % 7 !== 0) cells.push(null);
  const rows: (number | null)[][] = [];
  for (let i = 0; i < cells.length; i += 7) rows.push(cells.slice(i, i + 7));
  const monthName = cursor.toLocaleString("default", { month: "long", year: "numeric" });

  function key(d: number) {
    return `${year}-${String(month + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
  }

  return (
    <div className="minical">
      <div className="cal-head">
        <button className="btn small" onClick={() => setCursor(new Date(year, month - 1, 1))}>‹</button>
        <span>{monthName}</span>
        <button className="btn small" onClick={() => setCursor(new Date(year, month + 1, 1))}>›</button>
      </div>
      <table>
        <thead>
          <tr>{["S", "M", "T", "W", "T", "F", "S"].map((d, i) => <th key={i} style={{ fontSize: 10, color: "#888" }}>{d}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((r, ri) => (
            <tr key={ri}>
              {r.map((d, ci) => (
                <td key={ci} className={d === null ? "" : key(d) === todayKey ? "today" : eventDays.has(key(d)) ? "has-event" : ""}>
                  {d ?? ""}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 3: Write `frontend/src/components/CourseLayout.tsx`** — wraps a course page with the breadcrumb + course-nav rail + content. Reused by Home/Syllabus/Modules/Videos.

```tsx
import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import type { CourseDetail } from "../api/types";
import { AppLayout } from "./AppLayout";

const NAV: { to: string; label: string }[] = [
  { to: "", label: "Home" },
  { to: "/syllabus", label: "Syllabus" },
  { to: "/modules", label: "Modules" },
  { to: "/assignments", label: "Assignments" },
  { to: "/grades", label: "Grades" },
  { to: "/videos", label: "Video Lectures" },
  { to: "/announcements", label: "Announcements" },
];

export function CourseLayout({
  course,
  section,
  children,
  sidebar,
}: {
  course: CourseDetail;
  section: string; // breadcrumb leaf label
  children: ReactNode;
  sidebar?: ReactNode;
}) {
  const base = `/courses/${course.id}`;
  const crumbs =
    section === "Home"
      ? [{ label: `${course.code} ${course.title}` }]
      : [{ label: `${course.code} ${course.title}`, to: base }, { label: section }];

  return (
    <AppLayout crumbs={crumbs}>
      <div className="content-wrap">
        <nav className="course-nav">
          <div className="term">{course.term_label}</div>
          {NAV.map((n) => (
            <NavLink key={n.to} to={base + n.to} end={n.to === ""} className={({ isActive }) => (isActive ? "active" : "")}>
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="content">
          {sidebar ? (
            <div className="page-with-sidebar">
              <div className="col-main">{children}</div>
              <div className="col-side">{sidebar}</div>
            </div>
          ) : (
            children
          )}
        </div>
      </div>
    </AppLayout>
  );
}
```

- [ ] **Step 4: Write `frontend/src/components/CourseSidebar.tsx`** — the Stream/Calendar/Notifications buttons + To-Do + mini calendar (shared by Home & Syllabus)

```tsx
import { Link } from "react-router-dom";
import type { CourseDetail } from "../api/types";
import { MiniCalendar } from "./MiniCalendar";

export function CourseSidebar({ course }: { course: CourseDetail }) {
  const eventDays = new Set(
    course.assignments.filter((a) => a.due_at).map((a) => a.due_at!.slice(0, 10)),
  );
  return (
    <>
      <div className="widget">
        <Link className="btn" to="/calendar" style={{ width: "100%", marginBottom: 8 }}>📊 View Course Stream</Link>
        <Link className="btn" to="/calendar" style={{ width: "100%", marginBottom: 8 }}>📅 View Course Calendar</Link>
        <span className="btn muted" style={{ width: "100%" }}>🔔 View Course Notifications</span>
      </div>
      <div className="widget">
        <h2>To Do</h2>
        <div className="muted" style={{ fontSize: 13 }}>Assignment deadlines for this course appear here.</div>
      </div>
      <div className="widget">
        <MiniCalendar eventDays={eventDays} />
      </div>
    </>
  );
}
```

> Add `import "./CourseSidebar"` usage in CourseLayout consumers (Home/Syllabus) below. (Note: this file isn't in the Task 10 file list above — add `Create: frontend/src/components/CourseSidebar.tsx` to it.)

- [ ] **Step 5: Write `frontend/src/pages/CourseHomePage.tsx`**

```tsx
import { useParams } from "react-router-dom";
import { CourseLayout } from "../components/CourseLayout";
import { CourseSidebar } from "../components/CourseSidebar";
import { Markdown } from "../components/Markdown";
import { Spinner } from "../components/Spinner";
import { useCourse } from "../lib/useCourse";

export function CourseHomePage() {
  const { courseId } = useParams();
  const { course } = useCourse(courseId);
  if (!course) return <Spinner />;
  return (
    <CourseLayout course={course} section="Home" sidebar={<CourseSidebar course={course} />}>
      <h1 className="page-title">{course.code} {course.term_label && `(${course.term_label})`} {course.title}</h1>
      <p className="muted">{[course.institution, course.instructor].filter(Boolean).join(" · ")}</p>
      {course.home_page_md ? <Markdown>{course.home_page_md}</Markdown> : <p className="muted">No front page content yet.</p>}
      {course.external_home_url && (
        <p style={{ marginTop: 16 }}>
          <a href={course.external_home_url} target="_blank" rel="noreferrer" className="external-arrow">Official course site</a>
        </p>
      )}
    </CourseLayout>
  );
}
```

- [ ] **Step 6: Write `frontend/src/pages/CourseSyllabusPage.tsx`**

```tsx
import { useParams } from "react-router-dom";
import { CourseLayout } from "../components/CourseLayout";
import { CourseSidebar } from "../components/CourseSidebar";
import { Markdown } from "../components/Markdown";
import { Spinner } from "../components/Spinner";
import { useCourse } from "../lib/useCourse";

export function CourseSyllabusPage() {
  const { courseId } = useParams();
  const { course } = useCourse(courseId);
  if (!course) return <Spinner />;
  const summary = [...course.assignments].sort((a, b) => (a.due_at || "").localeCompare(b.due_at || ""));
  return (
    <CourseLayout course={course} section="Syllabus" sidebar={<CourseSidebar course={course} />}>
      <h1 className="page-title">Syllabus</h1>
      {course.syllabus_md ? <Markdown>{course.syllabus_md}</Markdown> : <p className="muted">No syllabus text yet.</p>}
      <h2 style={{ marginTop: 28, fontWeight: 400 }}>Course Summary</h2>
      <table className="data">
        <thead><tr><th>Date</th><th>Assignment</th><th>Points</th></tr></thead>
        <tbody>
          {summary.length === 0 && <tr><td colSpan={3} className="muted">No assignments yet.</td></tr>}
          {summary.map((a) => (
            <tr key={a.id}>
              <td>{a.due_at ? new Date(a.due_at).toLocaleDateString() : "—"}</td>
              <td>{a.title}</td>
              <td>{a.points_possible}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </CourseLayout>
  );
}
```

- [ ] **Step 7: Write `frontend/src/pages/CourseModulesPage.tsx`** — the core read-mostly page (and teacher-mode editing of modules/items is wired in Task 11)

```tsx
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { CourseDetail, Module, ModuleItem } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { CourseLayout } from "../components/CourseLayout";
import { Spinner } from "../components/Spinner";
import { ModuleEditModal, ModuleItemEditModal } from "../components/edit/ModuleEditModals";
import { api } from "../api/client";
import { useCourse } from "../lib/useCourse";

const ICON: Record<string, string> = { link: "🔗", video: "🔗", assignment: "📝", note: "📄", header: "›" };

export function CourseModulesPage() {
  const { courseId } = useParams();
  const { course, reload } = useCourse(courseId);
  const { teacherMode } = useAuth();
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [editingModule, setEditingModule] = useState<Module | "new" | null>(null);
  const [editingItem, setEditingItem] = useState<{ moduleId: string; item: ModuleItem | "new" } | null>(null);

  if (!course) return <Spinner />;

  function toggle(id: string) {
    setCollapsed((s) => {
      const n = new Set(s);
      n.has(id) ? n.delete(id) : n.add(id);
      return n;
    });
  }

  return (
    <CourseLayout course={course} section="Modules">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1 className="page-title">Modules</h1>
        <div>
          <button className="btn" onClick={() => setCollapsed(new Set(course.modules.map((m) => m.id)))}>Collapse All</button>
          {teacherMode && <button className="btn primary" style={{ marginLeft: 8 }} onClick={() => setEditingModule("new")}>+ Module</button>}
        </div>
      </div>
      {course.modules.length === 0 && <div className="center-empty">No modules yet.</div>}
      {course.modules.map((m) => (
        <div className="module" key={m.id}>
          <div className="module-head" onClick={() => toggle(m.id)}>
            <span>{collapsed.has(m.id) ? "▸" : "▾"}</span>
            <span style={{ flex: 1 }}>{m.title}</span>
            {teacherMode && (
              <span className="row-actions" onClick={(e) => e.stopPropagation()}>
                <button className="btn small" onClick={() => setEditingItem({ moduleId: m.id, item: "new" })}>+ Item</button>
                <button className="btn small" onClick={() => setEditingModule(m)}>Edit</button>
                <button className="btn small" onClick={async () => { if (confirm("Delete module?")) { await api.deleteModule(m.id); reload(); } }}>Delete</button>
              </span>
            )}
          </div>
          {!collapsed.has(m.id) &&
            m.items.map((it) => (
              <div className={`module-item indent-${it.indent} ${it.kind === "header" ? "header-row" : ""}`} key={it.id}>
                <span className="mi-icon">{ICON[it.kind] ?? "•"}</span>
                <span style={{ flex: 1 }}>
                  {it.kind === "header" ? (
                    <strong>{it.title}</strong>
                  ) : it.kind === "link" || it.kind === "video" ? (
                    <a href={it.external_url} target="_blank" rel="noreferrer" className="external-arrow">{it.title}</a>
                  ) : it.kind === "assignment" && it.assignment_id ? (
                    <Link to={`/courses/${course.id}/assignments/${it.assignment_id}`}>{it.title}</Link>
                  ) : (
                    <span>{it.title}</span>
                  )}
                  {it.kind === "assignment" && <ItemAssignmentSub course={course} item={it} />}
                </span>
                {teacherMode && (
                  <span className="row-actions">
                    <button className="btn small" onClick={() => setEditingItem({ moduleId: m.id, item: it })}>Edit</button>
                    <button className="btn small" onClick={async () => { if (confirm("Delete item?")) { await api.deleteItem(it.id); reload(); } }}>Delete</button>
                  </span>
                )}
              </div>
            ))}
        </div>
      ))}

      {editingModule && (
        <ModuleEditModal
          courseId={course.id}
          module={editingModule === "new" ? null : editingModule}
          nextPosition={course.modules.length}
          onClose={() => setEditingModule(null)}
          onSaved={() => { setEditingModule(null); reload(); }}
        />
      )}
      {editingItem && (
        <ModuleItemEditModal
          moduleId={editingItem.moduleId}
          item={editingItem.item === "new" ? null : editingItem.item}
          nextPosition={(course.modules.find((m) => m.id === editingItem.moduleId)?.items.length) ?? 0}
          assignments={course.assignments}
          onClose={() => setEditingItem(null)}
          onSaved={() => { setEditingItem(null); reload(); }}
        />
      )}
    </CourseLayout>
  );
}

function ItemAssignmentSub({ course, item }: { course: CourseDetail; item: ModuleItem }) {
  const a = course.assignments.find((x) => x.id === item.assignment_id);
  if (!a) return null;
  return <div className="mi-sub">{a.due_at ? `${new Date(a.due_at).toLocaleDateString()} · ` : ""}{a.points_possible} pts</div>;
}
```

- [ ] **Step 8: Write `frontend/src/pages/CourseVideosPage.tsx`**

```tsx
import { useParams } from "react-router-dom";
import { CourseLayout } from "../components/CourseLayout";
import { Spinner } from "../components/Spinner";
import { useCourse } from "../lib/useCourse";

export function CourseVideosPage() {
  const { courseId } = useParams();
  const { course } = useCourse(courseId);
  if (!course) return <Spinner />;
  const videos = course.modules.flatMap((m) => m.items.filter((it) => it.kind === "video").map((it) => ({ module: m.title, ...it })));
  return (
    <CourseLayout course={course} section="Video Lectures">
      <h1 className="page-title">Video Lectures</h1>
      {videos.length === 0 && <div className="center-empty">No video lectures yet.</div>}
      <table className="data">
        <thead><tr><th>Module</th><th>Lecture</th></tr></thead>
        <tbody>
          {videos.map((v) => (
            <tr key={v.id}>
              <td className="muted">{v.module}</td>
              <td><a href={v.external_url} target="_blank" rel="noreferrer" className="external-arrow">{v.title}</a></td>
            </tr>
          ))}
        </tbody>
      </table>
    </CourseLayout>
  );
}
```

- [ ] **Step 9: Write `frontend/src/pages/CoursesListPage.tsx`** (simple list — the rail's "Courses" target)

```tsx
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { Course } from "../api/types";
import { AppLayout } from "../components/AppLayout";
import { Spinner } from "../components/Spinner";

export function CoursesListPage() {
  const [courses, setCourses] = useState<Course[] | null>(null);
  useEffect(() => { api.listCourses().then(setCourses); }, []);
  return (
    <AppLayout crumbs={[{ label: "Courses" }]}>
      <div className="content">
        <h1 className="page-title">All Courses</h1>
        {courses === null ? <Spinner /> : (
          <table className="data">
            <thead><tr><th>Course</th><th>Term</th><th>Status</th></tr></thead>
            <tbody>
              {courses.map((c) => (
                <tr key={c.id}>
                  <td><Link to={`/courses/${c.id}`}>{c.code} — {c.title}</Link></td>
                  <td className="muted">{c.term_label}</td>
                  <td className="muted">{c.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </AppLayout>
  );
}
```

- [ ] **Step 10: Write `frontend/src/pages/CalendarPage.tsx`** — month grid of all courses' assignment due dates (uses what's available; in P1 likely empty)

```tsx
import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Course } from "../api/types";
import { AppLayout } from "../components/AppLayout";
import { MiniCalendar } from "../components/MiniCalendar";
import { Spinner } from "../components/Spinner";

export function CalendarPage() {
  const [courses, setCourses] = useState<Course[] | null>(null);
  const [days, setDays] = useState<Set<string>>(new Set());
  useEffect(() => {
    api.listCourses().then(async (cs) => {
      setCourses(cs);
      const ds = new Set<string>();
      for (const c of cs) {
        const d = await api.getCourse(c.id);
        d.assignments.forEach((a) => a.due_at && ds.add(a.due_at.slice(0, 10)));
      }
      setDays(ds);
    });
  }, []);
  return (
    <AppLayout crumbs={[{ label: "Calendar" }]}>
      <div className="content">
        <h1 className="page-title">Calendar</h1>
        {courses === null ? <Spinner /> : (
          <div style={{ maxWidth: 420 }}><MiniCalendar eventDays={days} /></div>
        )}
        <p className="muted" style={{ marginTop: 12 }}>Days with assignment deadlines are highlighted. Full agenda view is a later enhancement.</p>
      </div>
    </AppLayout>
  );
}
```

- [ ] **Step 11: Write `frontend/src/pages/AnnouncementsPage.tsx`** (stub — real announcements arrive in P4)

```tsx
import { AppLayout } from "../components/AppLayout";

export function AnnouncementsPage() {
  return (
    <AppLayout crumbs={[{ label: "Inbox" }]}>
      <div className="content">
        <h1 className="page-title">Announcements</h1>
        <div className="center-empty">No announcements yet. Graded-work and deadline notices will show up here once the homework system is live.</div>
      </div>
    </AppLayout>
  );
}
```

- [ ] **Step 12: Commit**

```bash
cd ..
git add -A
git commit -m "feat: course layout + Home/Syllabus/Modules/Videos/Calendar/Courses/Announcements pages"
```

---

### Task 11: Teacher-mode edit modals (course, module, module item, assignment group)

**Files:**
- Create: `frontend/src/components/edit/CourseEditModal.tsx`
- Create: `frontend/src/components/edit/ModuleEditModals.tsx` (exports `ModuleEditModal`, `ModuleItemEditModal`)
- Create: `frontend/src/components/edit/AssignmentGroupEditModal.tsx`
- Modify: `frontend/src/pages/CourseHomePage.tsx` (add a teacher-mode "Edit course" affordance — small button near the banner)

- [ ] **Step 1: Write `frontend/src/components/edit/CourseEditModal.tsx`**

```tsx
import { useState } from "react";
import { api } from "../../api/client";
import type { Course } from "../../api/types";
import { Modal } from "../Modal";

export function CourseEditModal({
  course,
  onClose,
  onSaved,
}: {
  course: Course | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [f, setF] = useState<Partial<Course>>(
    course ?? { code: "", title: "", color: "#394B58", status: "active", display_order: 0 },
  );
  const [busy, setBusy] = useState(false);
  function up<K extends keyof Course>(k: K, v: Course[K]) {
    setF((s) => ({ ...s, [k]: v }));
  }
  async function save() {
    setBusy(true);
    try {
      if (course) await api.updateCourse(course.id, f);
      else await api.createCourse(f);
      onSaved();
    } finally {
      setBusy(false);
    }
  }
  async function del() {
    if (!course || !confirm("Delete this course and everything in it?")) return;
    await api.deleteCourse(course.id);
    onSaved();
  }
  return (
    <Modal
      title={course ? "Edit course" : "Add course"}
      onClose={onClose}
      footer={
        <>
          {course ? <button className="btn" onClick={del}>Delete course</button> : <span />}
          <span>
            <button className="btn" onClick={onClose}>Cancel</button>
            <button className="btn primary" style={{ marginLeft: 8 }} disabled={busy} onClick={save}>Save</button>
          </span>
        </>
      }
    >
      <label className="req">Code</label>
      <input value={f.code ?? ""} onChange={(e) => up("code", e.target.value)} placeholder="MIT 18.100B" />
      <label className="req">Title</label>
      <input value={f.title ?? ""} onChange={(e) => up("title", e.target.value)} placeholder="Real Analysis" />
      <label>Institution</label>
      <input value={f.institution ?? ""} onChange={(e) => up("institution", e.target.value)} placeholder="MIT OpenCourseWare" />
      <label>Term label</label>
      <input value={f.term_label ?? ""} onChange={(e) => up("term_label", e.target.value)} placeholder="Spring 2025" />
      <label>Instructor</label>
      <input value={f.instructor ?? ""} onChange={(e) => up("instructor", e.target.value)} />
      <label>Official course URL</label>
      <input value={f.external_home_url ?? ""} onChange={(e) => up("external_home_url", e.target.value)} placeholder="https://ocw.mit.edu/..." />
      <label>Textbook</label>
      <input value={f.textbook ?? ""} onChange={(e) => up("textbook", e.target.value)} />
      <label>Home page (markdown)</label>
      <textarea rows={5} value={f.home_page_md ?? ""} onChange={(e) => up("home_page_md", e.target.value)} />
      <label>Syllabus (markdown)</label>
      <textarea rows={6} value={f.syllabus_md ?? ""} onChange={(e) => up("syllabus_md", e.target.value)} />
      <label>Description (card blurb)</label>
      <input value={f.description ?? ""} onChange={(e) => up("description", e.target.value)} />
      <label>Card color (hex)</label>
      <input value={f.color ?? ""} onChange={(e) => up("color", e.target.value)} placeholder="#8B0000" />
      <label>Status</label>
      <select value={f.status ?? "active"} onChange={(e) => up("status", e.target.value as Course["status"])}>
        <option value="active">active</option>
        <option value="completed">completed</option>
        <option value="planned">planned</option>
      </select>
      <label>Display order</label>
      <input type="number" value={f.display_order ?? 0} onChange={(e) => up("display_order", Number(e.target.value))} />
    </Modal>
  );
}
```

- [ ] **Step 2: Write `frontend/src/components/edit/ModuleEditModals.tsx`**

```tsx
import { useState } from "react";
import { api } from "../../api/client";
import type { AssignmentSummary, Module, ModuleItem, ModuleItemKind } from "../../api/types";
import { Modal } from "../Modal";

export function ModuleEditModal({
  courseId,
  module,
  nextPosition,
  onClose,
  onSaved,
}: {
  courseId: string;
  module: Module | null;
  nextPosition: number;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [title, setTitle] = useState(module?.title ?? "");
  const [position, setPosition] = useState(module?.position ?? nextPosition);
  const [published, setPublished] = useState(module?.published ?? true);
  async function save() {
    if (module) await api.updateModule(module.id, { title, position, published });
    else await api.createModule(courseId, { title, position, published });
    onSaved();
  }
  return (
    <Modal
      title={module ? "Edit module" : "Add module"}
      onClose={onClose}
      footer={
        <span style={{ marginLeft: "auto" }}>
          <button className="btn" onClick={onClose}>Cancel</button>
          <button className="btn primary" style={{ marginLeft: 8 }} onClick={save}>Save</button>
        </span>
      }
    >
      <label className="req">Title</label>
      <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Unit 1 — The Real Numbers" />
      <label>Position</label>
      <input type="number" value={position} onChange={(e) => setPosition(Number(e.target.value))} />
      <label><input type="checkbox" checked={published} onChange={(e) => setPublished(e.target.checked)} /> Published</label>
    </Modal>
  );
}

const KINDS: ModuleItemKind[] = ["link", "video", "assignment", "note", "header"];

export function ModuleItemEditModal({
  moduleId,
  item,
  nextPosition,
  assignments,
  onClose,
  onSaved,
}: {
  moduleId: string;
  item: ModuleItem | null;
  nextPosition: number;
  assignments: AssignmentSummary[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [kind, setKind] = useState<ModuleItemKind>(item?.kind ?? "link");
  const [title, setTitle] = useState(item?.title ?? "");
  const [externalUrl, setExternalUrl] = useState(item?.external_url ?? "");
  const [assignmentId, setAssignmentId] = useState<string | "">(item?.assignment_id ?? "");
  const [textMd, setTextMd] = useState(item?.text_md ?? "");
  const [indent, setIndent] = useState(item?.indent ?? 0);
  const [position, setPosition] = useState(item?.position ?? nextPosition);
  const [published, setPublished] = useState(item?.published ?? true);

  async function save() {
    const payload = {
      kind,
      title,
      external_url: kind === "link" || kind === "video" ? externalUrl : "",
      assignment_id: kind === "assignment" ? (assignmentId || null) : null,
      text_md: kind === "note" || kind === "header" ? textMd : "",
      indent,
      position,
      published,
    };
    if (item) await api.updateItem(item.id, payload);
    else await api.createItem(moduleId, payload);
    onSaved();
  }

  return (
    <Modal
      title={item ? "Edit module item" : "Add module item"}
      onClose={onClose}
      footer={
        <span style={{ marginLeft: "auto" }}>
          <button className="btn" onClick={onClose}>Cancel</button>
          <button className="btn primary" style={{ marginLeft: 8 }} onClick={save}>Save</button>
        </span>
      }
    >
      <label className="req">Kind</label>
      <select value={kind} onChange={(e) => setKind(e.target.value as ModuleItemKind)}>
        {KINDS.map((k) => <option key={k} value={k}>{k}</option>)}
      </select>
      <label className="req">Title</label>
      <input value={title} onChange={(e) => setTitle(e.target.value)} />
      {(kind === "link" || kind === "video") && (
        <>
          <label className="req">External URL (opens in a new tab — never re-host the file)</label>
          <input value={externalUrl} onChange={(e) => setExternalUrl(e.target.value)} placeholder="https://ocw.mit.edu/..." />
        </>
      )}
      {kind === "assignment" && (
        <>
          <label>Assignment</label>
          <select value={assignmentId} onChange={(e) => setAssignmentId(e.target.value)}>
            <option value="">(none — pick one)</option>
            {assignments.map((a) => <option key={a.id} value={a.id}>{a.title}</option>)}
          </select>
        </>
      )}
      {(kind === "note" || kind === "header") && (
        <>
          <label>Text (markdown)</label>
          <textarea rows={4} value={textMd} onChange={(e) => setTextMd(e.target.value)} />
        </>
      )}
      <label>Indent (0–2)</label>
      <input type="number" min={0} max={2} value={indent} onChange={(e) => setIndent(Number(e.target.value))} />
      <label>Position</label>
      <input type="number" value={position} onChange={(e) => setPosition(Number(e.target.value))} />
      <label><input type="checkbox" checked={published} onChange={(e) => setPublished(e.target.checked)} /> Published</label>
    </Modal>
  );
}
```

- [ ] **Step 3: Write `frontend/src/components/edit/AssignmentGroupEditModal.tsx`** (used now from a small "Manage assignment groups" affordance — keep it minimal; full assignment management is P2)

```tsx
import { useState } from "react";
import { api } from "../../api/client";
import type { AssignmentGroup } from "../../api/types";
import { Modal } from "../Modal";

export function AssignmentGroupEditModal({
  courseId,
  group,
  nextPosition,
  onClose,
  onSaved,
}: {
  courseId: string;
  group: AssignmentGroup | null;
  nextPosition: number;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState(group?.name ?? "");
  const [weight, setWeight] = useState<string>(group?.weight != null ? String(group.weight) : "");
  const [dropLowest, setDropLowest] = useState(group?.drop_lowest_n ?? 0);
  const [position, setPosition] = useState(group?.position ?? nextPosition);
  async function save() {
    const payload = { name, weight: weight === "" ? null : Number(weight), drop_lowest_n: dropLowest, position };
    if (group) await api.updateGroup(group.id, payload);
    else await api.createGroup(courseId, payload);
    onSaved();
  }
  return (
    <Modal
      title={group ? "Edit assignment group" : "Add assignment group"}
      onClose={onClose}
      footer={
        <span style={{ marginLeft: "auto" }}>
          <button className="btn" onClick={onClose}>Cancel</button>
          <button className="btn primary" style={{ marginLeft: 8 }} onClick={save}>Save</button>
        </span>
      }
    >
      <label className="req">Name</label>
      <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Problem Sets" />
      <label>Weight (% of course grade — leave blank for unweighted)</label>
      <input value={weight} onChange={(e) => setWeight(e.target.value)} placeholder="50" />
      <label>Drop lowest N</label>
      <input type="number" min={0} value={dropLowest} onChange={(e) => setDropLowest(Number(e.target.value))} />
      <label>Position</label>
      <input type="number" value={position} onChange={(e) => setPosition(Number(e.target.value))} />
    </Modal>
  );
}
```

- [ ] **Step 4: Add a teacher-mode "Edit course" button to `CourseHomePage.tsx`** — modify the page: import `useAuth`, `useState`, `CourseEditModal`, `useCourse`'s `reload`; near the `<h1>`, when `teacherMode`, show a small `Edit course` button that opens `CourseEditModal`. (Pattern identical to DashboardPage's usage in Task 9 Step 6 — see that code; reuse the same `CourseEditModal` props: `course`, `onClose`, `onSaved` where `onSaved` calls `reload()`.)

Concretely, change the top of `CourseHomePage`'s return to:

```tsx
  const { teacherMode } = useAuth();
  const { course, reload } = useCourse(courseId);
  const [editing, setEditing] = useState(false);
  if (!course) return <Spinner />;
  return (
    <CourseLayout course={course} section="Home" sidebar={<CourseSidebar course={course} />}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <h1 className="page-title">{course.code} {course.term_label && `(${course.term_label})`} {course.title}</h1>
        {teacherMode && <button className="btn small" onClick={() => setEditing(true)}>Edit course</button>}
      </div>
      {/* ...rest unchanged... */}
      {editing && <CourseEditModal course={course} onClose={() => setEditing(false)} onSaved={() => { setEditing(false); reload(); }} />}
    </CourseLayout>
  );
```
(Add the necessary imports: `useState` from react, `useAuth`, `CourseEditModal`.)

- [ ] **Step 5: Typecheck + build**

Run: `cd frontend && npm run typecheck && npm run lint && npm run build`
Expected: typecheck passes, eslint passes (warnings ok, no errors), `dist/` built. Fix any unused-import / type errors.

- [ ] **Step 6: Commit**

```bash
cd ..
git add -A
git commit -m "feat: teacher-mode edit modals for course/module/module-item/assignment-group"
```

---

### Task 12: Local end-to-end smoke + dev-runner docs

**Files:**
- Create: `backend/README.md` (short — how to run the backend locally)
- Create: `frontend/README.md` (short — how to run the frontend locally)
- Modify: repo-root `README.md` (link to the two, note the P1 state)

- [ ] **Step 1: Write `backend/README.md`**

```markdown
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
API at http://localhost:8000 ; docs at http://localhost:8000/docs

## Tests / lint
```bash
uv run pytest -q
uv run ruff check .
```
```

- [ ] **Step 2: Write `frontend/README.md`**

```markdown
# OCW Canvas — frontend

React + Vite + TypeScript SPA. Canvas-like UI; talks to the FastAPI backend.

## Run locally
```bash
cd frontend
npm install
cp .env.example .env          # VITE_API_BASE_URL=http://localhost:8000
npm run dev                   # http://localhost:5173
```
Make sure the backend is running first and that `FRONTEND_ORIGINS` in the backend `.env` includes `http://localhost:5173`.

## Build / checks
```bash
npm run typecheck
npm run lint
npm run build                 # outputs dist/ (base path /ocw-canvas/ for GitHub Pages)
```
```

- [ ] **Step 3: Update the repo-root `README.md`** — replace the "Status:" line:

```markdown
**Status:** P1 complete — runnable "Canvas without homework" (single-user auth; courses / modules / module-items / assignment-groups CRUD; Dashboard, Course Home, Syllabus, Modules, Video Lectures pages; teacher-mode editing). Backend: [`backend/README.md`](backend/README.md). Frontend: [`frontend/README.md`](frontend/README.md). Design spec: [`docs/superpowers/specs/2026-05-12-ocw-canvas-design.md`](docs/superpowers/specs/2026-05-12-ocw-canvas-design.md). Plans: [`docs/superpowers/plans/`](docs/superpowers/plans/).
```

- [ ] **Step 4: Manual smoke (do this once; not scriptable)**

1. `cd backend && uv run alembic upgrade head && uv run python -m app.manage create-owner --email a@b.c --password test --name Tester`
2. `uv run uvicorn app.main:app --reload --port 8000` (leave running)
3. In another shell: `cd frontend && npm run dev`
4. Open http://localhost:5173 → sign in with `a@b.c` / `test`.
5. Toggle teacher mode (the 👤/🛠 rail button) → "Add course" → fill code/title/color/term → Save → card appears.
6. Open the course → Modules → "+ Module" → add a module → "+ Item" → add a `link` item with an OCW URL → it renders with the ↗ arrow and opens in a new tab.
7. Course → Home shows the markdown front page; Syllabus shows the syllabus markdown + (empty) Course Summary; Video Lectures lists `video`-kind items.
8. Log out → redirected to /login.

Expected: all of the above works. If `/api/auth/me` 401s right after login in the browser (but works in tests), check CORS `allow_credentials` + that `FRONTEND_ORIGINS` matches exactly and `COOKIE_SAMESITE=lax` for http-localhost.

- [ ] **Step 5: Commit**

```bash
cd ..
git add -A
git commit -m "docs: backend/frontend run instructions; mark P1 complete"
```

---

### Task 13: CI workflow

**Files:**
- Create: `.github/workflows/ci.yml`
- Delete: `.github/workflows/.gitkeep`

- [ ] **Step 1: Write `.github/workflows/ci.yml`**

```yaml
name: CI
on:
  push:
    branches: [main, "feat/**"]
  pull_request:

jobs:
  backend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync
      - run: uv run ruff check .
      - run: uv run pytest -q

  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - run: npm ci
      - run: npm run lint
      - run: npm run typecheck
      - run: npm run build
```

- [ ] **Step 2: Remove the placeholder**

```bash
rm -f .github/workflows/.gitkeep
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "ci: lint + test + typecheck + build on push/PR"
```

---

### Task 14: Merge P1 to main

- [ ] **Step 1: Final full check**

```bash
cd backend && uv run pytest -q && uv run ruff check . && cd ..
cd frontend && npm run typecheck && npm run lint && npm run build && cd ..
```
Expected: everything green.

- [ ] **Step 2: Merge the branch**

```bash
git checkout main
git merge --no-ff feat/p1-skeleton -m "feat: P1 — skeleton + read-mostly Canvas"
```
(If the repo's default branch is `master`, use that name instead — check `git branch`.)

- [ ] **Step 3: Confirm**

```bash
git log --oneline -5
git status
```
Expected: P1 work is on the default branch; working tree clean. (Push is the user's call — do not push unless asked.)

---

## Self-Review notes

- **Spec coverage (P1 slice):** auth (§2 — native JWT cookie) → Tasks 4, 7, 9. Data model app_user/course/module/module_item/assignment_group/assignment (§3) → Tasks 2–3. CRUD API for course/module/module_item/assignment_group (§4, §7-P1) → Task 5. Global chrome + left rail + breadcrumb + course-nav (§4) → Tasks 8–10. Dashboard / Course Home / Syllabus (+Course Summary) / Modules / Video Lectures (§4) → Tasks 9–10. Teacher-mode editing (§4) → Task 11. Repo layout & CI (§6, §8) → Tasks 1, 6, 13. GH Pages base path + SPA fallback (§6, §10) → Task 6, 9. Out of P1 scope (assignments UI, submissions, AI, email, cron, deploy to Render/Supabase, seed course) — those are P2–P5; the assignments/grades/announcements routes are present as placeholders so the course nav has no dead links.
- **Placeholder scan:** the only intentional "placeholders" are (a) the assignments/grades routes pointing at `CourseModulesPage` until P2, (b) the "Forgot password?" link being non-functional until P4, (c) "To Do"/"Recent Feedback" widgets showing static text until P2/P3 — all called out explicitly in-task. No `TODO`/`TBD` left in code.
- **Type consistency:** `api` client methods ↔ backend routes match (`/courses`, `/courses/{id}/modules`, `/modules/{id}`, `/modules/{id}/items`, `/module-items/{id}`, `/courses/{id}/assignment-groups`, `/assignment-groups/{id}`). Frontend `types.ts` ↔ backend `schemas/course.py` field names match. `useCourse` returns `{ course, error, reload }` and is used that way. `CourseEditModal`/`ModuleEditModal`/`ModuleItemEditModal`/`AssignmentGroupEditModal` props match their call sites.
- **Note for executor:** add `Create: frontend/src/components/CourseSidebar.tsx` to Task 10's file list (it's defined in Task 10 Step 4 but was omitted from the header list).
