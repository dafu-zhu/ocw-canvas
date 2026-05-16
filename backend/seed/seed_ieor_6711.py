"""Seed the Columbia IEOR 6711 — Stochastic Models I course (Ward Whitt, Fall 2013).

Run:  cd backend && uv run python -m seed.seed_ieor_6711 [flags below]
Flags: [--force] [--update-urls] [--refresh-solutions]
Source: https://www.columbia.edu/~ww2040/6711F13/IEOR6711F13.html

Mirrors the ``seed_6_262`` shape, including the official-solution upload
pipeline, with three differences:

  - Source is Whitt's Columbia personal page (behind Cloudflare). The seed
    sends a browser-style User-Agent; probing showed PDFs are reachable.
    Graceful URL-only fallback covers any future tightening of the rules.
  - URLs are flat — ``{BASE}/homewk{N}Sols.pdf`` directly — so there is no
    hash-prefix scrape step (vs. ``seed_6_262._resolve_pdf_url``).
  - Textbook (Ross 2e) is not freely available; the seed only links the
    publisher page, not chapter PDFs.

Fall 2013 ran TWO midterms (Oct 6 covering Ch 1–2; Nov 17 covering Ch 3–4)
plus a Dec 15 final. Grading defaults to 30/20/20/30 — flagged in syllabus
as approximate since Whitt's page doesn't publish exact weights.
"""
from __future__ import annotations

import argparse

import httpx
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Assignment, AssignmentGroup, Course, Module, ModuleItem
from app.services import storage

CODE = "COLUMBIA IEOR 6711"
BASE = "https://www.columbia.edu/~ww2040/6711F13"
HOME = f"{BASE}/IEOR6711F13.html"
LECTURES_INDEX_URL = f"{BASE}/lectures6711.html"
HOMEWORK_INDEX_URL = f"{BASE}/homework6711.html"
LAPLACE_NOTES_URL = f"{BASE}/homewkLTnotes.pdf"
ROSS_TEXTBOOK_URL = (
    "https://www.wiley.com/en-us/Stochastic+Processes%2C+2nd+Edition-p-9780471120629"
)

_USER_AGENT = "Mozilla/5.0 (compatible; ocw-canvas-seed/1.0)"


# 20 primary lecture-note PDFs from Whitt's Fall 2013 lectures index.
# Fields: (lecture_number, url_slug, iso_date, topic, ross_reading_hint).
# Slugs come verbatim from `lectures6711.html`. The MMDD pattern is irregular —
# some files use date suffix only (lect0903, lect1010), one uses YYMMDD
# (lect091913), the CLT lecture has its own name (lectCLT), and the CTMC notes
# span multiple late-November sessions under one consolidated PDF
# (CTMCnotes120413). Class meetings without a published PDF (Nov 14 review,
# Nov 21/26, Dec 3/5) reference Ross or the consolidated CTMC notes — they
# are not included in this module so the list mirrors what Whitt actually
# published.
LECTURE_NOTES: list[tuple[int, str, str, str, str]] = [
    (1, "lect0903", "2013-09-03", "LLN; random variables", "Ross Ch 1"),
    (2, "lect0905", "2013-09-05", "Modes of convergence; SLLN proof", "Ross Ch 1"),
    (3, "lectCLT", "2013-09-10", "Normal approximation; CLT", "Ross Ch 1"),
    (4, "lect0912", "2013-09-12", "Transforms", "Ross Ch 1"),
    (5, "lect0917", "2013-09-17", "The exponential distribution", "Ross Ch 2 §2.1"),
    (6, "lect091913", "2013-09-19", "Poisson process as a special case", "Ross Ch 2 §2.2"),
    (7, "lect0926", "2013-09-26", "Mt/G/infinity queue & staffing", "Ross Ch 2 §§2.3–2.4"),
    (8, "lect1001", "2013-10-01", "Compound Poisson process", "Ross Ch 2 §2.5"),
    (9, "lect1003", "2013-10-03", "Simulating non-homogeneous Poisson", "Ross Ch 2 §2.4"),
    (10, "lect1008", "2013-10-08", "Elementary renewal-reward theory", "Ross Ch 3 §3.6"),
    (11, "lect1010", "2013-10-10", "Renewal function & renewal equation", "Ross Ch 3 §§3.3–3.5"),
    (12, "lect1015", "2013-10-15", "Inspection paradox; excess and age", "Ross Ch 3 §3.5"),
    (13, "lect1017", "2013-10-17", "Patterns", "Ross Ch 3"),
    (14, "lect1022", "2013-10-22", "Blackwell's renewal theorem (coupling)", "Ross Ch 3 §3.5"),
    (15, "lect1024", "2013-10-24", "Markov chains — introduction", "Ross Ch 4 §§4.1–4.3"),
    (16, "lect1029", "2013-10-29", "Contraction approach to DTMCs", "Ross Ch 4 §4.4"),
    (17, "lect1031", "2013-10-31", "M/G/1 queue", "Ross Ch 4 §4.5"),
    (18, "lect1107", "2013-11-07", "Reversibility", "Ross Ch 4 §4.7"),
    (19, "lect1112", "2013-11-12", "Regenerative & semi-Markov processes", "Ross Ch 4 §4.8"),
    (20, "CTMCnotes120413", "2013-11-19", "CTMCs — comprehensive notes", "Ross Ch 5"),
]


# 13 problem sets — (number, topic, lec_from, lec_to, ross_chapter_str).
# Topic + chapter mapping comes from `homework6711.html`. Lecture ranges
# correspond to LECTURE_NOTES indices above. HW5 and HW11 were "not required
# to be turned in" by Whitt; we keep them as graded for self-study.
PROBLEM_SETS: list[tuple[int, str, int, int, str]] = [
    (1,  "Probability",                              1,  2,  "Ross Ch 1"),
    (2,  "More probability",                         3,  4,  "Ross Ch 1"),
    (3,  "Poisson process",                          5,  6,  "Ross Ch 2"),
    (4,  "More Poisson process",                     7,  8,  "Ross Ch 2"),
    (5,  "Even more Poisson (optional turn-in)",     8,  9,  "Ross Ch 2"),
    (6,  "Renewal theory",                          10, 12,  "Ross Ch 3"),
    (7,  "Even more renewal theory",                12, 14,  "Ross Ch 3"),
    (8,  "Still more renewal theory",               14, 16,  "Ross Ch 3"),
    (9,  "Markov chains",                           15, 18,  "Ross Ch 4"),
    (10, "Markov chains (continued)",               17, 19,  "Ross Ch 4"),
    (11, "Markov chains (optional turn-in)",        19, 19,  "Ross Ch 4"),
    (12, "Continuous-time Markov chains",           20, 20,  "Ross Ch 5"),
    (13, "More continuous-time Markov chains",      20, 20,  "Ross Ch 5"),
]


# Exam specs: (paper_filename_stem, sols_filename_stem, lec_from, lec_to,
#              chapters_str, date_str).
MIDTERM_ONE_SPEC = (
    "midtermOne6711F13", "midtermOne6711F13sols",
    1, 9, "Chapters 1–2", "2013-10-06",
)
MIDTERM_TWO_SPEC = (
    "midtermTwo6711F13", "midtermTwo6711F13sols",
    10, 19, "Chapters 3–4", "2013-11-17",
)
FINAL_SPEC = (
    "final6711F13", "final6711F13sols",
    1, 20, "cumulative (Chapters 1–5)", "2013-12-15",
)


def _ps_paper_url(k: int) -> str:
    return f"{BASE}/homewk{k}.pdf"


def _ps_sol_url(k: int) -> str:
    return f"{BASE}/homewk{k}Sols.pdf"


def _ps_sol_filename(k: int) -> str:
    return f"homewk{k}Sols.pdf"


def _exam_paper_url(stem: str) -> str:
    return f"{BASE}/{stem}.pdf"


def _storage_key_for(filename: str) -> str:
    """Path inside the ``solutions`` bucket. Namespaced under ``official/ieor_6711/``
    so it doesn't collide with AI-generated solutions or other seeds' PDFs."""
    return f"official/ieor_6711/{filename}"


def _attach_official_solution(db: Session, a: Assignment, filename: str) -> None:
    """Download Whitt's solution PDF for ``filename`` and attach it to ``a``.

    On success: sets ``a.official_solution_file_path`` to the Storage key and
    clears ``a.official_solution_url`` so the AI grader resolves to the
    'official_file' branch and reads the PDF directly. On failure: sets
    ``a.official_solution_url`` only — the AI grader uses the URL-only branch
    ("solution exists at <url>; grade against standard rigor"). Either way
    the seed continues.

    Idempotent: if ``a.official_solution_file_path`` already points at a
    readable Storage object, skip the network round-trip.
    """
    storage_key = _storage_key_for(filename)
    direct_url = f"{BASE}/{filename}"

    if a.official_solution_file_path == storage_key:
        try:
            storage.read_bytes("solutions", storage_key)
            return  # already uploaded; skip network
        except Exception:  # noqa: BLE001 — re-download if storage object is gone
            pass

    try:
        resp = httpx.get(
            direct_url,
            timeout=60,
            follow_redirects=True,
            headers={"User-Agent": _USER_AGENT},
        )
        resp.raise_for_status()
        if not resp.content.startswith(b"%PDF"):
            raise RuntimeError(
                f"not a PDF (got first bytes {resp.content[:8]!r})"
            )
        storage.upload_bytes("solutions", storage_key, resp.content, "application/pdf")
        a.official_solution_file_path = storage_key
        a.official_solution_url = ""
    except Exception as exc:  # noqa: BLE001
        a.official_solution_url = direct_url
        print(f"warn(seed_ieor_6711): solution upload failed for {filename}: {exc}")


def _ps_description(k: int, topic: str, lec_from: int, lec_to: int, ross: str) -> str:
    return (
        f"Problem Set {k} — {topic}. Covers lectures {lec_from}–{lec_to} "
        f"({ross}).\n\n"
        f"- Paper: [HW{k} PDF]({_ps_paper_url(k)})\n"
        f"- Reference solution: [HW{k} Solutions]({_ps_sol_url(k)})\n\n"
        "Upload your worked solutions. The AI grades against Whitt's official "
        "solution (loaded from Storage when available, otherwise from the URL "
        "above)."
    )


def _exam_description(
    label: str,
    stem: str,
    sols_stem: str,
    chapters: str,
    date_str: str,
) -> str:
    return (
        f"{label} (Fall 2013 paper). Sat as a closed-book exam on {date_str}; "
        f"covers {chapters}.\n\n"
        f"- Paper: [Exam PDF]({_exam_paper_url(stem)})\n"
        f"- Reference solution: [Exam Solutions]({BASE}/{sols_stem}.pdf)\n\n"
        "Time yourself, upload your attempt; the AI grades against Whitt's "
        "solution."
    )


def _direct_links_items() -> list[dict]:
    return [
        {"kind": "link", "title": "IEOR 6711 course home (Whitt, Fall 2013)", "url": HOME},
        {"kind": "link", "title": "Lecture notes index", "url": LECTURES_INDEX_URL},
        {"kind": "link", "title": "Homework index", "url": HOMEWORK_INDEX_URL},
        {
            "kind": "link",
            "title": "Laplace transforms supplement (Whitt)",
            "url": LAPLACE_NOTES_URL,
        },
        {
            "kind": "link",
            "title": "Ross — Stochastic Processes 2e (Wiley publisher page)",
            "url": ROSS_TEXTBOOK_URL,
        },
    ]


def _lecture_notes_items() -> list[dict]:
    out: list[dict] = []
    for n, slug, iso, topic, _reading in LECTURE_NOTES:
        out.append(
            {
                "kind": "link",
                "title": f"Lecture {n:02d} ({iso}) — {topic}",
                "url": f"{BASE}/{slug}.pdf",
            }
        )
    return out


def _modules() -> list[tuple[str, list[dict]]]:
    """Two modules:

      1. "Direct links" — top-of-course navigation.
      2. "Lecture notes (Whitt)" — 20 primary lecture PDFs.

    Mirrors the seed_6_262 module structure minus the textbook-PDF module
    (Ross isn't free) and minus a practice-exams module (F13 only publishes
    one set of exam papers).
    """
    return [
        ("Direct links", _direct_links_items()),
        ("Lecture notes (Whitt)", _lecture_notes_items()),
    ]


SYLLABUS_MD = """## Prerequisites
Graduate-level probability comfort: random variables (discrete + continuous),
expectation, conditioning, basic limit theorems, the strong law and CLT. This
is a doctoral course at Columbia IEOR; it moves quickly.

## Textbook
- **Primary** — Sheldon Ross, *Stochastic Processes* (Wiley, 2nd ed., 1996).
  **Not freely available** — get a print or PDF copy from Wiley before
  starting.
- **Lecture notes** — Prof. Whitt's per-lecture PDFs (linked in the **Lecture
  notes (Whitt)** module) supplement Ross with detailed treatments of the
  CLT, M/G/1, reversibility, regenerative processes, and CTMCs. The
  Laplace-transform supplement is linked from the Direct links module.

## Grading (approximate — verify if you find Whitt's published split)
| Component | Weight |
|---|---|
| Problem sets (13) | 30% |
| First Midterm (Ch 1–2)  | 20% |
| Second Midterm (Ch 3–4) | 20% |
| Final Exam (cumulative) | 30% |

The 30/20/20/30 split is a defensible doctoral-course default. Whitt's
Fall 2013 page didn't publicly publish exact weights; adjust via teacher
mode if you confirm the real split.

## Problem-set policy
Whitt assigned a problem set roughly every Tuesday with solutions posted
shortly after the due date. HW5 and HW11 are marked "not required to be
turned in" on Whitt's page — they're kept as graded here so the gradebook
structure is uniform across all 13 sets. Don't peek at Whitt's solution
until you've made an honest attempt — the AI grader compares against it.

## Exams
The graded exams are the **Fall 2013 papers** for both midterms and the
final. Each is linked from its assignment page alongside Whitt's official
solution.
"""

HOME_MD = """**Columbia IEOR 6711 — Stochastic Models I (Whitt, Fall 2013).**

Course materials mirrored from Prof. Ward Whitt's Columbia personal page.
The term shown above is *your* self-study term — edit it from course
settings when your plan shifts.

The doctoral-level stochastic-models course in Columbia's IEOR department.
A natural follow-on to Gallager 6.262 — covers the same backbone (Bernoulli /
Poisson / Markov / renewal / martingales) at greater depth, plus M/G/1
queueing, reversibility, and CTMCs that Gallager treats more lightly.
Whitt's lecture notes supplement Ross's textbook with hand-written
treatments of CLT, regenerative processes, and CTMC theory.

Source: <https://www.columbia.edu/~ww2040/6711F13/IEOR6711F13.html>.
Textbook: Ross, *Stochastic Processes* (Wiley 2e, 1996) — **not freely
available**; get a copy before starting. Jump to **Syllabus**, **Modules**,
or **Assignments**.
"""

DESCRIPTION = (
    "Doctoral-level stochastic models: probability review, Poisson processes, "
    "renewal theory, discrete- and continuous-time Markov chains (including "
    "M/G/1 queueing applications), regenerative processes, and reversibility."
)

TEXTBOOK = (
    "Ross, Stochastic Processes 2e (Wiley 1996) — primary; not freely "
    "available, get a copy. Whitt's lecture notes (linked per-lecture in "
    "the Lecture notes module) supplement Ross with detailed treatments of "
    "CLT, M/G/1, reversibility, and CTMCs."
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
        title="Stochastic Models I",
        institution="Columbia University",
        term_label="Fall 2028",  # user's self-study term, not Whitt's recording year
        instructor="Prof. Ward Whitt",
        external_home_url=HOME,
        status="planned",
        color="#75AADB",  # Columbia light blue
        display_order=5,
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
    g_mid1 = AssignmentGroup(
        course_id=course.id, name="First Midterm", weight=20, drop_lowest_n=0, position=1
    )
    g_mid2 = AssignmentGroup(
        course_id=course.id, name="Second Midterm", weight=20, drop_lowest_n=0, position=2
    )
    g_final = AssignmentGroup(
        course_id=course.id, name="Final Exam", weight=30, drop_lowest_n=0, position=3
    )
    db.add_all([g_ps, g_mid1, g_mid2, g_final])
    db.flush()

    # 13 PSets
    for k, topic, lec_from, lec_to, ross in PROBLEM_SETS:
        a = Assignment(
            course_id=course.id,
            assignment_group_id=g_ps.id,
            title=f"Problem Set {k} — {topic}",
            description_md=_ps_description(k, topic, lec_from, lec_to, ross),
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
        _attach_official_solution(db, a, _ps_sol_filename(k))

    # First Midterm
    stem, sols_stem, mid1_from, mid1_to, mid1_ch, mid1_date = MIDTERM_ONE_SPEC
    a = Assignment(
        course_id=course.id,
        assignment_group_id=g_mid1.id,
        title="First Midterm (Fall 2013 paper)",
        description_md=_exam_description(
            "First Midterm", stem, sols_stem, mid1_ch, mid1_date
        ),
        points_possible=100,
        accepts_files=True,
        accepts_text=True,
        position=0,
        published=True,
        covers_lecture_from=mid1_from,
        covers_lecture_to=mid1_to,
        requires_solution_key=True,
    )
    db.add(a)
    db.flush()
    _attach_official_solution(db, a, f"{sols_stem}.pdf")

    # Second Midterm
    stem, sols_stem, mid2_from, mid2_to, mid2_ch, mid2_date = MIDTERM_TWO_SPEC
    a = Assignment(
        course_id=course.id,
        assignment_group_id=g_mid2.id,
        title="Second Midterm (Fall 2013 paper)",
        description_md=_exam_description(
            "Second Midterm", stem, sols_stem, mid2_ch, mid2_date
        ),
        points_possible=100,
        accepts_files=True,
        accepts_text=True,
        position=0,
        published=True,
        covers_lecture_from=mid2_from,
        covers_lecture_to=mid2_to,
        requires_solution_key=True,
    )
    db.add(a)
    db.flush()
    _attach_official_solution(db, a, f"{sols_stem}.pdf")

    # Final
    stem, sols_stem, fin_from, fin_to, fin_ch, fin_date = FINAL_SPEC
    a = Assignment(
        course_id=course.id,
        assignment_group_id=g_final.id,
        title="Final Exam (Fall 2013 paper)",
        description_md=_exam_description(
            "Final Exam", stem, sols_stem, fin_ch, fin_date
        ),
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
    _attach_official_solution(db, a, f"{sols_stem}.pdf")

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

_MIDTERM_ONE_TITLE = "First Midterm (Fall 2013 paper)"
_MIDTERM_TWO_TITLE = "Second Midterm (Fall 2013 paper)"
_FINAL_TITLE = "Final Exam (Fall 2013 paper)"


def _fixed_title_to_url() -> dict[str, str]:
    """Map a module-item title to the URL it should always point to."""
    out: dict[str, str] = {
        "IEOR 6711 course home (Whitt, Fall 2013)": HOME,
        "Lecture notes index": LECTURES_INDEX_URL,
        "Homework index": HOMEWORK_INDEX_URL,
        "Laplace transforms supplement (Whitt)": LAPLACE_NOTES_URL,
        "Ross — Stochastic Processes 2e (Wiley publisher page)": ROSS_TEXTBOOK_URL,
    }
    for n, slug, iso, topic, _reading in LECTURE_NOTES:
        out[f"Lecture {n:02d} ({iso}) — {topic}"] = f"{BASE}/{slug}.pdf"
    return out


def update_urls(db: Session) -> dict:
    """Refresh URLs on the live IEOR 6711 course in place — module-item URLs
    and assignment description_md / coverage / URL. Does NOT re-download PDFs
    (use --refresh-solutions for that). Preserves submissions / AI solutions /
    announcements / grades.
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

    dirty: set[str] = set()
    by_title = {a.title: a for a in course.assignments}

    for k, topic, lec_from, lec_to, ross in PROBLEM_SETS:
        a = next(
            (x for t, x in by_title.items() if t.startswith(f"Problem Set {k} ")),
            None,
        )
        if a is None:
            continue
        new_desc = _ps_description(k, topic, lec_from, lec_to, ross)
        if a.description_md != new_desc:
            a.description_md = new_desc
            dirty.add(a.id)
        if a.covers_lecture_from != lec_from or a.covers_lecture_to != lec_to:
            a.covers_lecture_from = lec_from
            a.covers_lecture_to = lec_to
            counts["coverage_updated"] += 1
        if not a.official_solution_file_path:
            new_url = _ps_sol_url(k)
            if a.official_solution_url != new_url:
                a.official_solution_url = new_url
                dirty.add(a.id)

    for title, spec, label in (
        (_MIDTERM_ONE_TITLE, MIDTERM_ONE_SPEC, "First Midterm"),
        (_MIDTERM_TWO_TITLE, MIDTERM_TWO_SPEC, "Second Midterm"),
        (_FINAL_TITLE, FINAL_SPEC, "Final Exam"),
    ):
        a = by_title.get(title)
        if a is None:
            continue
        stem, sols_stem, lec_from, lec_to, chapters, date_str = spec
        new_desc = _exam_description(label, stem, sols_stem, chapters, date_str)
        if a.description_md != new_desc:
            a.description_md = new_desc
            dirty.add(a.id)
        if a.covers_lecture_from != lec_from or a.covers_lecture_to != lec_to:
            a.covers_lecture_from = lec_from
            a.covers_lecture_to = lec_to
            counts["coverage_updated"] += 1
        if not a.official_solution_file_path:
            new_url = f"{BASE}/{sols_stem}.pdf"
            if a.official_solution_url != new_url:
                a.official_solution_url = new_url
                dirty.add(a.id)

    counts["assignments_updated"] = len(dirty)
    db.commit()
    return counts


def refresh_solutions(db: Session) -> dict:
    """Re-download every official-solution PDF on the live IEOR 6711 course.

    Clears ``official_solution_file_path`` first so ``_attach_official_solution``
    can't short-circuit on the idempotence check. Useful when Whitt rotates a
    PDF or if a previous seed ran in URL-only fallback mode.
    """
    course = db.query(Course).filter(Course.code == CODE).first()
    if course is None:
        return {"course_found": False, "refreshed": 0}

    counts = {"course_found": True, "refreshed": 0}
    by_title = {a.title: a for a in course.assignments}

    for k, *_ in PROBLEM_SETS:
        a = next(
            (x for t, x in by_title.items() if t.startswith(f"Problem Set {k} ")),
            None,
        )
        if a is None:
            continue
        a.official_solution_file_path = ""
        _attach_official_solution(db, a, _ps_sol_filename(k))
        counts["refreshed"] += 1

    for title, spec in (
        (_MIDTERM_ONE_TITLE, MIDTERM_ONE_SPEC),
        (_MIDTERM_TWO_TITLE, MIDTERM_TWO_SPEC),
        (_FINAL_TITLE, FINAL_SPEC),
    ):
        a = by_title.get(title)
        if a is None:
            continue
        _stem, sols_stem, *_ = spec
        a.official_solution_file_path = ""
        _attach_official_solution(db, a, f"{sols_stem}.pdf")
        counts["refreshed"] += 1

    db.commit()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the Columbia IEOR 6711 course.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="delete an existing IEOR 6711 course first",
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
        help="re-download every official-solution PDF from Whitt's host",
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
