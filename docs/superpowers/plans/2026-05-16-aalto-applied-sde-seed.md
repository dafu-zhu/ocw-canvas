# Aalto Applied SDE Seed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Seed Aalto MS-E1602 — Applied Stochastic Differential Equations (Särkkä & Solin, Autumn 2014) into OCW Canvas as a replacement for the dead Stanford MATH 236 slot. 6 project-mode AI-graded exercise rounds, 3 modules (Direct links / Booklet chapters / Lecture handouts), no exams, no Storage uploads, no published solutions.

**Architecture:** Single `backend/seed/seed_aalto_applied_sde.py`, modelled on the in-progress `seed_aalto_bda.py`. All 6 exercise rounds use `requires_solution_key=False` (project-mode grading shipped in PR #6) — Aalto publishes no solution keys, so the AI grades each round on quality / correctness / depth against the booklet's content. One assignment group ("Exercise Rounds", weight 100). CLI: `seed`, `--force`, `--update-urls` — no `--refresh-solutions` (no PDFs to refresh).

**Tech Stack:** Python 3.12, SQLAlchemy 2.x (existing ORM), pytest with the autouse `_fresh_schema` fixture from `tests/conftest.py` + a defensive `httpx` mock. No `httpx` or `storage` calls at seed time.

**Spec:** [docs/superpowers/specs/2026-05-16-aalto-applied-sde-seed-design.md](../specs/2026-05-16-aalto-applied-sde-seed-design.md)

---

## Pre-flight

- [x] **P1: Feature branch already created** (`feat/seed-aalto-applied-sde`, off master at `a10a169`). Spec already committed at `e268b54`.

- [ ] **P2: Verify clean working tree and baseline tests pass**

```bash
git status
cd backend && uv run pytest -q
```

Expected: only `.claude/`, the in-progress untracked `seed_aalto_bda.py` / `test_seed_aalto_bda.py` / `docs/superpowers/{plans,specs}/2026-05-16-aalto-bda-*` files, and this plan's docs are untracked. All existing tests pass on master.

---

### Task 1: Module skeleton — constants, URL helpers, narrative text

**Files:**
- Create: `backend/seed/seed_aalto_applied_sde.py`
- Create: `backend/tests/test_seed_aalto_applied_sde.py`

- [ ] **Step 1: Write the failing test for constants and URL helpers**

Create `backend/tests/test_seed_aalto_applied_sde.py`:

```python
import pytest

from seed.seed_aalto_applied_sde import (
    BASE,
    BOOKLET_URL,
    CHAPTERS,
    CODE,
    DESCRIPTION,
    EXERCISE_ROUNDS,
    HANDOUTS,
    HOME,
    HOME_MD,
    SYLLABUS_MD,
    TEXTBOOK,
    _exercise_url,
    _handout_url,
    _modules,
    seed,
    update_urls,
)


@pytest.fixture(autouse=True)
def _mock_network_for_seed(monkeypatch):
    """Defensive: the Aalto SDE seed makes no network calls today, but if a
    future change adds httpx usage we want tests to fail loudly rather than
    silently hit the live Aalto site."""
    import httpx

    def _boom(*a, **kw):
        raise AssertionError("seed must not perform network I/O during tests")

    monkeypatch.setattr(httpx, "get", _boom)
    monkeypatch.setattr(httpx, "post", _boom)
    yield


# ---------------------------------------------------------- constants / URL helpers


def test_code_and_base():
    assert CODE == "Aalto MS-E1602"
    assert BASE == "https://users.aalto.fi/~ssarkka/course_s2014"
    assert HOME == BASE + "/"


def test_booklet_url():
    assert BOOKLET_URL == BASE + "/sde_course_booklet.pdf"


def test_exercise_urls():
    assert _exercise_url(1) == BASE + "/ex1.pdf"
    assert _exercise_url(6) == BASE + "/ex6.pdf"


def test_handout_urls():
    assert _handout_url(1) == BASE + "/handout1.pdf"
    assert _handout_url(6) == BASE + "/handout6.pdf"


def test_exercise_rounds_count_and_uniform_points():
    """6 exercise rounds, all worth 100 points (uniform), all project-mode."""
    assert len(EXERCISE_ROUNDS) == 6
    for _n, _title, _ch, _lec_from, _lec_to, pts in EXERCISE_ROUNDS:
        assert pts == 100


def test_exercise_rounds_cover_chapters_2_through_7():
    """Round k covers booklet Ch k+1 (Ch 1 is ODE refresher, Ch 8 is bonus)."""
    pairs = [(n, ch) for (n, _t, ch, _lf, _lt, _p) in EXERCISE_ROUNDS]
    assert pairs == [
        (1, "Booklet Ch 2"),
        (2, "Booklet Ch 3"),
        (3, "Booklet Ch 4"),
        (4, "Booklet Ch 5"),
        (5, "Booklet Ch 6"),
        (6, "Booklet Ch 7"),
    ]


def test_chapters_count_and_order():
    """Booklet has 8 chapters; all 8 present in order."""
    assert len(CHAPTERS) == 8
    nums = [n for (n, _title) in CHAPTERS]
    assert nums == [1, 2, 3, 4, 5, 6, 7, 8]


def test_handouts_count():
    """6 handout PDFs — 1 per session."""
    assert len(HANDOUTS) == 6
```

- [ ] **Step 2: Run the failing tests**

```bash
cd backend && uv run pytest tests/test_seed_aalto_applied_sde.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'seed.seed_aalto_applied_sde'`.

- [ ] **Step 3: Create the module skeleton with constants and URL helpers**

Create `backend/seed/seed_aalto_applied_sde.py`:

```python
"""Seed the Aalto MS-E1602 — Applied Stochastic Differential Equations course.

Source: https://users.aalto.fi/~ssarkka/course_s2014/  (Sarkka & Solin, Autumn 2014)
Run:    cd backend && uv run python -m seed.seed_aalto_applied_sde [--force] [--update-urls]

Idempotent: if a course with code "Aalto MS-E1602" already exists this is a
no-op, unless ``--force`` (which deletes it first — the cascade on Course
removes its modules / assignment groups / assignments / announcements).

Pattern differences vs the Aalto BDA seed:
  - Every graded assignment is project-mode (``requires_solution_key=False``).
    Aalto publishes no solution keys for MS-E1602 — exercises were worked
    through in-person at the exercise session. First seed where *all* graded
    assignments are project-mode (Aalto BDA uses project-mode for the
    capstone only).
  - No exam group (course has no exams). Single assignment group: "Exercise
    Rounds" with weight=100.
  - No capstone (course doesn't publish one — faithful to source).
  - No Storage interaction, no ``--refresh-solutions`` flag.
"""
from __future__ import annotations

import argparse

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Assignment, AssignmentGroup, Course, Module, ModuleItem

CODE = "Aalto MS-E1602"
BASE = "https://users.aalto.fi/~ssarkka/course_s2014"

HOME = BASE + "/"
BOOKLET_URL = BASE + "/sde_course_booklet.pdf"
SARKKA_HOMEPAGE = "https://users.aalto.fi/~ssarkka/"
SOLIN_HOMEPAGE = "https://arno.solin.fi/"
CAMBRIDGE_BOOK_URL = (
    "https://www.cambridge.org/core/books/applied-stochastic-differential-equations/"
    "0F1F3D5A0E64E73E2F87DAEB57B620E2"
)
COMPANION_CODE_URL = "https://github.com/AaltoML/SDE"


def _exercise_url(n: int) -> str:
    return f"{BASE}/ex{n}.pdf"


def _handout_url(n: int) -> str:
    return f"{BASE}/handout{n}.pdf"


# 8 booklet chapters — all present in the published booklet.
# (chapter_number, display_title)
CHAPTERS: list[tuple[int, str]] = [
    (1, "Background on ordinary differential equations"),
    (2, "Pragmatic introduction to stochastic differential equations"),
    (3, "Itô calculus and stochastic differential equations"),
    (4, "Probability distributions and statistics of SDEs (FPK)"),
    (5, "Linearization and Itô–Taylor series of SDEs"),
    (6, "Stochastic Runge–Kutta methods"),
    (7, "Bayesian estimation of SDEs"),
    (8, "Further topics: martingales, Girsanov, Feynman–Kac, Fourier"),
]


# 6 lecture handouts — chapter mapping inferred from booklet TOC.
# (handout_number, display_title)
HANDOUTS: list[tuple[int, str]] = [
    (1, "Handout 1 — ODE refresher + pragmatic SDE intro (Chs 1–2)"),
    (2, "Handout 2 — Itô calculus (Ch 3)"),
    (3, "Handout 3 — FPK, transition densities, moments (Ch 4)"),
    (4, "Handout 4 — Itô–Taylor series; weak/strong approximations (Ch 5)"),
    (5, "Handout 5 — Stochastic Runge–Kutta (Ch 6)"),
    (6, "Handout 6 — Bayesian estimation + further topics (Chs 7–8)"),
]


# 6 exercise rounds. Tuple: (n, title_stem, chapter_reading, lec_from, lec_to, points_possible).
# All rounds use points_possible=100 (uniform weighting within the single group).
EXERCISE_ROUNDS: list[tuple[int, str, str, int, int, int]] = [
    (1, "Mean/covariance equations; Ornstein–Uhlenbeck; Euler–Maruyama",
        "Booklet Ch 2", 1, 1, 100),
    (2, "Itô formula; SDE solutions; mean/variance derivation",
        "Booklet Ch 3", 2, 2, 100),
    (3, "Fokker–Planck–Kolmogorov; numerical FPK; Langevin Brownian motion",
        "Booklet Ch 4", 3, 3, 100),
    (4, "Milstein method; strong/weak Itô–Taylor approximations; Gaussian approx",
        "Booklet Ch 5", 4, 4, 100),
    (5, "Stochastic Runge–Kutta (strong + weak); stochastic flow on the torus",
        "Booklet Ch 6", 5, 5, 100),
    (6, "Kalman filter + RTS smoother; Kushner–Stratonovich; extended Kalman–Bucy",
        "Booklet Ch 7", 6, 6, 100),
]


DESCRIPTION = (
    "Applied stochastic differential equations: ODE background, Itô calculus, "
    "Fokker–Planck–Kolmogorov, Itô–Taylor and stochastic Runge–Kutta numerics, "
    "Bayesian filtering for SDEs, Girsanov / Feynman–Kac. Companion to Särkkä "
    "& Solin's 2019 Cambridge textbook (2014 lecture-notes precursor is free)."
)

TEXTBOOK = (
    "Särkkä & Solin — Lecture Notes on Applied Stochastic Differential Equations, "
    "v1.1 (Dec 4, 2014), free PDF at the course source URL. Published successor: "
    "Applied Stochastic Differential Equations (Cambridge IMS Textbooks, 2019, "
    "paid; not used as primary)."
)

HOME_MD = """**Aalto MS-E1602 — Applied Stochastic Differential Equations
(Simo Särkkä & Arno Solin).**

Course materials mirrored from Aalto's public 2014 course site
(<https://users.aalto.fi/~ssarkka/course_s2014/>). The term shown above is
*your* self-study term — edit it from the course settings when your plan
shifts.

A 6-session applied SDE course aimed at probabilistic-modelling and
engineering applications rather than measure-theoretic rigour. Brownian
motion → Itô calculus → SDEs → Fokker–Planck–Kolmogorov → numerical
schemes (Euler–Maruyama, Milstein, Itô–Taylor, stochastic Runge–Kutta) →
Bayesian estimation of SDEs (Kalman–Bucy, Kushner–Stratonovich) →
martingales, Girsanov, Feynman–Kac.

The textbook is the 2014 lecture-notes booklet (119 pages, free) — the
direct precursor to Särkkä & Solin's *Applied Stochastic Differential
Equations* (Cambridge IMS, 2019). Each lecture session is paired with a
handout PDF; the 6 exercise rounds drive the grade.

Aalto did not publish solutions for the exercise rounds — they were
worked through in-person at the exercise session. For self-study, every
round is graded in **project mode**: the AI scores your worked solution
on quality / correctness / depth / clarity against the booklet's
content, without comparing to a reference key.

Jump to **Syllabus**, **Modules**, or **Assignments**.
"""

SYLLABUS_MD = """## Prerequisites
Calculus, linear algebra, probability (distributions, expectations,
multivariate normal). Comfort with ordinary differential equations and a
scientific programming language (the lecture notes use Matlab; Python +
SciPy works fine). Measure theory is *not* assumed — the booklet trades
rigour for readability and points at Øksendal (2003) and Karatzas–Shreve
(1991) for the measure-theoretic foundation.

## Textbook
- **Primary** — Särkkä & Solin, *Lecture Notes on Applied Stochastic
  Differential Equations*, v1.1 (Dec 4, 2014). Free PDF linked under
  **Direct links** in Modules.
- **Successor (paid)** — Särkkä & Solin, *Applied Stochastic Differential
  Equations* (Cambridge IMS Textbooks, 2019). Same content, polished and
  expanded.
- **Background references** cited by the booklet:
  - Øksendal, *Stochastic Differential Equations*, 6th ed (2003).
  - Karatzas & Shreve, *Brownian Motion and Stochastic Calculus* (1991).

## Grading
| Component | Weight |
|---|---|
| Exercise Rounds (6) | 100% |

Aalto's published scheme weights the exercise rounds against an in-person
final exam. There is no public exam to mirror, so for self-study the 6
rounds carry the whole grade — uniform 100 points each.

## Exercise policy
Each round corresponds to one booklet chapter (Ch 2 through Ch 7):

| Round | Booklet chapter | Topic |
|---|---|---|
| E1 | Ch 2 | Pragmatic SDE intro: mean/covariance, Ornstein–Uhlenbeck, Euler–Maruyama |
| E2 | Ch 3 | Itô calculus: Itô formula, explicit linear-SDE solutions |
| E3 | Ch 4 | FPK + numerical FPK, Langevin Brownian motion |
| E4 | Ch 5 | Itô–Taylor: Milstein method, strong/weak approximations, Gaussian approximation |
| E5 | Ch 6 | Stochastic Runge–Kutta: strong and weak methods, stochastic flow on the torus |
| E6 | Ch 7 | Bayesian estimation: Kalman filter + RTS smoother, Kushner–Stratonovich, extended Kalman–Bucy |

The AI grades each submission in **project mode** — no reference
solution is generated. It scores on quality of derivation,
correctness against the booklet's notation and results, code quality
for simulation problems, and clarity of presentation. Re-attempts are
allowed; the latest counts.

## What's not here
- **No public exam.** Aalto's exam was in-person only. The booklet has
  no answer appendix.
- **No videos.** The 2014 offering wasn't recorded.
- **Chapter 8** (martingales, Girsanov, Feynman–Kac, Fourier methods)
  has no exercise round in the Aalto offering. It ships as a module
  reading only — faithful to the source.
"""
```

- [ ] **Step 4: Re-run tests**

```bash
cd backend && uv run pytest tests/test_seed_aalto_applied_sde.py -q
```

Expected: constants/URL tests PASS; failures shift to `_modules`/`seed`/`update_urls` not defined.

- [ ] **Step 5: Commit the skeleton**

```bash
cd backend && uv run ruff check seed/seed_aalto_applied_sde.py tests/test_seed_aalto_applied_sde.py
git add backend/seed/seed_aalto_applied_sde.py backend/tests/test_seed_aalto_applied_sde.py
git commit -m "feat(seed/aalto-sde): module skeleton + URL helpers + tables"
```

---

### Task 2: `_modules()` helper + module-shape tests

**Files:**
- Modify: `backend/seed/seed_aalto_applied_sde.py` (append `_direct_links_items`, `_chapter_items`, `_handout_items`, `_modules`)
- Modify: `backend/tests/test_seed_aalto_applied_sde.py`

- [ ] **Step 1: Add the failing test for module shape**

Append to `backend/tests/test_seed_aalto_applied_sde.py`:

```python
# ---------------------------------------------------------- _modules()


def test_modules_shape():
    """3 modules with the expected item counts."""
    mods = _modules()
    titles = [t for (t, _items) in mods]
    assert titles == ["Direct links", "Booklet chapters", "Lecture handouts"]

    counts = {t: len(items) for (t, items) in mods}
    assert counts == {
        "Direct links": 6,
        "Booklet chapters": 8,
        "Lecture handouts": 6,
    }


def test_modules_only_link_kinds():
    """Every module item is kind='link' (no video, no inline text)."""
    for (_title, items) in _modules():
        for it in items:
            assert it["kind"] == "link", f"non-link kind: {it!r}"


def test_modules_chapter_titles():
    """Booklet chapter items carry the chapter number and topic."""
    by_module = dict(_modules())
    chap_items = by_module["Booklet chapters"]
    assert chap_items[0]["title"].startswith("Chapter 1 —")
    assert chap_items[-1]["title"].startswith("Chapter 8 —")
    # All 8 chapters point at the booklet PDF (no per-chapter PDF exists).
    for it in chap_items:
        assert it["url"] == BOOKLET_URL


def test_modules_handout_urls():
    """Lecture-handout items use _handout_url(N)."""
    by_module = dict(_modules())
    handout_items = by_module["Lecture handouts"]
    assert handout_items[0]["url"] == _handout_url(1)
    assert handout_items[-1]["url"] == _handout_url(6)
```

- [ ] **Step 2: Run the failing tests**

```bash
cd backend && uv run pytest tests/test_seed_aalto_applied_sde.py -q
```

Expected: FAIL with `NameError: name '_modules' is not defined`.

- [ ] **Step 3: Implement `_modules()` and helpers**

Append to `backend/seed/seed_aalto_applied_sde.py`:

```python
# --------------------------------------------------------------------------- modules


def _direct_links_items() -> list[dict]:
    return [
        {"kind": "link", "title": "Aalto MS-E1602 course home (Särkkä)",
         "url": HOME},
        {"kind": "link", "title": "Lecture notes booklet (119 pp PDF)",
         "url": BOOKLET_URL},
        {"kind": "link", "title": "Simo Särkkä — homepage",
         "url": SARKKA_HOMEPAGE},
        {"kind": "link", "title": "Arno Solin — homepage",
         "url": SOLIN_HOMEPAGE},
        {"kind": "link", "title": "Applied SDE — Cambridge book (paid successor)",
         "url": CAMBRIDGE_BOOK_URL},
        {"kind": "link", "title": "Companion MATLAB/Python code (AaltoML/SDE)",
         "url": COMPANION_CODE_URL},
    ]


def _chapter_items() -> list[dict]:
    """All 8 chapter items point at the booklet PDF — there's no per-chapter
    PDF. Chapter number + topic in the title carries the navigation hint."""
    return [
        {"kind": "link", "title": f"Chapter {n} — {topic}", "url": BOOKLET_URL}
        for n, topic in CHAPTERS
    ]


def _handout_items() -> list[dict]:
    return [
        {"kind": "link", "title": title, "url": _handout_url(n)}
        for n, title in HANDOUTS
    ]


def _modules() -> list[tuple[str, list[dict]]]:
    """Three modules mirroring the natural shape of Aalto's published page:

      1. "Direct links" — top-of-course navigation (booklet, authors,
         Cambridge book, companion code).
      2. "Booklet chapters" — 8 chapter readings, all linking to the same
         booklet PDF (no per-chapter PDFs exist).
      3. "Lecture handouts" — 6 handout PDFs paired with the chapters.

    No per-lecture unit modules and no kind='video' items — the 2014
    offering had no recordings. See feedback memory
    ``feedback-module-content-chapter-readings``.
    """
    return [
        ("Direct links", _direct_links_items()),
        ("Booklet chapters", _chapter_items()),
        ("Lecture handouts", _handout_items()),
    ]
```

- [ ] **Step 4: Re-run module tests**

```bash
cd backend && uv run pytest tests/test_seed_aalto_applied_sde.py -q
```

Expected: all module-shape tests PASS.

- [ ] **Step 5: Commit**

```bash
cd backend && uv run ruff check seed/seed_aalto_applied_sde.py
git add backend/seed/seed_aalto_applied_sde.py backend/tests/test_seed_aalto_applied_sde.py
git commit -m "feat(seed/aalto-sde): modules — Direct links + Booklet chapters + Handouts"
```

---

### Task 3: `seed()` — course, group, 6 project-mode assignments, modules

**Files:**
- Modify: `backend/seed/seed_aalto_applied_sde.py` (append assignment-description helpers, `_delete_existing`, `seed`)
- Modify: `backend/tests/test_seed_aalto_applied_sde.py`

- [ ] **Step 1: Write the failing tests for `seed()`**

Append to `backend/tests/test_seed_aalto_applied_sde.py`:

```python
# ---------------------------------------------------------- seed()


def test_seed_creates_course_with_expected_metadata(db):
    course = seed(db)
    assert course.code == "Aalto MS-E1602"
    assert course.title == "Applied Stochastic Differential Equations"
    assert course.institution == "Aalto University"
    assert course.instructor == "Profs. Simo Särkkä & Arno Solin"
    assert course.term_label == "Spring 2029"
    assert course.status == "planned"
    assert course.color == "#2D7A47"
    assert course.external_home_url == HOME
    assert course.home_page_md == HOME_MD
    assert course.syllabus_md == SYLLABUS_MD
    assert course.textbook == TEXTBOOK
    assert course.description == DESCRIPTION


def test_seed_creates_one_assignment_group_weight_100(db):
    course = seed(db)
    assert len(course.assignment_groups) == 1
    g = course.assignment_groups[0]
    assert g.name == "Exercise Rounds"
    assert g.weight == 100
    assert g.drop_lowest_n == 0
    assert g.position == 0


def test_seed_creates_six_project_mode_assignments(db):
    course = seed(db)
    assert len(course.assignments) == 6
    by_title = {a.title: a for a in course.assignments}

    for n, _title_stem, _ch, lec_from, lec_to, pts in EXERCISE_ROUNDS:
        match = [t for t in by_title if t.startswith(f"Exercise Round {n} —")]
        assert len(match) == 1, f"expected exactly one Round {n}, got {match}"
        a = by_title[match[0]]
        assert int(a.points_possible) == pts == 100
        # All 6 rounds are project-mode (no reference solution to compare against).
        assert a.requires_solution_key is False, (
            f"Round {n} must be project-mode (Aalto publishes no solutions)"
        )
        assert a.covers_lecture_from == lec_from
        assert a.covers_lecture_to == lec_to
        # description_md should reference the source PDF and the booklet chapter.
        assert _exercise_url(n) in a.description_md
        assert "project mode" in a.description_md.lower()


def test_seed_creates_three_modules_with_expected_items(db):
    course = seed(db)
    mods = sorted(course.modules, key=lambda m: m.position)
    assert [m.title for m in mods] == [
        "Direct links",
        "Booklet chapters",
        "Lecture handouts",
    ]
    counts = {m.title: len(m.items) for m in mods}
    assert counts == {
        "Direct links": 6,
        "Booklet chapters": 8,
        "Lecture handouts": 6,
    }


def test_seed_is_idempotent(db):
    first = seed(db)
    second = seed(db)
    assert first.id == second.id
    # No duplicate assignments / modules created.
    assert len(second.assignments) == 6
    assert len(second.modules) == 3


def test_seed_force_recreates_course(db):
    first = seed(db)
    first_id = first.id
    second = seed(db, force=True)
    assert second.id != first_id
    assert len(second.assignments) == 6
```

- [ ] **Step 2: Run failing tests**

```bash
cd backend && uv run pytest tests/test_seed_aalto_applied_sde.py -q
```

Expected: FAIL on `seed not defined` / `Course.code` not found.

- [ ] **Step 3: Implement assignment-description helpers + `seed()`**

Append to `backend/seed/seed_aalto_applied_sde.py`:

```python
# --------------------------------------------------------------------------- descriptions


# Per-round transcribed problem text, drawn verbatim from ex{N}.pdf (S\"arkk\"a
# & Solin, Autumn 2014). The AI grader reads this text directly — the source
# PDF is also linked for cross-reference, but we do not rely on the grader
# fetching it at runtime.
ROUND_PROBLEMS: dict[int, str] = {
    1: """**Exercise 1 (Mean and covariance equations).**
(a) Complete the missing steps in the derivation of the covariance (booklet eq. 2.37).
(b) Derive the mean and covariance differential equations (booklet eq. 2.38) by differentiating (2.36) and (2.37).

**Exercise 2 (Solution of an Ornstein–Uhlenbeck process).**
(a) Find the complete solution $x(t)$ as well as the mean $m(t)$ and variance $P(t)$ of the scalar SDE
$\\frac{dx(t)}{dt} = -\\lambda\\, x(t) + w(t),\\quad x(0)=x_0,$
where $x_0$ and $\\lambda > 0$ are given constants and the white noise $w(t)$ has spectral density $q$.
(b) Compute the limit of the mean and variance as $t\\to\\infty$ (i) directly via $\\lim_{t\\to\\infty} P(t)$, and (ii) by solving the stationary state of the variance ODE $dP/dt=0$.

**Exercise 3 (Euler–Maruyama solution of an O–U process).**
Simulate 1000 trajectories on $t \\in [0,1]$ from the O–U process above using Euler–Maruyama with $\\lambda=1/2$, $q=1$, $\\Delta t=1/100$, $x_0=1$ and check that the mean and covariance trajectories approximately agree with the theoretical values.""",
    2: """**Exercise 1 (Usage of the Itô formula).** Compute the Itô differential of
(a) $\\phi(\\beta) = t + \\exp(\\beta)$, where $\\beta(t)$ has diffusion constant $q$.
(b) $\\phi(x) = x^2$, where $x$ solves $dx = f(x)\\,dt + \\sigma\\,d\\beta$, $\\sigma$ constant, $\\beta$ standard ($q=1$).
(c) $\\phi(\\mathbf{x}) = \\mathbf{x}^\\top\\mathbf{x}$, where $d\\mathbf{x}=\\mathbf{F}\\mathbf{x}\\,dt + d\\boldsymbol{\\beta}$, $\\mathbf{F}$ constant, joint diffusion matrix of $\\boldsymbol{\\beta}$ is $\\mathbf{Q}$.

**Exercise 2 (Stochastic differential equations).**
(a) Check that $x(t)=\\exp(\\beta(t))$ solves $dx=\\tfrac{1}{2}x\\,dt + x\\,d\\beta$ ($\\beta$ standard).
(b) Solve $dx = -c\\,x\\,d\\beta$ ($c>0$, $\\beta$ standard) by changing variables to $y=\\ln x$.
(c) Convert the Stratonovich SDE $dx_1 = -x_2\\circ d\\beta,\\ dx_2 = x_1\\circ d\\beta$ ($\\beta$ scalar) to the equivalent Itô SDE.

**Exercise 3 (Mean and variance of differential equations).** For $dx = f(x)\\,dt + \\sigma(x)\\,d\\beta$ with diffusion $q$:
(a) Conclude from the definition of the Itô integral that $\\mathbb{E}\\!\\left[\\int_u^v \\sigma(x(t))\\,d\\beta(t)\\right] = 0$.
(b) Take expectations on both sides of the SDE and divide formally by $dt$ to get the ODE for $m(t)$.
(c) Apply Itô's formula to $\\phi(x,t)=(x-m(t))^2$ and take expectations to derive the variance ODE.
(d) Write the mean & variance ODEs for $dx=-\\lambda x\\,dt + d\\beta$ ($\\lambda>0$); solve with $x(0)=x_0$.""",
    3: """**Exercise 1 (FPK equation).** Consider $dx=\\tanh(x)\\,dt + d\\beta$, $x(0)=0$, $\\beta$ standard.
(a) Write down the FPK and check that $p(x,t) = \\tfrac{1}{\\sqrt{2\\pi t}}\\,\\cosh(x)\\,\\exp(-t/2)\\,\\exp(-x^2/(2t))$ solves it.
(b) Plot the evolution of the density for $t\\in[0,5]$.
(c) Simulate 1000 trajectories using Euler–Maruyama and check the histogram matches at $t=5$.

**Exercise 2 (Numerical solution of FPK).** Use finite differences on $x\\in[-L,L]$ with Dirichlet BCs $p(\\pm L,t)=0$.
(a) Divide the range into $n$ grid points with $h=1/(n+1)$; approximate $\\partial_x p$ and $\\partial_{xx} p$ by the standard 2nd-order central differences.
(b) Form the vector ODE $d\\mathbf{p}/dt = \\mathbf{F}\\mathbf{p}$ where $\\mathbf{p}=(p(h,t),\\ldots,p(nh,t))^\\top$.
(c) Solve via (i) backward Euler, (ii) numerical $\\exp(\\mathbf{F}t)$, (iii) forward Euler. Check against Ex 1.

**Exercise 3 (Langevin's physical Brownian motion).** Model $\\ddot{x} = -c\\dot{x} + w$, $x(0)=\\dot{x}(0)=0$, $c=6\\pi\\eta r$, white noise $w$ with spectral density $q$.
(a) Interpret as an Itô SDE; write the 2D state-space form.
(b) Write ODEs for the mean and the covariance entries $P_{11}, P_{12}, P_{21}, P_{22}$. Find the closed-form covariance solutions (start with $P_{22}$).
(c) Compute $\\lim_{t\\to\\infty} P_{22}(t)$ and use $m\\,\\mathbb{E}[(\\dot{x})^2] = RT/N$ to determine $q$.
(d) Plot $P_{11}(t)$ and show it asymptotically approaches a straight line; compute the asymptotic slope and conclude it recovers Langevin's result.""",
    4: """**Exercise 1 (Milstein's method).** Consider $dx = -c\\,x\\,dt + g\\,x\\,d\\beta$, $x(0)=x_0>0$, $\\beta$ standard.
(a) Check via the Itô formula that $x(t) = x_0\\,\\exp\\!\\big[(-c - g^2/2)t + g\\,\\beta(t)\\big]$ is the exact solution. *Hint:* $\\phi(\\beta,t) = x_0\\exp[(-c-g^2/2)t + g\\beta]$.
(b) Simulate trajectories with Milstein's method using $x_0=1, c=1/10, g=1/10$ and check that the histogram at $t=1$ matches sampling from the exact solution.

**Exercise 2 (Strong and weak approximations).** Consider $dx=\\tanh(x)\\,dt + d\\beta$, $x(0)=0$, with exact density $p(x,t)$ as in Round 3.
(a) Simulate 1000 trajectories with the **strong order 1.5** Itô–Taylor method (from the lecture notes); compare the histogram to the exact density at $t=5$.
(b) Simulate 1000 trajectories with the **weak order 2.0** Itô–Taylor method using (i) Gaussian increments and (ii) three-point distributed increments; compare to the exact density at $t=5$.
(c) Comment on the behavior of the simulated trajectories for $t\\in[0,5]$ across methods.

**Exercise 3 (Gaussian approximation of SDEs).**
(a) Form a Gaussian assumed-density approximation to the SDE in Ex 2 for $t\\in[0,5]$ and compare to the exact density (compute Gaussian integrals numerically on a uniform grid).
(b) Form a Gaussian assumed-density approximation to the SDE in Ex 1 and compare numerically to the histogram from 1(b).""",
    5: """**Exercise 1 (A strong stochastic Runge–Kutta method).** Consider the strong order 1.0 method with the extended Butcher tableau given in the lecture notes (booklet Ch 6).
(a) Write down the iteration equations corresponding to the tableau.
(b) For the Duffing–van der Pol oscillator
$dx_1 = x_2\\,dt,\\quad dx_2 = (x_1(\\alpha - x_1^2) - x_2)\\,dt + x_1\\,d\\beta,$
$\\beta$ a 1D Brownian motion with $q=0.5^2$ and $\\alpha=1$, use the method to draw trajectories starting from $x_2(0)=0$, $x_1(0)=-4,-3.9,\\ldots,-2$, on $t\\in[0,10]$. Plot in the $(x_1, x_2)$ plane.
(c) Experiment with step sizes $\\Delta t = 2^{-k}$, $k=0,2,4,6$ and visually compare to Euler–Maruyama.

**Exercise 2 (A weak stochastic Runge–Kutta method).** Consider the 2D SDE
$dx_1 = \\tfrac{3}{2} x_1\\,dt + \\tfrac{1}{10}x_1\\,d\\beta_1,\\quad dx_2 = \\tfrac{3}{2} x_2\\,dt + \\tfrac{1}{10}x_2\\,d\\beta_2,$
$\\mathbf{x}(0)=(1/10,1/10)$, $\\beta_i$ independent standard Brownians.
(a) Implement Euler–Maruyama for the system.
(b) Implement the weak order 2.0 Runge–Kutta scheme from the lecture notes (Alg. 6.4), with the tableau given in the round PDF.
(c) Simulate 1000 trajectories with both methods for $\\Delta t = 2^{-k}$, $k=0,\\ldots,6$. Compare to the expected value $\\mathbb{E}[x_i(t)] = (1/10)\\exp(3t/2)$ and plot absolute errors vs step size.

**Exercise 3 (Stochastic flow).** Consider the SDE on a torus $d\\mathbf{x} = \\mathbf{L}(\\mathbf{x})\\,d\\boldsymbol{\\beta}$ ($d=2$, $m=4$) with the diffusion columns
$\\mathbf{L}^1(\\mathbf{x}) = (\\cos\\alpha,\\sin\\alpha)^\\top \\sin(x_1),\\ \\mathbf{L}^2 = (\\cos\\alpha,\\sin\\alpha)^\\top \\cos(x_1),$
$\\mathbf{L}^3 = (-\\sin\\alpha,\\cos\\alpha)^\\top \\sin(x_2),\\ \\mathbf{L}^4 = (-\\sin\\alpha,\\cos\\alpha)^\\top \\cos(x_2)$ ($\\alpha=1$).
(a) Use Euler–Maruyama with the same Brownian-motion realization (reset seed) on a $15\\times 15$ grid of initial points in $[0,2\\pi]^2$ at step size $\\Delta t=2^{-4}$. Plot at $t=0.5,1.0,2.0,4.0$ (take $x_i$ mod $2\\pi$).
(b) Repeat with the weak order 2.0 SRK from the lecture notes (Alg. 6.5).""",
    6: """**Exercise 1 (Kalman filter and RTS smoother for OU).** Consider $dx = -\\lambda x\\,dt + d\\beta$, $y_k = x(t_k) + \\varepsilon_k$, with $\\lambda=1/2$, $q=1$, $x(0)\\sim N(0,P_\\infty)$, $\\varepsilon_k\\sim N(0,1)$, $P_\\infty$ the stationary variance.
(a) Simulate data with Euler–Maruyama ($\\Delta t=1/100$, $t\\in[0,10]$), measurements at $t_j=j$, $j=1,\\ldots,10$.
(b) Implement a Kalman filter; plot simulated data, observations, and filter mean together.
(c) Implement an RTS smoother; plot data, observations, and smoother mean together.
(d) How would you compute the smoothing solution at an arbitrary $t$?

**Exercise 2 (Continuous-time filtering).** For $dx=-\\lambda x\\,dt + d\\beta$, $dy = x\\,dt + d\\eta$ ($\\beta,\\eta$ independent standard Brownians):
(a) Write down the Kushner–Stratonovich equation.
(b) Write down the corresponding Zakai equation.
(c) Write down the Kalman–Bucy filter for the model.
(d) Show that the filters in (a)–(c) are equivalent.

**Exercise 3 (Continuous-time approximate non-linear filtering).** For $dx=\\tanh(x)\\,dt + d\\beta$, $dy=\\sin(x)\\,dt + d\\eta$ with $Q=1$ and $R=0.01$:
(a) Write down the extended Kalman–Bucy filter.
(b) Simulate data over $[0,5]$ with $\\Delta t=1/100$ and try implementing the filter numerically. How does it work?""",
}


def _round_description(
    n: int, title_stem: str, chapter: str, lec_from: int, lec_to: int
) -> str:
    """Full description for one exercise round — includes the transcribed
    problem text, source PDF link, booklet chapter reading pointer, and an
    explicit note about project-mode grading."""
    src_url = _exercise_url(n)
    lec_phrase = (
        f"Covers lecture {lec_from}" if lec_from == lec_to
        else f"Covers lectures {lec_from}–{lec_to}"
    )
    return (
        f"**Exercise Round {n}** ({title_stem}). {lec_phrase}. Reading: {chapter}.\n\n"
        f"- Source PDF: [ex{n}.pdf (Aalto)]({src_url})\n"
        f"- Reading: {chapter} of the lecture-notes booklet — see "
        "the *Booklet chapters* module.\n\n"
        "## Problems\n\n"
        f"{ROUND_PROBLEMS[n]}\n\n"
        "---\n\n"
        "**Grading.** Aalto did not publish solutions for this round — "
        "exercises were worked through in person at the exercise session. "
        "The AI grades your submission in **project mode**: it scores on "
        "quality of derivation, correctness against the booklet's notation "
        "and results, code quality for simulation problems, and clarity of "
        "presentation. There is no reference solution to compare against. "
        "Re-attempts are allowed; the latest counts."
    )


# --------------------------------------------------------------------------- seed


def _delete_existing(db: Session) -> None:
    for c in db.query(Course).filter(Course.code == CODE).all():
        db.delete(c)
    db.commit()


def _next_display_order(db: Session) -> int:
    """Take max(display_order)+1 across existing courses, defaulting to 0."""
    rows = [c.display_order for c in db.query(Course).all()]
    return (max(rows) + 1) if rows else 0


def seed(db: Session, force: bool = False) -> Course:
    existing = db.query(Course).filter(Course.code == CODE).first()
    if existing is not None:
        if not force:
            return existing
        _delete_existing(db)

    course = Course(
        code=CODE,
        title="Applied Stochastic Differential Equations",
        institution="Aalto University",
        term_label="Spring 2029",  # user's self-study term, editable in teacher mode
        instructor="Profs. Simo Särkkä & Arno Solin",
        external_home_url=HOME,
        status="planned",
        color="#2D7A47",  # forest green — distinct from prior seeds
        display_order=_next_display_order(db),
        textbook=TEXTBOOK,
        home_page_md=HOME_MD,
        syllabus_md=SYLLABUS_MD,
        description=DESCRIPTION,
    )
    db.add(course)
    db.flush()

    g_rounds = AssignmentGroup(
        course_id=course.id,
        name="Exercise Rounds",
        weight=100,
        drop_lowest_n=0,
        position=0,
    )
    db.add(g_rounds)
    db.flush()

    for n, title_stem, chapter, lec_from, lec_to, pts in EXERCISE_ROUNDS:
        a = Assignment(
            course_id=course.id,
            assignment_group_id=g_rounds.id,
            title=f"Exercise Round {n} — {title_stem}",
            description_md=_round_description(n, title_stem, chapter, lec_from, lec_to),
            points_possible=pts,
            accepts_files=True,
            accepts_text=True,
            position=n - 1,
            published=True,
            covers_lecture_from=lec_from,
            covers_lecture_to=lec_to,
            requires_solution_key=False,  # project-mode: no Aalto solution key exists
        )
        db.add(a)

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
cd backend && uv run pytest tests/test_seed_aalto_applied_sde.py -q
```

Expected: all `seed()` tests PASS.

- [ ] **Step 5: Commit**

```bash
cd backend && uv run ruff check seed/seed_aalto_applied_sde.py
git add backend/seed/seed_aalto_applied_sde.py backend/tests/test_seed_aalto_applied_sde.py
git commit -m "feat(seed/aalto-sde): seed() — course, group, 6 project-mode rounds, modules"
```

---

### Task 4: `update_urls()` + CLI

**Files:**
- Modify: `backend/seed/seed_aalto_applied_sde.py` (append `_fixed_title_to_url`, `update_urls`, `main`, `if __name__`)
- Modify: `backend/tests/test_seed_aalto_applied_sde.py`

- [ ] **Step 1: Write the failing tests for `update_urls`**

Append to `backend/tests/test_seed_aalto_applied_sde.py`:

```python
# ---------------------------------------------------------- update_urls


def test_update_urls_noop_on_fresh_seed(db):
    seed(db)
    counts = update_urls(db)
    assert counts["course_found"] is True
    assert counts["items_updated"] == 0
    assert counts["assignments_updated"] == 0
    assert counts["coverage_updated"] == 0
    assert counts["items_examined"] == 6 + 8 + 6  # 20


def test_update_urls_restores_tampered_url(db):
    course = seed(db)
    # Tamper with the booklet link.
    booklet_link = next(
        it for m in course.modules for it in m.items
        if it.title == "Lecture notes booklet (119 pp PDF)"
    )
    booklet_link.external_url = "https://example.com/wrong.pdf"
    db.commit()

    counts = update_urls(db)
    assert counts["items_updated"] == 1
    db.refresh(booklet_link)
    assert booklet_link.external_url == BOOKLET_URL


def test_update_urls_restores_tampered_description(db):
    course = seed(db)
    a1 = next(a for a in course.assignments if a.title.startswith("Exercise Round 1 "))
    a1.description_md = "tampered description"
    db.commit()

    counts = update_urls(db)
    assert counts["assignments_updated"] == 1
    db.refresh(a1)
    assert _exercise_url(1) in a1.description_md


def test_update_urls_restores_tampered_coverage(db):
    course = seed(db)
    a3 = next(a for a in course.assignments if a.title.startswith("Exercise Round 3 "))
    a3.covers_lecture_from = 99
    a3.covers_lecture_to = 99
    db.commit()

    counts = update_urls(db)
    assert counts["coverage_updated"] == 1
    db.refresh(a3)
    assert a3.covers_lecture_from == 3
    assert a3.covers_lecture_to == 3


def test_update_urls_on_missing_course(db):
    """No course present → returns course_found=False without raising."""
    out = update_urls(db)
    assert out == {"course_found": False}
```

- [ ] **Step 2: Run failing tests**

```bash
cd backend && uv run pytest tests/test_seed_aalto_applied_sde.py -q
```

Expected: FAIL — `update_urls` not defined.

- [ ] **Step 3: Implement `update_urls()` + `main()`**

Append to `backend/seed/seed_aalto_applied_sde.py`:

```python
# --------------------------------------------------------------------------- updater


def _fixed_title_to_url() -> dict[str, str]:
    """Map a module-item title to the URL it should always point to."""
    out: dict[str, str] = {
        "Aalto MS-E1602 course home (Särkkä)": HOME,
        "Lecture notes booklet (119 pp PDF)": BOOKLET_URL,
        "Simo Särkkä — homepage": SARKKA_HOMEPAGE,
        "Arno Solin — homepage": SOLIN_HOMEPAGE,
        "Applied SDE — Cambridge book (paid successor)": CAMBRIDGE_BOOK_URL,
        "Companion MATLAB/Python code (AaltoML/SDE)": COMPANION_CODE_URL,
    }
    # All chapter items point at the booklet (no per-chapter PDFs).
    for n, topic in CHAPTERS:
        out[f"Chapter {n} — {topic}"] = BOOKLET_URL
    for n, title in HANDOUTS:
        out[title] = _handout_url(n)
    return out


def update_urls(db: Session) -> dict:
    """Refresh URLs on the live Aalto MS-E1602 course in place — module-item
    URLs and assignment description_md / coverage. Preserves submissions / AI
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
    for n, title_stem, chapter, lec_from, lec_to, _pts in EXERCISE_ROUNDS:
        a = next(
            (x for t, x in by_title.items() if t.startswith(f"Exercise Round {n} ")),
            None,
        )
        if a is None:
            continue
        new_desc = _round_description(n, title_stem, chapter, lec_from, lec_to)
        if a.description_md != new_desc:
            a.description_md = new_desc
            dirty_assignments.add(a.id)
        if a.covers_lecture_from != lec_from or a.covers_lecture_to != lec_to:
            a.covers_lecture_from = lec_from
            a.covers_lecture_to = lec_to
            counts["coverage_updated"] += 1

    counts["assignments_updated"] = len(dirty_assignments)

    db.commit()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed the Aalto MS-E1602 (Applied SDE) course.",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="delete an existing Aalto MS-E1602 course first",
    )
    parser.add_argument(
        "--update-urls", action="store_true",
        help="only refresh module_item external_url + assignment fields on "
             "the existing course (no deletions)",
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
            f"Seeded {c.code} — {c.title}: {n_modules} modules, {n_items} "
            f"items, {n_assign} assignments."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Re-run tests**

```bash
cd backend && uv run pytest tests/test_seed_aalto_applied_sde.py -q
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
cd backend && uv run ruff check seed/seed_aalto_applied_sde.py
git add backend/seed/seed_aalto_applied_sde.py backend/tests/test_seed_aalto_applied_sde.py
git commit -m "feat(seed/aalto-sde): update_urls() + CLI"
```

---

### Task 5: Full backend test sweep + lint

- [ ] **Step 1: Run the full test suite**

```bash
cd backend && uv run pytest -q
```

Expected: all tests pass — no existing tests should regress (the autouse `_mock_network_for_seed` fixture is scoped to `test_seed_aalto_applied_sde.py` only).

- [ ] **Step 2: Lint everything that changed**

```bash
cd backend && uv run ruff check .
```

Expected: clean.

- [ ] **Step 3: Commit anything outstanding**

If steps 1–2 turned up fixes (typo, import order, line length): apply, re-run, commit with `style(seed/aalto-sde): ruff fixes` or equivalent.

---

### Task 6: Commit the plan, inspect for merge

- [ ] **Step 1: Commit this plan file to the feature branch**

```bash
git add docs/superpowers/plans/2026-05-16-aalto-applied-sde-seed.md
git commit -m "docs(seed/aalto-sde): implementation plan"
```

- [ ] **Step 2: Inspect against master for merge conflicts**

```bash
git fetch origin master
git diff --check master...feat/seed-aalto-applied-sde
git log --oneline master..feat/seed-aalto-applied-sde
git merge-tree $(git merge-base master feat/seed-aalto-applied-sde) master feat/seed-aalto-applied-sde | head -50
```

Expected:
- `--check` reports no whitespace / conflict markers.
- `git log` lists only the new spec / seed / test / plan commits on the branch.
- `git merge-tree` output is empty (no conflicts) — a clean fast-forward is possible.

Confirm the only files this branch touches are:

- `backend/seed/seed_aalto_applied_sde.py` (new)
- `backend/tests/test_seed_aalto_applied_sde.py` (new)
- `docs/superpowers/specs/2026-05-16-aalto-applied-sde-seed-design.md` (new)
- `docs/superpowers/plans/2026-05-16-aalto-applied-sde-seed.md` (new)

Specifically, **the untracked Aalto BDA files in the working tree must remain untracked** — this branch must not stage `backend/seed/seed_aalto_bda.py`, `backend/tests/test_seed_aalto_bda.py`, `docs/superpowers/plans/2026-05-16-aalto-bda-seed.md`, or `docs/superpowers/specs/2026-05-16-aalto-bda-seed-design.md`.

- [ ] **Step 3: Merge to master via no-ff** (user said "implement unattended"; the prior message also said "inspect git status and conflicts before merging" — Step 2 above is that inspection. Proceed if Step 2 reports clean.)

```bash
git checkout master
git merge --no-ff feat/seed-aalto-applied-sde -m "Merge feat/seed-aalto-applied-sde: seed Aalto MS-E1602 Applied SDE"
git status
```

Expected:
- Merge succeeds without conflicts.
- `git status` on master shows the same untracked Aalto BDA files (unchanged).

If `git merge` fails with conflicts (it shouldn't — only adds new files): stop, report the conflicts, do not push.

- [ ] **Step 4: Report merge status + memory updates pending**

Surface to the user:
- Branch sha range merged.
- Files merged (4 new files).
- Confirmation that the untracked Aalto BDA files are still untracked.
- Note that two memory files need updating post-merge:
  - `memory/study_plan_jhu_replacement.md` — record the Stanford MATH 236 → Aalto MS-E1602 substitution.
  - `memory/study_sequencing_2027_2030.md` — record that the 2029 SDE slot is now seeded; refresh the "currently seeded vs planned" section against actual master state (which also has 18.336 / IEOR 6711 / Cornell CS 4220 already merged that the previous memory snapshot did not reflect).

**Do not push to origin autonomously.** The user can push when ready.

---

## Self-review checklist (run against the spec)

- ✅ §3 (course meta — code, title, color, term_label) → Task 3, Step 1 (test_seed_creates_course_with_expected_metadata).
- ✅ §4 (grading — single group, weight 100) → Task 3, Step 1 (test_seed_creates_one_assignment_group_weight_100).
- ✅ §5 (6 rounds, uniform 100 pts, ALL project-mode) → Task 1 (test_exercise_rounds_count_and_uniform_points, test_exercise_rounds_cover_chapters_2_through_7) + Task 3 (test_seed_creates_six_project_mode_assignments).
- ✅ §6 (3 modules — 6 / 8 / 6 items, only links) → Task 2 (test_modules_shape, test_modules_only_link_kinds, test_modules_chapter_titles, test_modules_handout_urls) + Task 3 (test_seed_creates_three_modules_with_expected_items).
- ✅ §7 (CLI — `seed`, `--force`, `--update-urls`) → Task 3 + Task 4 (no `--refresh-solutions`).
- ✅ §8 (tests — idempotency, force, mocked network, update_urls noop & restore) → Tasks 3 + 4.
- ✅ §9 (no `--refresh-solutions`, no exam group, no capstone, no inline videos) → satisfied by absence; spec items §9 are negative requirements.
- ✅ §10 (risks — URL drift handled by `update_urls`; project-mode is new territory; doc-trail in spec/plan).
