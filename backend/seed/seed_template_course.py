"""Seed the MIT 18.100B — Real Analysis (Spring 2025) course.

Run:  cd backend && uv run python -m seed.seed_template_course [--force]
Source: https://ocw.mit.edu/courses/18-100b-real-analysis-spring-2025/

Idempotent: if a course with code "MIT 18.100B" already exists this is a no-op, unless
``--force`` (which deletes it first — the cascade on Course removes its modules / assignment
groups / assignments / announcements).

Note on links: every module item points *out* to MIT's real page; nothing is re-hosted.
Per-resource deep links use the stable section-index pages on the OCW course site (lecture
notes, video lectures, assignments, exams); refine to per-lecture URLs later if desired.
"""
from __future__ import annotations

import argparse
import re

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Assignment, AssignmentGroup, Course, Module, ModuleItem

CODE = "MIT 18.100B"
OCW = "https://ocw.mit.edu/courses/18-100b-real-analysis-spring-2025"
HOME = OCW + "/"
SYLLABUS_PAGE = OCW + "/pages/syllabus/"
VIDEOS = OCW + "/video_galleries/video-lectures/"
NOTES = OCW + "/pages/lecture-notes/"
ASSIGNMENTS_PAGE = OCW + "/pages/assignments/"
EXAMS_PAGE = OCW + "/pages/exams/"


def _res(slug: str) -> str:
    return f"{OCW}/resources/{slug}/"


# Per-lecture video resource URLs (date slugs from the OCW Spring 2025 schedule).
LECTURE_URLS: dict[int, str] = {
    1:  _res("ocw_18100b-lec01-2025feb04_mp4"),
    2:  _res("ocw_18100b-lec02-2025feb06_mp4"),
    3:  _res("ocw_18100b-lec03-2025feb11_mp4"),
    4:  _res("ocw_18100b-lec04-2025feb13_mp4"),
    5:  _res("ocw_18100b-lec05-2025feb20_mp4"),
    6:  _res("ocw_18100b-lec06-2025feb23_mp4"),
    7:  _res("ocw_18100b-lec07-2025feb27_mp4"),
    8:  _res("ocw_18100b-lec08-2025mar04_mp4"),
    9:  _res("ocw_18100b-lec09-2025mar06_mp4"),
    10: _res("ocw_18100b-lec10-2025mar11_mp4"),
    11: _res("ocw_18100b-lec11-2025mar13_mp4"),
    12: _res("ocw_18100b-lec12-2025apr01_mp4"),
    13: _res("ocw_18100b-lec13-2025apr03_mp4"),
    14: _res("ocw_18100b-lec14-2025apr08_mp4"),
    15: _res("ocw_18100b-lec15-2025apr10_mp4"),
    16: _res("ocw_18100b-lec16-2025apr15_mp4"),
    17: _res("ocw_18100b-lec17-2025apr17_mp4"),
    18: _res("ocw_18100b-lec18-2025apr22_mp4"),
    19: _res("ocw_18100b-lec19-2025apr24_mp4"),
    20: _res("ocw_18100b-lec20-2025apr29_mp4"),
    21: _res("ocw_18100b-lec21-2025may01_mp4"),
    22: _res("ocw_18100b-lec22-2025may06_mp4"),
    23: _res("ocw_18100b-lec23-2025may08_mp4"),
}
MIDTERM_REVIEW_URL = _res("ocw_18100b-midterm-review-2025mar18_mp4")
FINAL_REVIEW_URL = _res("ocw_18100b-final-exam-review-2025may13_mp4")

# Per-lecture lecture-notes PDF resource URLs.
# OCW pattern: /resources/mit18_100b_s25_lec<NN>_pdf/ (zero-padded).
LECTURE_NOTE_URLS: dict[int, str] = {
    n: _res(f"mit18_100b_s25_lec{n:02d}_pdf") for n in range(1, 24)
}

# (lecture_number, title) for the 23 lectures.
LECTURES: list[tuple[int, str]] = [
    (1, "The real numbers"),
    (2, "How to write a proof"),
    (3, "Archimedean property; supremum & infimum"),
    (4, "Sequences and convergence"),
    (5, "Monotone sequences; the monotone convergence theorem"),
    (6, "Cauchy sequences; completeness of R"),
    (7, "Bolzano–Weierstrass; subsequences"),
    (8, "Series; convergence tests"),
    (9, "Power series; limsup and liminf"),
    (10, "Continuous functions"),
    (11, "The exponential function; properties of continuity"),
    (12, "Extreme value theorem; intermediate value theorem"),
    (13, "Metric spaces; open and closed sets"),
    (14, "Compactness; sequential compactness"),
    (15, "Derivatives; differentiation rules"),
    (16, "Rolle's theorem; the mean value theorem; L'Hôpital"),
    (17, "Taylor's theorem; introduction to the Riemann integral"),
    (18, "Riemann integrable functions"),
    (19, "The fundamental theorem of calculus"),
    (20, "Pointwise and uniform convergence of sequences of functions"),
    (21, "Interchanging limits with integrals and derivatives"),
    (22, "Differentiating and integrating power series"),
    (23, "Picard–Lindelöf: existence & uniqueness for ODEs"),
]

# 10 problem sets — topic per the unit progression.
PROBLEM_SETS: list[tuple[int, str]] = [
    (1, "The real numbers & writing proofs"),
    (2, "Sequences & convergence"),
    (3, "Cauchy sequences; Bolzano–Weierstrass"),
    (4, "Series & convergence tests"),
    (5, "Power series; limsup/liminf"),
    (6, "Continuity; EVT/IVT"),
    (7, "Metric spaces; compactness"),
    (8, "Differentiation; the mean value theorem"),
    (9, "Riemann integration & the FTC"),
    (10, "Sequences of functions; uniform convergence; ODEs"),
]

SYLLABUS_MD = """## Prerequisites
18.02 Multivariable Calculus.

## Textbooks
- Thomson, Bruckner & Bruckner, *Elementary Real Analysis*, 2nd ed. (2008) — free PDF (primary).
- Rudin, *Principles of Mathematical Analysis*, 3rd ed. — secondary.

## Grading
| Component | Weight |
|---|---|
| Problem Sets (≈10, weekly; lowest dropped) | 50% |
| Midterm Exam | 20% |
| Final Exam | 30% |

## Problem-set policy
About ten weekly problem sets. Individual submission; collaboration on ideas is encouraged, but
write up your own solutions. The lowest score is dropped.

## Exam rules
One page of handwritten notes allowed; no computer or textbook.
"""

HOME_MD = """**18.100B — Real Analysis (Spring 2025), MIT OpenCourseWare.**

Two goals: (1) learn to write rigorous proofs; (2) put single-variable calculus on a rigorous
footing — sequences, series, continuity, differentiation, the Riemann integral, sequences of
functions, and a first existence/uniqueness theorem for ODEs.

Prerequisite: 18.02. Jump to **Syllabus**, **Modules**, or **Video Lectures**.
"""

DESCRIPTION = (
    "Rigorous single-variable analysis: proofs, sequences/series, continuity, differentiation, "
    "Riemann integration, sequences of functions, and ODE existence & uniqueness."
)

TEXTBOOK = (
    "Thomson, Bruckner & Bruckner, Elementary Real Analysis, 2nd ed. (2008) — free PDF; "
    "Rudin, Principles of Mathematical Analysis, 3rd ed. — secondary."
)


def _unit_items(lo: int, hi: int, reading_note: str) -> list[dict]:
    """Video + notes rows for lectures [lo, hi], then a Readings note."""
    items: list[dict] = []
    for n, title in LECTURES:
        if lo <= n <= hi:
            items.append(
                {
                    "kind": "video",
                    "title": f"Lecture {n}: {title} (video)",
                    "url": LECTURE_URLS.get(n, VIDEOS),
                }
            )
            items.append(
                {
                    "kind": "link",
                    "title": f"Lecture {n} notes",
                    "url": LECTURE_NOTE_URLS.get(n, NOTES),
                    "indent": 1,
                }
            )
    items.append({"kind": "note", "title": "Readings", "text_md": reading_note})
    return items


def _units() -> list[tuple[str, list[dict]]]:
    return [
        (
            "Direct links",
            [
                {"kind": "link", "title": "18.100B course home (MIT OpenCourseWare)", "url": HOME},
                {"kind": "link", "title": "Syllabus", "url": SYLLABUS_PAGE},
                {"kind": "link", "title": "Lecture notes (all)", "url": NOTES},
                {"kind": "link", "title": "Video lectures (all)", "url": VIDEOS},
                {"kind": "link", "title": "Problem sets (all)", "url": ASSIGNMENTS_PAGE},
                {"kind": "link", "title": "Exams", "url": EXAMS_PAGE},
            ],
        ),
        (
            "Unit 1 — The Real Numbers (Lectures 1–3)",
            _unit_items(1, 3, "Readings: §1.1–1.7 (Thomson/Bruckner/Bruckner)."),
        ),
        (
            "Unit 2 — Sequences & Series (Lectures 4–9)",
            _unit_items(4, 9, "Readings: ch. 2–3, §10.2."),
        ),
        (
            "Unit 3 — Continuity & Metric Spaces (Lectures 10–14)",
            _unit_items(10, 14, "Readings: §5.x, ch. 13."),
        ),
        (
            "Midterm Exam",
            [
                {
                    "kind": "video",
                    "title": "Midterm review session (video)",
                    "url": MIDTERM_REVIEW_URL,
                },
                {"kind": "assignment", "title": "Midterm Exam", "_assignment": "Midterm Exam"},
                {"kind": "link", "title": "Exam materials (MIT OCW)", "url": EXAMS_PAGE},
            ],
        ),
        (
            "Unit 4 — Differentiation (Lectures 15–17)",
            _unit_items(15, 17, "Readings: §7.x."),
        ),
        (
            "Unit 5 — Riemann Integration (Lectures 17–19)",
            _unit_items(17, 19, "Readings: §8.3, §8.6."),
        ),
        (
            "Unit 6 — Sequences of Functions & ODEs (Lectures 20–23)",
            _unit_items(20, 23, "Readings: §9.x, §13.11.4."),
        ),
        (
            "Final Exam",
            [
                {
                    "kind": "video",
                    "title": "Final review session (video)",
                    "url": FINAL_REVIEW_URL,
                },
                {"kind": "assignment", "title": "Final Exam", "_assignment": "Final Exam"},
                {"kind": "link", "title": "Exam materials (MIT OCW)", "url": EXAMS_PAGE},
            ],
        ),
    ]


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
        title="Real Analysis",
        institution="MIT OpenCourseWare",
        term_label="Spring 2025",
        instructor="Prof. Tobias Holck Colding",
        external_home_url=HOME,
        status="planned",
        color="#A31F34",
        display_order=0,
        textbook=TEXTBOOK,
        home_page_md=HOME_MD,
        syllabus_md=SYLLABUS_MD,
        description=DESCRIPTION,
    )
    db.add(course)
    db.flush()

    g_ps = AssignmentGroup(
        course_id=course.id, name="Problem Sets", weight=50, drop_lowest_n=1, position=0
    )
    g_mid = AssignmentGroup(
        course_id=course.id, name="Midterm", weight=20, drop_lowest_n=0, position=1
    )
    g_fin = AssignmentGroup(
        course_id=course.id, name="Final Exam", weight=30, drop_lowest_n=0, position=2
    )
    db.add_all([g_ps, g_mid, g_fin])
    db.flush()

    by_name: dict[str, Assignment] = {}
    for k, topic in PROBLEM_SETS:
        a = Assignment(
            course_id=course.id,
            assignment_group_id=g_ps.id,
            title=f"Problem Set {k} — {topic}",
            description_md=(
                f"Problem Set {k}. Find this set's PDF on the MIT OCW assignments page: "
                f"[{ASSIGNMENTS_PAGE}]({ASSIGNMENTS_PAGE}). Upload your worked solutions; the AI "
                "generates a reference solution and grades against it."
            ),
            points_possible=100,
            accepts_files=True,
            accepts_text=True,
            position=k - 1,
            published=True,
        )
        db.add(a)
        by_name[a.title] = a
    _exam_link = f"Materials on the MIT OCW exams page: [{EXAMS_PAGE}]({EXAMS_PAGE})."
    mid = Assignment(
        course_id=course.id,
        assignment_group_id=g_mid.id,
        title="Midterm Exam",
        description_md=f"Midterm exam. {_exam_link}",
        points_possible=100,
        accepts_files=True,
        accepts_text=True,
        position=0,
        published=True,
    )
    fin = Assignment(
        course_id=course.id,
        assignment_group_id=g_fin.id,
        title="Final Exam",
        description_md=f"Final exam. {_exam_link}",
        points_possible=100,
        accepts_files=True,
        accepts_text=True,
        position=0,
        published=True,
    )
    db.add_all([mid, fin])
    by_name["Midterm Exam"] = mid
    by_name["Final Exam"] = fin
    db.flush()

    for mpos, (mtitle, items) in enumerate(_units()):
        m = Module(course_id=course.id, title=mtitle, position=mpos, published=True)
        db.add(m)
        db.flush()
        for ipos, it in enumerate(items):
            kind = it["kind"]
            title = it["title"]
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


# --------------------------------------------------------------------------- in-place updater

_LECTURE_VIDEO_RE = re.compile(r"^Lecture (\d+):.*\(video\)\s*$")
_LECTURE_NOTES_RE = re.compile(r"^Lecture (\d+) notes\s*$")


def update_urls(db: Session) -> dict:
    """Refresh every module_item URL on the live MIT 18.100B course in place — preserves
    submissions / AI solutions / announcements. Returns counts of what was touched."""
    course = db.query(Course).filter(Course.code == CODE).first()
    if course is None:
        return {"course_found": False, "updated": 0, "examined": 0}
    counts = {"course_found": True, "updated": 0, "examined": 0}
    for m in course.modules:
        for it in m.items:
            counts["examined"] += 1
            new_url: str | None = None
            mv = _LECTURE_VIDEO_RE.match(it.title)
            mn = _LECTURE_NOTES_RE.match(it.title)
            if mv:
                new_url = LECTURE_URLS.get(int(mv.group(1)))
            elif mn:
                new_url = LECTURE_NOTE_URLS.get(int(mn.group(1)))
            elif it.title == "Midterm review session (video)":
                new_url = MIDTERM_REVIEW_URL
            elif it.title == "Final review session (video)":
                new_url = FINAL_REVIEW_URL
            elif it.title == "Video lectures (all)":
                new_url = VIDEOS
            if new_url and new_url != it.external_url:
                it.external_url = new_url
                counts["updated"] += 1
    db.commit()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the MIT 18.100B course.")
    parser.add_argument(
        "--force", action="store_true", help="delete an existing MIT 18.100B course first"
    )
    parser.add_argument(
        "--update-urls",
        action="store_true",
        help="only refresh module_item external_url values on the existing course (no deletions)",
    )
    args = parser.parse_args()
    db = SessionLocal()
    try:
        if args.update_urls:
            counts = update_urls(db)
            print(
                f"update_urls: course_found={counts['course_found']} "
                f"updated={counts['updated']} examined={counts['examined']}"
            )
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
