"""Seed the MIT 6.262 — Discrete Stochastic Processes course (Robert Gallager, Spring 2011).

Run:  cd backend && uv run python -m seed.seed_6_262 [--force] [--update-urls] [--refresh-solutions]
Source: https://ocw.mit.edu/courses/6-262-discrete-stochastic-processes-spring-2011/

Idempotent: if a course with code "MIT 6.262" already exists this is a no-op,
unless ``--force`` (which deletes it first — the cascade on Course removes its
modules / assignment groups / assignments / announcements).

Pattern differences vs the MIT 18.065 / 18.700 seeds:
  - This is the first seed to ship *official* solution PDFs. OCW publishes
    Gallager's solutions for every problem set and every historical exam. The
    seed downloads the 14 PDFs for graded assignments (12 PSets + 1 midterm +
    1 final), uploads them to the ``solutions`` Supabase Storage bucket under
    ``official/6_262/``, and sets ``assignment.official_solution_file_path``.
    The AI grader (see ``app.services.ai_jobs.grade_with_ai``) reads the PDF
    into its working directory and grades against Gallager's reference rather
    than regenerating its own.
  - OCW PDF URLs are content-hash-prefixed (e.g.
    ``c12643…_MIT6_262S11_assn01_sol.pdf``); the hash is not derivable from
    the slug. The seed scrapes ``/resources/{slug}/`` for the PDF URL.
  - Graceful degradation: if a PDF download/upload fails, the assignment
    keeps ``official_solution_url`` set; the AI grader falls back to URL-only
    awareness ("solution exists at <url>; grade against standard rigor").
"""
from __future__ import annotations

import argparse  # noqa: F401 — used in later tasks (CLI in main())

from sqlalchemy.orm import Session  # noqa: F401 — used in later tasks

from app.db import SessionLocal  # noqa: F401 — used in later tasks
from app.models import (  # noqa: F401 — used in later tasks
    Assignment,
    AssignmentGroup,
    Course,
    Module,
    ModuleItem,
)
from app.services import storage  # noqa: F401 — used in later tasks

CODE = "MIT 6.262"
BASE = (
    "https://ocw.mit.edu/courses/"
    "6-262-discrete-stochastic-processes-spring-2011"
)
HOME = BASE + "/"
SYLLABUS_URL = BASE + "/pages/syllabus/"
CALENDAR_URL = BASE + "/pages/calendar/"
COURSE_NOTES_URL = BASE + "/pages/course-notes/"
ASSIGNMENTS_URL = BASE + "/pages/assignments/"
EXAMS_URL = BASE + "/pages/exams/"
VIDEOS_INDEX_URL = BASE + "/video_galleries/video-lectures/"
GALLAGER_NOTES_ARCHIVE_URL = (
    "https://web.archive.org/web/20230107224918/"
    "https:/www.rle.mit.edu/rgallager/notes.htm"
)


def _ps_url(n: int) -> str:
    return f"{BASE}/resources/mit6_262s11_assn{n:02d}/"


def _ps_sol_url(n: int) -> str:
    return f"{BASE}/resources/mit6_262s11_assn{n:02d}_sol/"


def _exam_slug(kind: str, year: int) -> str:
    """kind in {'mid', 'final'}, year in {2009, 2010, 2011}. Returns the
    short slug stem (e.g. 'mit6_262s11_mid11'). Year is 2-digit suffix."""
    assert kind in ("mid", "final"), kind
    yy = year % 100
    return f"mit6_262s11_{kind}{yy:02d}"


def _exam_url(kind: str, year: int) -> str:
    return f"{BASE}/resources/{_exam_slug(kind, year)}/"


def _exam_sol_url(kind: str, year: int) -> str:
    return f"{BASE}/resources/{_exam_slug(kind, year)}_sol/"


def _video_url(n: int) -> str:
    # 25 recorded lectures; URL slugs come from a per-lecture map populated in
    # Task 2 (LECTURE_VIDEO_SLUGS). Implemented as a stub here so the import
    # graph is stable.
    raise NotImplementedError("populated in Task 2")
