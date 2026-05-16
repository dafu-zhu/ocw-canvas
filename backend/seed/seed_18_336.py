"""Seed the MIT 18.336 — Numerical Methods for Partial Differential Equations
(Benjamin Seibold, Spring 2009).

Run:  cd backend && uv run python -m seed.seed_18_336 [--force] [--update-urls]
Source: https://ocw.mit.edu/courses/18-336-numerical-methods-for-partial-differential-equations-spring-2009/

Idempotent: existing course → no-op unless ``--force`` (which deletes + reseeds,
losing submissions / AI solutions / announcements on this course).

Pattern differences vs the 18.065 seed:
  - No videos. OCW does not publish recorded video lectures for this offering;
    per-lecture note items show topic + textbook reading only.
  - No solution PDFs. OCW publishes the 5 homework PDFs but no solutions, so
    PSets rely on AI-generated keys (requires_solution_key=True, default). No
    --refresh-solutions flag and no Storage uploads.
  - Multi-textbook readings. Each lecture's reading maps to chapters across
    7 different books (LeVeque '07, LeVeque '02, Trefethen, Evans, Strang,
    Fletcher, Canuto). The readings string is rendered verbatim per OCW's
    Readings table.
  - Course project replaces exams. Original course is graded 50% homework
    + 50% project, no exams. The project is one Assignment with
    requires_solution_key=False — AI grades on quality / depth / clarity
    (same mode as 18.065's Final Project). See feedback memory
    feedback-project-assignments-no-reference.
  - Lectures 8 (FFT guest by S. Johnson) and 26 (project presentations) have
    no lecture-note PDF. Lec 26 is dropped from Modules entirely (not a
    content lecture); Lec 8 stays but its note item omits the PDF link.
"""
from __future__ import annotations

import argparse
import re

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Assignment, AssignmentGroup, Course, Module, ModuleItem

CODE = "MIT 18.336"
BASE = (
    "https://ocw.mit.edu/courses/"
    "18-336-numerical-methods-for-partial-differential-equations-spring-2009"
)
HOME = BASE + "/"
SYLLABUS_URL = BASE + "/pages/syllabus/"
CALENDAR_URL = BASE + "/pages/calendar/"
READINGS_URL = BASE + "/pages/readings/"
LECTURE_NOTES_URL = BASE + "/pages/lecture-notes/"
ASSIGNMENTS_URL = BASE + "/pages/assignments/"
PROJECTS_URL = BASE + "/pages/projects/"
MATLAB_URL = BASE + "/pages/matlab/"


def _lec_url(n: int) -> str:
    """Per-lecture note PDF landing page. Slug stem is NOT zero-padded
    (mit18_336s09_lec1 .. mit18_336s09_lec25). Lec 8 and 26 have no PDF and
    callers must not invoke this for them."""
    return f"{BASE}/resources/mit18_336s09_lec{n}/"


def _hw_url(k: int) -> str:
    """Homework PDF landing page. Slug stem IS zero-padded (hw01..hw05)."""
    return f"{BASE}/resources/mit18_336s09_hw{k:02d}/"


# (lecture_number, topic, readings). Readings strings are rendered verbatim
# from OCW's /pages/readings/ table. Empty string means OCW lists no reading
# for that lecture (Lec 8 guest, Lec 20 operator splitting, Lec 25 particle
# methods). Lectures 21-22 reference instructor notes (not standard textbook
# chapters) and are rendered as such.
LECTURE_TOPICS: dict[int, tuple[str, str]] = {
    1:  ("Fundamental concepts and examples",         "Evans §§1.1, 1.2"),
    2:  ("Well-posedness; Fourier methods (IVPs)",    "Evans §1.3; Strang §6.1"),
    3:  ("Laplace and Poisson equation",              "Evans §2.2"),
    4:  ("Heat, transport, and wave equations",       "Evans §§2.1, 2.3–2.4"),
    5:  ("Finite differences; Poisson",               "LeVeque 2007 ch. 1, §§2.1–2.4, 2.12"),
    6:  ("Elliptic FD: stability, Lax equivalence",   "LeVeque 2007 §§2.5–2.9, 2.15 (rec. 2.17)"),
    7:  ("Spectral methods",                          "Trefethen ch. 1, 3"),
    8:  ("Fast Fourier transform (guest)",            ""),
    9:  ("Spectral methods (continued)",              "Trefethen ch. 6, 7, 8"),
    10: ("Elliptic equations and linear systems",     "LeVeque 2007 ch. 3"),
    11: ("Sparse linear systems: multigrid",          "LeVeque 2007 §§4.1–4.2, 4.6; Strang §7.1"),
    12: ("Sparse linear systems: Krylov methods",     "LeVeque 2007 §§4.3–4.4"),
    13: ("Ordinary differential equations",           "LeVeque 2007 §9.2, ch. 5"),
    14: ("ODE stability; von Neumann analysis",       "LeVeque 2007 ch. 7, §§9.6–9.7"),
    15: ("Advection equation; modified equation",     "LeVeque 2002 §§4.4–4.9, 8.6"),
    16: ("Advection equation: ENO / WENO",            "LeVeque 2002 §§6.1, 6.3, 6.7, 10.4"),
    17: ("Conservation laws: theory",                 "LeVeque 2002 ch. 11"),
    18: ("Conservation laws: numerical methods",      "LeVeque 2002 §§12.1–12.9 (+ 12.10–12.11)"),
    19: ("Conservation laws: high-resolution",        "LeVeque 2002 §12.12, §§6.4–6.12"),
    20: ("Operator splitting; fractional steps",      ""),
    21: ("Systems of IVPs: wave eq., leapfrog grids", "Instructor notes (wave eq.; PMLs)"),
    22: ("Level set method",                          "Instructor notes & presentation"),
    23: ("Navier–Stokes: finite-difference methods",  "Fletcher; Canuto"),
    24: ("Navier–Stokes: pseudospectral methods",     "Fletcher; Canuto"),
    25: ("Particle methods",                          ""),
    # Lec 26 (project presentations) intentionally absent — not a content lecture.
}

# Lectures whose note PDF is published on OCW. Verified via WebFetch
# 2026-05-16: every lecture 1–25 except 8 has a PDF; 26 (presentations) has
# nothing.
LECTURE_HAS_PDF: set[int] = {n for n in range(1, 26) if n != 8}


# 5 problem sets — (number, topic, covers_lecture_from, covers_lecture_to).
# OCW does not publish a HW → lecture-range mapping; the spans below are
# inferred from the natural HW boundaries (calendar order + which lectures
# the topics need). Adjust the constants and re-run --update-urls if the
# inference turns out wrong.
PROBLEM_SETS: list[tuple[int, str, int, int]] = [
    (1, "Foundations & finite differences",                1,  6),
    (2, "Spectral methods & FFT",                          7,  9),
    (3, "Linear solvers: multigrid & Krylov",             10, 12),
    (4, "Time-stepping & advection",                      13, 16),
    (5, "Conservation laws & beyond",                     17, 22),
]

PROJECT_COVERS_FROM = 1
PROJECT_COVERS_TO = 25


# Module unit definitions: (module_title, [lecture_numbers]).
UNITS: list[tuple[str, list[int]]] = [
    ("Unit I — Foundations (Lec 1–4)",                  [1, 2, 3, 4]),
    ("Unit II — Elliptic problems & solvers (Lec 5–12)", [5, 6, 7, 8, 9, 10, 11, 12]),
    ("Unit III — Time-dependent problems (Lec 13–22)",   [13, 14, 15, 16, 17, 18, 19, 20, 21, 22]),
    ("Unit IV — Applications (Lec 23–25)",              [23, 24, 25]),
]


SYLLABUS_MD = f"""## Prerequisites
18.330 (Introduction to Numerical Analysis) and 18.335J (Introduction to
Numerical Methods). Comfort with linear algebra, complex analysis basics,
ODEs, and at least one programming language (the original course expects
MATLAB; any scientific-computing language works for self-study).

## Textbooks
This course uses a working bibliography of seven references; readings
rotate across them by lecture. None is required end-to-end — each
lecture's Readings note in **Modules** cites the specific chapters.

- LeVeque, *Finite Difference Methods for ODE / PDE* (SIAM, 2007).
- LeVeque, *Finite Volume Methods for Hyperbolic Problems* (Cambridge, 2002).
- Trefethen, *Spectral Methods in MATLAB* (SIAM, 2000).
- Evans, *Partial Differential Equations* (AMS, 2nd ed. 2010).
- Strang, *Computational Science and Engineering* (Wellesley-Cambridge, 2007).
- Fletcher, *Computational Techniques for Fluid Dynamics*, vols. 1–2 (Springer, 1991).
- Canuto et al., *Spectral Methods: Fundamentals in Single Domains* (Springer, 2006).

## Grading (mirror OCW)
| Component | Weight |
|---|---|
| Homework (5 problem sets) | 50% |
| Course Project | 50% |

The original course had **no exams** — "Grading: 50% Homework, 50% Course
Project," per Seibold's syllabus. We mirror that exactly.

## Problem-set policy
OCW publishes the 5 homework PDFs but **does not publish solutions**. The
AI generates a reference solution on your first submission and grades
against it (same workflow as 18.065 / 18.700). Don't search the web for
solutions — let the AI key do its job.

## Course Project
The project replaces the exam half of the course. Original course structure:

- **Proposal** (project title, background, questions/goals, plan).
- **Midterm report** — 20% of the project grade.
- **Final report** — 60% of the project grade.
- **Presentation** — 20% of the project grade.

For self-study, submit a single combined writeup (proposal + final report +
code) once you've worked through the lectures. The AI grades in **project
mode** — no reference solution, evaluation is on the quality of the chosen
approach, depth of the analysis, clarity of the writeup, and overall
effort. OCW publishes 12 student-project abstracts from Spring 2009 on the
[Projects page]({PROJECTS_URL}) as inspiration; pick a direction that
genuinely interests you.
"""

HOME_MD = """**MIT 18.336 — Numerical Methods for Partial Differential Equations
(Seibold, Spring 2009).** The term shown above is *your* self-study term —
edit it from the course settings when your plan shifts.

The graduate numerical-PDE course at MIT. Covers the full pipeline from
foundational PDE theory (well-posedness, Fourier methods, Laplace / Poisson
/ heat / transport / wave equations) through finite differences for elliptic
problems, spectral methods (Fourier + Chebyshev) and the FFT, modern linear
solvers (multigrid + Krylov), ODE integrators with stability analysis, and
hyperbolic methods for advection and conservation laws (modified equation,
ENO / WENO, high-resolution schemes). The applications stretch — operator
splitting, wave equations with PML, level set methods, Navier–Stokes (FD +
pseudospectral), and particle methods — anchors the theory in real PDE
problems. Half the grade is a semester-long course project, which OCW
illustrates with 12 sample project abstracts.

Source: <https://ocw.mit.edu/courses/18-336-numerical-methods-for-partial-differential-equations-spring-2009/>.
The original Spring 2023 offering by Steven Johnson is **not on OCW** — this
is the only published 18.336 mirror. Jump to **Syllabus**, **Modules**, or
**Assignments**.
"""

DESCRIPTION = (
    "Graduate numerical PDEs: well-posedness and Fourier methods; finite "
    "differences for elliptic / parabolic / hyperbolic problems; spectral "
    "methods and the FFT; multigrid and Krylov solvers; ODE stability and "
    "von Neumann analysis; conservation laws (ENO / WENO, high-resolution "
    "schemes); operator splitting; wave equations with PML; level set "
    "methods; Navier–Stokes (FD + pseudospectral); particle methods."
)

TEXTBOOK = (
    "Multi-reference bibliography rotating by lecture: LeVeque (2007 FDM, "
    "2002 FVM); Trefethen (Spectral Methods in MATLAB); Evans (PDE); "
    "Strang (CSE); Fletcher (CFD vols. 1–2); Canuto (Spectral Methods)."
)


def _ps_description(k: int, topic: str, lec_from: int, lec_to: int) -> str:
    hw_url = _hw_url(k)
    return (
        f"Problem Set {k} ({topic}). Covers lectures {lec_from}–{lec_to}.\n\n"
        f"- Paper: [HW{k} PDF (landing page)]({hw_url})\n\n"
        "OCW does not publish solutions for these problem sets. Upload your "
        "worked solutions; the AI generates a reference key on the first "
        "grading attempt and grades against it. Don't search the web for "
        "solutions — let the AI key do its job."
    )


def _project_description() -> str:
    return (
        "Course Project (50% of grade). Replaces the exam half of the "
        "course. The original course structures the project as a proposal "
        "(project title, background, questions/goals, plan) → midterm "
        "report (20% of the project grade) → final report (60%) + "
        f"presentation (20%). OCW's [Projects page]({PROJECTS_URL}) lists "
        "12 student-project abstracts from Spring 2009 as inspiration "
        "(Poisson with variable coefficients, elastic waves, atmospheric "
        "dynamics, blood-flow simulation, glacial ice streams, etc.).\n\n"
        "For self-study, submit a single combined writeup (proposal + "
        "final report + code) when ready. The AI grades this in **project "
        "mode** — no reference solution, evaluation is on the quality of "
        "the chosen approach, depth of the analysis, clarity of the "
        "writeup, and overall effort."
    )


def _unit_items(lecture_numbers: list[int]) -> list[dict]:
    """One note item per lecture. Body shows the readings mapping (verbatim
    per OCW's Readings table) and a link to the lecture-note PDF when
    published. Omits the Readings line when OCW lists none, and omits the
    PDF link when the lecture has no PDF (Lec 8 guest)."""
    items: list[dict] = []
    for n in lecture_numbers:
        topic, readings = LECTURE_TOPICS[n]
        lines = [f"**{topic}**"]
        if readings:
            lines.append("")
            lines.append(f"Readings: {readings}")
        if n in LECTURE_HAS_PDF:
            lines.append("")
            lines.append(f"[Lecture notes PDF →]({_lec_url(n)})")
        items.append({
            "kind": "note",
            "title": f"Lec {n} — {topic}",
            "text_md": "\n".join(lines),
        })
    return items


def _direct_links_items() -> list[dict]:
    return [
        {
            "kind": "link",
            "title": "18.336 course home (Seibold, MIT OCW Spring 2009)",
            "url": HOME,
        },
        {"kind": "link", "title": "Syllabus", "url": SYLLABUS_URL},
        {"kind": "link", "title": "Calendar", "url": CALENDAR_URL},
        {
            "kind": "link",
            "title": "Readings (per-lecture chapter map)",
            "url": READINGS_URL,
        },
        {
            "kind": "link",
            "title": "Lecture notes (index of per-lecture PDFs)",
            "url": LECTURE_NOTES_URL,
        },
        {"kind": "link", "title": "Assignments page", "url": ASSIGNMENTS_URL},
        {
            "kind": "link",
            "title": "Projects page (description + 12 sample abstracts)",
            "url": PROJECTS_URL,
        },
        {"kind": "link", "title": "MATLAB files", "url": MATLAB_URL},
    ]


def _modules() -> list[tuple[str, list[dict]]]:
    """1 direct-links module + 4 unit modules + 1 Course-Project module = 6.

    No video items (this OCW offering has no recorded videos). Lec 26
    (project presentations) is not a content lecture and is not represented
    in any unit module — it would only be a placeholder pointing to
    student-project slides."""
    out: list[tuple[str, list[dict]]] = [
        ("Direct links", _direct_links_items()),
    ]
    for title, lecture_nums in UNITS:
        out.append((title, _unit_items(lecture_nums)))
    out.append(
        (
            "Course Project",
            [
                {
                    "kind": "link",
                    "title": "Projects page (description + 12 sample abstracts)",
                    "url": PROJECTS_URL,
                },
                {"kind": "assignment", "_assignment": "Course Project"},
            ],
        )
    )
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
        title="Numerical Methods for Partial Differential Equations",
        institution="Massachusetts Institute of Technology",
        # term_label is *your* self-study term, not OCW's recording year.
        term_label="Summer 2029",
        instructor="Dr. Benjamin Seibold",
        external_home_url=HOME,
        status="planned",
        color="#1E5A6F",  # dark teal — distinct from the existing palette
        display_order=5,
        textbook=TEXTBOOK,
        home_page_md=HOME_MD,
        syllabus_md=SYLLABUS_MD,
        description=DESCRIPTION,
    )
    db.add(course)
    db.flush()

    g_hw = AssignmentGroup(
        course_id=course.id, name="Homework", weight=50, drop_lowest_n=0, position=0
    )
    g_proj = AssignmentGroup(
        course_id=course.id, name="Course Project", weight=50, drop_lowest_n=0, position=1
    )
    db.add_all([g_hw, g_proj])
    db.flush()

    by_name: dict[str, Assignment] = {}
    for k, topic, lec_from, lec_to in PROBLEM_SETS:
        a = Assignment(
            course_id=course.id,
            assignment_group_id=g_hw.id,
            title=f"Problem Set {k} — {topic}",
            description_md=_ps_description(k, topic, lec_from, lec_to),
            points_possible=100,
            accepts_files=True,
            accepts_text=True,
            position=k - 1,
            published=True,
            covers_lecture_from=lec_from,
            covers_lecture_to=lec_to,
            requires_solution_key=True,
        )
        db.add(a)
        by_name[a.title] = a

    proj = Assignment(
        course_id=course.id,
        assignment_group_id=g_proj.id,
        title="Course Project",
        description_md=_project_description(),
        points_possible=100,
        accepts_files=True,
        accepts_text=True,
        # Project-style: AI grades on quality / depth / clarity / effort,
        # no reference solution. Mirrors 18.065's Final Project handling.
        requires_solution_key=False,
        position=0,
        published=True,
        covers_lecture_from=PROJECT_COVERS_FROM,
        covers_lecture_to=PROJECT_COVERS_TO,
    )
    db.add(proj)
    by_name["Course Project"] = proj
    db.flush()

    for mpos, (mtitle, items) in enumerate(_modules()):
        m = Module(course_id=course.id, title=mtitle, position=mpos, published=True)
        db.add(m)
        db.flush()
        for ipos, it in enumerate(items):
            kind = it["kind"]
            title = it.get("title", "")
            assignment_id = None
            if kind == "assignment":
                assignment_id = by_name[it["_assignment"]].id
                title = by_name[it["_assignment"]].title
            db.add(
                ModuleItem(
                    module_id=m.id,
                    position=ipos,
                    indent=it.get("indent", 0),
                    kind=kind,
                    title=title,
                    external_url=it.get("url", ""),
                    text_md=it.get("text_md", ""),
                    assignment_id=assignment_id,
                    published=True,
                )
            )
    db.commit()
    db.refresh(course)
    return course


# --------------------------------------------------------------------------- updater

# "Lec 12 — <topic>" — match per-lecture note items.
_LECTURE_NOTE_RE = re.compile(r"^Lec (\d+)\b")
# "Problem Set 3 — <topic>"
_PS_TITLE_RE = re.compile(r"^Problem Set (\d+)\b")

# Module-item titles whose URL is fixed.
_FIXED_TITLE_TO_URL: dict[str, str] = {
    "18.336 course home (Seibold, MIT OCW Spring 2009)": HOME,
    "Syllabus": SYLLABUS_URL,
    "Calendar": CALENDAR_URL,
    "Readings (per-lecture chapter map)": READINGS_URL,
    "Lecture notes (index of per-lecture PDFs)": LECTURE_NOTES_URL,
    "Assignments page": ASSIGNMENTS_URL,
    "Projects page (description + 12 sample abstracts)": PROJECTS_URL,
    "MATLAB files": MATLAB_URL,
}


def _note_text_for(n: int) -> str:
    topic, readings = LECTURE_TOPICS[n]
    lines = [f"**{topic}**"]
    if readings:
        lines.append("")
        lines.append(f"Readings: {readings}")
    if n in LECTURE_HAS_PDF:
        lines.append("")
        lines.append(f"[Lecture notes PDF →]({_lec_url(n)})")
    return "\n".join(lines)


def update_urls(db: Session) -> dict:
    """Refresh URLs and per-lecture note bodies on the live MIT 18.336 course
    in place — fixed module-item URLs, per-lecture note text, and assignment
    description_md / coverage. Preserves submissions / AI solutions /
    announcements / grades."""
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
            if it.title in _FIXED_TITLE_TO_URL:
                new_url = _FIXED_TITLE_TO_URL[it.title]
                if new_url != it.external_url:
                    it.external_url = new_url
                    counts["items_updated"] += 1
            ln = _LECTURE_NOTE_RE.match(it.title or "")
            if ln and it.kind == "note":
                n = int(ln.group(1))
                if n in LECTURE_TOPICS:
                    new_text = _note_text_for(n)
                    if it.text_md != new_text:
                        it.text_md = new_text
                        counts["items_updated"] += 1

    by_title = {a.title: a for a in course.assignments}
    for k, topic, lec_from, lec_to in PROBLEM_SETS:
        a = next(
            (
                x for t, x in by_title.items()
                if _PS_TITLE_RE.match(t) and t.startswith(f"Problem Set {k} ")
            ),
            None,
        )
        if a is None:
            continue
        new_desc = _ps_description(k, topic, lec_from, lec_to)
        if a.description_md != new_desc:
            a.description_md = new_desc
            counts["assignments_updated"] += 1
        if a.covers_lecture_from != lec_from or a.covers_lecture_to != lec_to:
            a.covers_lecture_from = lec_from
            a.covers_lecture_to = lec_to
            counts["coverage_updated"] += 1

    proj = by_title.get("Course Project")
    if proj is not None:
        new_desc = _project_description()
        if proj.description_md != new_desc:
            proj.description_md = new_desc
            counts["assignments_updated"] += 1
        if (
            proj.covers_lecture_from != PROJECT_COVERS_FROM
            or proj.covers_lecture_to != PROJECT_COVERS_TO
        ):
            proj.covers_lecture_from = PROJECT_COVERS_FROM
            proj.covers_lecture_to = PROJECT_COVERS_TO
            counts["coverage_updated"] += 1

    db.commit()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the MIT 18.336 course.")
    parser.add_argument(
        "--force", action="store_true", help="delete an existing MIT 18.336 course first"
    )
    parser.add_argument(
        "--update-urls",
        action="store_true",
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
