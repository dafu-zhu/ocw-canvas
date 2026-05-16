# Aalto BDA Seed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Seed Aalto BDA (CS-E5710 — Vehtari) into OCW Canvas: 9 weekly AI-graded assignments + 1 project-mode capstone, 3 modules (Direct links / BDA3 chapter notes / Lecture slides), no exams, no Storage uploads.

**Architecture:** Single `backend/seed/seed_aalto_bda.py`, modelled on `seed_6_262.py` minus the OCW-PDF-scrape / Storage-upload machinery (Aalto publishes no official solution PDFs). All weekly assignments use `requires_solution_key=True` (AI generates its own key, à la CMU 36-705); the capstone uses `requires_solution_key=False` (project-mode AI grading shipped in PR #6). CLI: `seed`, `--force`, `--update-urls` — no `--refresh-solutions`.

**Tech Stack:** Python 3.12, SQLAlchemy 2.x (existing ORM), pytest with autouse `_fresh_schema` (from `tests/conftest.py`) + `httpx` mocked defensively. No `httpx` or `storage` calls at seed time — neither is needed — so the autouse mock is just belt-and-braces.

**Spec:** [docs/superpowers/specs/2026-05-16-aalto-bda-seed-design.md](../specs/2026-05-16-aalto-bda-seed-design.md)

---

## Pre-flight

- [x] **P1: Create a feature branch** (already done before plan write)

```bash
git checkout -b feat/seed-aalto-bda
```

- [ ] **P2: Verify clean working tree and baseline tests pass**

```bash
git status
cd backend && uv run pytest -q
```

Expected: only `.claude/`, `docs/superpowers/specs/2026-05-16-aalto-bda-seed-design.md`, `docs/superpowers/plans/2026-05-16-aalto-bda-seed.md`, and the unrelated `docs/superpowers/specs/2026-05-16-ieor-6711-seed-design.md` are untracked. All existing tests pass.

---

### Task 1: Module skeleton, constants & URL helpers

**Files:**
- Create: `backend/seed/seed_aalto_bda.py`
- Create: `backend/tests/test_seed_aalto_bda.py`

- [ ] **Step 1: Write the failing test for URL helpers and constants**

Create `backend/tests/test_seed_aalto_bda.py`:

```python
import pytest

import seed.seed_aalto_bda as seed_mod
from app.models import Assignment, Course
from seed.seed_aalto_bda import (
    ASSIGNMENTS_INDEX_URL,
    BASE,
    CHAPTER_NOTES,
    CODE,
    DESCRIPTION,
    GITHUB_BASE,
    HOME,
    HOME_MD,
    PANOPTO_FOLDER_URL,
    PROJECT_URL,
    SLIDE_DECKS,
    SYLLABUS_MD,
    TEXTBOOK,
    WEEKLY_ASSIGNMENTS,
    _assignment_url,
    _chapter_note_url,
    _modules,
    _slide_url,
    seed,
    update_urls,
)


@pytest.fixture(autouse=True)
def _mock_network_for_seed(monkeypatch):
    """Defensive mock — the Aalto seed makes no network calls today, but if a
    future change adds httpx usage we want tests to fail loudly, not silently
    hit the live Aalto site."""
    import httpx
    def _boom(*a, **kw):
        raise AssertionError("seed must not perform network I/O during tests")
    monkeypatch.setattr(httpx, "get", _boom)
    monkeypatch.setattr(httpx, "post", _boom)
    yield


def test_code_and_base():
    assert CODE == "Aalto BDA"
    assert BASE == "https://avehtari.github.io/BDA_course_Aalto"
    assert HOME == BASE + "/"
    assert GITHUB_BASE == "https://github.com/avehtari/BDA_course_Aalto"


def test_assignment_urls():
    assert _assignment_url(1) == BASE + "/assignments/assignment1.html"
    assert _assignment_url(9) == BASE + "/assignments/assignment9.html"


def test_chapter_note_urls():
    assert _chapter_note_url(1) == BASE + "/chapter_notes/BDA_notes_ch1.pdf"
    assert _chapter_note_url(12) == BASE + "/chapter_notes/BDA_notes_ch12.pdf"


def test_slide_url_uses_github_raw():
    assert _slide_url("1a") == (
        GITHUB_BASE + "/raw/master/slides/BDA_lecture_1a.pdf"
    )
    assert _slide_url("11c") == (
        GITHUB_BASE + "/raw/master/slides/BDA_lecture_11c.pdf"
    )


def test_weekly_assignments_count_and_weights():
    """9 weeklies; points_possible scaled ×10 from GSU 2023 weights."""
    assert len(WEEKLY_ASSIGNMENTS) == 9
    weights = [pts for (_n, _title, _ch, _lec_from, _lec_to, pts) in WEEKLY_ASSIGNMENTS]
    assert weights == [60, 60, 190, 120, 120, 120, 120, 120, 60]


def test_chapter_notes_skip_chapter_8():
    """BDA3 ch 8 is intentionally omitted by the course."""
    chapters = [n for (n, _title) in CHAPTER_NOTES]
    assert chapters == [1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12]


def test_slide_decks_ordered_by_lecture():
    """Slides ordered by (lecture-number, sub-deck)."""
    slugs = [slug for (slug, _title) in SLIDE_DECKS]
    assert slugs == [
        "1a", "1b", "2", "3", "4", "5", "6", "7",
        "8a", "8b", "9",
        "10a", "10b", "10c",
        "11a", "11b", "11c",
    ]
```

- [ ] **Step 2: Run the failing tests**

```bash
cd backend && uv run pytest tests/test_seed_aalto_bda.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'seed.seed_aalto_bda'`.

- [ ] **Step 3: Create the module skeleton with constants and URL helpers**

Create `backend/seed/seed_aalto_bda.py`:

```python
"""Seed the Aalto BDA — Bayesian Data Analysis course (Aki Vehtari, CS-E5710).

Run:  cd backend && uv run python -m seed.seed_aalto_bda [--force] [--update-urls]
Source: https://avehtari.github.io/BDA_course_Aalto/

Idempotent: if a course with code "Aalto BDA" already exists this is a no-op,
unless ``--force`` (which deletes it first — the cascade on Course removes its
modules / assignment groups / assignments / announcements).

Pattern differences vs the MIT 6.262 seed:
  - No exams (Aalto BDA has none). Grade scheme is Weekly Assignments 70% +
    Capstone Project 30%.
  - No official-solution PDFs (Aalto runs peer grading via peergrade.io /
    FeedbackFruits — no public solution keys). All 9 weekly assignments have
    ``requires_solution_key=True``; the AI generates its own reference key
    per assignment, like CMU 36-705. No Supabase Storage uploads, no
    ``--refresh-solutions`` CLI flag.
  - First seed to ship a project-mode assignment: the capstone has
    ``requires_solution_key=False`` and is graded by the project-mode AI
    grading flow shipped in PRs #6 / #7.
  - Within-group assignment weighting is encoded via ``points_possible``
    (there is no per-assignment weight field). Weekly weights follow the
    GSU 2023 scheme (6/6/19/12/12/12/12/12/6 %) scaled ×10 to give round
    points: 60/60/190/120/120/120/120/120/60.
"""
from __future__ import annotations

import argparse

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Assignment, AssignmentGroup, Course, Module, ModuleItem

CODE = "Aalto BDA"
BASE = "https://avehtari.github.io/BDA_course_Aalto"
GITHUB_BASE = "https://github.com/avehtari/BDA_course_Aalto"

HOME = BASE + "/"
AALTO_2025_URL = BASE + "/Aalto2025.html"
BDA3_PDF_URL = "https://users.aalto.fi/~ave/BDA3.pdf"
CHAPTER_NOTES_INDEX_URL = BASE + "/BDA3_notes.html"
ASSIGNMENTS_INDEX_URL = BASE + "/assignments.html"
PROJECT_URL = BASE + "/project.html"
PROJECT_RUBRIC_URL = BASE + "/project_rubric.html"
DEMOS_URL = BASE + "/demos.html"
R_DEMOS_URL = "https://github.com/avehtari/BDA_R_demos"
PY_DEMOS_URL = "https://github.com/avehtari/BDA_py_demos"
# 2024 lecture-video Panopto folder — most stable folder ID published on the
# index page (the 2025 folder ID rotates; --update-urls handles drift).
PANOPTO_FOLDER_URL = (
    "https://aalto.cloud.panopto.eu/Panopto/Pages/Sessions/List.aspx"
    "?folderID=b6f169ef-a8b4-4a04-983b-b1df009838f8"
)
STAN_HOME_URL = "https://mc-stan.org/"
FAQ_URL = BASE + "/FAQ.html"


def _assignment_url(n: int) -> str:
    return f"{BASE}/assignments/assignment{n}.html"


def _chapter_note_url(n: int) -> str:
    return f"{BASE}/chapter_notes/BDA_notes_ch{n}.pdf"


def _slide_url(slug: str) -> str:
    return f"{GITHUB_BASE}/raw/master/slides/BDA_lecture_{slug}.pdf"


# BDA3 chapter notes published by the course. Ch 8 is intentionally omitted.
# (chapter_number, display_title)
CHAPTER_NOTES: list[tuple[int, str]] = [
    (1,  "Background"),
    (2,  "Single-parameter models"),
    (3,  "Multiparameter models"),
    (4,  "Normal approximation & frequency properties"),
    (5,  "Hierarchical models"),
    (6,  "Model checking"),
    (7,  "Evaluating and comparing models"),
    (9,  "Decision analysis"),
    (10, "Computational methods"),
    (11, "Markov chain Monte Carlo"),
    (12, "Stan & probabilistic programming"),
]


# 17 lecture-slide PDFs, ordered by (lecture-number, sub-deck).
# (slug, display_title)
SLIDE_DECKS: list[tuple[str, str]] = [
    ("1a",  "Lecture 1a — Course intro & computational probabilistic modelling"),
    ("1b",  "Lecture 1b — Uncertainty & modelling"),
    ("2",   "Lecture 2 — Single-parameter models"),
    ("3",   "Lecture 3 — Multiparameter models"),
    ("4",   "Lecture 4 — Monte Carlo"),
    ("5",   "Lecture 5 — Markov chain Monte Carlo"),
    ("6",   "Lecture 6 — Stan, HMC, probabilistic programming"),
    ("7",   "Lecture 7 — Hierarchical models"),
    ("8a",  "Lecture 8a — Model checking"),
    ("8b",  "Lecture 8b — Cross-validation"),
    ("9",   "Lecture 9 — Model comparison & selection (LOO, WAIC)"),
    ("10a", "Lecture 10a — Decision analysis (intro)"),
    ("10b", "Lecture 10b — Decision analysis (continued)"),
    ("10c", "Lecture 10c — Decision analysis (extra)"),
    ("11a", "Lecture 11a — Normal approximation"),
    ("11b", "Lecture 11b — Frequency properties"),
    ("11c", "Lecture 11c — Laplace approximation"),
]


# 9 weekly assignments. Tuple: (n, title, chapter_reading, lec_from, lec_to, points_possible).
# points_possible encodes within-group weighting (GSU 2023 scheme ×10).
WEEKLY_ASSIGNMENTS: list[tuple[int, str, str, int, int, int]] = [
    (1, "Introduction & basics of Bayesian inference",     "BDA3 Ch 1",      1,  1, 60),
    (2, "Single-parameter models",                         "BDA3 Ch 2",      2,  2, 60),
    (3, "Multidimensional posterior (multiparameter)",     "BDA3 Ch 3",      3,  3, 190),
    (4, "Monte Carlo methods",                             "BDA3 Ch 10",     4,  4, 120),
    (5, "Markov chain Monte Carlo",                        "BDA3 Ch 11",     5,  5, 120),
    (6, "Stan, HMC & probabilistic programming",           "BDA3 Ch 12",     6,  6, 120),
    (7, "Hierarchical models & exchangeability",           "BDA3 Ch 5",      7,  7, 120),
    (8, "Model checking & comparison (LOO-CV / WAIC)",     "BDA3 Chs 6 + 7", 8,  9, 120),
    (9, "Decision analysis",                               "BDA3 Ch 9",      10, 10, 60),
]


# Capstone project — graded in project-mode (no reference solution).
PROJECT_TITLE = "Capstone Project — Bayesian workflow end-to-end"
PROJECT_LEC_FROM = 1
PROJECT_LEC_TO = 12
PROJECT_POINTS = 100
```

- [ ] **Step 4: Re-run the constants/URL tests**

```bash
cd backend && uv run pytest tests/test_seed_aalto_bda.py -q
```

Expected: failures shift to "module-level constants exist but `_modules`, `seed`, `update_urls`, `HOME_MD`, `SYLLABUS_MD`, `TEXTBOOK`, `DESCRIPTION` not defined" once the URL/constant tests pass (or all pass if every name listed in the test exists).

- [ ] **Step 5: Add narrative constants (`HOME_MD`, `SYLLABUS_MD`, `TEXTBOOK`, `DESCRIPTION`)**

Append to `backend/seed/seed_aalto_bda.py`:

```python
DESCRIPTION = (
    "Bayesian data analysis with Stan: priors, single- and multi-parameter "
    "models, hierarchical modelling, Monte Carlo and Markov-chain Monte Carlo, "
    "model checking, cross-validation and model comparison, decision analysis. "
    "Companion to Gelman et al. Bayesian Data Analysis (3rd ed)."
)

TEXTBOOK = (
    "Gelman, Carlin, Stern, Dunson, Vehtari, Rubin, Bayesian Data Analysis, "
    "3rd ed (CRC 2013) — primary; free PDF at users.aalto.fi/~ave/BDA3.pdf. "
    "Gelman, Hill, Vehtari, Regression and Other Stories (Cambridge 2020) — "
    "secondary."
)

HOME_MD = """**Aalto BDA — Bayesian Data Analysis (Aki Vehtari, CS-E5710).**

Course materials mirrored from Aki Vehtari's public Aalto course site
(<https://avehtari.github.io/BDA_course_Aalto/>). The term shown above is
*your* self-study term — edit it from the course settings when your plan
shifts.

A 12-week applied Bayesian course: probability foundations → single- and
multi-parameter models → Monte Carlo and MCMC → Stan and probabilistic
programming → hierarchical models → model checking and comparison
(LOO-CV / WAIC) → decision analysis → Laplace approximation. The
textbook is Gelman et al. *BDA3*; the lectures, slides, and chapter
notes are open-licensed (CC-BY-NC 4.0).

Aalto runs the course with peer grading via peergrade.io / FeedbackFruits;
no official solution keys are published. For self-study, the AI grader
generates its own reference solution per weekly assignment and grades
against it. The capstone project is graded in **project mode** — no
reference solution, scored on quality / coverage of the Bayesian
workflow / clarity, against the rubric criteria.

Jump to **Syllabus**, **Modules**, or **Assignments**.
"""

SYLLABUS_MD = """## Prerequisites
Probability (probability, density, distribution; sum, product, Bayes' rule;
expectation, mean, variance). Some calculus and linear algebra. Basic R or
Python comfort (we lean on R + Stan). If BDA3 itself feels too steep,
McElreath's *Statistical Rethinking* (2nd ed) and Gelman-Hill-Vehtari
*Regression and Other Stories* are gentler on-ramps.

## Textbook
- **Primary** — Gelman, Carlin, Stern, Dunson, Vehtari, Rubin,
  *Bayesian Data Analysis*, 3rd ed (CRC 2013). [Free PDF
  ](https://users.aalto.fi/~ave/BDA3.pdf) for non-commercial use.
- **Secondary** — Gelman, Hill, Vehtari, *Regression and Other Stories*
  (Cambridge 2020). Useful for the regression-and-workflow examples that
  fill in around BDA3.
- **Chapter notes** — Vehtari's own per-chapter reading notes are linked
  from the "BDA3 Chapter notes" module; treat them as the canonical
  reading-list for each week.

## Grading (self-study split)
| Component | Weight |
|---|---|
| Weekly Assignments (9) | 70% |
| Capstone Project | 30% |

Within the weekly group, the relative weights follow Aalto's GSU 2023
self-study scheme — 6 / 6 / 19 / 12 / 12 / 12 / 12 / 12 / 6 % —
encoded here as `points_possible` (60 / 60 / 190 / 120 / 120 / 120 /
120 / 120 / 60). Assignment 3 (multiparameter models) is the heaviest;
1, 2, and 9 are warm-up / decision-analysis lighter rounds.

## Weekly assignment policy
Each assignment is published by week N and is intended to take one week
(A6 and A7 each get two weeks in Aalto's calendar — a midterm break sits
between weeks 6 and 7). For self-study, pick a sustainable cadence and
hand in at the end of each week.

The AI generates its own reference solution per assignment (Aalto
publishes no key — they peer-grade) and grades your submission against
it. You can re-attempt; the latest attempt is what counts.

## Capstone project
The project is open-ended: pick a real dataset and run a complete
Bayesian workflow end-to-end (see the **Project description** link in
Direct links and the **Project rubric** for the criteria). The AI grades
in *project mode* — no reference solution; it scores on quality,
workflow-step coverage, and clarity. Aim for a 10–20 page report; the
rubric criteria (priors, MCMC diagnostics, posterior predictive checks,
LOO-CV comparison, sensitivity analysis, discussion + self-reflection)
should each be visibly present.
"""
```

- [ ] **Step 6: Commit the skeleton**

```bash
cd backend && uv run ruff check seed/seed_aalto_bda.py tests/test_seed_aalto_bda.py
git add backend/seed/seed_aalto_bda.py backend/tests/test_seed_aalto_bda.py
git commit -m "feat(seed/aalto-bda): module skeleton + URL helpers + tables"
```

---

### Task 2: `_modules()` helper + module-shape test

**Files:**
- Modify: `backend/seed/seed_aalto_bda.py` (append `_direct_links_items`, `_chapter_notes_items`, `_slides_items`, `_modules`)
- Modify: `backend/tests/test_seed_aalto_bda.py`

- [ ] **Step 1: Add the failing test for module shape**

Append to `backend/tests/test_seed_aalto_bda.py`:

```python
def test_modules_shape():
    """3 modules with the expected item counts; no per-lecture units, no
    inline video items (per feedback-module-content-chapter-readings)."""
    mods = _modules()
    titles = [t for (t, _items) in mods]
    assert titles == ["Direct links", "BDA3 Chapter notes", "Lecture slides"]

    counts = {t: len(items) for (t, items) in mods}
    assert counts == {
        "Direct links": 13,
        "BDA3 Chapter notes": 11,
        "Lecture slides": 17,
    }


def test_modules_no_video_kind_items():
    """No items have kind='video' — videos belong in the (separate) Video
    Lectures section if/when it lands. The single Panopto-folder link in
    Direct links is kind='link', not kind='video'."""
    for (_title, items) in _modules():
        for it in items:
            assert it["kind"] == "link", f"non-link kind: {it!r}"


def test_modules_chapter_note_titles_carry_chapter_number():
    chap_items = dict(_modules())["BDA3 Chapter notes"]
    assert chap_items[0]["title"].startswith("Chapter 1 —")
    assert chap_items[-1]["title"].startswith("Chapter 12 —")
    # Ch 8 omitted between Ch 7 and Ch 9.
    titles = [it["title"] for it in chap_items]
    assert any("Chapter 7 " in t for t in titles)
    assert any("Chapter 9 " in t for t in titles)
    assert not any(t.startswith("Chapter 8 —") for t in titles)
```

- [ ] **Step 2: Run the failing tests**

```bash
cd backend && uv run pytest tests/test_seed_aalto_bda.py -q
```

Expected: FAIL with `NameError: name '_modules' is not defined` (or `ImportError` on the import line).

- [ ] **Step 3: Implement `_modules()` and helpers**

Append to `backend/seed/seed_aalto_bda.py`:

```python
def _direct_links_items() -> list[dict]:
    return [
        {"kind": "link", "title": "Aalto BDA course home (Vehtari)", "url": HOME},
        {"kind": "link", "title": "Aalto 2025 iteration page", "url": AALTO_2025_URL},
        {"kind": "link", "title": "BDA3 — free PDF (textbook)", "url": BDA3_PDF_URL},
        {"kind": "link", "title": "BDA3 chapter notes (index)", "url": CHAPTER_NOTES_INDEX_URL},
        {"kind": "link", "title": "Weekly assignments — overview", "url": ASSIGNMENTS_INDEX_URL},
        {"kind": "link", "title": "Capstone project — description", "url": PROJECT_URL},
        {"kind": "link", "title": "Capstone project — rubric", "url": PROJECT_RUBRIC_URL},
        {"kind": "link", "title": "Demos (R + Python)", "url": DEMOS_URL},
        {"kind": "link", "title": "BDA R demos (GitHub)", "url": R_DEMOS_URL},
        {"kind": "link", "title": "BDA Python demos (GitHub)", "url": PY_DEMOS_URL},
        {"kind": "link", "title": "Lecture videos (Panopto, 2024 folder)", "url": PANOPTO_FOLDER_URL},
        {"kind": "link", "title": "Stan home", "url": STAN_HOME_URL},
        {"kind": "link", "title": "Course FAQ", "url": FAQ_URL},
    ]


def _chapter_notes_items() -> list[dict]:
    return [
        {"kind": "link", "title": f"Chapter {n} — {topic}", "url": _chapter_note_url(n)}
        for n, topic in CHAPTER_NOTES
    ]


def _slides_items() -> list[dict]:
    return [
        {"kind": "link", "title": title, "url": _slide_url(slug)}
        for slug, title in SLIDE_DECKS
    ]


def _modules() -> list[tuple[str, list[dict]]]:
    """Three modules, mirroring the natural shape of Aalto's published pages:

      1. "Direct links" — top-of-course navigation (course home, textbook,
         assignment + project pages, demos, video gallery, FAQ).
      2. "BDA3 Chapter notes" — 11 chapter-note PDFs (chs 1, 2, 3, 4, 5, 6,
         7, 9, 10, 11, 12 — ch 8 omitted by the course).
      3. "Lecture slides" — 17 slide-deck PDFs from the GitHub slides/ folder.

    No per-lecture unit modules and no kind='video' items — videos are
    surfaced through the single Panopto-folder link in Direct links. See
    feedback memory ``feedback-module-content-chapter-readings``.
    """
    return [
        ("Direct links", _direct_links_items()),
        ("BDA3 Chapter notes", _chapter_notes_items()),
        ("Lecture slides", _slides_items()),
    ]
```

- [ ] **Step 4: Re-run module tests**

```bash
cd backend && uv run pytest tests/test_seed_aalto_bda.py -q
```

Expected: all module-shape tests PASS.

- [ ] **Step 5: Commit**

```bash
cd backend && uv run ruff check seed/seed_aalto_bda.py
git add backend/seed/seed_aalto_bda.py backend/tests/test_seed_aalto_bda.py
git commit -m "feat(seed/aalto-bda): modules — Direct links + Chapter notes + Slides"
```

---

### Task 3: `seed()` — course, groups, assignments, modules

**Files:**
- Modify: `backend/seed/seed_aalto_bda.py` (add `seed`, `_delete_existing`, assignment-description helpers)
- Modify: `backend/tests/test_seed_aalto_bda.py`

- [ ] **Step 1: Write the failing tests for `seed()`**

Append to `backend/tests/test_seed_aalto_bda.py`:

```python
def test_seed_creates_course_with_expected_metadata(db):
    course = seed(db)
    assert course.code == "Aalto BDA"
    assert course.title == "Bayesian Data Analysis"
    assert course.institution == "Aalto University"
    assert course.instructor == "Prof. Aki Vehtari"
    assert course.term_label == "Spring 2030"
    assert course.status == "planned"
    assert course.color == "#0066B3"
    assert course.display_order == 5
    assert course.external_home_url == HOME
    assert course.home_page_md == HOME_MD
    assert course.syllabus_md == SYLLABUS_MD
    assert course.textbook == TEXTBOOK
    assert course.description == DESCRIPTION


def test_seed_creates_two_assignment_groups_with_70_30_weights(db):
    course = seed(db)
    by_name = {g.name: g for g in course.assignment_groups}
    assert set(by_name) == {"Weekly Assignments", "Capstone Project"}
    assert by_name["Weekly Assignments"].weight == 70
    assert by_name["Capstone Project"].weight == 30
    assert by_name["Weekly Assignments"].position == 0
    assert by_name["Capstone Project"].position == 1


def test_seed_creates_9_weeklies_plus_1_project(db):
    course = seed(db)
    assert len(course.assignments) == 10
    by_title = {a.title: a for a in course.assignments}

    # 9 weeklies with the GSU 2023 point scale.
    for n, title_stem, _ch, _from, _to, pts in WEEKLY_ASSIGNMENTS:
        match = [t for t in by_title if t.startswith(f"Assignment {n} —")]
        assert len(match) == 1, f"expected exactly one Assignment {n}, got {match}"
        a = by_title[match[0]]
        assert title_stem in a.title
        assert int(a.points_possible) == pts
        assert a.requires_solution_key is True
        assert a.covers_lecture_from == _from
        assert a.covers_lecture_to == _to

    # Project — requires_solution_key=False.
    proj = [a for a in course.assignments if a.title == PROJECT_TITLE]
    assert len(proj) == 1
    p = proj[0]
    assert p.requires_solution_key is False
    assert int(p.points_possible) == PROJECT_POINTS
    assert p.covers_lecture_from == PROJECT_LEC_FROM
    assert p.covers_lecture_to == PROJECT_LEC_TO


def test_seed_creates_three_modules_with_expected_items(db):
    course = seed(db)
    mods = sorted(course.modules, key=lambda m: m.position)
    assert [m.title for m in mods] == [
        "Direct links",
        "BDA3 Chapter notes",
        "Lecture slides",
    ]
    counts = {m.title: len(m.items) for m in mods}
    assert counts == {
        "Direct links": 13,
        "BDA3 Chapter notes": 11,
        "Lecture slides": 17,
    }


def test_seed_is_idempotent(db):
    first = seed(db)
    second = seed(db)
    assert first.id == second.id
    # No duplicate assignments / modules created.
    assert len(second.assignments) == 10
    assert len(second.modules) == 3


def test_seed_force_recreates_course(db):
    first = seed(db)
    first_id = first.id
    second = seed(db, force=True)
    assert second.id != first_id
    assert len(second.assignments) == 10
```

- [ ] **Step 2: Run failing tests**

```bash
cd backend && uv run pytest tests/test_seed_aalto_bda.py -q
```

Expected: FAIL on `seed` not defined / `Course.code` not found.

- [ ] **Step 3: Implement assignment-description helpers + `seed()`**

Append to `backend/seed/seed_aalto_bda.py`:

```python
def _weekly_description(n: int, title_stem: str, chapter: str, lec_from: int, lec_to: int) -> str:
    paper_url = _assignment_url(n)
    lec_phrase = (
        f"Covers lecture {lec_from}" if lec_from == lec_to
        else f"Covers lectures {lec_from}–{lec_to}"
    )
    return (
        f"Assignment {n} ({title_stem}). {lec_phrase}. Reading: {chapter}.\n\n"
        f"- Paper: [Assignment {n} (Aalto)]({paper_url})\n"
        f"- Reading: {chapter} — see the BDA3 chapter notes module for the PDF\n\n"
        "Aalto runs the live course with peer grading via peergrade.io / "
        "FeedbackFruits and does not publish an official solution key. The "
        "AI generates its own reference solution and grades against it. "
        "Upload your worked solution (PDF or text) — re-attempts are allowed."
    )


def _project_description() -> str:
    return (
        "Capstone project — pick a real dataset and run a complete Bayesian "
        "workflow end-to-end, as introduced in Aalto's project rubric.\n\n"
        f"- Project description: [Aalto project page]({PROJECT_URL})\n"
        f"- Grading rubric: [Project rubric]({PROJECT_RUBRIC_URL})\n\n"
        "## Required report sections\n"
        "1. Introduction (motivation, problem, modelling idea; illustrative figure recommended)\n"
        "2. Data + analysis problem (source, prior use, how your analysis differs)\n"
        "3. At least two models (non-hierarchical vs hierarchical, linear vs non-linear, "
        "different observation models, or variable selection)\n"
        "4. Informative or weakly-informative priors — with justification\n"
        "5. Stan / brms / rstanarm code\n"
        "6. MCMC run details (options, sampler settings)\n"
        "7. Convergence diagnostics (Rhat, ESS, divergences) — for *all* models\n"
        "8. Posterior predictive checks — for *all* models\n"
        "9. (Bonus) Predictive performance assessment\n"
        "10. Sensitivity analysis vs prior choice — for *all* models\n"
        "11. Model comparison (LOO-CV)\n"
        "12. Discussion + potential improvements\n"
        "13. Conclusion\n"
        "14. Self-reflection (what you learned doing the project)\n\n"
        "The AI grades this in **project mode** — there is no reference "
        "solution. Scoring is on quality, workflow-step coverage, and "
        "clarity, against the rubric criteria. Aim for 10–20 pages."
    )


def _delete_existing(db: Session) -> None:
    for c in db.query(Course).filter(Course.code == CODE).all():
        db.delete(c)
    db.commit()


def seed(db: Session, force: bool = False) -> Course:
    existing = db.query(Course).filter(Course.code == CODE).first()
    if existing is not None:
        if not force:
            return existing
        _delete_existing(db)

    course = Course(
        code=CODE,
        title="Bayesian Data Analysis",
        institution="Aalto University",
        term_label="Spring 2030",  # user's self-study term, editable in teacher mode
        instructor="Prof. Aki Vehtari",
        external_home_url=HOME,
        status="planned",
        color="#0066B3",  # Aalto blue
        display_order=5,
        textbook=TEXTBOOK,
        home_page_md=HOME_MD,
        syllabus_md=SYLLABUS_MD,
        description=DESCRIPTION,
    )
    db.add(course)
    db.flush()

    g_weekly = AssignmentGroup(
        course_id=course.id, name="Weekly Assignments", weight=70, drop_lowest_n=0, position=0
    )
    g_project = AssignmentGroup(
        course_id=course.id, name="Capstone Project", weight=30, drop_lowest_n=0, position=1
    )
    db.add_all([g_weekly, g_project])
    db.flush()

    for n, title_stem, chapter, lec_from, lec_to, pts in WEEKLY_ASSIGNMENTS:
        a = Assignment(
            course_id=course.id,
            assignment_group_id=g_weekly.id,
            title=f"Assignment {n} — {title_stem}",
            description_md=_weekly_description(n, title_stem, chapter, lec_from, lec_to),
            points_possible=pts,
            accepts_files=True,
            accepts_text=True,
            position=n - 1,
            published=True,
            covers_lecture_from=lec_from,
            covers_lecture_to=lec_to,
            requires_solution_key=True,
        )
        db.add(a)

    proj = Assignment(
        course_id=course.id,
        assignment_group_id=g_project.id,
        title=PROJECT_TITLE,
        description_md=_project_description(),
        points_possible=PROJECT_POINTS,
        accepts_files=True,
        accepts_text=True,
        position=0,
        published=True,
        covers_lecture_from=PROJECT_LEC_FROM,
        covers_lecture_to=PROJECT_LEC_TO,
        requires_solution_key=False,
    )
    db.add(proj)
    db.flush()

    for mpos, (mtitle, items) in enumerate(_modules()):
        m = Module(course_id=course.id, title=mtitle, position=mpos, published=True)
        db.add(m)
        db.flush()
        for ipos, it in enumerate(items):
            db.add(
                ModuleItem(
                    module_id=m.id,
                    position=ipos,
                    indent=it.get("indent", 0),
                    kind=it["kind"],
                    title=it.get("title", ""),
                    external_url=it.get("url", ""),
                    text_md=it.get("text_md", ""),
                    assignment_id=None,
                    published=True,
                )
            )
    db.commit()
    db.refresh(course)
    return course
```

- [ ] **Step 4: Re-run tests**

```bash
cd backend && uv run pytest tests/test_seed_aalto_bda.py -q
```

Expected: all `seed()` tests PASS.

- [ ] **Step 5: Commit**

```bash
cd backend && uv run ruff check seed/seed_aalto_bda.py
git add backend/seed/seed_aalto_bda.py backend/tests/test_seed_aalto_bda.py
git commit -m "feat(seed/aalto-bda): seed() — course, groups, assignments, modules"
```

---

### Task 4: `update_urls()` + CLI

**Files:**
- Modify: `backend/seed/seed_aalto_bda.py` (append `update_urls`, `_fixed_title_to_url`, `main`, `if __name__`)
- Modify: `backend/tests/test_seed_aalto_bda.py`

- [ ] **Step 1: Write the failing tests for `update_urls`**

Append to `backend/tests/test_seed_aalto_bda.py`:

```python
def test_update_urls_noop_on_fresh_seed(db):
    course = seed(db)
    counts = update_urls(db)
    assert counts["course_found"] is True
    assert counts["items_updated"] == 0
    assert counts["assignments_updated"] == 0
    assert counts["coverage_updated"] == 0
    assert counts["items_examined"] == 13 + 11 + 17


def test_update_urls_restores_tampered_url(db):
    course = seed(db)
    # Tamper with the BDA3 PDF link.
    bda3_link = next(
        it for m in course.modules for it in m.items
        if it.title == "BDA3 — free PDF (textbook)"
    )
    bda3_link.external_url = "https://example.com/wrong.pdf"
    db.commit()

    counts = update_urls(db)
    assert counts["items_updated"] == 1
    db.refresh(bda3_link)
    assert bda3_link.external_url == BDA3_PDF_URL


def test_update_urls_restores_tampered_coverage(db):
    course = seed(db)
    a3 = next(a for a in course.assignments if a.title.startswith("Assignment 3 "))
    a3.covers_lecture_from = 99
    a3.covers_lecture_to = 99
    db.commit()

    counts = update_urls(db)
    assert counts["coverage_updated"] == 1
    db.refresh(a3)
    assert a3.covers_lecture_from == 3
    assert a3.covers_lecture_to == 3


def test_update_urls_on_missing_course():
    """No course present → returns course_found=False without raising."""
    from app.db import SessionLocal as _SL  # noqa: N813 — local alias
    # Use the test session fixture's underlying engine via a fresh session:
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import create_engine
    eng = create_engine("sqlite:///:memory:", future=True)
    from app.db import Base
    Base.metadata.create_all(eng)
    Sess = sessionmaker(bind=eng, autoflush=False, autocommit=False, future=True)
    with Sess() as s:
        out = update_urls(s)
    assert out == {"course_found": False}
```

- [ ] **Step 2: Run failing tests**

```bash
cd backend && uv run pytest tests/test_seed_aalto_bda.py -q
```

Expected: FAIL — `update_urls` not defined.

- [ ] **Step 3: Implement `update_urls()` + `main()`**

Append to `backend/seed/seed_aalto_bda.py`:

```python
# --------------------------------------------------------------------------- updater

def _fixed_title_to_url() -> dict[str, str]:
    """Map a module-item title to the URL it should always point to."""
    out: dict[str, str] = {
        "Aalto BDA course home (Vehtari)": HOME,
        "Aalto 2025 iteration page": AALTO_2025_URL,
        "BDA3 — free PDF (textbook)": BDA3_PDF_URL,
        "BDA3 chapter notes (index)": CHAPTER_NOTES_INDEX_URL,
        "Weekly assignments — overview": ASSIGNMENTS_INDEX_URL,
        "Capstone project — description": PROJECT_URL,
        "Capstone project — rubric": PROJECT_RUBRIC_URL,
        "Demos (R + Python)": DEMOS_URL,
        "BDA R demos (GitHub)": R_DEMOS_URL,
        "BDA Python demos (GitHub)": PY_DEMOS_URL,
        "Lecture videos (Panopto, 2024 folder)": PANOPTO_FOLDER_URL,
        "Stan home": STAN_HOME_URL,
        "Course FAQ": FAQ_URL,
    }
    for n, topic in CHAPTER_NOTES:
        out[f"Chapter {n} — {topic}"] = _chapter_note_url(n)
    for slug, title in SLIDE_DECKS:
        out[title] = _slide_url(slug)
    return out


def update_urls(db: Session) -> dict:
    """Refresh URLs on the live Aalto BDA course in place — module-item URLs
    and assignment description_md / coverage. Preserves submissions / AI
    solutions / announcements / grades.

    Counter semantics:
      - ``items_examined`` / ``items_updated``: per module-item.
      - ``assignments_updated``: count of *distinct* assignments with any
        field change (description_md). An assignment with multiple field
        changes is counted once.
      - ``coverage_updated``: per assignment whose covers_lecture_from/to
        changed.
    """
    course = db.query(Course).filter(Course.code == CODE).first()
    if course is None:
        return {"course_found": False}
    counts = {
        "course_found": True,
        "items_examined": 0,
        "items_updated": 0,
        "assignments_updated": 0,
        "coverage_updated": 0,
    }

    fixed = _fixed_title_to_url()

    for m in course.modules:
        for it in m.items:
            counts["items_examined"] += 1
            if it.title in fixed:
                new_url = fixed[it.title]
                if new_url != it.external_url:
                    it.external_url = new_url
                    counts["items_updated"] += 1

    dirty_assignments: set[str] = set()
    by_title = {a.title: a for a in course.assignments}
    for n, title_stem, chapter, lec_from, lec_to, _pts in WEEKLY_ASSIGNMENTS:
        a = next(
            (x for t, x in by_title.items() if t.startswith(f"Assignment {n} —")),
            None,
        )
        if a is None:
            continue
        new_desc = _weekly_description(n, title_stem, chapter, lec_from, lec_to)
        if a.description_md != new_desc:
            a.description_md = new_desc
            dirty_assignments.add(a.id)
        if a.covers_lecture_from != lec_from or a.covers_lecture_to != lec_to:
            a.covers_lecture_from = lec_from
            a.covers_lecture_to = lec_to
            counts["coverage_updated"] += 1

    proj = by_title.get(PROJECT_TITLE)
    if proj is not None:
        new_desc = _project_description()
        if proj.description_md != new_desc:
            proj.description_md = new_desc
            dirty_assignments.add(proj.id)
        if (
            proj.covers_lecture_from != PROJECT_LEC_FROM
            or proj.covers_lecture_to != PROJECT_LEC_TO
        ):
            proj.covers_lecture_from = PROJECT_LEC_FROM
            proj.covers_lecture_to = PROJECT_LEC_TO
            counts["coverage_updated"] += 1

    counts["assignments_updated"] = len(dirty_assignments)

    db.commit()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the Aalto BDA course.")
    parser.add_argument(
        "--force", action="store_true",
        help="delete an existing Aalto BDA course first",
    )
    parser.add_argument(
        "--update-urls", action="store_true",
        help="only refresh module_item external_url + assignment fields on the "
             "existing course (no deletions)",
    )
    args = parser.parse_args()
    db = SessionLocal()
    try:
        if args.update_urls:
            counts = update_urls(db)
            print("update_urls: " + ", ".join(f"{k}={v}" for k, v in counts.items()))
            return
        c = seed(db, force=args.force)
        n_modules = len(c.modules)
        n_items = sum(len(m.items) for m in c.modules)
        n_assign = len(c.assignments)
        print(
            f"Seeded {c.code} — {c.title}: {n_modules} modules, {n_items} items, "
            f"{n_assign} assignments."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Re-run tests**

```bash
cd backend && uv run pytest tests/test_seed_aalto_bda.py -q
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
cd backend && uv run ruff check seed/seed_aalto_bda.py
git add backend/seed/seed_aalto_bda.py backend/tests/test_seed_aalto_bda.py
git commit -m "feat(seed/aalto-bda): update_urls() + CLI"
```

---

### Task 5: Full backend test sweep + lint

- [ ] **Step 1: Run the full test suite**

```bash
cd backend && uv run pytest -q
```

Expected: all tests pass — no existing tests should regress (the autouse `_mock_network_for_seed` fixture is scoped to `test_seed_aalto_bda.py` only).

- [ ] **Step 2: Lint everything that changed**

```bash
cd backend && uv run ruff check .
```

Expected: clean.

- [ ] **Step 3: Commit anything outstanding**

If steps 1-2 turned up fixes (typo, import order, line length): apply, re-run, commit with `style(seed/aalto-bda): ruff fixes` or equivalent.

---

### Task 6: Commit the spec + plan, push, inspect for merge

- [ ] **Step 1: Commit the spec + plan to the feature branch**

```bash
git add docs/superpowers/specs/2026-05-16-aalto-bda-seed-design.md docs/superpowers/plans/2026-05-16-aalto-bda-seed.md
git commit -m "docs(seed/aalto-bda): design spec + implementation plan"
```

- [ ] **Step 2: Push the branch**

```bash
git push -u origin feat/seed-aalto-bda
```

- [ ] **Step 3: Inspect against master for merge conflicts**

```bash
git fetch origin master
git diff --check master...feat/seed-aalto-bda
git log --oneline master..feat/seed-aalto-bda
```

Expected:
- `--check` reports no whitespace / conflict markers.
- `git log` lists only the new seed/spec/plan commits.

- [ ] **Step 4: Open a PR** (do NOT auto-merge; user wanted conflict inspection first)

```bash
gh pr create --title "feat(seed/aalto-bda): Aalto BDA — Bayesian Data Analysis seed course" \
  --body "$(cat <<'EOF'
## Summary
- New seed: `Aalto BDA — Bayesian Data Analysis` (Vehtari, CS-E5710).
- 9 AI-graded weekly assignments + 1 project-mode capstone (`requires_solution_key=False` — first live use of the project-mode AI grading flow shipped in PRs #6/#7).
- 3 modules: Direct links (13) + BDA3 Chapter notes (11) + Lecture slides (17).
- No exams, no official-solution PDFs, no Storage uploads, no `--refresh-solutions` flag.
- Grade split 70% Weekly Assignments / 30% Capstone Project; within-group weights encoded as `points_possible` from the GSU 2023 scheme.

## Test plan
- [x] `cd backend && uv run pytest -q` (all green)
- [x] `cd backend && uv run ruff check .` (clean)
- [ ] After merge: `python -m seed.seed_aalto_bda` against the live Supabase DB to actually create the course

See [the design spec](docs/superpowers/specs/2026-05-16-aalto-bda-seed-design.md) and [implementation plan](docs/superpowers/plans/2026-05-16-aalto-bda-seed.md).
EOF
)"
```

- [ ] **Step 5: Report PR URL + merge readiness**

Surface to the user:
- PR URL
- Output of `git diff --check master...feat/seed-aalto-bda`
- Whether merge is clean (fast-forward / no conflicts) or has conflicts to resolve

**Do not run `gh pr merge` autonomously** — the user explicitly asked to "inspect git status and conflicts before merging", so the merge step is theirs.

---

## Self-review checklist (already run against spec)

- ✅ §3 (course meta) → Task 3, Step 1 (test_seed_creates_course_with_expected_metadata).
- ✅ §4 (grading 70/30) → Task 3, Step 1 (test_seed_creates_two_assignment_groups_with_70_30_weights).
- ✅ §5.1 (9 weeklies + points scale) → Task 3, Step 1 + Task 1, Step 1.
- ✅ §5.2 (project, `requires_solution_key=False`) → Task 3, Step 1.
- ✅ §6 (modules — 13/11/17) → Task 2, Step 1 + Task 3, Step 1.
- ✅ §7 (CLI — `seed`, `--force`, `--update-urls`) → Task 3 + Task 4.
- ✅ §8 (tests — idempotency, force, mocked network, update_urls noop & restore) → Tasks 3 + 4 cover each bullet.
- ✅ §9 (no `--refresh-solutions`, no exam group) → not implemented (negative requirement satisfied by absence).
