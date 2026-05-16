"""Seed the MIT 18.02SC — Multivariable Calculus course (Denis Auroux, Fall 2010).

Run:  cd backend && uv run python -m seed.seed_18_02sc \
        [--force] [--update-urls] [--refresh-solutions]
Source: https://ocw.mit.edu/courses/18-02sc-multivariable-calculus-fall-2010/

Idempotent: if a course with code "MIT 18.02SC" already exists this is a no-op,
unless ``--force`` (which deletes it first — the cascade on Course removes its
modules / assignment groups / assignments / announcements).

Pattern notes:
  - This is the first foundation-refresher seed; it predates the JHU-replacement
    sequence (per the user's study-plan memory) and is the "mid–late 2026"
    pre-job warm-up before MIT 18.700 (Axler).
  - 18.02SC is the OCW Scholar version: 4 units × 3 parts each → 12 problem sets
    (one per Part), 4 unit exams, and 1 final. OCW publishes Auroux's official
    solutions for every PSet and every exam.
  - Mirrors the **6.262 solution-PDF pipeline**: per assignment, scrape the OCW
    resource page for the PDF URL (content-hash-prefixed; not derivable from
    slug), upload to the ``solutions`` Supabase bucket under
    ``official/18_02sc/``, and set ``assignment.official_solution_file_path``.
  - URL pattern is identical to 6.262 — ``/resources/{slug}/`` resource pages —
    with slug stems ``mit18_02sc_pset{N}`` / ``mit18_02sc_pset{N}sol`` /
    ``mit18_02sc_exam{N}`` / ``mit18_02sc_exam{N}sol`` /
    ``mit18_02sc_finalexam`` / ``mit18_02sc_finalexamsol``.
  - Graceful degradation: if a PDF download/upload fails, the assignment keeps
    ``official_solution_url`` set; the AI grader falls back to URL-only mode.

Lecture / session numbering:
  - OCW Scholar organises by "session" (~100 across the course) rather than
    classroom "lecture". For ``covers_lecture_from/to`` we use the underlying
    standard-18.02 lecture count (~36 across a semester), partitioned as
    3 lectures per Part. The schedule-modal cadence operates on these. The
    session-level granularity is preserved in module-item titles.
"""
from __future__ import annotations

import argparse
import re
from urllib.parse import urljoin

import httpx
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Assignment, AssignmentGroup, Course, Module, ModuleItem
from app.services import storage

CODE = "MIT 18.02SC"
BASE = (
    "https://ocw.mit.edu/courses/"
    "18-02sc-multivariable-calculus-fall-2010"
)
HOME = BASE + "/"
SYLLABUS_URL = BASE + "/pages/syllabus/"
DOWNLOAD_URL = BASE + "/download"

# Unit landing-page URLs (4 units). Each unit has 3 Parts and one unit exam.
UNIT_PAGE_URL: dict[int, str] = {
    1: BASE + "/pages/1.-vectors-and-matrices/",
    2: BASE + "/pages/2.-partial-derivatives/",
    3: BASE + "/pages/3.-double-integrals-and-line-integrals-in-the-plane/",
    4: BASE + "/pages/4.-triple-integrals-and-surface-integrals-in-3-space/",
}

# Per-Unit Part slugs — used to build the OCW pages/<unit>/<part>/ URLs.
PART_SLUGS: dict[tuple[int, str], str] = {
    (1, "A"): "part-a-vectors-determinants-and-planes",
    (1, "B"): "part-b-matrices-and-systems-of-equations",
    (1, "C"): "part-c-parametric-equations-for-curves",
    (2, "A"): "part-a-functions-of-two-variables-tangent-approximation-and-optimization",
    (2, "B"): "part-b-chain-rule-gradient-and-directional-derivatives",
    (2, "C"): "part-c-lagrange-multipliers-and-constrained-differentials",
    (3, "A"): "part-a-double-integrals",
    (3, "B"): "part-b-vector-fields-and-line-integrals",
    (3, "C"): "part-c-greens-theorem",
    (4, "A"): "part-a-triple-integrals",
    (4, "B"): "part-b-flux-and-the-divergence-theorem",
    (4, "C"): "part-c-line-integrals-and-stokes-theorem",
}

# Unit titles, used in module headers and assignment descriptions.
UNIT_TITLE: dict[int, str] = {
    1: "Vectors and Matrices",
    2: "Partial Derivatives",
    3: "Double Integrals and Line Integrals in the Plane",
    4: "Triple Integrals and Surface Integrals in 3-Space",
}

# Slug for the unit-4 "Physics Applications" sub-page (no analogue in other units).
PHYSICS_APPS_URL = UNIT_PAGE_URL[4] + "physics-applications/"

# Final-exam landing pages.
FINAL_LANDING_URL = BASE + "/pages/final-exam-1/"
PRACTICE_FINAL_URL = FINAL_LANDING_URL + "practice-final-exam/"
FINAL_REVIEW_URL = FINAL_LANDING_URL + "review/"
FINAL_EXAM_PAGE_URL = FINAL_LANDING_URL + "final-exam/"


def _part_url(unit: int, part: str) -> str:
    return UNIT_PAGE_URL[unit] + PART_SLUGS[(unit, part)] + "/"


def _exam_page_url(unit: int) -> str:
    return UNIT_PAGE_URL[unit] + f"exam-{unit}/"


def _ps_page_url(n: int) -> str:
    """Page URL for the problem-set landing (where OCW shows paper + solution).

    Derived from the canonical (unit, part) for this PSet — PS1=1A, PS2=1B,
    PS3=1C, PS4=2A, … PS12=4C.
    """
    unit = (n - 1) // 3 + 1
    part = "ABC"[(n - 1) % 3]
    return _part_url(unit, part) + f"problem-set-{n}/"


# Resource slugs — used to scrape PDF URLs and namespace Storage paths.
def _ps_slug(n: int) -> str:
    return f"mit18_02sc_pset{n}"


def _ps_sol_slug(n: int) -> str:
    return f"mit18_02sc_pset{n}sol"


def _exam_slug(n: int) -> str:
    return f"mit18_02sc_exam{n}"


def _exam_sol_slug(n: int) -> str:
    return f"mit18_02sc_exam{n}sol"


FINAL_SLUG = "mit18_02sc_finalexam"
FINAL_SOL_SLUG = "mit18_02sc_finalexamsol"


# Resource-page URLs (the landing for each PDF; the content-hashed PDF URL
# itself is discovered by scraping).
def _res_url(slug: str) -> str:
    return f"{BASE}/resources/{slug}/"


_PDF_HREF_RE = re.compile(r'href="(/courses/[^"]+\.pdf)"')


def _resolve_pdf_url(slug: str) -> str:
    """Scrape ``BASE/resources/{slug}/`` for the PDF URL matching this slug.

    OCW renders PDFs with a content-hash-prefixed href (e.g.
    ``/courses/.../c12643..._MIT18_02SC_pset1sol.pdf``). The hash is not
    derivable from the slug, so we scrape the landing page and pick the PDF
    whose filename embeds the slug stem (case-insensitive).

    Raises ``RuntimeError`` if no PDF matches.
    """
    page_url = _res_url(slug)
    resp = httpx.get(page_url, timeout=30)
    resp.raise_for_status()
    needle = slug.lower()
    for path in _PDF_HREF_RE.findall(resp.text):
        if needle in path.lower():
            return urljoin("https://ocw.mit.edu", path)
    raise RuntimeError(f"no PDF link matching slug '{slug}' on {page_url}")


def _storage_key_for(slug: str) -> str:
    """Path inside the ``solutions`` bucket. Namespaced under ``official/18_02sc/``
    so it doesn't collide with AI-generated solutions (``solutions/{id}.md``)."""
    return f"official/18_02sc/{slug}.pdf"


def _attach_official_solution(db: Session, a: Assignment, slug: str) -> None:
    """Download Auroux's solution PDF for ``slug`` and attach it to ``a``.

    Sets ``a.official_solution_file_path`` to the Storage key on success;
    ``a.official_solution_url`` stays empty so the AI grader resolves to the
    'official_file' branch and reads the PDF. On download/upload failure,
    falls back to setting ``official_solution_url`` only.

    Idempotent: if the assignment already points at a readable Storage object,
    skip.
    """
    storage_key = _storage_key_for(slug)
    landing_url = _res_url(slug)

    if a.official_solution_file_path == storage_key:
        try:
            storage.read_bytes("solutions", storage_key)
            return
        except Exception:  # noqa: BLE001
            pass

    try:
        pdf_url = _resolve_pdf_url(slug)
        resp = httpx.get(pdf_url, timeout=60)
        resp.raise_for_status()
        storage.upload_bytes("solutions", storage_key, resp.content, "application/pdf")
        a.official_solution_file_path = storage_key
        a.official_solution_url = ""
    except Exception as exc:  # noqa: BLE001
        a.official_solution_url = landing_url
        print(f"warn(seed_18_02sc): solution upload failed for {slug}: {exc}")


# 12 problem sets — (number, unit, part_letter, topic, covers_lec_from, covers_lec_to).
# Lecture ranges follow standard 18.02 semester (~36 lectures, ~3 per Part). Schedule
# modal uses these for cadence.
PROBLEM_SETS: list[tuple[int, int, str, str, int, int]] = [
    (1,  1, "A", "Vectors, determinants and planes",                       1,  3),
    (2,  1, "B", "Matrices and systems of equations",                      4,  6),
    (3,  1, "C", "Parametric equations for curves",                        7,  9),
    (4,  2, "A", "Functions of two variables; tangent approx; optimization", 10, 12),
    (5,  2, "B", "Chain rule, gradient, directional derivatives",         13, 15),
    (6,  2, "C", "Lagrange multipliers; constrained differentials",       16, 18),
    (7,  3, "A", "Double integrals",                                       19, 21),
    (8,  3, "B", "Vector fields and line integrals",                       22, 24),
    (9,  3, "C", "Green's theorem",                                        25, 27),
    (10, 4, "A", "Triple integrals",                                       28, 30),
    (11, 4, "B", "Flux and the divergence theorem",                        31, 33),
    (12, 4, "C", "Line integrals and Stokes' theorem",                     34, 36),
]


# 4 unit exams — (unit_number, covers_lec_from, covers_lec_to).
UNIT_EXAMS: list[tuple[int, int, int]] = [
    (1, 1, 9),
    (2, 10, 18),
    (3, 19, 27),
    (4, 28, 36),
]


# Final exam coverage (cumulative).
FINAL_COVERS_FROM = 1
FINAL_COVERS_TO = 36


def _ps_description(n: int, unit: int, part: str, topic: str, lec_from: int, lec_to: int) -> str:
    paper_url = _res_url(_ps_slug(n))
    sol_url = _res_url(_ps_sol_slug(n))
    page_url = _ps_page_url(n)
    return (
        f"Problem Set {n} — {topic} (Unit {unit}, Part {part}). "
        f"Covers lectures {lec_from}–{lec_to}.\n\n"
        f"- Problem-set page: [{page_url}]({page_url})\n"
        f"- Paper PDF: [PS{n} (OCW resource)]({paper_url})\n"
        f"- Reference solution: [PS{n} Solutions]({sol_url})\n\n"
        "Upload your worked solutions. The AI grades against Auroux's official "
        "solution (loaded from Storage). OCW publishes the public solution PDF "
        "at the link above; if the seed couldn't download it, the AI grader "
        "falls back to URL-only awareness ('an official solution exists at "
        "<url>; grade against standard rigor')."
    )


def _exam_description(unit: int, lec_from: int, lec_to: int) -> str:
    paper_url = _res_url(_exam_slug(unit))
    sol_url = _res_url(_exam_sol_slug(unit))
    page_url = _exam_page_url(unit)
    title = UNIT_TITLE[unit]
    return (
        f"Unit {unit} Exam — {title}. Closed-book exam covering lectures "
        f"{lec_from}–{lec_to}.\n\n"
        f"- Exam page (with review sessions): [{page_url}]({page_url})\n"
        f"- Paper PDF: [Exam {unit} (OCW resource)]({paper_url})\n"
        f"- Reference solution: [Exam {unit} Solutions]({sol_url})\n\n"
        "Time yourself (the original course allotted 50 minutes per unit exam). "
        "Upload your attempt; the AI grades against Auroux's solution. OCW "
        "also publishes review-of-topics and review-of-problems sessions on "
        "the exam page above — they're additional self-paced practice, not "
        "graded here."
    )


def _final_description() -> str:
    paper_url = _res_url(FINAL_SLUG)
    sol_url = _res_url(FINAL_SOL_SLUG)
    return (
        f"Final Exam — cumulative, covers lectures {FINAL_COVERS_FROM}–{FINAL_COVERS_TO}.\n\n"
        f"- Final-exam page: [{FINAL_EXAM_PAGE_URL}]({FINAL_EXAM_PAGE_URL})\n"
        f"- Paper PDF: [Final Exam (OCW resource)]({paper_url})\n"
        f"- Reference solution: [Final Solutions]({sol_url})\n"
        f"- Practice final: [{PRACTICE_FINAL_URL}]({PRACTICE_FINAL_URL})\n"
        f"- Review materials: [{FINAL_REVIEW_URL}]({FINAL_REVIEW_URL})\n\n"
        "Time yourself (3 hours, matching the original course). Upload your "
        "attempt; the AI grades against Auroux's solution. The practice final "
        "and review pages above are *not* graded — they're for self-paced "
        "preparation."
    )


# --------------------------------------------------------------------------- modules

def _direct_links_items() -> list[dict]:
    return [
        {"kind": "link", "title": "18.02SC course home (Auroux, MIT OCW Fall 2010)", "url": HOME},
        {"kind": "link", "title": "Syllabus", "url": SYLLABUS_URL},
        {"kind": "link", "title": "Download full course package", "url": DOWNLOAD_URL},
    ]


def _unit_items(unit: int) -> list[dict]:
    """Module items for one Unit: the unit landing page + Parts A/B/C +
    (Unit 4 only) the Physics Applications page."""
    title = UNIT_TITLE[unit]
    items: list[dict] = [
        {"kind": "link", "title": f"Unit {unit} overview — {title}", "url": UNIT_PAGE_URL[unit]},
    ]
    for part in ("A", "B", "C"):
        items.append(
            {
                "kind": "link",
                "title": f"Part {part}",
                "url": _part_url(unit, part),
                "indent": 1,
            }
        )
    items.append(
        {
            "kind": "link",
            "title": f"Exam {unit} page (review sessions + paper)",
            "url": _exam_page_url(unit),
            "indent": 1,
        }
    )
    if unit == 4:
        items.append(
            {
                "kind": "link",
                "title": "Physics Applications (supplementary)",
                "url": PHYSICS_APPS_URL,
                "indent": 1,
            }
        )
    return items


def _final_review_items() -> list[dict]:
    return [
        {"kind": "link", "title": "Final Exam page", "url": FINAL_LANDING_URL},
        {"kind": "link", "title": "Practice Final Exam", "url": PRACTICE_FINAL_URL, "indent": 1},
        {"kind": "link", "title": "Final Review materials", "url": FINAL_REVIEW_URL, "indent": 1},
    ]


def _modules() -> list[tuple[str, list[dict]]]:
    """Six modules:
      0. Direct links (course home, syllabus, full-course download).
      1–4. One module per Unit, with Parts A/B/C and the unit-exam page.
      5. Final Exam — practice + review (the graded final is an Assignment).

    Per ``feedback-module-content-chapter-readings`` memory: module items link
    to OCW landing pages (not embedded videos and not per-session items). The
    graded exams + PSets live as Assignments, not module items.
    """
    return [
        ("Direct links", _direct_links_items()),
        (f"Unit 1 — {UNIT_TITLE[1]}", _unit_items(1)),
        (f"Unit 2 — {UNIT_TITLE[2]}", _unit_items(2)),
        (f"Unit 3 — {UNIT_TITLE[3]}", _unit_items(3)),
        (f"Unit 4 — {UNIT_TITLE[4]}", _unit_items(4)),
        ("Final Exam — review & practice", _final_review_items()),
    ]


# --------------------------------------------------------------------------- prose

SYLLABUS_MD = """## Prerequisites
Single-variable calculus (MIT 18.01 or equivalent). Comfort with derivatives,
integrals, sequences, and elementary linear algebra (vectors / dot product /
determinants) is helpful but the course re-introduces matrices in Unit 1.

## Textbook
**None required.** From the OCW syllabus: "This OCW Scholar course is
self-contained and no textbook is required." Lecture notes, video lectures,
recitations, problem sets, exams, and solutions are all published on OCW.

If you want a printed companion, *Vector Calculus* by Marsden & Tromba (W. H.
Freeman, 6th ed.) or Edwards & Penney's *Multivariable Calculus* both cover
this material at the same level.

## Grading
| Component | Weight |
|---|---|
| Problem sets (12, one per Part — drop lowest 1) | 40% |
| Unit exams (4) | 30% |
| Final exam | 30% |

OCW publishes no official grading breakdown for the Scholar version of 18.02SC
(the page contains assessments and solutions but no weighting). The breakdown
above is a sensible self-study default; edit the assignment-group weights in
the teacher-mode UI if you prefer a different split.

OCW publishes Auroux's official solutions for every problem set and every
exam — the seed downloads each PDF and uploads it to Supabase Storage, and
the AI grader compares your work to the real reference rather than a
regenerated AI key.

## Problem-set policy
The OCW Scholar problem sets are "carefully selected from a longer list of
questions". Each Part also publishes a *Supplemental Problems* PDF with its
own solutions — those are extra practice, not graded here. For self-study:
pick a weekly cadence (the schedule modal will set due dates), make an honest
attempt before opening the solution.

## Exams
Four unit exams + one cumulative final. Each unit exam is paired with two
"review" sessions on the same OCW page — they walk through topics and
worked problems; treat them as study aids, not graded material. Time
yourself on the actual exam paper.
"""

HOME_MD = """**MIT 18.02SC — Multivariable Calculus (Auroux, Fall 2010, OCW Scholar).**

Course materials mirrored from MIT OCW. The term shown above is *your*
self-study term — edit it from the course settings when your plan shifts.

The standard MIT multivariable-calculus course, re-cut by OCW as a self-paced
"Scholar" offering: full lecture videos, recitation videos with worked
examples, lecture notes, 12 problem sets with solutions, 4 unit exams + a
final (all with solutions), and Mathlets for interactive exploration.
Self-contained — no required textbook.

Source: <https://ocw.mit.edu/courses/18-02sc-multivariable-calculus-fall-2010/>.
Foundation refresher before MIT 18.700 (Axler linear algebra) and the rest
of the JHU-replacement sequence — covers the vector calculus you'll lean on
for 18.336 numerical PDEs and any continuous-state stochastic-control work.
Jump to **Syllabus**, **Modules**, or **Assignments**.
"""

DESCRIPTION = (
    "Differential, integral and vector calculus for functions of more than one "
    "variable: vectors, matrices and parametric curves; partial derivatives, "
    "tangent approximations, gradient and Lagrange multipliers; double and "
    "triple integrals; line and surface integrals; Green's, divergence and "
    "Stokes' theorems."
)

TEXTBOOK = (
    "None required — OCW Scholar 18.02SC is self-contained. Notes, video "
    "lectures, recitations, problem sets, and exams are all on OCW. "
    "Optional printed companion: Marsden & Tromba, *Vector Calculus* (W. H. "
    "Freeman, 6e), or Edwards & Penney's *Multivariable Calculus*."
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
        title="Multivariable Calculus",
        institution="Massachusetts Institute of Technology",
        # term_label is *your* self-study term, not the OCW recording year.
        # Mid–late 2026 foundation refresher per study-sequencing memory.
        term_label="Fall 2026",
        instructor="Prof. Denis Auroux",
        external_home_url=HOME,
        status="planned",
        color="#8B5A2B",  # sienna — distinct from cardinal/teal/navy/purple/green
        display_order=_next_display_order(db),
        textbook=TEXTBOOK,
        home_page_md=HOME_MD,
        syllabus_md=SYLLABUS_MD,
        description=DESCRIPTION,
    )
    db.add(course)
    db.flush()

    g_ps = AssignmentGroup(
        course_id=course.id, name="Problem Sets", weight=40, drop_lowest_n=1, position=0
    )
    g_unit = AssignmentGroup(
        course_id=course.id, name="Unit Exams", weight=30, drop_lowest_n=0, position=1
    )
    g_final = AssignmentGroup(
        course_id=course.id, name="Final Exam", weight=30, drop_lowest_n=0, position=2
    )
    db.add_all([g_ps, g_unit, g_final])
    db.flush()

    # 12 PSets with official solution PDFs.
    for n, unit, part, topic, lec_from, lec_to in PROBLEM_SETS:
        a = Assignment(
            course_id=course.id,
            assignment_group_id=g_ps.id,
            title=f"Problem Set {n} — {topic}",
            description_md=_ps_description(n, unit, part, topic, lec_from, lec_to),
            points_possible=100,
            accepts_files=True,
            accepts_text=True,
            position=n - 1,
            published=True,
            covers_lecture_from=lec_from,
            covers_lecture_to=lec_to,
            requires_solution_key=True,
        )
        db.add(a)
        db.flush()
        _attach_official_solution(db, a, _ps_sol_slug(n))

    # 4 unit exams.
    for unit, lec_from, lec_to in UNIT_EXAMS:
        a = Assignment(
            course_id=course.id,
            assignment_group_id=g_unit.id,
            title=f"Unit {unit} Exam — {UNIT_TITLE[unit]}",
            description_md=_exam_description(unit, lec_from, lec_to),
            points_possible=100,
            accepts_files=True,
            accepts_text=True,
            position=unit - 1,
            published=True,
            covers_lecture_from=lec_from,
            covers_lecture_to=lec_to,
            requires_solution_key=True,
        )
        db.add(a)
        db.flush()
        _attach_official_solution(db, a, _exam_sol_slug(unit))

    # Final exam.
    a = Assignment(
        course_id=course.id,
        assignment_group_id=g_final.id,
        title="Final Exam",
        description_md=_final_description(),
        points_possible=100,
        accepts_files=True,
        accepts_text=True,
        position=0,
        published=True,
        covers_lecture_from=FINAL_COVERS_FROM,
        covers_lecture_to=FINAL_COVERS_TO,
        requires_solution_key=True,
    )
    db.add(a)
    db.flush()
    _attach_official_solution(db, a, FINAL_SOL_SLUG)

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


# --------------------------------------------------------------------------- updater

_PS_TITLE_RE = re.compile(r"^Problem Set (\d+)\b")
_UNIT_EXAM_TITLE_RE = re.compile(r"^Unit (\d+) Exam\b")


def _fixed_title_to_url() -> dict[str, str]:
    """Map a module-item title to the URL it should always point to."""
    out: dict[str, str] = {
        "18.02SC course home (Auroux, MIT OCW Fall 2010)": HOME,
        "Syllabus": SYLLABUS_URL,
        "Download full course package": DOWNLOAD_URL,
        "Final Exam page": FINAL_LANDING_URL,
        "Practice Final Exam": PRACTICE_FINAL_URL,
        "Final Review materials": FINAL_REVIEW_URL,
        "Physics Applications (supplementary)": PHYSICS_APPS_URL,
    }
    for unit, title in UNIT_TITLE.items():
        out[f"Unit {unit} overview — {title}"] = UNIT_PAGE_URL[unit]
        out[f"Exam {unit} page (review sessions + paper)"] = _exam_page_url(unit)
    return out


def update_urls(db: Session) -> dict:
    """Refresh URLs / descriptions / coverage on the live MIT 18.02SC course.

    Mirrors 6.262's update_urls semantics. Does NOT touch term_label or
    home_page_md (user-customised), does NOT re-download PDFs (use
    ``--refresh-solutions`` for that), does NOT touch submissions / AI
    solutions / announcements.

    Quirk: module items titled "Part A" / "Part B" / "Part C" appear in every
    Unit module, so they're identified by their parent module's title +
    item-title pair rather than the global title-to-URL map.
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

    # Module-item external URLs.
    for m in course.modules:
        unit_match = re.match(r"^Unit (\d+) ", m.title)
        unit_for_module = int(unit_match.group(1)) if unit_match else None
        for it in m.items:
            counts["items_examined"] += 1
            new_url: str | None = None
            if it.title in fixed:
                new_url = fixed[it.title]
            elif unit_for_module is not None and it.title in ("Part A", "Part B", "Part C"):
                new_url = _part_url(unit_for_module, it.title[-1])
            if new_url is not None and new_url != it.external_url:
                it.external_url = new_url
                counts["items_updated"] += 1

    # Assignments: refresh description_md, coverage, official_solution_url.
    dirty_assignments: set[str] = set()
    by_title = {a.title: a for a in course.assignments}

    for n, unit, part, topic, lec_from, lec_to in PROBLEM_SETS:
        a = next(
            (x for t, x in by_title.items() if t.startswith(f"Problem Set {n} ")),
            None,
        )
        if a is None:
            continue
        new_desc = _ps_description(n, unit, part, topic, lec_from, lec_to)
        if a.description_md != new_desc:
            a.description_md = new_desc
            dirty_assignments.add(a.id)
        if a.covers_lecture_from != lec_from or a.covers_lecture_to != lec_to:
            a.covers_lecture_from = lec_from
            a.covers_lecture_to = lec_to
            counts["coverage_updated"] += 1
        if not a.official_solution_file_path:
            new_url = _res_url(_ps_sol_slug(n))
            if a.official_solution_url != new_url:
                a.official_solution_url = new_url
                dirty_assignments.add(a.id)

    for unit, lec_from, lec_to in UNIT_EXAMS:
        a = next(
            (
                x for t, x in by_title.items()
                if _UNIT_EXAM_TITLE_RE.match(t)
                and int(_UNIT_EXAM_TITLE_RE.match(t).group(1)) == unit
            ),
            None,
        )
        if a is None:
            continue
        new_desc = _exam_description(unit, lec_from, lec_to)
        if a.description_md != new_desc:
            a.description_md = new_desc
            dirty_assignments.add(a.id)
        if a.covers_lecture_from != lec_from or a.covers_lecture_to != lec_to:
            a.covers_lecture_from = lec_from
            a.covers_lecture_to = lec_to
            counts["coverage_updated"] += 1
        if not a.official_solution_file_path:
            new_url = _res_url(_exam_sol_slug(unit))
            if a.official_solution_url != new_url:
                a.official_solution_url = new_url
                dirty_assignments.add(a.id)

    a = by_title.get("Final Exam")
    if a is not None:
        new_desc = _final_description()
        if a.description_md != new_desc:
            a.description_md = new_desc
            dirty_assignments.add(a.id)
        if (
            a.covers_lecture_from != FINAL_COVERS_FROM
            or a.covers_lecture_to != FINAL_COVERS_TO
        ):
            a.covers_lecture_from = FINAL_COVERS_FROM
            a.covers_lecture_to = FINAL_COVERS_TO
            counts["coverage_updated"] += 1
        if not a.official_solution_file_path:
            new_url = _res_url(FINAL_SOL_SLUG)
            if a.official_solution_url != new_url:
                a.official_solution_url = new_url
                dirty_assignments.add(a.id)

    counts["assignments_updated"] = len(dirty_assignments)

    db.commit()
    return counts


def refresh_solutions(db: Session) -> dict:
    """Re-download every official-solution PDF on the live MIT 18.02SC course.

    Clears ``official_solution_file_path`` first so ``_attach_official_solution``
    re-fetches (otherwise idempotence short-circuits). Useful when OCW rotates
    a PDF's content hash.
    """
    course = db.query(Course).filter(Course.code == CODE).first()
    if course is None:
        return {"course_found": False, "refreshed": 0}

    counts = {"course_found": True, "refreshed": 0}
    by_title = {a.title: a for a in course.assignments}

    for n, *_ in PROBLEM_SETS:
        a = next(
            (x for t, x in by_title.items() if t.startswith(f"Problem Set {n} ")),
            None,
        )
        if a is None:
            continue
        a.official_solution_file_path = ""
        _attach_official_solution(db, a, _ps_sol_slug(n))
        counts["refreshed"] += 1

    for unit, *_ in UNIT_EXAMS:
        a = next(
            (
                x for t, x in by_title.items()
                if _UNIT_EXAM_TITLE_RE.match(t)
                and int(_UNIT_EXAM_TITLE_RE.match(t).group(1)) == unit
            ),
            None,
        )
        if a is None:
            continue
        a.official_solution_file_path = ""
        _attach_official_solution(db, a, _exam_sol_slug(unit))
        counts["refreshed"] += 1

    a = by_title.get("Final Exam")
    if a is not None:
        a.official_solution_file_path = ""
        _attach_official_solution(db, a, FINAL_SOL_SLUG)
        counts["refreshed"] += 1

    db.commit()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the MIT 18.02SC course.")
    parser.add_argument(
        "--force", action="store_true", help="delete an existing MIT 18.02SC course first"
    )
    parser.add_argument(
        "--update-urls",
        action="store_true",
        help="only refresh module_item external_url + assignment description_md "
        "+ coverage + official_solution_url on the existing course (no deletions, "
        "no PDF re-download)",
    )
    parser.add_argument(
        "--refresh-solutions",
        action="store_true",
        help="re-download every official-solution PDF from OCW (use if hash drift "
        "breaks the existing Storage paths)",
    )
    args = parser.parse_args()
    db = SessionLocal()
    try:
        if args.update_urls:
            counts = update_urls(db)
            print("update_urls: " + ", ".join(f"{k}={v}" for k, v in counts.items()))
            return
        if args.refresh_solutions:
            counts = refresh_solutions(db)
            print("refresh_solutions: " + ", ".join(f"{k}={v}" for k, v in counts.items()))
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
