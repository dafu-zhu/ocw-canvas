# Cornell CS 4220 Seed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `backend/seed/seed_cornell_cs4220.py` + tests, on branch `feat/seed-cornell-cs4220`, mirroring the `seed_cmu_36705.py` shape but with two project-mode assignments and topic-grouped (not per-lecture) modules.

**Architecture:** Pure ORM seed module. Two new files, no schema or app changes. Project-mode assignments use the existing `requires_solution_key=False` flag (migration 0006).

**Tech Stack:** Python 3.12 · SQLAlchemy · pytest · uv · ruff.

**Spec:** `docs/superpowers/specs/2026-05-16-cornell-cs4220-seed-design.md`.

---

### Task 1: Write the seed module

**Files:**
- Create: `backend/seed/seed_cornell_cs4220.py`

- [ ] **Step 1: Write `backend/seed/seed_cornell_cs4220.py`** with constants + `seed(db, force=False) -> Course` + `update_urls(db) -> dict` + `main()`. Follow the `seed_cmu_36705.py` skeleton; key differences listed in spec §9.

Structure:

```python
"""Seed Cornell CS 4220 / MATH 4260 — Numerical Analysis: Linear and Nonlinear
Problems (David Bindel, Spring 2024).

Run:  cd backend && uv run python -m seed.seed_cornell_cs4220 [--force] [--update-urls]
Source: https://www.cs.cornell.edu/courses/cs4220/2024sp/

Pattern differences vs the CMU 36-705 seed:
  - No per-lecture notes PDF (Bindel publishes none; just AG chapter pointers).
  - Modules are topic-grouped (7 + Direct links = 8); each topic module's items
    are `kind="note"` blocks listing the lectures and AG sections covered.
  - Two project-style assignments with requires_solution_key=False — the AI
    grades them in project mode (no reference solution generated).
  - Midterm and final dropped entirely: source publishes no paper, no solution.
"""
from __future__ import annotations

import argparse
import re

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Assignment, AssignmentGroup, Course, Module, ModuleItem

CODE = "Cornell CS 4220"
BASE = "https://www.cs.cornell.edu/courses/cs4220/2024sp"
HOME = BASE + "/"
ASCHER_GREIF_URL = "https://epubs.siam.org/doi/book/10.1137/1.9780898719987"
BINDEL_HOME = "https://www.cs.cornell.edu/~bindel/"


def _hw_url(n: int) -> str:
    return f"{BASE}/hw{n}.pdf"


HW_DATA_URL: dict[int, str] = {2: f"{BASE}/hw2_data.zip"}


def _proj_url(n: int) -> str:
    return f"{BASE}/P{n}.pdf"


PROJ_DATA_URL: dict[int, str] = {1: f"{BASE}/P1data.zip"}

# Inline references for specific lectures.
LECTURE_REFS: dict[int, str] = {
    1: "https://people.maths.ox.ac.uk/trefethen/publication/PDF/1992_55.pdf",
    16: f"{BASE}/Perturbation.pdf",
    38: "https://people.eecs.berkeley.edu/~brecht/opt4ml_book/",
    39: "https://epubs.siam.org/doi/10.1137/090771806",
    40: "https://epubs.siam.org/doi/10.1137/090771806",
    41: "https://epubs.siam.org/doi/10.1137/090771806",
}

# 6 homeworks — (number, topic, covers_lecture_from, covers_lecture_to).
HOMEWORKS: list[tuple[int, str, int, int]] = [
    (1, "Intro · LA background · numerical algorithms · floating point",  1,  7),
    (2, "LU, pivoting, Cholesky, sparse matrices",                        8, 11),
    (3, "Least squares & QR · eigenvalue problems · SVD",                12, 20),
    (4, "Iterative methods · nonlinear & optimization intro",            21, 29),
    (5, "BFGS, Gauss-Newton, IRLS, constraints",                         30, 36),
    (6, "Constraints, stochastic optimization, randomized NLA",          37, 42),
]

# 2 projects — (number, title, covers_lecture_from, covers_lecture_to).
PROJECTS: list[tuple[int, str, int, int]] = [
    (1, "Numerical linear algebra through eigenvalues / SVD",  1, 20),
    (2, "Iterative methods + nonlinear optimization",         21, 37),
]

# Topic modules: (title, [(lec_lo, lec_hi, ag_ref, optional_lecture_url_for_block)]).
# Each tuple inside the list is one note item; lec_lo == lec_hi means a single lecture.
TOPIC_MODULES: list[tuple[str, list[tuple[int, int, str, str]]]] = [
    (
        "Background & error analysis",
        [
            (1, 1, "Introduction (Trefethen, *The definition of numerical analysis*)", LECTURE_REFS[1]),
            (2, 3, "Linear algebra background (AG ch 4)", ""),
            (4, 4, "Numerical algorithms and error (AG ch 1)", ""),
            (5, 5, "Sensitivity and conditioning (AG ch 1-2)", ""),
            (6, 7, "Floating point (AG ch 2)", ""),
        ],
    ),
    (
        "Direct linear solvers",
        [
            (8, 9, "LU, pivoting; LU & Cholesky (AG §5.1-5.3)", ""),
            (10, 10, "LU with complete pivoting and Cholesky (AG §5.3, 5.5)", ""),
            (11, 11, "Sparse matrices (AG §5.6-5.7)", ""),
        ],
    ),
    (
        "Least squares & QR",
        [
            (12, 12, "Least squares and QR factorizations (AG §6.1-6.2)", ""),
            (13, 14, "QR factorization (AG §6.3)", ""),
            (15, 15, "Ill-posedness and regularization (AG §8.2)", ""),
        ],
    ),
    (
        "Eigenvalue problems",
        [
            (16, 16, "Intro to eigenvalue problems · perturbation handout (AG §8.1)", LECTURE_REFS[16]),
            (17, 17, "Power and subspace iteration (AG §8.1)", ""),
            (18, 18, "Orthogonal iteration (AG §8.3)", ""),
            (19, 20, "QR algorithm and SVD (AG §8.3)", ""),
        ],
    ),
    (
        "Iterative methods",
        [
            (21, 21, "Classical iterations (AG §7.2-7.3)", ""),
            (22, 23, "Krylov subspace methods (AG §7.4-7.5)", ""),
            (24, 24, "Krylov subspace methods: preconditioning (AG §7.4-7.5)", ""),
        ],
    ),
    (
        "Nonlinear systems & optimization",
        [
            (25, 25, "Nonlinear equations and optimization (AG §9.1)", ""),
            (26, 26, "Intro to optimization (AG §9.2)", ""),
            (27, 27, "Search direction methods: gradient descent and Newton (AG §9.2)", ""),
            (28, 28, "Line search (AG §9.2)", ""),
            (29, 29, "Quasi-Newton methods (AG §9.2)", ""),
            (30, 31, "BFGS and practical tips (AG §9.2)", ""),
            (32, 32, "Gauss-Newton (AG §9.2)", ""),
            (33, 33, "Iteratively reweighted least squares (AG §9.2)", ""),
            (34, 37, "Constraints (AG §9.3)", ""),
        ],
    ),
    (
        "Advanced topics",
        [
            (38, 38, "Stochastic optimization (Recht & Wright, *Optimization for Machine Learning*)", LECTURE_REFS[38]),
            (39, 41, "Randomized numerical linear algebra (Halko, Martinsson, Tropp 2011)", LECTURE_REFS[39]),
        ],
    ),
]

SYLLABUS_MD = """## Prerequisites
Linear algebra (MIT 18.06 or equivalent), single-variable & multivariable calculus,
basic programming (Julia or Python preferred). Some exposure to numerical methods
helps but isn't required.

## Textbook
**Ascher & Greif, *A First Course in Numerical Methods* (SIAM, 2011).** Cited
throughout as "AG: §X.Y". Available through SIAM via a Cornell subscription
(your access may vary).

## Grading (self-study)
| Component | Weight |
|---|---|
| Homework (6 problem sets) | 60% |
| Projects (2 open-ended) | 40% |

Bindel's original course splits the grade across HW (30%) / Projects (30%) /
take-home midterm (20%) / take-home final (20%), but the exam papers are not
posted publicly — they're distributed via Gradescope. Rather than carry
ungradable phantom assignments, this self-study version drops the exams and
renormalizes the remaining weights.

## Homework policy
Six problem sets, due roughly every two to three weeks. The original policy
allows discussion but requires independent write-ups. For self-study, write up
your own solutions; the AI generates a reference key after you submit.

## Project policy
Two open-ended projects. Pick a direction, work it deeply, and submit a
writeup + code. The AI grades these in **project mode** — it evaluates the
depth, clarity, and effort of your writeup rather than comparing to a
reference solution.
"""

HOME_MD = """**Cornell CS 4220 / MATH 4260 — Numerical Analysis: Linear and
Nonlinear Problems.** Course materials from David Bindel's Cornell page
(Spring 2024 offering). The term shown above is *your* self-study term — edit
it from the course settings when you've picked one.

This course covers numerical linear algebra (LU, QR, eigenvalues, SVD,
iterative methods) and nonlinear optimization (Newton, BFGS, Gauss-Newton,
constraints, stochastic optimization, randomized NLA). Two open-ended projects
plus six problem sets.

Prerequisites: linear algebra (18.06 / equivalent), calculus, basic
programming. Jump to **Syllabus**, **Modules**, or **Assignments**.
"""

DESCRIPTION = (
    "Numerical linear algebra (LU, Cholesky, QR, eigenvalues, SVD, iterative "
    "Krylov methods) and nonlinear optimization (gradient descent, Newton, "
    "quasi-Newton/BFGS, Gauss-Newton, IRLS, constraints, stochastic and "
    "randomized methods)."
)

TEXTBOOK = (
    "Ascher & Greif, *A First Course in Numerical Methods* (SIAM, 2011) — "
    "primary reference (cited as 'AG: §X.Y')."
)


def _hw_description(n: int, topic: str) -> str:
    parts = [
        f"Homework {n} ({topic}). Source PDF: [hw{n}.pdf]({_hw_url(n)}).",
    ]
    if n in HW_DATA_URL:
        parts.append(f"Data: [hw{n}_data.zip]({HW_DATA_URL[n]}).")
    parts.append(
        "Discuss freely with peers; write up your own solutions. Upload your "
        "worked solutions; the AI generates a reference solution and grades "
        "against it."
    )
    return " ".join(parts)


def _project_description(n: int, topic: str) -> str:
    parts = [
        f"Project {n} ({topic}). Source PDF: [P{n}.pdf]({_proj_url(n)}).",
    ]
    if n in PROJ_DATA_URL:
        parts.append(f"Data: [P{n}data.zip]({PROJ_DATA_URL[n]}).")
    parts.append(
        "Open-ended: pick a direction, work it deeply, and submit a writeup + "
        "code. Graded in **project mode** — the AI evaluates depth, clarity, "
        "and effort. No reference solution is generated."
    )
    return " ".join(parts)


def _topic_module_items(blocks: list[tuple[int, int, str, str]]) -> list[dict]:
    items: list[dict] = []
    for lo, hi, ref_text, url in blocks:
        title = f"Lec {lo}" if lo == hi else f"Lec {lo}-{hi}"
        title = f"{title}: {ref_text}"
        item: dict = {"kind": "note", "title": title, "text_md": ref_text}
        if url:
            item["url"] = url
            item["kind"] = "link"
        items.append(item)
    return items


def _modules() -> list[tuple[str, list[dict]]]:
    out: list[tuple[str, list[dict]]] = [
        (
            "Direct links",
            [
                {"kind": "link", "title": "CS 4220 / MATH 4260 course home (Bindel, Spring 2024)", "url": HOME},
                {"kind": "link", "title": "Homework 1", "url": _hw_url(1)},
                {"kind": "link", "title": "Homework 2", "url": _hw_url(2)},
                {"kind": "link", "title": "Homework 3", "url": _hw_url(3)},
                {"kind": "link", "title": "Homework 4", "url": _hw_url(4)},
                {"kind": "link", "title": "Homework 5", "url": _hw_url(5)},
                {"kind": "link", "title": "Homework 6", "url": _hw_url(6)},
                {"kind": "link", "title": "Project 1", "url": _proj_url(1)},
                {"kind": "link", "title": "Project 2", "url": _proj_url(2)},
                {"kind": "link", "title": "Ascher & Greif (SIAM)", "url": ASCHER_GREIF_URL},
                {"kind": "link", "title": "David Bindel — Cornell faculty page", "url": BINDEL_HOME},
            ],
        ),
    ]
    for title, blocks in TOPIC_MODULES:
        out.append((title, _topic_module_items(blocks)))
    return out


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
        title="Numerical Analysis: Linear and Nonlinear Problems",
        institution="Cornell University",
        term_label="Spring 2030",
        instructor="Prof. David Bindel",
        external_home_url=HOME,
        status="planned",
        color="#B31B1B",  # Cornell Big Red
        display_order=5,
        textbook=TEXTBOOK,
        home_page_md=HOME_MD,
        syllabus_md=SYLLABUS_MD,
        description=DESCRIPTION,
    )
    db.add(course)
    db.flush()

    g_hw = AssignmentGroup(
        course_id=course.id, name="Homework", weight=60, drop_lowest_n=0, position=0
    )
    g_proj = AssignmentGroup(
        course_id=course.id, name="Projects", weight=40, drop_lowest_n=0, position=1
    )
    db.add_all([g_hw, g_proj])
    db.flush()

    for k, topic, lec_from, lec_to in HOMEWORKS:
        db.add(
            Assignment(
                course_id=course.id,
                assignment_group_id=g_hw.id,
                title=f"Homework {k}",
                description_md=_hw_description(k, topic),
                points_possible=100,
                accepts_files=True,
                accepts_text=True,
                position=k - 1,
                published=True,
                covers_lecture_from=lec_from,
                covers_lecture_to=lec_to,
                requires_solution_key=True,
            )
        )
    for k, topic, lec_from, lec_to in PROJECTS:
        db.add(
            Assignment(
                course_id=course.id,
                assignment_group_id=g_proj.id,
                title=f"Project {k}",
                description_md=_project_description(k, topic),
                points_possible=100,
                accepts_files=True,
                accepts_text=True,
                position=k - 1,
                published=True,
                covers_lecture_from=lec_from,
                covers_lecture_to=lec_to,
                requires_solution_key=False,
            )
        )
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
                    published=True,
                )
            )
    db.commit()
    db.refresh(course)
    return course


# Module-item titles whose URL is fixed (not parameterized by HW/Project number).
_FIXED_ITEM_URLS: dict[str, str] = {
    "CS 4220 / MATH 4260 course home (Bindel, Spring 2024)": HOME,
    "Ascher & Greif (SIAM)": ASCHER_GREIF_URL,
    "David Bindel — Cornell faculty page": BINDEL_HOME,
}

_HW_TITLE_RE = re.compile(r"^Homework (\d+)$")
_PROJ_TITLE_RE = re.compile(r"^Project (\d+)$")
_HW_LINK_TITLE_RE = re.compile(r"^Homework (\d+)$")
_PROJ_LINK_TITLE_RE = re.compile(r"^Project (\d+)$")


def update_urls(db: Session) -> dict:
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

    for m in course.modules:
        for it in m.items:
            counts["items_examined"] += 1
            new_url: str | None = None
            if it.title in _FIXED_ITEM_URLS:
                new_url = _FIXED_ITEM_URLS[it.title]
            else:
                mh = _HW_LINK_TITLE_RE.match(it.title or "")
                mp = _PROJ_LINK_TITLE_RE.match(it.title or "")
                if mh:
                    new_url = _hw_url(int(mh.group(1)))
                elif mp:
                    new_url = _proj_url(int(mp.group(1)))
            if new_url and new_url != it.external_url:
                it.external_url = new_url
                counts["items_updated"] += 1

    by_title = {a.title: a for a in course.assignments}
    for k, topic, lec_from, lec_to in HOMEWORKS:
        a = by_title.get(f"Homework {k}")
        if a is None:
            continue
        new_desc = _hw_description(k, topic)
        if a.description_md != new_desc:
            a.description_md = new_desc
            counts["assignments_updated"] += 1
        if a.covers_lecture_from != lec_from or a.covers_lecture_to != lec_to:
            a.covers_lecture_from = lec_from
            a.covers_lecture_to = lec_to
            counts["coverage_updated"] += 1
    for k, topic, lec_from, lec_to in PROJECTS:
        a = by_title.get(f"Project {k}")
        if a is None:
            continue
        new_desc = _project_description(k, topic)
        if a.description_md != new_desc:
            a.description_md = new_desc
            counts["assignments_updated"] += 1
        if a.covers_lecture_from != lec_from or a.covers_lecture_to != lec_to:
            a.covers_lecture_from = lec_from
            a.covers_lecture_to = lec_to
            counts["coverage_updated"] += 1

    db.commit()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the Cornell CS 4220 course.")
    parser.add_argument("--force", action="store_true", help="delete an existing Cornell CS 4220 course first")
    parser.add_argument("--update-urls", action="store_true", help="refresh URLs/descriptions in place (no deletions)")
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

- [ ] **Step 2: Lint the file** — `cd backend && uv run ruff check seed/seed_cornell_cs4220.py`. Expected: pass.

---

### Task 2: Write tests

**Files:**
- Create: `backend/tests/test_seed_cornell_cs4220.py`

- [ ] **Step 1: Write tests** covering meta, group weights, assignment counts/coverage, project-mode flag, modules shape (no video, no per-lecture link items in topic modules), idempotence, force-recreate, and `update_urls` idempotence.

```python
import pytest

import seed.seed_cornell_cs4220 as seed_mod
from app.models import Course
from seed.seed_cornell_cs4220 import (
    BASE,
    CODE,
    DESCRIPTION,
    HOME,
    HOME_MD,
    HOMEWORKS,
    HW_DATA_URL,
    PROJECTS,
    PROJ_DATA_URL,
    SYLLABUS_MD,
    TEXTBOOK,
    _hw_url,
    _modules,
    _proj_url,
    seed,
    update_urls,
)


def test_code_and_base():
    assert CODE == "Cornell CS 4220"
    assert BASE == "https://www.cs.cornell.edu/courses/cs4220/2024sp"
    assert HOME == BASE + "/"


def test_hw_and_proj_urls():
    assert _hw_url(1) == BASE + "/hw1.pdf"
    assert _hw_url(6) == BASE + "/hw6.pdf"
    assert _proj_url(1) == BASE + "/P1.pdf"
    assert _proj_url(2) == BASE + "/P2.pdf"
    assert HW_DATA_URL == {2: BASE + "/hw2_data.zip"}
    assert PROJ_DATA_URL == {1: BASE + "/P1data.zip"}


def test_homeworks_cover_1_to_42_no_gaps():
    nums = [k for (k, *_rest) in HOMEWORKS]
    assert nums == [1, 2, 3, 4, 5, 6]
    last_to = 0
    for k, _topic, lec_from, lec_to in HOMEWORKS:
        assert lec_from == last_to + 1, f"HW{k} from must follow previous to"
        assert lec_to >= lec_from
        last_to = lec_to
    assert last_to == 42


def test_projects_overlap_homework_ranges():
    nums = [k for (k, *_rest) in PROJECTS]
    assert nums == [1, 2]
    assert PROJECTS[0][2] == 1 and PROJECTS[0][3] == 20
    assert PROJECTS[1][2] == 21 and PROJECTS[1][3] == 37


def test_modules_shape():
    mods = _modules()
    titles = [m[0] for m in mods]
    assert titles == [
        "Direct links",
        "Background & error analysis",
        "Direct linear solvers",
        "Least squares & QR",
        "Eigenvalue problems",
        "Iterative methods",
        "Nonlinear systems & optimization",
        "Advanced topics",
    ]


def test_modules_no_video_items():
    """Per feedback-module-content-chapter-readings Rule 1: no video items in
    Modules; Bindel publishes no video anyway."""
    for _title, items in _modules():
        for it in items:
            assert it["kind"] != "video"


def test_modules_direct_links_lists_hw_and_projects():
    mods = dict(_modules())
    titles = [i["title"] for i in mods["Direct links"]]
    for n in (1, 2, 3, 4, 5, 6):
        assert f"Homework {n}" in titles
    for n in (1, 2):
        assert f"Project {n}" in titles
    assert "CS 4220 / MATH 4260 course home (Bindel, Spring 2024)" in titles


def test_syllabus_describes_self_study_split():
    assert "60%" in SYLLABUS_MD
    assert "40%" in SYLLABUS_MD
    # Self-study version drops the take-home midterm/final.
    assert "Gradescope" in SYLLABUS_MD or "exam" in SYLLABUS_MD.lower()
    # Project-mode policy is documented.
    assert "project mode" in SYLLABUS_MD.lower()


def test_home_md_mentions_bindel_and_self_study():
    assert "Bindel" in HOME_MD
    assert "self-study" in HOME_MD


def test_description_and_textbook_nonempty():
    assert "linear algebra" in DESCRIPTION.lower()
    assert "Ascher" in TEXTBOOK
    assert "Greif" in TEXTBOOK


def test_seed_creates_basic_shape(db):
    c = seed(db)
    assert c.code == CODE
    assert c.title == "Numerical Analysis: Linear and Nonlinear Problems"
    assert c.instructor == "Prof. David Bindel"
    assert c.institution == "Cornell University"
    assert c.term_label == "Spring 2030"
    assert c.color == "#B31B1B"
    assert c.display_order == 5
    assert c.status == "planned"
    assert c.external_home_url == HOME


def test_seed_groups_and_weights(db):
    c = seed(db)
    weights = {g.name: (float(g.weight), g.drop_lowest_n) for g in c.assignment_groups}
    assert weights["Homework"] == (60.0, 0)
    assert weights["Projects"] == (40.0, 0)
    assert sum(w for w, _ in weights.values()) == 100.0


def test_seed_assignment_counts(db):
    c = seed(db)
    n_assign = len(c.assignments)
    # 6 HWs + 2 Projects = 8 assignments
    assert n_assign == 8
    # 8 modules total
    assert len(c.modules) == 8


def test_seed_homework_coverage(db):
    c = seed(db)
    hws = sorted(
        (a for a in c.assignments if a.title.startswith("Homework")),
        key=lambda a: a.position,
    )
    assert len(hws) == 6
    assert all(a.requires_solution_key for a in hws)
    assert hws[0].covers_lecture_from == 1
    assert hws[0].covers_lecture_to == 7
    assert hws[-1].covers_lecture_from == 37
    assert hws[-1].covers_lecture_to == 42


def test_seed_projects_use_project_mode(db):
    c = seed(db)
    projs = sorted(
        (a for a in c.assignments if a.title.startswith("Project")),
        key=lambda a: a.position,
    )
    assert len(projs) == 2
    assert all(not a.requires_solution_key for a in projs)
    assert projs[0].covers_lecture_from == 1
    assert projs[0].covers_lecture_to == 20
    assert projs[1].covers_lecture_from == 21
    assert projs[1].covers_lecture_to == 37
    # Project descriptions must NOT promise a reference solution.
    for a in projs:
        assert "project mode" in a.description_md.lower()


def test_seed_module_items_no_video(db):
    c = seed(db)
    for m in c.modules:
        for it in m.items:
            assert it.kind != "video"


def test_seed_is_idempotent(db):
    c1 = seed(db)
    n1 = (len(c1.modules), len(c1.assignments))
    c2 = seed(db)
    assert c2.id == c1.id
    assert (len(c2.modules), len(c2.assignments)) == n1
    assert db.query(Course).filter(Course.code == CODE).count() == 1


def test_seed_force_recreates(db):
    seed(db)
    c = seed(db, force=True)
    assert db.query(Course).filter(Course.code == CODE).count() == 1
    assert len(c.assignments) == 8


def test_update_urls_idempotent(db):
    seed(db)
    counts1 = update_urls(db)
    counts2 = update_urls(db)
    assert counts1["course_found"] is True
    assert counts2["items_updated"] == 0
    assert counts2["assignments_updated"] == 0
    assert counts2["coverage_updated"] == 0


def test_update_urls_no_course():
    """Calling update_urls when nothing's been seeded must not crash; returns
    course_found=False."""
    from app.db import Base
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    S = sessionmaker(bind=engine, future=True)
    with S() as s:
        assert update_urls(s) == {"course_found": False}
```

- [ ] **Step 2: Run the test suite** — `cd backend && uv run pytest tests/test_seed_cornell_cs4220.py -q`. Expected: all pass.

- [ ] **Step 3: Run ruff on the whole project** — `cd backend && uv run ruff check .`. Expected: pass (no new violations).

- [ ] **Step 4: Run the full test suite** — `cd backend && uv run pytest -q`. Expected: all pass.

---

### Task 3: Commit + merge

- [ ] **Step 1: Stage + commit** the seed + test files.

```bash
git add backend/seed/seed_cornell_cs4220.py backend/tests/test_seed_cornell_cs4220.py docs/superpowers/plans/2026-05-16-cornell-cs4220-seed.md
git commit -m "feat(seed): add Cornell CS 4220 (Numerical Analysis) seed course"
```

- [ ] **Step 2: Inspect git status + check for merge conflicts against master.**

```bash
git status
git fetch origin
git log --oneline master..HEAD
git log --oneline HEAD..master  # should be empty if master hasn't moved
git merge-tree $(git merge-base HEAD master) HEAD master  # empty output = no conflicts
```

- [ ] **Step 3: Merge to master** via `--no-ff` (per project rule).

```bash
git switch master
git merge --no-ff feat/seed-cornell-cs4220 -m "Merge branch 'feat/seed-cornell-cs4220'"
git status  # verify clean
```

---

### Task 4: Update memory

- [ ] Update `study_sequencing_2027_2030.md` to mark CS 4220 as seeded (move from ⏳ pending to ✅ seeded list).
- [ ] Update `study_plan_jhu_replacement.md` to correct the "CS 4220 / MATH 4250" course-number conflation (the ODE half is CS 4210 / MATH 4250; CS 4220 / MATH 4260 is the NLA course we just seeded).
- [ ] Update `feedback_project_assignments_no_reference.md` — the feature IS implemented (migration 0006, `requires_solution_key` flag); remove the "currently NOT implemented" caveat.
