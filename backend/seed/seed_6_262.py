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
import re
from urllib.parse import urljoin

import httpx
from sqlalchemy.orm import Session

from app.db import SessionLocal  # noqa: F401 — used in later tasks (main() CLI)
from app.models import Assignment, AssignmentGroup, Course, Module, ModuleItem
from app.services import storage

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


# 25 video-lecture URL slugs. Verified against the OCW video gallery.
LECTURE_VIDEO_SLUGS: dict[int, str] = {
    1:  "lecture-1-introduction-and-probability-review",
    2:  "lecture-2-more-review-the-bernoulli-process",
    3:  "lecture-3-law-of-large-numbers-convergence",
    4:  "lecture-4-poisson-the-perfect-arrival-process",
    5:  "lecture-5-poisson-combining-and-splitting",
    6:  "lecture-6-from-poisson-to-markov",
    7:  "lecture-7-finite-state-markov-chains-the-matrix-approach",
    8:  "lecture-8-markov-eigenvalues-and-eigenvectors",
    9:  "lecture-9-markov-rewards-and-dynamic-programming",
    10: "lecture-10-renewals-and-the-strong-law-of-large-numbers",
    11: "lecture-11-renewals-strong-law-and-rewards",
    12: "lecture-12-renewal-rewards-stopping-trials-and-walds-inequality",
    13: "lecture-13-little-m-g-1-ensemble-averages",
    14: "lecture-14-review",
    15: "lecture-15-the-last-renewal",
    16: "lecture-16-renewals-and-countable-state-markov",
    17: "lecture-17-countable-state-markov-chains",
    18: "lecture-18-countable-state-markov-chains-and-processes",
    19: "lecture-19-countable-state-markov-processes",
    20: "lecture-20-markov-processes-and-random-walks",
    21: "lecture-21-hypothesis-testing-and-random-walks",
    22: "lecture-22-random-walks-and-thresholds",
    23: "lecture-23-martingales-plain-sub-and-super",
    24: "lecture-24-martingales-stopping-and-converging",
    25: "lecture-25-putting-it-all-together",
}


def _video_url(n: int) -> str:
    return f"{BASE}/resources/{LECTURE_VIDEO_SLUGS[n]}/"


_PDF_HREF_RE = re.compile(r'href="(/courses/[^"]+\.pdf)"')


def _resolve_pdf_url(slug: str) -> str:
    """Scrape ``BASE/resources/{slug}/`` for the PDF URL matching this slug.

    OCW renders PDFs with a content-hash-prefixed href (e.g.
    ``/courses/.../c12643..._MIT6_262S11_assn01_sol.pdf``) where the
    filename embeds the slug stem in uppercase (``MIT6_262S11_…``). The
    hash is not derivable from the slug, so we scrape the landing page.

    Multiple PDFs may be linked on one page (transcripts, related readings);
    we pick the one whose filename actually matches the requested slug.

    Raises ``RuntimeError`` if no PDF matches (e.g. OCW restructured the
    page or removed the resource).
    """
    page_url = f"{BASE}/resources/{slug}/"
    resp = httpx.get(page_url, timeout=30)
    resp.raise_for_status()
    needle = slug.lower()  # OCW filenames are case-insensitive-equivalent
    for path in _PDF_HREF_RE.findall(resp.text):
        if needle in path.lower():
            return urljoin("https://ocw.mit.edu", path)
    raise RuntimeError(f"no PDF link matching slug '{slug}' on {page_url}")


def _storage_key_for(slug: str) -> str:
    """Path inside the ``solutions`` bucket. Namespaced under ``official/6_262/``
    so it doesn't collide with AI-generated solutions (``solutions/{id}.md``)."""
    return f"official/6_262/{slug}.pdf"


def _attach_official_solution(db: Session, a: Assignment, slug: str) -> None:
    """Download Gallager's solution PDF for ``slug`` and attach it to ``a``.

    Idempotent: if ``a.official_solution_file_path`` already points at a
    readable Storage object, do nothing.

    Graceful: any download/upload failure is logged to stdout and leaves
    ``official_solution_url`` set as the AI's URL-only fallback.
    """
    storage_key = _storage_key_for(slug)
    landing_url = f"{BASE}/resources/{slug}/"

    # Always set the URL — it's cheap and serves as a fallback flag.
    a.official_solution_url = landing_url

    if a.official_solution_file_path == storage_key:
        try:
            storage.read_bytes("solutions", storage_key)
            return  # already uploaded; skip network
        except Exception:  # noqa: BLE001 — re-download if storage object is gone
            pass

    try:
        pdf_url = _resolve_pdf_url(slug)
        resp = httpx.get(pdf_url, timeout=60)
        resp.raise_for_status()
        storage.upload_bytes("solutions", storage_key, resp.content, "application/pdf")
        # Storage write commits immediately; the file_path assignment below
        # only persists on the caller's db.commit().
        a.official_solution_file_path = storage_key
    except Exception as exc:  # noqa: BLE001
        # Don't break the seed for one missing solution; degrade to URL-only.
        print(f"warn(seed_6_262): solution upload failed for {slug}: {exc}")


# (lecture_number, topic, gallager_reading). The OCW calendar publishes
# lecture topics but NOT per-lecture chapter references; chapter mapping
# below is by topical match against Gallager's table of contents.
LECTURE_TOPICS: dict[int, tuple[str, str]] = {
    1:  ("Introduction & probability review",            "Gallager Ch 1 (review)"),
    2:  ("Bernoulli process",                            "Gallager Ch 1 §1.3"),
    3:  ("Law of large numbers; convergence",            "Gallager Ch 1 §1.5"),
    4:  ("Poisson — the perfect arrival process",        "Gallager Ch 2 §§2.1–2.2"),
    5:  ("Poisson combining & splitting",                "Gallager Ch 2 §§2.3–2.4"),
    6:  ("From Poisson to Markov",                       "Gallager Ch 2 → Ch 3 (transition)"),
    7:  ("Finite-state Markov chains: matrix approach",  "Gallager Ch 3 §3.1"),
    8:  ("Markov eigenvalues & eigenvectors",            "Gallager Ch 3 §§3.2–3.4"),
    9:  ("Markov rewards & dynamic programming",         "Gallager Ch 3 §3.5"),
    10: ("Renewals & the strong law",                    "Gallager Ch 4 §§4.1–4.2"),
    11: ("Renewals: strong law & rewards",               "Gallager Ch 4 §§4.3–4.4"),
    12: ("Renewal rewards; Wald's inequality",           "Gallager Ch 4 §§4.5–4.6"),
    13: ("Little's theorem; M/G/1; ensemble averages",   "Gallager Ch 4 §4.7"),
    14: ("Review",                                       "Gallager Ch 1–4 (review)"),
    15: ("The last renewal",                             "Gallager Ch 4 §4.8"),
    16: ("Renewals & countable-state Markov",            "Gallager Ch 5 §5.1"),
    17: ("Countable-state Markov chains",                "Gallager Ch 5 §§5.2–5.3"),
    18: ("Countable-state Markov chains & processes",    "Gallager Ch 5 → Ch 6 (transition)"),
    19: ("Countable-state Markov processes",             "Gallager Ch 6 §§6.1–6.3"),
    20: ("Markov processes & random walks",              "Gallager Ch 6 → Ch 7 (transition)"),
    21: ("Hypothesis testing & random walks",            "Gallager Ch 7 §§7.1–7.2"),
    22: ("Random walks & thresholds",                    "Gallager Ch 7 §§7.3–7.4"),
    23: ("Martingales (plain, sub, super)",              "Gallager Ch 7 §7.5"),
    24: ("Martingales: stopping & converging",           "Gallager Ch 7 §§7.6–7.7"),
    25: ("Putting it all together",                      "Gallager Ch 1–7 (full-course review)"),
}


# 12 problem sets — (number, topic, covers_lecture_from, covers_lecture_to).
# Due dates from the calendar: after Lec 3 / 5 / 7 / 9 / 11 / 13 / 15 / 18 /
# 19 / 21 / 23. Calendar publishes 11 due dates; PS12 is inferred to land
# after Lec 25 to cover the tail (24–25).
PROBLEM_SETS: list[tuple[int, str, int, int]] = [
    (1,  "Probability review; Bernoulli",                  1,  3),
    (2,  "Poisson processes",                              4,  5),
    (3,  "Finite-state Markov: matrix approach",           6,  7),
    (4,  "Markov eigenvalues; rewards",                    8,  9),
    (5,  "Renewals: strong law",                          10, 11),
    (6,  "Renewal rewards; Wald",                         12, 13),
    (7,  "Review; M/G/1",                                 14, 15),
    (8,  "Countable-state Markov chains",                 16, 18),
    (9,  "Countable-state Markov processes",              19, 19),
    (10, "Markov processes; random walks",                20, 21),
    (11, "Random walks & thresholds",                     22, 23),
    (12, "Martingales; cumulative",                       24, 25),
]


# Midterm & Final exam specs: (paper_year, covers_from, covers_to,
# tuple_of_practice_years). The graded assignment is the 2011 paper; other
# years are linked from the description as practice (not graded).
MIDTERM_SPEC: tuple[int, int, int, tuple[int, ...]] = (2011, 1, 14, (2010, 2009))
FINAL_SPEC: tuple[int, int, int, tuple[int, ...]] = (2011, 15, 25, (2009,))


# Module unit definitions: (module_title, [lecture_numbers], readings_md).
UNITS: list[tuple[str, list[int], str]] = [
    (
        "Unit 1 — Probability review & Bernoulli",
        [1, 2, 3],
        "Readings: Gallager Chapter 1. Probability spaces, expectations, "
        "convergence; the Bernoulli process.",
    ),
    (
        "Unit 2 — Poisson processes",
        [4, 5],
        "Readings: Gallager Chapter 2. The Poisson process, its memoryless "
        "structure, combining and splitting independent streams.",
    ),
    (
        "Unit 3 — Finite-state Markov chains",
        [6, 7, 8, 9],
        "Readings: Gallager Chapter 3. Transition matrices, eigenvalue "
        "analysis, classification of states, Markov rewards and dynamic "
        "programming.",
    ),
    (
        "Unit 4 — Renewal processes",
        [10, 11, 12, 13, 14, 15],
        "Readings: Gallager Chapter 4. Renewal counting processes, the "
        "strong law and key renewal theorem, renewal-reward processes, "
        "Wald's inequality, Little's theorem, M/G/1 queues, ensemble "
        "averages. Lec 14 is a review session.",
    ),
    (
        "Unit 5 — Countable-state Markov chains & processes",
        [16, 17, 18, 19, 20],
        "Readings: Gallager Chapters 5 and 6. Countable-state Markov "
        "chains, classification (transience / null- vs positive-recurrence), "
        "countable-state Markov processes in continuous time, birth-death "
        "and queueing applications.",
    ),
    (
        "Unit 6 — Random walks & martingales",
        [21, 22, 23, 24, 25],
        "Readings: Gallager Chapter 7. Hypothesis testing, random walks, "
        "first-passage and threshold problems, martingales (plain, sub-, "
        "super-), optional stopping, martingale convergence. Lec 25 is a "
        "full-course wrap-up.",
    ),
]


# Gallager textbook chapter PDFs (mirrored on OCW). Slug → display title.
GALLAGER_CHAPTERS: list[tuple[str, str]] = [
    ("mit6_262s11_front", "Front matter"),
    ("mit6_262s11_chap01", "Chapter 1"),
    ("mit6_262s11_chap02", "Chapter 2"),
    ("mit6_262s11_chap03", "Chapter 3"),
    ("mit6_262s11_chap04", "Chapter 4"),
    ("mit6_262s11_chap05", "Chapter 5"),
    ("mit6_262s11_chap06", "Chapter 6"),
    ("mit6_262s11_chap07", "Chapter 7"),
    ("mit6_262s11_back", "Back matter"),
]


def _gallager_chap_url(slug: str) -> str:
    return f"{BASE}/resources/{slug}/"


def _unit_items(lecture_numbers: list[int], readings_md: str) -> list[dict]:
    """For each lecture: a 'note' item with Gallager chapter+topic as primary
    text, followed by a [Watch video →] link. Closed with the unit-level
    Readings note.
    """
    items: list[dict] = []
    for n in lecture_numbers:
        topic, ref = LECTURE_TOPICS[n]
        items.append(
            {
                "kind": "note",
                "title": f"Lec {n} — {topic}",
                "text_md": f"**{ref}.** {topic}.",
            }
        )
        items.append(
            {
                "kind": "link",
                "title": "Watch video →",
                "url": _video_url(n),
                "indent": 1,
            }
        )
    items.append({"kind": "note", "title": "Readings", "text_md": readings_md})
    return items


def _direct_links_items() -> list[dict]:
    return [
        {"kind": "link", "title": "6.262 course home (Gallager, MIT OCW Spring 2011)", "url": HOME},
        {"kind": "link", "title": "Syllabus", "url": SYLLABUS_URL},
        {"kind": "link", "title": "Calendar", "url": CALENDAR_URL},
        {"kind": "link", "title": "Course notes (Gallager chapter PDFs)", "url": COURSE_NOTES_URL},
        {"kind": "link", "title": "Assignments index", "url": ASSIGNMENTS_URL},
        {"kind": "link", "title": "Exams index", "url": EXAMS_URL},
        {"kind": "link", "title": "Video lectures gallery", "url": VIDEOS_INDEX_URL},
        {
            "kind": "link",
            "title": "Gallager — updated draft notes (web archive)",
            "url": GALLAGER_NOTES_ARCHIVE_URL,
        },
    ]


def _gallager_notes_items() -> list[dict]:
    return [
        {"kind": "link", "title": title, "url": _gallager_chap_url(slug)}
        for slug, title in GALLAGER_CHAPTERS
    ]


def _practice_exams_items() -> list[dict]:
    """Links to all 5 historical papers + their solutions, for browseability.
    These are NOT graded assignments (see MIDTERM_SPEC / FINAL_SPEC — only the
    2011 papers are gradable). 10 items total."""
    out: list[dict] = []
    for year in (2011, 2010, 2009):
        out.append(
            {"kind": "link", "title": f"Midterm {year} — paper", "url": _exam_url("mid", year)}
        )
        out.append(
            {
                "kind": "link",
                "title": f"Midterm {year} — solution",
                "url": _exam_sol_url("mid", year),
                "indent": 1,
            }
        )
    for year in (2011, 2009):
        out.append(
            {"kind": "link", "title": f"Final {year} — paper", "url": _exam_url("final", year)}
        )
        out.append(
            {
                "kind": "link",
                "title": f"Final {year} — solution",
                "url": _exam_sol_url("final", year),
                "indent": 1,
            }
        )
    return out


def _modules() -> list[tuple[str, list[dict]]]:
    """9 modules total: direct-links + 6 unit modules + Gallager notes + Practice exams."""
    out: list[tuple[str, list[dict]]] = [("Direct links", _direct_links_items())]
    for title, lecture_nums, readings_md in UNITS:
        out.append((title, _unit_items(lecture_nums, readings_md)))
    out.append(("Gallager course notes", _gallager_notes_items()))
    out.append(("Practice exams", _practice_exams_items()))
    return out


SYLLABUS_MD = """## Prerequisites
6.041 / 6.431 (Probabilistic Systems Analysis & Applied Probability), or
equivalent comfort with elementary probability: discrete and continuous random
variables, expectation, conditioning, basic limit theorems. Some patience for
careful mathematical reasoning.

## Textbook
- **Primary** — Gallager, *Stochastic Processes: Theory for Applications*
  (Cambridge University Press, 2013). The OCW course notes (chapter PDFs
  linked from the **Gallager course notes** module) are the 2011 draft of
  this same book.
- **Prerequisite text** — Bertsekas & Tsitsiklis, *Introduction to Probability*
  (Athena Scientific, 2nd ed. 2008) — referenced for probability review.
- The "updated and improved version" of Gallager's draft notes lives at the
  web-archive link in the Direct links module.

## Grading (mirror OCW)
| Component | Weight |
|---|---|
| Problem sets (12) | 20% |
| Midterm Quiz | 35% |
| Final Exam | 45% |

The original 6.262 syllabus splits the grade as 20% homework / 35% quiz /
45% final. We mirror it exactly. Unlike most of the seeded courses, OCW
publishes Gallager's official solutions for every problem set and every
historical exam, so the AI grader compares your submission against the
real reference — not a regenerated AI key. (You can find the solution
PDFs linked from each assignment.)

## Problem-set policy
"Homework assignments will be passed out each Wednesday in class; your
solutions are due the following Wednesday and official solutions will be
available before the weekend." Collaboration is encouraged, but write your
own solutions. For self-study: pick a weekly cadence and stick to it;
don't peek at solutions until you've made an honest attempt.

## Exams
The graded midterm is the **Spring 2011 paper**; the graded final is the
**Spring 2011 final**. OCW also publishes papers from 2010 (midterm only)
and 2009 (midterm + final) with full solutions — they're linked from each
exam assignment's description as additional practice, and also collected
in the **Practice exams** module.
"""

HOME_MD = """**MIT 6.262 — Discrete Stochastic Processes (Gallager, Spring 2011).**

Course materials mirrored from MIT OCW. The term shown above is *your*
self-study term — edit it from the course settings when your plan shifts.

The proof-flavoured stochastic-processes course at MIT. Builds out the
machinery for working with random processes that evolve in time — Bernoulli
and Poisson, finite- and countable-state Markov chains, Markov processes,
renewal processes (with Wald, M/G/1 queueing, Little's theorem), random
walks and first-passage problems, and martingales (plain / sub- / super-,
with optional stopping). The course notes are the working draft of
Gallager's 2013 Cambridge textbook *Stochastic Processes: Theory for
Applications*.

Source: <https://ocw.mit.edu/courses/6-262-discrete-stochastic-processes-spring-2011/>.
Textbook: Gallager (Cambridge 2013); the 2011 draft chapter PDFs are
mirrored on OCW. Jump to **Syllabus**, **Modules**, or **Assignments**.
"""

DESCRIPTION = (
    "Discrete stochastic processes: Bernoulli and Poisson processes, "
    "finite- and countable-state Markov chains and processes, renewal "
    "processes (Wald, M/G/1, Little's theorem), random walks and "
    "first-passage problems, martingales and optional stopping."
)

TEXTBOOK = (
    "Gallager, Stochastic Processes: Theory for Applications "
    "(Cambridge 2013) — primary. The 2011 draft is mirrored on OCW "
    "chapter-by-chapter. Bertsekas-Tsitsiklis, Introduction to "
    "Probability (Athena 2008), is the prereq probability text."
)


def _ps_description(k: int, topic: str, lec_from: int, lec_to: int) -> str:
    paper_url = _ps_url(k)
    sol_url = _ps_sol_url(k)
    return (
        f"Problem Set {k} ({topic}). Covers lectures {lec_from}–{lec_to}.\n\n"
        f"- Paper: [PS{k} PDF (landing page)]({paper_url})\n"
        f"- Reference solution: [PS{k} Solution (landing page)]({sol_url})\n\n"
        "Upload your worked solutions. The AI grades against Gallager's "
        "official solution (loaded from Storage). OCW publishes the public "
        "solution PDF at the link above."
    )


def _midterm_description(spec: tuple[int, int, int, tuple[int, ...]]) -> str:
    year, _f, _to, practice = spec
    paper_url = _exam_url("mid", year)
    sol_url = _exam_sol_url("mid", year)
    lines = [
        f"Midterm Quiz ({year} paper). Closed-book exam covering lectures 1–14.",
        "",
        f"- Paper: [{year} Midterm PDF]({paper_url})",
        f"- Reference solution: [{year} Midterm Solution]({sol_url})",
        "",
        "## Additional practice papers",
    ]
    for py in practice:
        lines.append(
            f"- Midterm {py}: [paper]({_exam_url('mid', py)}) · "
            f"[solution]({_exam_sol_url('mid', py)})"
        )
    lines.append("")
    lines.append(
        "Time yourself (80 minutes for the 2011 paper, matching the original "
        "course). Upload your attempt; the AI grades against Gallager's "
        "solution. The practice papers above are *not* graded — they're for "
        "self-paced review."
    )
    return "\n".join(lines)


def _final_description(spec: tuple[int, int, int, tuple[int, ...]]) -> str:
    year, _f, _to, practice = spec
    paper_url = _exam_url("final", year)
    sol_url = _exam_sol_url("final", year)
    lines = [
        f"Final Exam ({year} paper). Cumulative; emphasises lectures 15–25.",
        "",
        f"- Paper: [{year} Final PDF]({paper_url})",
        f"- Reference solution: [{year} Final Solution]({sol_url})",
        "",
        "## Additional practice papers",
    ]
    for py in practice:
        lines.append(
            f"- Final {py}: [paper]({_exam_url('final', py)}) · "
            f"[solution]({_exam_sol_url('final', py)})"
        )
    lines.append("")
    lines.append(
        "Time yourself (3 hours, matching the original course). Upload your "
        "attempt; the AI grades against Gallager's solution. The practice "
        "papers above are *not* graded — they're for self-paced review."
    )
    return "\n".join(lines)


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
        title="Discrete Stochastic Processes",
        institution="Massachusetts Institute of Technology",
        term_label="Summer 2028",  # user's self-study term, not OCW recording year
        instructor="Prof. Robert Gallager",
        external_home_url=HOME,
        status="planned",
        color="#4A2C82",  # deep purple — distinct from cardinal/teal/navy/tartan
        display_order=4,
        textbook=TEXTBOOK,
        home_page_md=HOME_MD,
        syllabus_md=SYLLABUS_MD,
        description=DESCRIPTION,
    )
    db.add(course)
    db.flush()

    g_ps = AssignmentGroup(
        course_id=course.id, name="Problem Sets", weight=20, drop_lowest_n=0, position=0
    )
    g_mid = AssignmentGroup(
        course_id=course.id, name="Midterm Quiz", weight=35, drop_lowest_n=0, position=1
    )
    g_final = AssignmentGroup(
        course_id=course.id, name="Final Exam", weight=45, drop_lowest_n=0, position=2
    )
    db.add_all([g_ps, g_mid, g_final])
    db.flush()

    # 12 PSets — create then attach the official solution PDF
    for k, topic, lec_from, lec_to in PROBLEM_SETS:
        a = Assignment(
            course_id=course.id,
            assignment_group_id=g_ps.id,
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
        db.flush()
        _attach_official_solution(db, a, f"mit6_262s11_assn{k:02d}_sol")

    # Midterm (2011 paper)
    mid_year, mid_from, mid_to, _ = MIDTERM_SPEC
    a = Assignment(
        course_id=course.id,
        assignment_group_id=g_mid.id,
        title=f"Midterm Exam ({mid_year} paper)",
        description_md=_midterm_description(MIDTERM_SPEC),
        points_possible=100,
        accepts_files=True,
        accepts_text=True,
        position=0,
        published=True,
        covers_lecture_from=mid_from,
        covers_lecture_to=mid_to,
        requires_solution_key=True,
    )
    db.add(a)
    db.flush()
    _attach_official_solution(db, a, f"{_exam_slug('mid', mid_year)}_sol")

    # Final (2011 paper)
    fin_year, fin_from, fin_to, _ = FINAL_SPEC
    a = Assignment(
        course_id=course.id,
        assignment_group_id=g_final.id,
        title=f"Final Exam ({fin_year} paper)",
        description_md=_final_description(FINAL_SPEC),
        points_possible=100,
        accepts_files=True,
        accepts_text=True,
        position=0,
        published=True,
        covers_lecture_from=fin_from,
        covers_lecture_to=fin_to,
        requires_solution_key=True,
    )
    db.add(a)
    db.flush()
    _attach_official_solution(db, a, f"{_exam_slug('final', fin_year)}_sol")

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

_LECTURE_NOTE_RE = re.compile(r"^Lec (\d+)\b")
_MIDTERM_TITLE_RE = re.compile(r"^Midterm Exam \((\d{4}) paper\)")
_FINAL_TITLE_RE = re.compile(r"^Final Exam \((\d{4}) paper\)")


def _fixed_title_to_url() -> dict[str, str]:
    """Map a module-item title to the URL it should always point to."""
    out: dict[str, str] = {
        "6.262 course home (Gallager, MIT OCW Spring 2011)": HOME,
        "Syllabus": SYLLABUS_URL,
        "Calendar": CALENDAR_URL,
        "Course notes (Gallager chapter PDFs)": COURSE_NOTES_URL,
        "Assignments index": ASSIGNMENTS_URL,
        "Exams index": EXAMS_URL,
        "Video lectures gallery": VIDEOS_INDEX_URL,
        "Gallager — updated draft notes (web archive)": GALLAGER_NOTES_ARCHIVE_URL,
    }
    for slug, title in GALLAGER_CHAPTERS:
        out[title] = _gallager_chap_url(slug)
    for year in (2011, 2010, 2009):
        out[f"Midterm {year} — paper"] = _exam_url("mid", year)
        out[f"Midterm {year} — solution"] = _exam_sol_url("mid", year)
    for year in (2011, 2009):
        out[f"Final {year} — paper"] = _exam_url("final", year)
        out[f"Final {year} — solution"] = _exam_sol_url("final", year)
    return out


def update_urls(db: Session) -> dict:
    """Refresh URLs on the live MIT 6.262 course in place — module-item URLs,
    per-lecture note text, and assignment description_md / coverage / URL.
    Does NOT re-download PDFs (use --refresh-solutions for that). Preserves
    submissions / AI solutions / announcements / grades.

    Counter semantics:
      - ``items_examined`` / ``items_updated``: per module-item.
      - ``assignments_updated``: count of *distinct* assignments with any
        field change (description_md and/or official_solution_url). An
        assignment with two field changes is counted once.
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

    # 1) Module-item external URLs.
    for m in course.modules:
        for it in m.items:
            counts["items_examined"] += 1
            if it.title in fixed:
                new_url = fixed[it.title]
                if new_url != it.external_url:
                    it.external_url = new_url
                    counts["items_updated"] += 1
            if it.title == "Watch video →":
                # Look back at preceding sibling "Lec N — ..." note to find N.
                mn = None
                for prev in m.items:
                    if prev.position == it.position - 1:
                        mn = _LECTURE_NOTE_RE.match(prev.title or "")
                        break
                if mn:
                    n = int(mn.group(1))
                    new_url = _video_url(n)
                    if new_url != it.external_url:
                        it.external_url = new_url
                        counts["items_updated"] += 1

    # 2) Per-lecture note text (refresh Gallager chapter ref).
    for m in course.modules:
        for it in m.items:
            mn = _LECTURE_NOTE_RE.match(it.title or "")
            if not mn:
                continue
            n = int(mn.group(1))
            spec = LECTURE_TOPICS.get(n)
            if spec is None:
                continue
            topic, ref = spec
            new_text = f"**{ref}.** {topic}."
            if it.text_md != new_text:
                it.text_md = new_text
                counts["items_updated"] += 1

    # 3) Assignments: refresh description_md, coverage, official_solution_url.
    dirty_assignments: set[str] = set()
    by_title = {a.title: a for a in course.assignments}
    for k, topic, lec_from, lec_to in PROBLEM_SETS:
        a = next(
            (
                x for t, x in by_title.items()
                if t.startswith(f"Problem Set {k} ")
            ),
            None,
        )
        if a is None:
            continue
        new_desc = _ps_description(k, topic, lec_from, lec_to)
        if a.description_md != new_desc:
            a.description_md = new_desc
            dirty_assignments.add(a.id)
        if a.covers_lecture_from != lec_from or a.covers_lecture_to != lec_to:
            a.covers_lecture_from = lec_from
            a.covers_lecture_to = lec_to
            counts["coverage_updated"] += 1
        new_url = _ps_sol_url(k)
        if a.official_solution_url != new_url:
            a.official_solution_url = new_url
            dirty_assignments.add(a.id)

    for title_re, spec, kind, builder in (
        (_MIDTERM_TITLE_RE, MIDTERM_SPEC, "mid", _midterm_description),
        (_FINAL_TITLE_RE, FINAL_SPEC, "final", _final_description),
    ):
        year, lec_from, lec_to, _ = spec
        a = next(
            (x for t, x in by_title.items() if title_re.match(t)),
            None,
        )
        if a is None:
            continue
        new_desc = builder(spec)
        if a.description_md != new_desc:
            a.description_md = new_desc
            dirty_assignments.add(a.id)
        if a.covers_lecture_from != lec_from or a.covers_lecture_to != lec_to:
            a.covers_lecture_from = lec_from
            a.covers_lecture_to = lec_to
            counts["coverage_updated"] += 1
        new_url = _exam_sol_url(kind, year)
        if a.official_solution_url != new_url:
            a.official_solution_url = new_url
            dirty_assignments.add(a.id)

    counts["assignments_updated"] = len(dirty_assignments)

    db.commit()
    return counts
