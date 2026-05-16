"""Seed the MIT 6.231 — Dynamic Programming and Stochastic Control course
(Dimitri Bertsekas, Fall 2015).

Run:  cd backend && uv run python -m seed.seed_mit_6_231
        [--force] [--update-urls] [--refresh-solutions]
Source: https://ocw.mit.edu/courses/6-231-dynamic-programming-and-stochastic-control-fall-2015/

Idempotent: if a course with code "MIT 6.231" already exists this is a no-op,
unless ``--force`` (which deletes it first — the cascade on Course removes its
modules / assignment groups / assignments / announcements).

Pattern differences vs the MIT 6.262 seed:
  - Three assignment groups (30 / 30 / 40) instead of three exam-flavoured
    groups (20 / 35 / 45). Same solution-PDF pipeline.
  - No final exam (6.231 has only a midterm; the heavy assessment is the
    Course Project at 40% weight). The project is a single Assignment with
    ``requires_solution_key=False`` — AI grades in project mode, no reference
    solution. Same pattern as 18.336's Course Project and 18.065's Final
    Project.
  - PSet 9 has no published OCW solution. ``requires_solution_key=True``, no
    ``official_solution_file_path`` populated → AI generates its own key,
    like CMU 36-705 and the Aalto BDA weeklies.
  - PSet 8 is a custom OCW homework (not from the textbook). The solution PDF
    restates the problems, so we upload only the solution; the homework PDF
    URL goes in ``description_md`` for the user. The AI grades against the
    solution PDF as usual.
  - Solution PDFs uploaded under ``official/6_231/`` in the ``solutions``
    Supabase bucket — namespaced to avoid collisions with 6.262's
    ``official/6_262/``.
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

CODE = "MIT 6.231"
BASE = (
    "https://ocw.mit.edu/courses/"
    "6-231-dynamic-programming-and-stochastic-control-fall-2015"
)
HOME = BASE + "/"
SYLLABUS_URL = BASE + "/pages/syllabus/"
LECTURE_NOTES_URL = BASE + "/pages/lecture-notes/"
ASSIGNMENTS_URL = BASE + "/pages/assignments/"
EXAMS_URL = BASE + "/pages/exams/"
PROJECTS_URL = BASE + "/pages/projects/"
RELATED_VIDEOS_URL = BASE + "/pages/related-video-lectures/"


def _lec_url(n: int) -> str:
    """Per-lecture slide-deck landing page. Slug is NOT zero-padded."""
    return f"{BASE}/resources/mit6_231f15_lec{n}/"


def _ps_sol_url(n: int) -> str:
    """Problem-set solution landing page. Slugs 1..8; 9 has no solution."""
    return f"{BASE}/resources/mit6_231f15_solution{n}/"


def _hw8_url() -> str:
    """PSet 8 custom homework PDF landing page (the only PSet not pulled
    from Bertsekas's Vol I/II textbook)."""
    return f"{BASE}/resources/mit6_231f15_homework8/"


def _midterm_url(year: int) -> str:
    """Midterm paper landing page. Years: 2008, 2009, 2011, 2015."""
    return f"{BASE}/resources/mit6_231f15_mid_{year}/"


def _midterm_sol_url(year: int) -> str:
    """Midterm solution landing page."""
    return f"{BASE}/resources/mit6_231f15_mid_{year}_sol/"


def _project_topics_url() -> str:
    """List-of-project-topics PDF (references + suggested directions)."""
    return f"{BASE}/resources/mit6_231f15_references/"


def _resource_url(slug: str) -> str:
    """OCW resource landing page for any ``mit6_231f15_*`` (or video) slug."""
    return f"{BASE}/resources/{slug}/"


# --------------------------------------------------------------------------- Related
# OCW's "Related Video Lectures" page bundles a parallel resource:
# Bertsekas's 6-lecture, 12-hour short course on Approximate DP, taught at
# Tsinghua University in June 2014. The page also links 7 lecture-note PDFs
# from a Summer 2012 short course. We mirror BOTH:
#   - The slide PDFs (+ explanation) live in a new "Approximate DP —
#     short-course notes" module under Modules.
#   - The 18 video segments live as ``kind="video"`` items in a separate
#     "Video Lectures — Tsinghua 2014" module so they surface on the
#     Video Lectures page (and not in the Modules view — the frontend
#     filters ``kind="video"`` out of CourseModulesPage).

COMPLETE_SLIDES_SLUG = "mit6_231f15_complete_slide"

# (lecture #, lecture title verbatim from OCW, slide-PDF slug, [video segment slugs])
TSINGHUA_2014_LECTURES: list[tuple[int, str, str, list[str]]] = [
    (1, "Introduction to Dynamic Programming",
     "mit6_231f15_lec1-1",
     ["approximate-dynamic-programming-lecture-1-part-1",
      "approximate-dynamic-programming-lecture-1-part-2",
      "approximate-dynamic-programming-lecture-1-part-3"]),
    (2, "Review of Discounted Problem Theory",
     "mit6_231f15_lec2-1",
     ["approximate-dynamic-programming-lecture-2-part-1",
      "approximate-dynamic-programming-lecture-2-part-2",
      "approximate-dynamic-programming-lecture-2-part-3"]),
    (3, "General Issues of Approximation and Simulation",
     "mit6_231f15_lec3-1",
     ["approximate-dynamic-programming-lecture-3-part-1",
      "approximate-dynamic-programming-lecture-3-part-2"]),
    (4, "Approximate Policy Iteration",
     "mit6_231f15_lec4-1",
     ["approximate-dynamic-programming-lecture-4-part-1",
      "approximate-dynamic-programming-lecture-4-part-2"]),
    (5, "Aggregation Methods",
     "mit6_231f15_lec5-1",
     ["approximate-dynamic-programming-lecture-5-part-1",
      "approximate-dynamic-programming-lecture-5-part-2",
      "approximate-dynamic-programming-lecture-5-part-3"]),
    (6, "Q-Learning and Approximation in Policy Space",
     "mit6_231f15_lec6-1",
     ["approximate-dynamic-programming-lecture-6-part-1",
      "approximate-dynamic-programming-lecture-6-part-2"]),
]

# (display title verbatim from OCW, resource slug). PDF-only, no videos.
SUMMER_2012_NOTES: list[tuple[str, str]] = [
    ("Short Course Notes (PDF)", "mit6_231f15_notes_short"),
    ("Exact DP: Infinite Horizon Problems (PDF)", "mit6_231f15_lec01_short"),
    ("Exact DP: Large-scale Computational Methods (PDF)", "mit6_231f15_lec02_short"),
    ("General Issues of Approximation and Simulation (PDF)", "mit6_231f15_lec03_short"),
    ("Temporal Differences (TD), Projected Equations, Galerkin Approximation (PDF)",
     "mit6_231f15_lec04_short"),
    ("Aggregation Methods (PDF)", "mit6_231f15_lec05_short"),
    ("Stochastic Approximation, Q-learning, and Other Methods (PDF)",
     "mit6_231f15_lec06_short"),
    ("Monte Carlo Methods (PDF)", "mit6_231f15_lec07_short"),
]

RELATED_VIDEOS_INTRO_MD = """These materials are from a 6-lecture, 12-hour short course on
**Approximate Dynamic Programming**, taught by Professor Dimitri P. Bertsekas
at **Tsinghua University in Beijing, China in June 2014**. They focus primarily
on the advanced research-oriented issues of large-scale infinite-horizon
dynamic programming, which corresponds to **lectures 11–23 of the MIT 6.231
course**.

The complete set of lecture notes is available as the *Complete Slides*
link below, and is also divided by lecture. Additional supporting material
can be obtained on Prof. Bertsekas' web site.

*Note to OCW users:* All videos are from Shuvomoy Das Gupta on YouTube and are
**not provided under OCW's Creative Commons License**. They are surfaced on
the **Video Lectures** page of this course.

A second set of seven **Summer 2012 short-course** lecture notes (PDF only,
no videos) is also linked at the bottom of this module.
"""


_PDF_HREF_RE = re.compile(r'href="(/courses/[^"]+\.pdf)"')


def _resolve_pdf_url(slug: str) -> str:
    """Scrape ``BASE/resources/{slug}/`` for the PDF URL matching this slug.

    OCW renders PDFs with a content-hash-prefixed href (e.g.
    ``/courses/.../def456..._MIT6_231F15_solution1.pdf``) where the
    filename embeds the slug stem in uppercase (``MIT6_231F15_…``). The
    hash is not derivable from the slug, so we scrape the landing page.

    Multiple PDFs may be linked on one page; we pick the one whose
    filename actually matches the requested slug.

    Raises ``RuntimeError`` if no PDF matches (e.g. OCW restructured the
    page or removed the resource).
    """
    page_url = f"{BASE}/resources/{slug}/"
    resp = httpx.get(page_url, timeout=30)
    resp.raise_for_status()
    needle = slug.lower()
    for path in _PDF_HREF_RE.findall(resp.text):
        if needle in path.lower():
            return urljoin("https://ocw.mit.edu", path)
    raise RuntimeError(f"no PDF link matching slug '{slug}' on {page_url}")


def _storage_key_for(slug: str) -> str:
    """Path inside the ``solutions`` bucket. Namespaced under ``official/6_231/``
    so it doesn't collide with 6.262 or AI-generated solutions."""
    return f"official/6_231/{slug}.pdf"


def _attach_official_solution(db: Session, a: Assignment, slug: str) -> None:
    """Download OCW's solution PDF for ``slug`` and attach it to ``a``.

    Sets ``a.official_solution_file_path`` to the Storage key on success;
    ``a.official_solution_url`` stays empty so the AI grader resolves to the
    'official_file' branch and reads the PDF. On download/upload failure,
    falls back to setting ``official_solution_url`` only — the AI grader
    then uses the URL-only branch.

    Idempotent: if ``a.official_solution_file_path`` already points at a
    readable Storage object, do nothing.
    """
    storage_key = _storage_key_for(slug)
    landing_url = f"{BASE}/resources/{slug}/"

    if a.official_solution_file_path == storage_key:
        try:
            storage.read_bytes("solutions", storage_key)
            return
        except Exception:  # noqa: BLE001 — re-download if storage object is gone
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
        print(f"warn(seed_mit_6_231): solution upload failed for {slug}: {exc}")


# 23 lectures — (number, topic, textbook chapter reference). Chapter refs
# inferred by topical match against Bertsekas Vol I/II ToCs; the OCW
# syllabus's four-unit split is: Lec 1–9 (Finite Horizon + Imperfect Info),
# Lec 10–13 (Simple Infinite Horizon), Lec 14–18 (Advanced Infinite Horizon),
# Lec 19–23 (Approximate Dynamic Programming).
LECTURE_TOPICS: dict[int, tuple[str, str]] = {
    1:  ("Introduction to Dynamic Programming",                      "Vol I Ch 1"),
    2:  ("The Basic Problem",                                        "Vol I Ch 1"),
    3:  ("Deterministic Finite-State Problem",                       "Vol I Ch 2"),
    4:  ("Examples of Stochastic Dynamic Programming Problems",      "Vol I Ch 3-4"),
    5:  ("Stopping Problems",                                        "Vol I Ch 4"),
    6:  ("Problems with Imperfect State Info",                       "Vol I Ch 5"),
    7:  ("Imperfect State Information",                              "Vol I Ch 5"),
    8:  ("Suboptimal Control",                                       "Vol I Ch 6"),
    9:  ("Rollout Algorithms",                                       "Vol I Ch 6 / Vol II Ch 6"),
    10: ("Infinite Horizon Problems",                                "Vol I Ch 7"),
    11: ("Review of Stochastic Shortest Path Problems",              "Vol II Ch 2"),
    12: ("Average Cost Per Stage Problems",                          "Vol II Ch 4"),
    13: ("Control of Continuous-Time Markov Chains",                 "Vol II Ch 5"),
    14: ("Introduction to Advanced Infinite Horizon DP",             "Vol II Ch 1"),
    15: ("Review of Basic Theory of Discounted Problems",            "Vol II Ch 1"),
    16: ("Review of Computational Theory of Discounted Problems",    "Vol II Ch 1"),
    17: ("Undiscounted Problems",                                    "Vol II Ch 3"),
    18: ("Undiscounted Total Cost Problems",                         "Vol II Ch 3"),
    19: ("Introduction to Approximate Dynamic Programming",          "Vol II Ch 6"),
    20: ("Discounted Problems (Approximate methods)",                "Vol II Ch 6"),
    21: ("Review of Approximate Policy Iteration",                   "Vol II Ch 6"),
    22: ("Aggregation as an Approximation Methodology",              "Vol II Ch 6"),
    23: ("Additional Topics in Advanced Dynamic Programming",        "Vol II Ch 7"),
}


# 9 problem sets — (number, topic, problems_md, covers_from, covers_to,
# homework_slug, solution_slug). PSet 9 has no published solution (None).
# PSet 8 has a custom homework PDF; the rest reference Vol I or Vol II by
# problem number.
PROBLEM_SETS: list[tuple[int, str, str, int, int, str | None, str | None]] = [
    (1, "Introduction & basic problem",
     "Volume I — Problems 1.2, 1.3, 1.22, 2.1, 2.7, 2.9",
     1, 2, None, "mit6_231f15_solution1"),
    (2, "Deterministic & stochastic finite-horizon",
     "Volume I — Problems 4.1, 4.2, 4.29, 4.33, 4.34",
     3, 5, None, "mit6_231f15_solution2"),
    (3, "Stopping problems",
     "Volume I — Problems 5.2(a), 5.7, 5.14",
     5, 6, None, "mit6_231f15_solution3"),
    (4, "Imperfect state info",
     "Volume I — Problems 6.2 (ignore first two sentences), 6.10, 6.16, 6.20",
     6, 7, None, "mit6_231f15_solution4"),
    (5, "Suboptimal control",
     "Volume I — Problem 7.2",
     8, 8, None, "mit6_231f15_solution5"),
    (6, "Rollout & limited lookahead",
     "Volume I — Problems 7.3, 7.5, 7.7, 7.8a, 7.10, 7.11",
     8, 9, None, "mit6_231f15_solution6"),
    (7, "Approximate DP",
     "Volume I — Problems 7.20, 7.22, 7.23, 7.24, 7.25, 7.26",
     9, 9, None, "mit6_231f15_solution7"),
    (8, "Infinite-horizon (custom homework)",
     "See attached custom homework PDF (problems on infinite-horizon DP — not from the textbook).",
     10, 13, "mit6_231f15_homework8", "mit6_231f15_solution8"),
    (9, "Approximate DP (Vol II)",
     "Volume II — Problems 4.12 and 4.17",
     19, 22, None, None),
]


# Midterm — graded year + lecture coverage. Other years are practice in
# Modules.
MIDTERM_GRADED_YEAR = 2015
MIDTERM_COVERS_FROM = 1
MIDTERM_COVERS_TO = 9
_PRACTICE_MIDTERM_YEARS: tuple[int, ...] = (2008, 2009, 2011)


# Course Project — covers everything, project mode (no reference solution).
PROJECT_COVERS_FROM = 1
PROJECT_COVERS_TO = 23


def _direct_links_items() -> list[dict]:
    return [
        {"kind": "link", "title": "6.231 course home (Bertsekas, MIT OCW Fall 2015)", "url": HOME},
        {"kind": "link", "title": "Syllabus", "url": SYLLABUS_URL},
        {"kind": "link", "title": "Lecture slides index", "url": LECTURE_NOTES_URL},
        {"kind": "link", "title": "Assignments index", "url": ASSIGNMENTS_URL},
        {"kind": "link", "title": "Exams index", "url": EXAMS_URL},
        {"kind": "link", "title": "Projects page", "url": PROJECTS_URL},
        {
            "kind": "link",
            "title": "Related video lectures (Bertsekas 2014 Tsinghua short course)",
            "url": RELATED_VIDEOS_URL,
        },
    ]


def _lecture_slides_items() -> list[dict]:
    return [
        {
            "kind": "link",
            "title": f"Lecture {n}: {topic}",
            "url": _lec_url(n),
        }
        for n, (topic, _ch) in sorted(LECTURE_TOPICS.items())
    ]


def _project_resources_items() -> list[dict]:
    return [
        {
            "kind": "link",
            "title": "List of project topics (with references)",
            "url": _project_topics_url(),
        },
    ]


def _practice_midterms_items() -> list[dict]:
    """Links to *practice* midterm years only — paper + indented solution.

    The graded 2015 paper is the Midterm Assignment and does NOT appear here;
    a real teacher wouldn't publish the actual graded test + solution under
    "Modules". See feedback-module-content-chapter-readings Rule 3.
    """
    out: list[dict] = []
    for year in _PRACTICE_MIDTERM_YEARS:
        out.append(
            {"kind": "link", "title": f"Midterm {year} — paper", "url": _midterm_url(year)}
        )
        out.append(
            {
                "kind": "link",
                "title": f"Midterm {year} — solution",
                "url": _midterm_sol_url(year),
                "indent": 1,
            }
        )
    return out


def _related_short_course_notes_items() -> list[dict]:
    """Module body for OCW's Related Video Lectures page — *slides only*.

    Mirrors OCW: an explanation note at the top, the Complete Slides PDF,
    six Tsinghua-2014 lecture-note PDFs (one per lecture, in OCW's order),
    and the seven Summer 2012 lecture-note PDFs at the bottom.

    The 18 video segments do NOT appear here — they live in the separate
    "Video Lectures (Bertsekas 2014 Tsinghua)" module as ``kind="video"``
    items so they only surface on the Video Lectures page.
    """
    items: list[dict] = [
        {
            "kind": "note",
            "title": "About these short-course materials",
            "text_md": RELATED_VIDEOS_INTRO_MD,
        },
        {
            "kind": "link",
            "title": "Complete Slides (PDF — 1.6MB)",
            "url": _resource_url(COMPLETE_SLIDES_SLUG),
        },
        {
            "kind": "header",
            "title": "Summer 2014 — Tsinghua Short Course (6 lectures)",
        },
    ]
    for n, title, slide_slug, _videos in TSINGHUA_2014_LECTURES:
        items.append(
            {
                "kind": "link",
                "title": f"Lecture {n} — {title} (PDF)",
                "url": _resource_url(slide_slug),
                "indent": 1,
            }
        )
    items.append(
        {
            "kind": "header",
            "title": "Summer 2012 — Short Course (7 lecture-note PDFs)",
        }
    )
    for title, slug in SUMMER_2012_NOTES:
        items.append(
            {
                "kind": "link",
                "title": title,
                "url": _resource_url(slug),
                "indent": 1,
            }
        )
    return items


def _tsinghua_2014_video_items() -> list[dict]:
    """Module body for the Video Lectures page — 18 ``kind="video"`` items.

    Titles are verbatim from OCW (``Approximate Dynamic Programming,
    Lecture N, Part P``). The Modules page filters ``kind="video"`` items
    out of its view, so this module exists purely to populate
    CourseVideosPage from ``course.modules.flatMap(...kind == "video")``.
    """
    items: list[dict] = []
    for n, _title, _slide, video_slugs in TSINGHUA_2014_LECTURES:
        for part_idx, slug in enumerate(video_slugs, start=1):
            items.append(
                {
                    "kind": "video",
                    "title": f"Approximate Dynamic Programming, Lecture {n}, Part {part_idx}",
                    "url": _resource_url(slug),
                }
            )
    return items


def _modules() -> list[tuple[str, list[dict]]]:
    """Six modules:

      1. "Direct links" — top-of-course navigation.
      2. "Lecture Slides" — 23 link items, one per MIT 6.231 lecture.
      3. "Project Resources" — list-of-topics PDF.
      4. "Practice Midterms" — 2008/2009/2011 papers + solutions (the 2015
         midterm is the graded Assignment, not in Modules).
      5. "Approximate DP — Short-course lecture notes" — slides from
         OCW's Related Video Lectures page (Tsinghua 2014 + Summer 2012).
      6. "Video Lectures (Bertsekas 2014 Tsinghua)" — 18 ``kind="video"``
         items mirroring OCW. Surfaces on the Video Lectures page only;
         filtered out of the Modules view (see CourseModulesPage).
    """
    return [
        ("Direct links", _direct_links_items()),
        ("Lecture Slides", _lecture_slides_items()),
        ("Project Resources", _project_resources_items()),
        ("Practice Midterms", _practice_midterms_items()),
        (
            "Approximate DP — Short-course lecture notes (Bertsekas 2014 + 2012)",
            _related_short_course_notes_items(),
        ),
        (
            "Video Lectures (Bertsekas 2014 Tsinghua)",
            _tsinghua_2014_video_items(),
        ),
    ]


SYLLABUS_MD = """## Prerequisites
6.041 (Probabilistic Systems Analysis) or equivalent comfort with undergraduate
probability — conditional distributions, expectations, Markov chains. Real
analysis is helpful but not strictly required. Mathematical maturity is
essential.

## Textbook
- **Primary** — Bertsekas, *Dynamic Programming and Optimal Control*, Vol I
  (3rd ed., 2005). Athena Scientific.
- **Primary (ADP half)** — Bertsekas, *Dynamic Programming and Optimal Control*,
  Vol II: Approximate Dynamic Programming (4th ed., 2012). Athena Scientific.
- Both are *not* free PDFs; you need the books. Athena's printed editions are
  the standard.

## Grading (mirror OCW)
| Component | Weight |
|---|---|
| Problem Sets (9) | 30% |
| Midterm | 30% |
| Course Project | 40% |

The original 6.231 syllabus splits the grade as 30% homework / 30% quiz /
40% project. We mirror it exactly.

## Problem-set policy
PSets 1–7 are textbook problems from Vol I — solve them, then check against
the official solution PDFs OCW publishes (linked from each assignment).
PSet 8 is a custom OCW homework on infinite-horizon DP. PSet 9 (Vol II
4.12, 4.17) has **no published solution**, so the AI grader generates its
own reference key for grading.

## Midterm
The graded paper is **2015**, covering Lec 1–9 (finite + imperfect-info
horizon). OCW also publishes papers from 2008, 2009, and 2011 with full
solutions — they're collected in the **Practice Midterms** module.

## Course Project
Bertsekas's project format:

- **Theoretical** — read and report on 2–3 papers in a stochastic-control
  subarea, with critical evaluation + original commentary on extensions.
  Individual work only.
- **Applied** — formulate a stochastic-control problem computationally;
  either develop insights into problem variants or compare algorithmic
  approaches. Solo or two-person teams.

Format: ≤15 pp 12pt single-spaced + figures, appendices allowed. Proposal
(1 page) ~ end of Week 11. Final report + 15-min presentation in Week 15.
See the **Project Resources** module for the list of project topics.

The project is graded in **project mode** (no reference solution) — the AI
evaluates quality of formulation, depth of analysis, clarity of write-up,
and original contribution.
"""

HOME_MD = """**MIT 6.231 — Dynamic Programming and Stochastic Control (Bertsekas, Fall 2015).**

Course materials mirrored from MIT OCW. The term shown above is *your*
self-study term — edit it from the course settings when your plan shifts.

The graduate DP course at MIT. Sequential decision-making under uncertainty:
finite-horizon problems with perfect and imperfect information, infinite-horizon
problems (discounted, average cost, stochastic shortest path), and approximate
dynamic programming (rollout, policy iteration, aggregation). Bertsekas's own
course — his two Athena Scientific textbooks (Vol I + Vol II) are the spine;
this seed indexes lecture topics against chapter ranges.

Source: <https://ocw.mit.edu/courses/6-231-dynamic-programming-and-stochastic-control-fall-2015/>.
Jump to **Syllabus**, **Modules**, or **Assignments**.
"""

DESCRIPTION = (
    "Dynamic programming & stochastic control: finite- and infinite-horizon "
    "problems, imperfect state information, suboptimal control, rollout, "
    "policy iteration, and approximate dynamic programming."
)

TEXTBOOK = (
    "Bertsekas, Dynamic Programming and Optimal Control, Vol I (3rd ed., "
    "2005) and Vol II: Approximate Dynamic Programming (4th ed., 2012). "
    "Athena Scientific. Both volumes required."
)


def _ps_description(
    k: int,
    topic: str,
    problems_md: str,
    lec_from: int,
    lec_to: int,
    homework_slug: str | None,
    solution_slug: str | None,
) -> str:
    lines = [
        f"Problem Set {k} ({topic}). Covers lectures {lec_from}–{lec_to}.",
        "",
        f"**Problems:** {problems_md}",
        "",
    ]
    if homework_slug:
        lines.append(
            f"- Homework PDF (custom): "
            f"[{homework_slug}.pdf]({BASE}/resources/{homework_slug}/)"
        )
    if solution_slug:
        lines.append(
            f"- Reference solution: [PS{k} Solution (landing page)]"
            f"({BASE}/resources/{solution_slug}/)"
        )
    lines.append("")
    if solution_slug:
        lines.append(
            "Upload your worked solutions. The AI grades against Bertsekas's "
            "official solution (loaded from Storage). OCW publishes the public "
            "solution PDF at the link above."
        )
    else:
        lines.append(
            "Upload your worked solutions. OCW publishes **no** official "
            "solution for this problem set, so the AI grader generates its "
            "own reference key from the problem statement before grading."
        )
    return "\n".join(lines)


def _midterm_description() -> str:
    year = MIDTERM_GRADED_YEAR
    paper_url = _midterm_url(year)
    sol_url = _midterm_sol_url(year)
    lines = [
        f"Midterm Exam ({year} paper). Closed-book exam covering lectures "
        f"{MIDTERM_COVERS_FROM}–{MIDTERM_COVERS_TO} (finite-horizon + "
        "imperfect-info problems).",
        "",
        f"- Paper: [{year} Midterm PDF]({paper_url})",
        f"- Reference solution: [{year} Midterm Solution]({sol_url})",
        "",
        "## Additional practice papers",
    ]
    for py in _PRACTICE_MIDTERM_YEARS:
        lines.append(
            f"- Midterm {py}: [paper]({_midterm_url(py)}) · "
            f"[solution]({_midterm_sol_url(py)})"
        )
    lines.extend([
        "",
        "Time yourself (~90 minutes). Upload your attempt; the AI grades "
        "against Bertsekas's official solution. The practice papers above "
        "are *not* graded — they're for self-paced review.",
    ])
    return "\n".join(lines)


def _project_description() -> str:
    topics_url = _project_topics_url()
    return (
        "**Course Project — stochastic-control study.**\n\n"
        "Choose **theoretical** (read & critically evaluate 2–3 papers in a "
        "stochastic-control subarea, with original commentary on extensions; "
        "individual work) or **applied** (formulate a stochastic-control "
        "problem computationally — either develop insights into problem "
        "variants or compare algorithmic approaches; solo or two-person "
        "teams).\n\n"
        "**Format:** ≤15 pages, 12pt single-spaced + figures; appendices "
        "allowed. Proposal (1 page) by end of Week 11. Final report + 15-min "
        "presentation in Week 15.\n\n"
        f"**Starting points:** see the [List of project topics with references]"
        f"({topics_url}) on OCW.\n\n"
        "**Grading:** project mode — no reference solution. The AI evaluates "
        "quality of problem formulation, depth of analysis, clarity of "
        "write-up, and originality. Upload your final report (PDF) plus any "
        "code / numerical results as supplementary files."
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
        title="Dynamic Programming and Stochastic Control",
        institution="Massachusetts Institute of Technology",
        term_label="Fall 2030",  # user's self-study term, not OCW recording year
        instructor="Prof. Dimitri P. Bertsekas",
        external_home_url=HOME,
        status="planned",
        color="#1F7A4D",  # forest green — distinct from existing palette
        display_order=6,
        textbook=TEXTBOOK,
        home_page_md=HOME_MD,
        syllabus_md=SYLLABUS_MD,
        description=DESCRIPTION,
    )
    db.add(course)
    db.flush()

    g_ps = AssignmentGroup(
        course_id=course.id, name="Problem Sets", weight=30, drop_lowest_n=0, position=0
    )
    g_mid = AssignmentGroup(
        course_id=course.id, name="Midterm", weight=30, drop_lowest_n=0, position=1
    )
    g_proj = AssignmentGroup(
        course_id=course.id, name="Course Project", weight=40, drop_lowest_n=0, position=2
    )
    db.add_all([g_ps, g_mid, g_proj])
    db.flush()

    # 9 PSets — create then attach official solution (PSets 1-8 only).
    for k, topic, problems_md, lec_from, lec_to, hw_slug, sol_slug in PROBLEM_SETS:
        a = Assignment(
            course_id=course.id,
            assignment_group_id=g_ps.id,
            title=f"Problem Set {k} — {topic}",
            description_md=_ps_description(
                k, topic, problems_md, lec_from, lec_to, hw_slug, sol_slug
            ),
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
        db.flush()
        if sol_slug is not None:
            _attach_official_solution(db, a, sol_slug)

    # Midterm (2015 paper) — graded, with official solution.
    a_mid = Assignment(
        course_id=course.id,
        assignment_group_id=g_mid.id,
        title=f"Midterm Exam ({MIDTERM_GRADED_YEAR} paper)",
        description_md=_midterm_description(),
        points_possible=100,
        accepts_files=True,
        accepts_text=True,
        position=0,
        published=True,
        covers_lecture_from=MIDTERM_COVERS_FROM,
        covers_lecture_to=MIDTERM_COVERS_TO,
        requires_solution_key=True,
    )
    db.add(a_mid)
    db.flush()
    _attach_official_solution(db, a_mid, f"mit6_231f15_mid_{MIDTERM_GRADED_YEAR}_sol")

    # Course Project — project mode, no reference solution.
    a_proj = Assignment(
        course_id=course.id,
        assignment_group_id=g_proj.id,
        title="Course Project — stochastic-control study",
        description_md=_project_description(),
        points_possible=100,
        accepts_files=True,
        accepts_text=True,
        # Project-style: AI grades on quality/depth/clarity/originality,
        # no reference solution.
        requires_solution_key=False,
        position=0,
        published=True,
        covers_lecture_from=PROJECT_COVERS_FROM,
        covers_lecture_to=PROJECT_COVERS_TO,
    )
    db.add(a_proj)
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


# --------------------------------------------------------------------------- updater

_PSET_TITLE_RE = re.compile(r"^Problem Set (\d+) — ")
_MIDTERM_TITLE_RE = re.compile(r"^Midterm Exam \((\d{4}) paper\)")


def _fixed_title_to_url() -> dict[str, str]:
    """Map a module-item title to the URL it should always point to."""
    out: dict[str, str] = {
        "6.231 course home (Bertsekas, MIT OCW Fall 2015)": HOME,
        "Syllabus": SYLLABUS_URL,
        "Lecture slides index": LECTURE_NOTES_URL,
        "Assignments index": ASSIGNMENTS_URL,
        "Exams index": EXAMS_URL,
        "Projects page": PROJECTS_URL,
        "Related video lectures (Bertsekas 2014 Tsinghua short course)": RELATED_VIDEOS_URL,
        "List of project topics (with references)": _project_topics_url(),
        # Approximate DP short-course notes module — slides only.
        "Complete Slides (PDF — 1.6MB)": _resource_url(COMPLETE_SLIDES_SLUG),
    }
    for n, (topic, _ch) in LECTURE_TOPICS.items():
        out[f"Lecture {n}: {topic}"] = _lec_url(n)
    # Practice-midterm years only — the graded 2015 paper is the Assignment.
    for year in _PRACTICE_MIDTERM_YEARS:
        out[f"Midterm {year} — paper"] = _midterm_url(year)
        out[f"Midterm {year} — solution"] = _midterm_sol_url(year)
    # Tsinghua 2014 short course — slide PDFs (one per lecture).
    for n, title, slide_slug, _videos in TSINGHUA_2014_LECTURES:
        out[f"Lecture {n} — {title} (PDF)"] = _resource_url(slide_slug)
    # Summer 2012 short course — 7 lecture-note PDFs.
    for title, slug in SUMMER_2012_NOTES:
        out[title] = _resource_url(slug)
    # Tsinghua 2014 video segments — kind="video" items, but title→URL still
    # canonical for --update-urls.
    for n, _title, _slide, video_slugs in TSINGHUA_2014_LECTURES:
        for part_idx, slug in enumerate(video_slugs, start=1):
            out[f"Approximate Dynamic Programming, Lecture {n}, Part {part_idx}"] = (
                _resource_url(slug)
            )
    return out


# Title renames to apply during update_urls so existing-DB courses get the new
# title without losing the row. Format: {old_title: new_title}.
_TITLE_RENAMES: dict[str, str] = {
    "Related video lectures (Bertsekas 2014 ASU)": (
        "Related video lectures (Bertsekas 2014 Tsinghua short course)"
    ),
}


def update_urls(db: Session) -> dict:
    """Refresh URLs on the live MIT 6.231 course in place — module-item URLs
    and assignment description_md / coverage / URL. Does NOT re-download PDFs
    (use --refresh-solutions for that). Preserves submissions / AI solutions /
    announcements / grades.

    Counter semantics:
      - ``items_examined`` / ``items_updated``: per module-item.
      - ``assignments_updated``: count of *distinct* assignments with any
        field change.
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
            # Apply title renames before URL lookup so the renamed title hits
            # the new entry in ``fixed``.
            if it.title in _TITLE_RENAMES:
                it.title = _TITLE_RENAMES[it.title]
                counts["items_updated"] += 1
            if it.title in fixed:
                new_url = fixed[it.title]
                if new_url != it.external_url:
                    it.external_url = new_url
                    counts["items_updated"] += 1

    dirty_assignments: set[str] = set()
    by_title = {a.title: a for a in course.assignments}

    # PSets — refresh description_md, coverage, official_solution_url.
    for k, topic, problems_md, lec_from, lec_to, hw_slug, sol_slug in PROBLEM_SETS:
        a = next(
            (x for t, x in by_title.items() if t.startswith(f"Problem Set {k} ")),
            None,
        )
        if a is None:
            continue
        new_desc = _ps_description(k, topic, problems_md, lec_from, lec_to, hw_slug, sol_slug)
        if a.description_md != new_desc:
            a.description_md = new_desc
            dirty_assignments.add(a.id)
        if a.covers_lecture_from != lec_from or a.covers_lecture_to != lec_to:
            a.covers_lecture_from = lec_from
            a.covers_lecture_to = lec_to
            counts["coverage_updated"] += 1
        if sol_slug is not None and not a.official_solution_file_path:
            new_url = _ps_sol_url(k)
            if a.official_solution_url != new_url:
                a.official_solution_url = new_url
                dirty_assignments.add(a.id)

    # Midterm — refresh description_md, coverage, official_solution_url.
    a_mid = next(
        (x for t, x in by_title.items() if _MIDTERM_TITLE_RE.match(t)),
        None,
    )
    if a_mid is not None:
        new_desc = _midterm_description()
        if a_mid.description_md != new_desc:
            a_mid.description_md = new_desc
            dirty_assignments.add(a_mid.id)
        if (
            a_mid.covers_lecture_from != MIDTERM_COVERS_FROM
            or a_mid.covers_lecture_to != MIDTERM_COVERS_TO
        ):
            a_mid.covers_lecture_from = MIDTERM_COVERS_FROM
            a_mid.covers_lecture_to = MIDTERM_COVERS_TO
            counts["coverage_updated"] += 1
        if not a_mid.official_solution_file_path:
            new_url = _midterm_sol_url(MIDTERM_GRADED_YEAR)
            if a_mid.official_solution_url != new_url:
                a_mid.official_solution_url = new_url
                dirty_assignments.add(a_mid.id)

    # Project — refresh description_md, coverage. No solution URL.
    a_proj = next(
        (x for t, x in by_title.items() if t.startswith("Course Project")),
        None,
    )
    if a_proj is not None:
        new_desc = _project_description()
        if a_proj.description_md != new_desc:
            a_proj.description_md = new_desc
            dirty_assignments.add(a_proj.id)
        if (
            a_proj.covers_lecture_from != PROJECT_COVERS_FROM
            or a_proj.covers_lecture_to != PROJECT_COVERS_TO
        ):
            a_proj.covers_lecture_from = PROJECT_COVERS_FROM
            a_proj.covers_lecture_to = PROJECT_COVERS_TO
            counts["coverage_updated"] += 1

    counts["assignments_updated"] = len(dirty_assignments)

    db.commit()
    return counts


def refresh_solutions(db: Session) -> dict:
    """Re-download every official-solution PDF on the live MIT 6.231 course.

    Forces ``_attach_official_solution`` to re-fetch by clearing the
    ``official_solution_file_path`` field first. Useful when OCW rotates a
    PDF's content hash.

    Skips PSet 9 (no published solution) and the project (project mode).
    """
    course = db.query(Course).filter(Course.code == CODE).first()
    if course is None:
        return {"course_found": False, "refreshed": 0}

    counts = {"course_found": True, "refreshed": 0}
    by_title = {a.title: a for a in course.assignments}

    for k, _topic, _pmd, _f, _t, _hw, sol_slug in PROBLEM_SETS:
        if sol_slug is None:
            continue
        a = next(
            (x for t, x in by_title.items() if t.startswith(f"Problem Set {k} ")),
            None,
        )
        if a is None:
            continue
        a.official_solution_file_path = ""
        _attach_official_solution(db, a, sol_slug)
        counts["refreshed"] += 1

    a_mid = next((x for t, x in by_title.items() if _MIDTERM_TITLE_RE.match(t)), None)
    if a_mid is not None:
        a_mid.official_solution_file_path = ""
        _attach_official_solution(db, a_mid, f"mit6_231f15_mid_{MIDTERM_GRADED_YEAR}_sol")
        counts["refreshed"] += 1

    db.commit()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the MIT 6.231 course.")
    parser.add_argument(
        "--force", action="store_true", help="delete an existing MIT 6.231 course first"
    )
    parser.add_argument(
        "--update-urls",
        action="store_true",
        help="only refresh module_item external_url + assignment fields on the "
        "existing course (no deletions, no PDF re-download)",
    )
    parser.add_argument(
        "--refresh-solutions",
        action="store_true",
        help="re-download every official-solution PDF from OCW (use if hash drift "
        "breaks the existing paths)",
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
