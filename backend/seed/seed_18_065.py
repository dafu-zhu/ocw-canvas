"""Seed the MIT 18.065 — Matrix Methods in Data Analysis, Signal Processing,
and Machine Learning (Gilbert Strang, Spring 2018).

Run:  cd backend && uv run python -m seed.seed_18_065 [--force]
Source: https://ocw.mit.edu/courses/18-065-matrix-methods-in-data-analysis-signal-processing-and-machine-learning-spring-2018/

Idempotent: existing course → no-op unless ``--force``.

Pattern differences vs the MIT 18.700 seed:
  - Has lecture videos. 34 of 36 are recorded; per the chapter-readings rule,
    each lecture is a 'note' item showing the Strang section as primary
    content, with the video URL embedded inline as a [Watch video →] link.
    Lectures 28-29 were unrecorded in-class Julia/Python labs — note items
    explain that and point to Strang's online code instead.
  - OCW publishes problem sets as a single combined PDF (not per-week). Six
    self-study PSets each link to the same combined PDF and span a contiguous
    lecture range; the user reads the relevant section of the PDF.
  - Final Project IS published (description + topic suggestions, no rubric).
    The original course substitutes the project for the last 3 homeworks; we
    mirror that — PSets cover lec 1-27, Final Project covers lec 28-36. The
    Final Project sets requires_solution_key=False so the AI grades it in
    project-mode (quality/depth/clarity, no reference comparison).
  - No exams in the original course either ("homework + lab + final project"
    grading, per Strang's syllabus). Self-study split: PSets 70%, Project 30%.
"""
from __future__ import annotations

import argparse
import re

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Assignment, AssignmentGroup, Course, Module, ModuleItem

CODE = "MIT 18.065"
BASE = (
    "https://ocw.mit.edu/courses/"
    "18-065-matrix-methods-in-data-analysis-signal-processing-and-machine-learning-spring-2018"
)
HOME = BASE + "/"
SYLLABUS_URL = BASE + "/pages/syllabus/"
CALENDAR_URL = BASE + "/pages/calendar/"
READINGS_URL = BASE + "/pages/readings/"
ASSIGNMENTS_URL = BASE + "/pages/assignments/"
FINAL_PROJECT_URL = BASE + "/pages/final-project/"
RELATED_URL = BASE + "/pages/related-resources/"
INSTRUCTOR_URL = BASE + "/pages/instructor-insights/"
VIDEOS_INDEX_URL = BASE + "/video_galleries/video-lectures/"
PSETS_URL = BASE + "/resources/mit18_065s18psets/"  # all problem sets, one PDF
STRANG_BOOK_URL = "https://math.mit.edu/~gs/learningfromdata/"

# Per-lecture video resource URLs. Slug pattern is "/resources/{slug}/", where
# the slug embeds the lecture number and a kebab-cased topic. Some slugs use
# numeric Unicode codepoints in place of special chars (e.g. 2019 = ’,
# 2016 = ‖) — these are OCW's actual URL conventions, verified against the
# video-gallery page.
LECTURE_VIDEO_SLUGS: dict[int, str] = {
    1: "lecture-1-the-column-space-of-a-contains-all-vectors-ax",
    2: "lecture-2-multiplying-and-factoring-matrices",
    3: "lecture-3-orthonormal-columns-in-q-give-q2019q-i",
    4: "lecture-4-eigenvalues-and-eigenvectors",
    5: "lecture-5-positive-definite-and-semidefinite-matrices",
    6: "lecture-6-singular-value-decomposition-svd",
    7: "lecture-7-eckart-young-the-closest-rank-k-matrix-to-a",
    8: "lecture-8-norms-of-vectors-and-matrices",
    9: "lecture-9-four-ways-to-solve-least-squares-problems",
    10: "lecture-10-survey-of-difficulties-with-ax-b",
    11: "lecture-11-minimizing-2016x2016-subject-to-ax-b",
    12: "lecture-12-computing-eigenvalues-and-singular-values",
    13: "lecture-13-randomized-matrix-multiplication",
    14: "lecture-14-low-rank-changes-in-a-and-its-inverse",
    15: "lecture-15-matrices-a-t-depending-on-t-derivative-da-dt",
    16: "lecture-16-derivatives-of-inverse-and-singular-values",
    17: "lecture-17-rapidly-decreasing-singular-values",
    18: "lecture-18-counting-parameters-in-svd-lu-qr-saddle-points",
    19: "lecture-19-saddle-points-continued-maxmin-principle",
    20: "lecture-20-definitions-and-inequalities",
    21: "lecture-21-minimizing-a-function-step-by-step",
    22: "lecture-22-gradient-descent-downhill-to-a-minimum",
    23: "lecture-23-accelerating-gradient-descent-use-momentum",
    24: "lecture-24-linear-programming-and-two-person-games",
    25: "lecture-25-stochastic-gradient-descent",
    26: "lecture-26-structure-of-neural-nets-for-deep-learning",
    27: "lecture-27-backpropagation-find-partial-derivatives",
    # 28, 29: in-class Julia/Python labs, NOT recorded.
    30: "lecture-30-completing-a-rank-one-matrix-circulants",
    31: "lecture-31-eigenvectors-of-circulant-matrices-fourier-matrix",
    32: "lecture-32-imagenet-is-a-cnn-the-convolution-rule",
    33: "lecture-33-neural-nets-and-the-learning-function",
    34: "lecture-34-distance-matrices-procrustes-problem-first-project",
    35: "lecture-35-finding-clusters-in-graphs-second-project-handwriting",
    36: "lecture-36-third-project-alan-edelman-and-julia-language",
}


def _video_url(n: int) -> str:
    return f"{BASE}/resources/{LECTURE_VIDEO_SLUGS[n]}/"


# (lecture_number, topic, strang_section) — Strang Roman-numeral chapters
# (I, II, III, IV, VI, VII; Ch V is mostly skipped). Lec 28-29 are unrecorded
# labs with no reading; lec 36 is Edelman's guest talk.
LECTURE_TOPICS: dict[int, tuple[str, str]] = {
    1:  ("Column space of A contains all vectors Ax",   "Strang §I.1"),
    2:  ("Multiplying & factoring matrices",            "Strang §I.2"),
    3:  ("Orthonormal columns: Q'Q = I",                "Strang §I.5"),
    4:  ("Eigenvalues & eigenvectors",                  "Strang §I.6"),
    5:  ("Positive (semi)definite matrices",            "Strang §I.7"),
    6:  ("Singular value decomposition (SVD)",          "Strang §I.8"),
    7:  ("Eckart-Young: closest rank-k matrix to A",    "Strang §I.9"),
    8:  ("Norms of vectors and matrices",               "Strang §I.11"),
    9:  ("Four ways to solve least squares",            "Strang §II.2"),
    10: ("Survey of difficulties with Ax = b",          "Strang Ch II intro"),
    11: ("Minimizing ‖x‖ subject to Ax = b",            "Strang §I.11"),
    12: ("Computing eigenvalues & singular values",     "Strang §II.1"),
    13: ("Randomized matrix multiplication",            "Strang §II.4"),
    14: ("Low rank changes in A and its inverse",       "Strang §III.1"),
    15: ("Matrices A(t); derivative dA/dt",             "Strang §§III.1-III.2"),
    16: ("Derivatives of inverse & singular values",    "Strang §§III.1-III.2"),
    17: ("Rapidly decreasing singular values",          "Strang §III.3"),
    18: ("Counting parameters: SVD/LU/QR; saddle pts",  "Strang §III.2"),
    19: ("Saddle points; maxmin principle",             "Strang §§III.2 + V.1"),
    20: ("Definitions and inequalities",                "(no specific reading)"),
    21: ("Minimizing a function step by step",          "Strang §§VI.1, VI.4"),
    22: ("Gradient descent: downhill to a minimum",     "Strang §VI.4"),
    23: ("Accelerating gradient descent (momentum)",    "Strang §VI.4"),
    24: ("Linear programming & two-person games",       "Strang §§VI.2, VI.3"),
    25: ("Stochastic gradient descent",                 "Strang §VI.5"),
    26: ("Structure of neural nets for deep learning",  "Strang §VII.1"),
    27: ("Backpropagation: partial derivatives",        "Strang §VII.3"),
    28: ("Computing in class — Julia/Python lab",       "(no recording, no reading)"),
    29: ("Computing in class (cont.)",                  "(no recording, no reading)"),
    30: ("Completing rank-one matrices; circulants",    "Strang §§IV.8, IV.2"),
    31: ("Circulant matrices; the Fourier matrix",      "Strang §IV.2"),
    32: ("ImageNet is a CNN; the convolution rule",     "Strang §IV.2"),
    33: ("Neural nets & the learning function",         "Strang §§VII.1, IV.10"),
    34: ("Distance matrices; Procrustes problem",       "Strang §§IV.9, IV.10"),
    35: ("Finding clusters in graphs",                  "Strang §§IV.6, IV.7"),
    36: ("Alan Edelman & the Julia language",           "Strang §§III.3, VII.2"),
}

# 6 problem sets — (number, topic, covers_lecture_from, covers_lecture_to).
# All link to the single combined OCW PSets PDF; each spans a contiguous
# lecture range. Final Project (separate group) covers lec 28-36, mirroring
# the original course where the project replaced the last 3 homeworks.
PROBLEM_SETS: list[tuple[int, str, int, int]] = [
    (1, "Foundations: multiplication, factoring, eigenvalues, SVD",  1,  7),
    (2, "Norms, least squares, Ax=b",                                8, 11),
    (3, "Numerical & randomized linear algebra",                    12, 13),
    (4, "Low rank, derivatives, saddle points",                     14, 19),
    (5, "Convex optimization & gradient methods",                   20, 25),
    (6, "Deep learning fundamentals",                               26, 27),
]
FINAL_PROJECT_COVERS_FROM = 28
FINAL_PROJECT_COVERS_TO = 36

# Module unit definitions: (module_title, [lecture_numbers], readings_md).
UNITS: list[tuple[str, list[int], str]] = [
    (
        "Unit 1 — Highlights of Linear Algebra (Strang Ch I.1–I.9)",
        [1, 2, 3, 4, 5, 6, 7],
        "Readings: Strang Chapter I, sections 1–9 (multiplication Ax via "
        "columns, AB factorizations, orthogonal matrices, eigenvalues, "
        "positive definiteness, SVD, Eckart-Young).",
    ),
    (
        "Unit 2 — Norms, Least Squares & Ax=b (Strang Ch I.11, II.2)",
        [8, 9, 10, 11],
        "Readings: Strang §I.11 (norms) and §II.2 (least squares — four "
        "approaches), plus the Chapter II intro on large matrix difficulties.",
    ),
    (
        "Unit 3 — Numerical & Randomized Linear Algebra (Strang Ch II)",
        [12, 13],
        "Readings: Strang §II.1 (numerical methods for eigenvalues/SVD) and "
        "§II.4 (randomized matrix multiplication).",
    ),
    (
        "Unit 4 — Sensitivity, Low Rank & Saddle Points (Strang Ch III, §V.1)",
        [14, 15, 16, 17, 18, 19],
        "Readings: Strang Chapter III §§1–3 (changes in A⁻¹, derivatives, "
        "rapidly decreasing singular values, interlacing eigenvalues) and "
        "§V.1 for the maxmin principle in Lec 19.",
    ),
    (
        "Unit 5 — Convex Optimization (Strang Ch VI)",
        [20, 21, 22, 23, 24, 25],
        "Readings: Strang Chapter VI §§1–5 (definitions/inequalities, "
        "gradient descent, momentum, linear programming + two-person games, "
        "stochastic gradient descent / ADAM).",
    ),
    (
        "Unit 6 — Deep Learning Fundamentals (Strang Ch VII)",
        [26, 27, 28, 29],
        "Readings: Strang §§VII.1 (deep net construction) and VII.3 "
        "(backpropagation). Lectures 28–29 were unrecorded Julia/Python lab "
        "sessions; for self-study, work through Strang's online code "
        "examples (linked from his book site) instead.",
    ),
    (
        "Unit 7 — Special Matrices, Applications & Capstone (Strang Ch IV + Final Project)",
        [30, 31, 32, 33, 34, 35, 36],
        "Readings: Strang Chapter IV (special matrices: circulants, "
        "Fourier matrix, distance matrices, graph clustering, deep learning "
        "matrices), plus VII.1/IV.10 for Lec 33 and §III.3/§VII.2 for "
        "Lec 36 (Edelman's Julia talk). The Final Project replaces additional "
        "homework in this stretch.",
    ),
]

SYLLABUS_MD = """## Prerequisites
18.06 Linear Algebra (or equivalent comfort with matrices, eigenvalues, and
SVD). 18.065 takes those tools and applies them to data analysis, signal
processing, and machine learning — Strang's "applied half" sequel to 18.06.

## Textbook
- Strang, Gilbert. *Linear Algebra and Learning from Data*.
  Wellesley-Cambridge Press, 2019. ISBN 978-0692196380.
- Strang's companion site: <https://math.mit.edu/~gs/learningfromdata/> —
  table of contents, sample chapters, and code examples for the labs.

## Grading (self-study)
| Component | Weight |
|---|---|
| Problem sets (6) | 70% |
| Final Project | 30% |

The original course graded "based on all three elements: homework, lab, final
project" with no published percentages. There were **no exams**. For
self-study we keep the no-exams structure and split as 70/30 between problem
sets and the project — close to a typical capstone-with-coursework split.

## Problem-set policy
OCW publishes all problem sets as a single combined PDF. Each of the six
self-study PSets here points to that same PDF and spans a contiguous lecture
range — work the relevant sections as you reach them. Don't search for
solutions online; let the AI generate the reference key after you submit.

## Final Project
The original course substitutes a project for the last three weekly
homeworks. Strang's Final Project page lists ~13 topic suggestions (SVD/PCA,
random matrices, gradient-descent variants, sparse/L1 methods, matrix
completion, neural-net experiments, low-rank approximation). Pick one, work
it deeply, and submit a writeup + code. The AI grades this in **project
mode**: no reference solution, evaluation is on quality of approach, depth
of analysis, clarity of writing, and overall effort.
"""

HOME_MD = """**MIT 18.065 — Matrix Methods in Data Analysis, Signal Processing,
and Machine Learning (Strang, Spring 2018).** The term shown above is *your*
self-study term — edit it from the course settings when your plan shifts.

This is Strang's "applied half" of linear algebra: SVD and Eckart-Young low-
rank approximation, norms and least squares, randomized algorithms, sensitivity
and saddle points, convex optimization (gradient descent, momentum, SGD),
neural networks and backpropagation, special matrices (circulants, Fourier,
distance, clustering). All taught in Strang's accessible-but-honest style,
with extensive lecture videos.

Prerequisite: 18.06 (or comparable working knowledge of linear algebra). Pairs
naturally with 18.700 — do 18.700 first for proof maturity, then 18.065 for
the modern applied half. Source: <https://ocw.mit.edu/courses/18-065-matrix-methods-in-data-analysis-signal-processing-and-machine-learning-spring-2018/>.
Jump to **Syllabus**, **Modules**, or **Assignments**.
"""

DESCRIPTION = (
    "Applied linear algebra for data analysis, signal processing, and ML: "
    "SVD, Eckart-Young, norms, least squares, randomized LA, sensitivity, "
    "saddle points, convex optimization, gradient descent / momentum / SGD, "
    "neural nets, backpropagation, circulants, Fourier matrix, distance "
    "matrices, graph clustering."
)

TEXTBOOK = (
    "Strang, Linear Algebra and Learning from Data (Wellesley-Cambridge "
    "Press, 2019). Companion site: math.mit.edu/~gs/learningfromdata/."
)


def _ps_description(k: int, topic: str) -> str:
    return (
        f"Problem Set {k} ({topic}). OCW publishes all problem sets as a "
        f"single combined PDF: [All Problem Sets (PDF page)]({PSETS_URL}). "
        f"Work the problems associated with lectures in this PSet's coverage "
        "range. Upload your worked solutions; the AI generates a reference "
        "solution and grades against it. OCW does not publish solutions — "
        "the AI key is your reference."
    )


def _final_project_description() -> str:
    return (
        "Final Project. Replaces the last three weekly problem sets, mirroring "
        "the original course. Strang's project page lists ~13 topic ideas "
        f"(SVD/PCA, random matrices, gradient-descent variants, sparse/L1, "
        f"matrix completion, neural-net experiments, low-rank approximation): "
        f"[Final Project page]({FINAL_PROJECT_URL}). Pick one direction, work "
        "it deeply, submit a writeup + code (any language; Strang's labs use "
        "Julia and Python). The AI grades this in **project mode** — no "
        "reference solution, evaluation is on quality of approach, depth of "
        "analysis, and clarity of writing."
    )


def _unit_items(lecture_numbers: list[int], readings_md: str) -> list[dict]:
    """One note item per lecture, showing the Strang chapter/section reading
    as the primary content. Recorded lectures get an inline video link in the
    note body; unrecorded labs (28-29) get a placeholder explanation. Closed
    with the unit-level Readings summary note."""
    items: list[dict] = []
    for n in lecture_numbers:
        topic, section = LECTURE_TOPICS[n]
        if n in LECTURE_VIDEO_SLUGS:
            text = f"**{section}.** {topic}. [Watch video →]({_video_url(n)})"
        else:
            text = (
                f"**{section}.** {topic}. *Not recorded — in-class lab session. "
                "Work through Strang's online code examples instead "
                "(linked from his book site).*"
            )
        items.append({"kind": "note", "title": f"Lec {n} — {topic}", "text_md": text})
    items.append({"kind": "note", "title": "Readings", "text_md": readings_md})
    return items


def _modules() -> list[tuple[str, list[dict]]]:
    """1 direct-links module + 7 unit modules + 1 Final-Project module = 9."""
    out: list[tuple[str, list[dict]]] = [
        (
            "Direct links",
            [
                {
                    "kind": "link",
                    "title": "18.065 course home (Strang, MIT OCW Spring 2018)",
                    "url": HOME,
                },
                {"kind": "link", "title": "Syllabus", "url": SYLLABUS_URL},
                {"kind": "link", "title": "Calendar", "url": CALENDAR_URL},
                {"kind": "link", "title": "Readings (lecture → Strang map)", "url": READINGS_URL},
                {"kind": "link", "title": "Video lectures (gallery)", "url": VIDEOS_INDEX_URL},
                {"kind": "link", "title": "Assignments page", "url": ASSIGNMENTS_URL},
                {
                    "kind": "link",
                    "title": "All Problem Sets (combined PDF page)",
                    "url": PSETS_URL,
                },
                {
                    "kind": "link",
                    "title": "Final Project (description + topic ideas)",
                    "url": FINAL_PROJECT_URL,
                },
                {"kind": "link", "title": "Instructor Insights (Strang)", "url": INSTRUCTOR_URL},
                {"kind": "link", "title": "Related resources", "url": RELATED_URL},
                {
                    "kind": "link",
                    "title": "Strang — Linear Algebra and Learning from Data (book site)",
                    "url": STRANG_BOOK_URL,
                },
            ],
        ),
    ]
    for title, lecture_nums, readings_md in UNITS:
        out.append((title, _unit_items(lecture_nums, readings_md)))
    out.append(
        (
            "Final Project",
            [
                {
                    "kind": "link",
                    "title": "Final Project page (description + ~13 topic ideas)",
                    "url": FINAL_PROJECT_URL,
                },
                {"kind": "assignment", "_assignment": "Final Project"},
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
        title="Matrix Methods in Data Analysis, Signal Processing, and Machine Learning",
        institution="Massachusetts Institute of Technology",
        # term_label is *your* self-study term, not the OCW recording year.
        term_label="Spring 2028",
        instructor="Prof. Gilbert Strang",
        external_home_url=HOME,
        status="planned",
        color="#0F4C81",  # deep navy — distinct from MIT-cardinal 18.100B and teal 18.700
        display_order=3,
        textbook=TEXTBOOK,
        home_page_md=HOME_MD,
        syllabus_md=SYLLABUS_MD,
        description=DESCRIPTION,
    )
    db.add(course)
    db.flush()

    g_ps = AssignmentGroup(
        course_id=course.id, name="Problem Sets", weight=70, drop_lowest_n=0, position=0
    )
    g_proj = AssignmentGroup(
        course_id=course.id, name="Final Project", weight=30, drop_lowest_n=0, position=1
    )
    db.add_all([g_ps, g_proj])
    db.flush()

    by_name: dict[str, Assignment] = {}
    for k, topic, lec_from, lec_to in PROBLEM_SETS:
        a = Assignment(
            course_id=course.id,
            assignment_group_id=g_ps.id,
            title=f"Problem Set {k} — {topic}",
            description_md=_ps_description(k, topic),
            points_possible=100,
            accepts_files=True,
            accepts_text=True,
            position=k - 1,
            published=True,
            covers_lecture_from=lec_from,
            covers_lecture_to=lec_to,
        )
        db.add(a)
        by_name[a.title] = a

    proj = Assignment(
        course_id=course.id,
        assignment_group_id=g_proj.id,
        title="Final Project",
        description_md=_final_project_description(),
        points_possible=100,
        accepts_files=True,
        accepts_text=True,
        # Project-style: AI grades on quality/effort, no reference solution.
        requires_solution_key=False,
        position=0,
        published=True,
        covers_lecture_from=FINAL_PROJECT_COVERS_FROM,
        covers_lecture_to=FINAL_PROJECT_COVERS_TO,
    )
    db.add(proj)
    by_name["Final Project"] = proj
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
# "Problem Set 7 — <topic>"
_PS_TITLE_RE = re.compile(r"^Problem Set (\d+)\b")

# Module-item titles whose URL is fixed.
_FIXED_TITLE_TO_URL: dict[str, str] = {
    "18.065 course home (Strang, MIT OCW Spring 2018)": HOME,
    "Syllabus": SYLLABUS_URL,
    "Calendar": CALENDAR_URL,
    "Readings (lecture → Strang map)": READINGS_URL,
    "Video lectures (gallery)": VIDEOS_INDEX_URL,
    "Assignments page": ASSIGNMENTS_URL,
    "All Problem Sets (combined PDF page)": PSETS_URL,
    "Final Project (description + topic ideas)": FINAL_PROJECT_URL,
    "Final Project page (description + ~13 topic ideas)": FINAL_PROJECT_URL,
    "Instructor Insights (Strang)": INSTRUCTOR_URL,
    "Related resources": RELATED_URL,
    "Strang — Linear Algebra and Learning from Data (book site)": STRANG_BOOK_URL,
}


def update_urls(db: Session) -> dict:
    """Refresh every URL on the live MIT 18.065 course in place — fixed module
    items, per-lecture video URLs, and assignment description_md / coverage.
    Preserves submissions / AI solutions / announcements / grades."""
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

    # 1) Module-item URLs (fixed-title direct-links items).
    for m in course.modules:
        for it in m.items:
            counts["items_examined"] += 1
            if it.title in _FIXED_TITLE_TO_URL:
                new_url = _FIXED_TITLE_TO_URL[it.title]
                if new_url != it.external_url:
                    it.external_url = new_url
                    counts["items_updated"] += 1
            # Refresh per-lecture note text (chapter ref + embedded video URL).
            ln = _LECTURE_NOTE_RE.match(it.title or "")
            if ln and it.kind == "note":
                n = int(ln.group(1))
                spec = LECTURE_TOPICS.get(n)
                if spec is not None:
                    topic, section = spec
                    if n in LECTURE_VIDEO_SLUGS:
                        new_text = (
                            f"**{section}.** {topic}. "
                            f"[Watch video →]({_video_url(n)})"
                        )
                    else:
                        new_text = (
                            f"**{section}.** {topic}. *Not recorded — in-class "
                            "lab session. Work through Strang's online code "
                            "examples instead (linked from his book site).*"
                        )
                    if it.text_md != new_text:
                        it.text_md = new_text
                        counts["items_updated"] += 1

    # 2) Assignment description_md + lecture coverage.
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
        new_desc = _ps_description(k, topic)
        if a.description_md != new_desc:
            a.description_md = new_desc
            counts["assignments_updated"] += 1
        if a.covers_lecture_from != lec_from or a.covers_lecture_to != lec_to:
            a.covers_lecture_from = lec_from
            a.covers_lecture_to = lec_to
            counts["coverage_updated"] += 1

    proj = by_title.get("Final Project")
    if proj is not None:
        new_desc = _final_project_description()
        if proj.description_md != new_desc:
            proj.description_md = new_desc
            counts["assignments_updated"] += 1
        if (
            proj.covers_lecture_from != FINAL_PROJECT_COVERS_FROM
            or proj.covers_lecture_to != FINAL_PROJECT_COVERS_TO
        ):
            proj.covers_lecture_from = FINAL_PROJECT_COVERS_FROM
            proj.covers_lecture_to = FINAL_PROJECT_COVERS_TO
            counts["coverage_updated"] += 1

    db.commit()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the MIT 18.065 course.")
    parser.add_argument(
        "--force", action="store_true", help="delete an existing MIT 18.065 course first"
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
