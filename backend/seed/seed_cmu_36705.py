"""Seed the CMU 36-705 — Intermediate Statistics course (Larry Wasserman).

Run:  cd backend && uv run python -m seed.seed_cmu_36705 [--force]
Source: https://www.stat.cmu.edu/~larry/=stat705/

Idempotent: if a course with code "CMU 36-705" already exists this is a no-op, unless
``--force`` (which deletes it first — the cascade on Course removes its modules /
assignment groups / assignments / announcements).

Pattern differences vs the MIT 18.100B seed (see
docs/superpowers/specs/2026-05-13-cmu-36705-seed-design.md):
  - No video items: CMU's source has no public recordings.
  - Lecture notes use slots Lecture11a.pdf / Lecture12a.pdf (no plain 11 / 12).
  - HW filenames are mixed case: HW1 is lowercase ("homework1.pdf"), HW2-13 Title-case.
  - Tests and Final have no source paper and no review handout.
"""
from __future__ import annotations

import argparse
import re

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Assignment, AssignmentGroup, Course, Module, ModuleItem

CODE = "CMU 36-705"
BASE = "https://www.stat.cmu.edu/~larry/=stat705"
HOME = BASE + "/"
SYLLABUS = BASE + "/syllabus.pdf"
PIAZZA = "https://piazza.com/class/keg3v6nru7z18j"  # Fall 2020 legacy link

# Lecture-notes URLs. 27 distinct PDFs but slots 11 and 12 use the "a" variants
# (no plain Lecture11.pdf / Lecture12.pdf exist on the source).
_LEC_FILE: dict[int, str] = {11: "Lecture11a.pdf", 12: "Lecture12a.pdf"}


def _lec_url(n: int) -> str:
    return f"{BASE}/{_LEC_FILE.get(n, f'Lecture{n}.pdf')}"


# Homework URLs. HW1 is lowercase; HW2..HW13 are Title-case (verified by inspecting
# the actual hrefs on the source page).
_HW_FILE: dict[int, str] = {1: "homework1.pdf"}


def _hw_url(n: int) -> str:
    return f"{BASE}/{_HW_FILE.get(n, f'Homework{n}.pdf')}"


LECTURE_NOTE_URLS: dict[int, str] = {n: _lec_url(n) for n in range(1, 28)}
HOMEWORK_URLS: dict[int, str] = {n: _hw_url(n) for n in range(1, 14)}

# 13 homeworks — (number, topic, covers_lecture_from, covers_lecture_to).
# Coverage is calendar-derived; the sum across all rows is exactly LN 1..27.
HOMEWORKS: list[tuple[int, str, int, int]] = [
    (1,  "Probability review & concentration",          1,  2),
    (2,  "Concentration II, convergence & CLT",         3,  5),
    (3,  "Empirical process / uniform laws",            6,  7),
    (4,  "Likelihood, sufficiency, MLE, MoM, Bayes",    8, 10),
    (5,  "Decision theory & asymptotic theory",        11, 12),
    (6,  "Hypothesis testing; GoF; two-sample",        13, 14),
    (7,  "Multiple testing",                           15, 15),
    (8,  "Confidence intervals",                       16, 17),
    (9,  "Confidence intervals (cont.)",               18, 18),
    (10, "Bootstrap",                                  19, 20),
    (11, "Bayesian inference",                         21, 22),
    (12, "Linear & nonparametric regression",          23, 24),
    (13, "Minimax, high-dim & model selection",        25, 27),
]
# Tests are no-collaboration homeworks (per the syllabus). Cumulative coverage.
TEST1_COVERS_TO = 7
TEST2_COVERS_TO = 18
FINAL_COVERS_TO = 27

# (lecture_number, topic) for the 27 lecture notes. Topics inferred from the
# syllabus calendar's session labels; the per-PDF titles aren't published on the
# source index page.
LECTURE_TOPICS: dict[int, str] = {
    1:  "Probability review (random variables, expectation, key distributions)",
    2:  "Concentration inequalities I (Markov, Chebyshev, Hoeffding)",
    3:  "Concentration inequalities II / start of convergence",
    4:  "Convergence of random variables",
    5:  "Central Limit Theorem & the Delta method",
    6:  "Uniform laws & empirical process theory I",
    7:  "Uniform laws & empirical process theory II",
    8:  "Likelihood & sufficiency",
    9:  "Point estimation: maximum likelihood",
    10: "Point estimation: method of moments & Bayes",
    11: "Decision theory",
    12: "Asymptotic theory",
    13: "Hypothesis testing",
    14: "Goodness-of-fit, two-sample, independence",
    15: "Multiple testing",
    16: "Confidence intervals I",
    17: "Confidence intervals II",
    18: "Confidence intervals III",
    19: "Bootstrap I",
    20: "Bootstrap II",
    21: "Bayesian inference I",
    22: "Bayesian inference II",
    23: "Linear regression",
    24: "Nonparametric regression",
    25: "Minimax lower bounds",
    26: "High-dimensional statistics",
    27: "Model selection",
}

# Module unit definitions: (module_title, lecture_low, lecture_high, readings_md).
UNITS: list[tuple[str, int, int, str]] = [
    (
        "Unit 1 — Foundations: Probability Review, Concentration, Convergence & CLT",
        1, 5,
        "Readings: Wasserman, *All of Statistics*, Chapters 1-5 (probability, "
        "random variables, expectation, inequalities, convergence).",
    ),
    (
        "Unit 2 — Empirical Process Theory",
        6, 7,
        "Readings: supplementary material. For a deeper treatment see "
        "van der Vaart, *Asymptotic Statistics* (2000), Chapter 19. Not covered in "
        "Wasserman's *All of Statistics*.",
    ),
    (
        "Unit 3 — Point Estimation & Decision Theory",
        8, 12,
        "Readings: Wasserman ch. 6 (statistical inference), ch. 9 (parametric "
        "inference / MLE), ch. 12 (decision theory).",
    ),
    (
        "Unit 4 — Hypothesis Testing & Multiple Testing",
        13, 15,
        "Readings: Wasserman ch. 10 (hypothesis testing & p-values). Multiple "
        "testing is supplementary (FWER, FDR / Benjamini-Hochberg).",
    ),
    (
        "Unit 5 — Confidence Intervals",
        16, 18,
        "Readings: confidence intervals are introduced throughout Wasserman "
        "ch. 6 and revisited in ch. 9.",
    ),
    (
        "Unit 6 — Bootstrap & Bayesian Inference",
        19, 22,
        "Readings: Wasserman ch. 8 (the bootstrap), ch. 11 (Bayesian inference).",
    ),
    (
        "Unit 7 — Modern Statistics: Regression, Minimax, High-Dim, Model Selection",
        23, 27,
        "Readings: Wasserman ch. 13 (linear regression), ch. 20 (nonparametric "
        "regression). Minimax / high-dim / model selection are supplementary "
        "(see van der Vaart and additional course notes).",
    ),
]

SYLLABUS_MD = """## Prerequisites
Basic probability and mathematical statistics (Chapters 1-3 of Wasserman). If you
need a slower-paced course, CMU's 36-700 covers similar material with less assumed
background.

## Textbooks
- **Primary** — Wasserman, *All of Statistics: A Concise Course in Statistical
  Inference* (2004). Covers Chapters 1-12 plus supplementary material.
- Casella & Berger, *Statistical Inference*, 2nd ed. (2002) — reference.
- Rice, *Mathematical Statistics and Data Analysis*, 2nd ed. (1977) — reference.
- (Advanced) van der Vaart, *Asymptotic Statistics* (2000).
- (Advanced) Bickel & Doksum, *Mathematical Statistics* (1977).

## Grading
| Component | Weight |
|---|---|
| Homework (13 problem sets, weekly) | 50% |
| Test I (no-collaboration homework) | 10% |
| Test II (no-collaboration homework) | 10% |
| Final Exam | 30% |

## Homework policy
Approximately weekly. You may discuss problems with other students but **write up
your final solutions on your own**, crediting collaborators. Do not search for
solutions online. No late assignments without prior approval.

## Test / Final policy
"The tests will just be homework assignments where you will not be allowed to
collaborate with other students." The source course posts no test paper and no
review handout — for self-study, ask the AI to generate fresh problems on the
covered material at the chosen point in your schedule, or reserve one of the
weekly homeworks as a no-collaboration test.
"""

HOME_MD = """**CMU 36-705 — Intermediate Statistics.** Course materials from
Larry Wasserman's CMU page (Fall 2020 session; lecture notes 1-27). The term
shown above is *your* self-study term — edit it from the course settings when
you've picked one.

This course covers the fundamentals of theoretical statistics: concentration of
measure, empirical process theory, convergence, point and interval estimation,
maximum likelihood, hypothesis testing, Bayesian inference, nonparametric
statistics and bootstrap resampling. Excellent preparation for advanced work in
statistics and machine learning.

Prerequisite: basic probability (Wasserman ch. 1-3). Jump to **Syllabus**,
**Modules**, or **Assignments**.
"""

DESCRIPTION = (
    "Theoretical statistics: concentration, empirical processes, convergence, "
    "estimation (MLE / MoM / Bayes), decision theory, hypothesis testing, "
    "confidence intervals, bootstrap, Bayesian inference, regression, minimax "
    "lower bounds, high-dimensional statistics, model selection."
)

TEXTBOOK = (
    "Wasserman, All of Statistics (2004) — primary. References: Casella & Berger, "
    "Rice, van der Vaart (Asymptotic Statistics), Bickel & Doksum."
)


def _hw_description(k: int, topic: str) -> str:
    url = HOMEWORK_URLS[k]
    return (
        f"Homework {k} ({topic}). Source PDF on CMU/Wasserman: "
        f"[Homework {k} (PDF)]({url}). Upload your worked solutions; the AI "
        "generates a reference solution and grades against it."
    )


def _test_description(num: int, covers_to: int) -> str:
    return (
        f"Test {num} (no-collaboration homework, per syllabus §3). The source "
        f"course posts no Test {num} paper and no review handout. For "
        f"self-study, either ask the AI to generate fresh problems covering "
        f"Lectures 1-{covers_to}, or reserve one of the weekly homeworks "
        f"(HW1-HW{covers_to // 2 + 1}) as a no-collaboration test and submit "
        "that here. Manual grading expected — there is no source PDF for the "
        "AI to grade against."
    )


def _final_description() -> str:
    return (
        f"Final Exam, cumulative across Lectures 1-{FINAL_COVERS_TO}. The "
        "source course posts no final paper and no review handout. For "
        "self-study, ask the AI to generate a comprehensive exam covering all "
        "course material, or assemble your own from the lecture notes. Manual "
        "grading expected — there is no source PDF for the AI to grade against."
    )


def _unit_items(lo: int, hi: int, readings_md: str) -> list[dict]:
    """Lecture-note links for lectures [lo, hi], then a Readings note.

    Unlike the 18.100B seed there are no per-lecture video items here, because
    CMU's source has no public recordings.
    """
    items: list[dict] = []
    for n in range(lo, hi + 1):
        items.append(
            {
                "kind": "link",
                "title": f"Lecture {n} notes — {LECTURE_TOPICS[n]}",
                "url": LECTURE_NOTE_URLS[n],
            }
        )
    items.append({"kind": "note", "title": "Readings", "text_md": readings_md})
    return items


def _modules() -> list[tuple[str, list[dict]]]:
    """The full module-tree: 1 direct-links module + 7 unit modules interleaved
    with 2 in-term tests + 1 final = 11 modules."""
    out: list[tuple[str, list[dict]]] = [
        (
            "Direct links",
            [
                {
                    "kind": "link",
                    "title": "36-705 course home (Larry Wasserman, CMU)",
                    "url": HOME,
                },
                {"kind": "link", "title": "Syllabus (PDF)", "url": SYLLABUS},
                {
                    "kind": "link",
                    "title": "Lecture notes & homeworks (index)",
                    "url": HOME,
                },
                {
                    "kind": "link",
                    "title": "Piazza (Fall 2020 — legacy)",
                    "url": PIAZZA,
                },
            ],
        ),
    ]
    # Interleave units with the two tests and the final at the right
    # cumulative-coverage stop-points.
    test_stops = {
        TEST1_COVERS_TO: "Test I",
        TEST2_COVERS_TO: "Test II",
    }
    for title, lo, hi, readings_md in UNITS:
        out.append((title, _unit_items(lo, hi, readings_md)))
        if hi in test_stops:
            label = test_stops[hi]
            out.append((label, [{"kind": "assignment", "_assignment": label}]))
    out.append(("Final Exam", [{"kind": "assignment", "_assignment": "Final Exam"}]))
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
        title="Intermediate Statistics",
        institution="Carnegie Mellon University",
        # term_label is *your* self-study term, not the OCW recording year.
        # Empty string by default — set it in teacher mode when you've decided.
        term_label="",
        instructor="Prof. Larry Wasserman",
        external_home_url=HOME,
        status="planned",
        color="#C41230",  # CMU Tartan red
        display_order=1,
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
    g_t1 = AssignmentGroup(
        course_id=course.id, name="Test I", weight=10, drop_lowest_n=0, position=1
    )
    g_t2 = AssignmentGroup(
        course_id=course.id, name="Test II", weight=10, drop_lowest_n=0, position=2
    )
    g_fin = AssignmentGroup(
        course_id=course.id, name="Final Exam", weight=30, drop_lowest_n=0, position=3
    )
    db.add_all([g_hw, g_t1, g_t2, g_fin])
    db.flush()

    by_name: dict[str, Assignment] = {}
    for k, topic, lec_from, lec_to in HOMEWORKS:
        a = Assignment(
            course_id=course.id,
            assignment_group_id=g_hw.id,
            title=f"Homework {k} — {topic}",
            description_md=_hw_description(k, topic),
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

    test1 = Assignment(
        course_id=course.id,
        assignment_group_id=g_t1.id,
        title="Test I",
        description_md=_test_description(1, TEST1_COVERS_TO),
        points_possible=100,
        accepts_files=True,
        accepts_text=True,
        position=0,
        published=True,
        covers_lecture_from=1,
        covers_lecture_to=TEST1_COVERS_TO,
    )
    test2 = Assignment(
        course_id=course.id,
        assignment_group_id=g_t2.id,
        title="Test II",
        description_md=_test_description(2, TEST2_COVERS_TO),
        points_possible=100,
        accepts_files=True,
        accepts_text=True,
        position=0,
        published=True,
        covers_lecture_from=1,
        covers_lecture_to=TEST2_COVERS_TO,
    )
    fin = Assignment(
        course_id=course.id,
        assignment_group_id=g_fin.id,
        title="Final Exam",
        description_md=_final_description(),
        points_possible=100,
        accepts_files=True,
        accepts_text=True,
        position=0,
        published=True,
        covers_lecture_from=1,
        covers_lecture_to=FINAL_COVERS_TO,
    )
    db.add_all([test1, test2, fin])
    by_name["Test I"] = test1
    by_name["Test II"] = test2
    by_name["Final Exam"] = fin
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


# --------------------------------------------------------------------------- in-place updater

# "Lecture 12 notes — <whatever topic suffix>"
_LECTURE_NOTE_RE = re.compile(r"^Lecture (\d+) notes\b")
# "Homework 7 — <topic>"
_HW_TITLE_RE = re.compile(r"^Homework (\d+)\b")

# Module-item titles whose URL is fixed (i.e. not parameterized by lecture/HW number).
_ITEM_TITLE_TO_URL: dict[str, str] = {
    "36-705 course home (Larry Wasserman, CMU)": HOME,
    "Syllabus (PDF)": SYLLABUS,
    "Lecture notes & homeworks (index)": HOME,
    "Piazza (Fall 2020 — legacy)": PIAZZA,
}


def update_urls(db: Session) -> dict:
    """Refresh every URL on the live CMU 36-705 course in place — module-item
    external_urls AND assignment description_md (so per-HW links go to the
    right PDF). Preserves submissions / AI solutions / announcements / grades."""
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

    # 1) Module-item external URLs.
    for m in course.modules:
        for it in m.items:
            counts["items_examined"] += 1
            new_url: str | None = None
            mn = _LECTURE_NOTE_RE.match(it.title or "")
            if mn:
                n = int(mn.group(1))
                new_url = LECTURE_NOTE_URLS.get(n)
            elif it.title in _ITEM_TITLE_TO_URL:
                new_url = _ITEM_TITLE_TO_URL[it.title]
            if new_url and new_url != it.external_url:
                it.external_url = new_url
                counts["items_updated"] += 1

    # 2) Assignment description_md + lecture coverage.
    by_title = {a.title: a for a in course.assignments}
    for k, topic, lec_from, lec_to in HOMEWORKS:
        # Fuzzy match: prefix "Homework K" — user may have edited the topic suffix.
        a = next(
            (
                x for t, x in by_title.items()
                if _HW_TITLE_RE.match(t) and t.startswith(f"Homework {k} ")
            ),
            None,
        )
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

    # Test I / Test II / Final coverage + descriptions.
    for title, cov_to, desc_fn in (
        ("Test I", TEST1_COVERS_TO, lambda: _test_description(1, TEST1_COVERS_TO)),
        ("Test II", TEST2_COVERS_TO, lambda: _test_description(2, TEST2_COVERS_TO)),
        ("Final Exam", FINAL_COVERS_TO, _final_description),
    ):
        a = by_title.get(title)
        if a is None:
            continue
        if a.covers_lecture_from != 1 or a.covers_lecture_to != cov_to:
            a.covers_lecture_from = 1
            a.covers_lecture_to = cov_to
            counts["coverage_updated"] += 1
        new_desc = desc_fn()
        if a.description_md != new_desc:
            a.description_md = new_desc
            counts["assignments_updated"] += 1

    db.commit()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the CMU 36-705 course.")
    parser.add_argument(
        "--force", action="store_true", help="delete an existing CMU 36-705 course first"
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
