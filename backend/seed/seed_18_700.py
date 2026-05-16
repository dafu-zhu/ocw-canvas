"""Seed the MIT 18.700 — Linear Algebra course (David Vogan, Fall 2013).

Run:  cd backend && uv run python -m seed.seed_18_700 [--force]
Source: https://ocw.mit.edu/courses/18-700-linear-algebra-fall-2013/

Idempotent: if a course with code "MIT 18.700" already exists this is a no-op,
unless ``--force`` (which deletes it first — the cascade on Course removes its
modules / assignment groups / assignments / announcements).

Pattern differences vs the CMU 36-705 seed:
  - Per-lecture content is the Axler textbook reading, not a standalone PDF.
    Each lecture is a 'note' item with the Axler chapter + page range. Six
    specific lectures have OCW supplementary PDFs (one-sided inverses,
    Gaussian elimination, finite fields, orthogonal bases, spectral theorem,
    generalized eigenspaces) — added as 'link' items alongside.
  - 9 problem sets (vs CMU's 13). PS9's OCW slug is ``ps92`` (an OCW quirk),
    not ``ps9``; verified by hitting the assignments page directly.
  - No lecture videos: Fall 2013 wasn't recorded.
  - No exam papers / final paper / review handouts published by OCW. Per the
    seed-flexibility rule (see CMU 36-705 commit a2e7…), exams are omitted
    entirely rather than carried as ungradable phantoms; HW carries 100%.
"""
from __future__ import annotations

import argparse
import re

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Assignment, AssignmentGroup, Course, Module, ModuleItem

CODE = "MIT 18.700"
BASE = "https://ocw.mit.edu/courses/18-700-linear-algebra-fall-2013"
HOME = BASE + "/"
SYLLABUS_URL = BASE + "/pages/syllabus/"
CALENDAR_URL = BASE + "/pages/calendar/"
READINGS_URL = BASE + "/pages/readings/"
STUDY_MATERIALS_URL = BASE + "/pages/study-materials/"
ASSIGNMENTS_URL = BASE + "/pages/assignments/"
AXLER_BOOK_URL = "https://linear.axler.net/"  # Axler's site — 4e (2024) free PDF

# Problem set URLs. PS1-8 are clean; PS9's OCW slug is "ps92" (slug collision).
_PS_SLUG: dict[int, str] = {9: "mit18_700f13_ps92"}


def _ps_url(n: int) -> str:
    slug = _PS_SLUG.get(n, f"mit18_700f13_ps{n}")
    return f"{BASE}/resources/{slug}/"


PROBLEM_SET_URLS: dict[int, str] = {n: _ps_url(n) for n in range(1, 10)}

# Supplementary lecture-note PDFs published by OCW (only for these 6 specific
# lectures plus 2 thematic notes). Each is a /resources/{slug}/ page.
SUPP_NOTES: dict[str, tuple[str, str]] = {
    # slug → (title, brief description)
    "mit18_700f13_one_sided": (
        "Notes — One-sided inverses (Lec 8)",
        "Supplementary handout: one-sided matrix inverses.",
    ),
    "mit18_700f13_gauss": (
        "Notes — Gaussian elimination (Lec 8–9)",
        "Supplementary handout: row reduction & solving systems.",
    ),
    "mit18_700f13_finite_fields": (
        "Notes — Finite fields (Lec 8, 10, 13)",
        "Supplementary handout: linear algebra over Fp.",
    ),
    "mit18_700f13_orthgnl_base": (
        "Notes — Orthogonal bases (Lec 15)",
        "Supplementary handout on orthogonal bases.",
    ),
    "mit18_700f13_spctrl_thrm": (
        "Notes — Proof of the Spectral Theorem (Lec 18)",
        "Supplementary handout: full proof of the spectral theorem.",
    ),
    "mit18_700f13_generalized": (
        "Notes — Generalized eigenspaces (Lec 22–23)",
        "Supplementary handout: generalized eigenspace decomposition.",
    ),
    "mit18_700f13_intstng_base": (
        "Notes — Some interesting bases",
        "Supplementary thematic note (cross-cuts several lectures).",
    ),
    "mit18_700f13_qntm_mechnc": (
        "Notes — Mathematical formalism of quantum mechanics",
        "Supplementary thematic note: linear algebra in QM.",
    ),
}


def _supp_url(slug: str) -> str:
    return f"{BASE}/resources/{slug}/"


# (lecture_number, topic, axler_reading). axler_reading is the right-column
# text for each row of the OCW Readings table; 26 lectures total but exam
# days (7, 14, 21) and lectures 8/9 (no Axler reading — taught from the
# supplementary handouts) are absent from the readings table.
LECTURE_TOPICS: dict[int, tuple[str, str]] = {
    1:  ("Vector spaces — definitions & properties",   "Axler Ch 1, pp. 2–12"),
    2:  ("Subspaces, sums, direct sums",               "Axler Ch 1, pp. 13–18"),
    3:  ("Span, linear independence, bases",           "Axler Ch 2, pp. 21–31"),
    4:  ("Bases & dimension",                          "Axler Ch 2, pp. 31–34"),
    5:  ("Linear maps; null space & range",            "Axler Ch 3, pp. 38–47"),
    6:  ("Matrices; invertibility",                    "Axler Ch 3, pp. 48–58"),
    8:  ("Finite fields; systems of equations",        "Supplementary handouts (no Axler reading)"),
    9:  ("Gaussian elimination",                       "Supplementary handout (no Axler reading)"),
    10: ("Counting over Fp; invariant subspaces",      "Axler Ch 5, pp. 75–79"),
    11: ("Finding eigenvectors",                       "Axler Ch 5, pp. 80–81"),
    12: ("Upper triangular & diagonal matrices",       "Axler Ch 5, pp. 81–90"),
    13: ("Eigenvectors over R and Fp",                 "Axler Ch 5, pp. 91–93"),
    15: ("Inner products; Gram-Schmidt",               "Axler Ch 6, pp. 97–111"),
    16: ("Orthogonal projection; minimization",        "Axler Ch 6, pp. 111–116"),
    17: ("Adjoint, self-adjoint, normal operators",    "Axler Ch 7, pp. 127–132"),
    18: ("Spectral theorem",                           "Axler Ch 7, pp. 132–144"),
    19: ("Positive operators",                         "Axler Ch 7, pp. 144–147"),
    20: ("Isometries; polar decomposition",            "Axler Ch 7, pp. 147–157"),
    22: ("Generalized eigenspaces",                    "Axler Ch 8, pp. 163–168"),
    23: ("Generalized eigenspace decomposition",       "Axler Ch 8, pp. 173–178"),
    24: ("Characteristic polynomial",                  "Axler Ch 8, pp. 168–173"),
    25: ("Determinant",                                "Axler Ch 10"),
    26: ("Trace; canonical commutation relations",     "Axler Ch 10"),
}

# 9 problem sets — (number, topic, covers_lecture_from, covers_lecture_to).
# Coverage is "lectures since the previous PS, inclusive". The original course
# had PS9 due at lec 24, leaving lec 25–26 only on the final exam; for self-
# study (no final), PS9 is stretched to cover lec 23–26. Sum = 1..26 cleanly.
PROBLEM_SETS: list[tuple[int, str, int, int]] = [
    (1, "Vector spaces, subspaces, span",                1,  3),
    (2, "Bases, dimension, linear maps",                 4,  5),
    (3, "Matrices, finite fields, Gaussian elimination", 6,  9),
    (4, "Invariant subspaces & eigenvectors",           10, 11),
    (5, "Upper triangular operators",                   12, 12),
    (6, "Eigenvectors over R/Fp; inner products",       13, 16),
    (7, "Adjoints; spectral theorem",                   17, 18),
    (8, "Positive operators; isometries; gen. eigen.",  19, 22),
    (9, "Generalized eigenspaces; det. & trace",        23, 26),
]

# Module unit definitions: (module_title, [lecture_numbers], readings_md).
# Lectures 7, 14, 21 (the original in-term exams) are skipped because we omit
# exams entirely — see header docstring.
UNITS: list[tuple[str, list[int], str]] = [
    (
        "Unit 1 — Vector Spaces & Linear Independence",
        [1, 2, 3, 4],
        "Readings: Axler Chapters 1–2 (vector spaces, subspaces, sums and "
        "direct sums, span, linear independence, bases, dimension).",
    ),
    (
        "Unit 2 — Linear Maps",
        [5, 6],
        "Readings: Axler Chapter 3 (linear maps, null space, range, "
        "matrices, invertibility).",
    ),
    (
        "Unit 3 — Systems, Finite Fields & Invariant Subspaces",
        [8, 9, 10],
        "Readings: Axler Chapter 5 §1 (invariant subspaces) plus the OCW "
        "supplementary handouts on Gaussian elimination, one-sided inverses, "
        "and finite fields. Axler does not cover finite fields — that material "
        "comes entirely from Vogan's handouts.",
    ),
    (
        "Unit 4 — Eigenvalues & Diagonalization",
        [11, 12, 13],
        "Readings: Axler Chapter 5 (eigenvalues, eigenvectors, upper triangular "
        "and diagonal matrices). The handout on finite fields is also relevant "
        "for Lec 13.",
    ),
    (
        "Unit 5 — Inner Product Spaces",
        [15, 16],
        "Readings: Axler Chapter 6 (inner products, Gram-Schmidt, orthogonal "
        "projections, minimization). See also the supplementary handout on "
        "orthogonal bases.",
    ),
    (
        "Unit 6 — Operators on Inner Product Spaces",
        [17, 18, 19, 20],
        "Readings: Axler Chapter 7 (adjoint, self-adjoint, normal operators, "
        "spectral theorem, positive operators, isometries, polar decomposition). "
        "See also the supplementary spectral-theorem proof handout.",
    ),
    (
        "Unit 7 — Generalized Eigenspaces, Determinants & Trace",
        [22, 23, 24, 25, 26],
        "Readings: Axler Chapter 8 (generalized eigenspaces, characteristic "
        "polynomial) and Chapter 10 (determinants, trace). See also the "
        "supplementary handout on generalized eigenspaces. **Note:** Axler "
        "moved determinants in 4e (2024) — chapter numbering may differ if "
        "you read the newer edition; the topics are unchanged.",
    ),
]

# Lecture → list of supplementary-note slugs to attach. A single slug can
# appear under multiple lectures (e.g. finite_fields under 8, 10, 13).
LECTURE_SUPPLEMENTS: dict[int, list[str]] = {
    8:  ["mit18_700f13_one_sided", "mit18_700f13_gauss", "mit18_700f13_finite_fields"],
    9:  ["mit18_700f13_gauss"],
    10: ["mit18_700f13_finite_fields"],
    13: ["mit18_700f13_finite_fields"],
    15: ["mit18_700f13_orthgnl_base"],
    18: ["mit18_700f13_spctrl_thrm"],
    22: ["mit18_700f13_generalized"],
    23: ["mit18_700f13_generalized"],
}

SYLLABUS_MD = """## Prerequisites
18.02 Multivariable Calculus (or equivalent comfort with vector calculus and
mathematical reasoning). 18.700 is the proof-heavy alternative to the more
computational 18.06.

## Textbook
- **Primary** — Axler, *Linear Algebra Done Right*, 2nd ed. (2004) — the
  edition the OCW readings table cites.
- The 4th edition (2024) is freely available from the author at
  <https://linear.axler.net/>. Strictly better and more current; topics align
  but determinants were moved to a later chapter, so the per-lecture page
  references in OCW's readings table won't match exactly.
- Vogan also distributes ~8 supplementary OCW handouts covering finite fields,
  Gaussian elimination, the spectral theorem proof, and a few others — all
  linked under the relevant unit modules.

## Grading (self-study)
| Component | Weight |
|---|---|
| Problem sets (9) | 100% |

The original course's grading split was 26% problem sets / 15% × 3 in-term
exams / 29% final = 74% on exams. OCW publishes **no exam papers**, **no final
paper**, and **no review handouts** — only problem sets are released. Per the
self-study seed-flexibility rule, the four exams are dropped entirely rather
than carried as ungradable phantoms; problem sets carry the full grade. Treat
the problem sets as the genuine assessment of mastery.

## Problem-set policy
Late homework was not accepted in the original course. For self-study: pick a
weekly cadence and stick to it. Don't search for solutions online; do them
honestly, then let the AI generate a reference solution for grading.

## Exams (omitted)
"There will be three eighty-minute exams during the lecture hour, and one
three-hour final examination" (original syllabus). None of these exam papers
are published on OCW. If you want test-like checkpoints, ask the AI to
generate fresh problems covering the relevant lecture range, or budget two
extra weeks at the end of the course as a Final review pass through Axler's
chapter exercises.
"""

HOME_MD = """**MIT 18.700 — Linear Algebra (Vogan, Fall 2013).** Course materials
mirrored from MIT OCW. The term shown above is *your* self-study term — edit
it from the course settings when your plan shifts.

This is the proof-oriented linear algebra course at MIT (the rigorous twin of
18.06). It builds linear algebra from the ground up — vector spaces, linear
maps, eigenvalues, inner products, the spectral theorem, generalized
eigenspaces, determinants — using Axler's coordinate-free, operator-first
approach. No matrix-pushing without a reason.

Source: <https://ocw.mit.edu/courses/18-700-linear-algebra-fall-2013/>.
Textbook: Axler, *Linear Algebra Done Right* (2e cited; 4e is free at
<https://linear.axler.net/>). Jump to **Syllabus**, **Modules**, or
**Assignments**.
"""

DESCRIPTION = (
    "Proof-based linear algebra: vector spaces, linear maps, eigenvalues, "
    "diagonalization, inner product spaces, spectral theorem, generalized "
    "eigenspaces, determinants, trace. Axler's coordinate-free treatment."
)

TEXTBOOK = (
    "Axler, Linear Algebra Done Right, 2e (Springer 2004) — primary, cited by "
    "OCW. The 4e (2024) is free at linear.axler.net — strictly better, but "
    "the determinants chapter moved."
)


def _ps_description(k: int, topic: str) -> str:
    url = PROBLEM_SET_URLS[k]
    return (
        f"Problem Set {k} ({topic}). Source PDF on MIT OCW: "
        f"[Problem Set {k} (PDF)]({url}). Upload your worked solutions; the AI "
        "generates a reference solution and grades against it. OCW does not "
        "publish solutions — the AI key is your reference."
    )


def _unit_items(lecture_numbers: list[int], readings_md: str) -> list[dict]:
    """For each lecture: a note with the Axler reading, then any supplementary
    PDF links attached to that lecture. Closed with the unit-level Readings note.

    No video items because Fall 2013 wasn't recorded.
    """
    items: list[dict] = []
    for n in lecture_numbers:
        topic, axler_ref = LECTURE_TOPICS[n]
        items.append(
            {
                "kind": "note",
                "title": f"Lec {n} — {topic}",
                "text_md": f"**{axler_ref}.** {topic}.",
            }
        )
        for slug in LECTURE_SUPPLEMENTS.get(n, []):
            supp_title, _ = SUPP_NOTES[slug]
            items.append(
                {
                    "kind": "link",
                    "title": supp_title,
                    "url": _supp_url(slug),
                    "indent": 1,
                }
            )
    items.append({"kind": "note", "title": "Readings", "text_md": readings_md})
    return items


def _modules() -> list[tuple[str, list[dict]]]:
    """1 direct-links module + 7 unit modules + 1 thematic-notes module = 9
    modules. No exam modules (OCW publishes no exam papers)."""
    out: list[tuple[str, list[dict]]] = [
        (
            "Direct links",
            [
                {
                    "kind": "link",
                    "title": "18.700 course home (Vogan, MIT OCW Fall 2013)",
                    "url": HOME,
                },
                {"kind": "link", "title": "Syllabus", "url": SYLLABUS_URL},
                {"kind": "link", "title": "Calendar", "url": CALENDAR_URL},
                {"kind": "link", "title": "Readings (lecture → Axler map)", "url": READINGS_URL},
                {"kind": "link", "title": "Assignments index", "url": ASSIGNMENTS_URL},
                {"kind": "link", "title": "Study materials index", "url": STUDY_MATERIALS_URL},
                {
                    "kind": "link",
                    "title": "Axler — Linear Algebra Done Right (4e, 2024, free PDF)",
                    "url": AXLER_BOOK_URL,
                },
            ],
        ),
    ]
    for title, lecture_nums, readings_md in UNITS:
        out.append((title, _unit_items(lecture_nums, readings_md)))
    # Thematic supplements that aren't tied to a single lecture.
    out.append(
        (
            "Supplementary thematic notes",
            [
                {
                    "kind": "link",
                    "title": SUPP_NOTES[slug][0],
                    "url": _supp_url(slug),
                }
                for slug in ("mit18_700f13_intstng_base", "mit18_700f13_qntm_mechnc")
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
        title="Linear Algebra",
        institution="Massachusetts Institute of Technology",
        # term_label is *your* self-study term, not the OCW recording year.
        term_label="Summer 2027",
        instructor="Prof. David Vogan",
        external_home_url=HOME,
        status="planned",
        color="#1F5F5B",  # deep teal — distinct from MIT-cardinal 18.100B
        display_order=2,
        textbook=TEXTBOOK,
        home_page_md=HOME_MD,
        syllabus_md=SYLLABUS_MD,
        description=DESCRIPTION,
    )
    db.add(course)
    db.flush()

    g_ps = AssignmentGroup(
        course_id=course.id, name="Problem Sets", weight=100, drop_lowest_n=0, position=0
    )
    db.add(g_ps)
    db.flush()

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

# "Lec 12 — <topic>" — used to spot per-lecture note items in update_urls.
_LECTURE_NOTE_RE = re.compile(r"^Lec (\d+)\b")
# "Problem Set 7 — <topic>"
_PS_TITLE_RE = re.compile(r"^Problem Set (\d+)\b")

# Module-item titles whose URL is fixed (i.e. not parameterized by lecture/PS).
_FIXED_TITLE_TO_URL: dict[str, str] = {
    "18.700 course home (Vogan, MIT OCW Fall 2013)": HOME,
    "Syllabus": SYLLABUS_URL,
    "Calendar": CALENDAR_URL,
    "Readings (lecture → Axler map)": READINGS_URL,
    "Assignments index": ASSIGNMENTS_URL,
    "Study materials index": STUDY_MATERIALS_URL,
    "Axler — Linear Algebra Done Right (4e, 2024, free PDF)": AXLER_BOOK_URL,
}
# Supplementary-note titles → URL.
for _slug, (_title, _) in SUPP_NOTES.items():
    _FIXED_TITLE_TO_URL[_title] = _supp_url(_slug)


def update_urls(db: Session) -> dict:
    """Refresh every URL on the live MIT 18.700 course in place — module-item
    external_urls AND assignment description_md (so per-PS links go to the right
    PDF). Preserves submissions / AI solutions / announcements / grades."""
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

    # 1) Module-item external URLs (fixed-title items only — per-lecture notes
    #    have no external_url).
    for m in course.modules:
        for it in m.items:
            counts["items_examined"] += 1
            if it.title in _FIXED_TITLE_TO_URL:
                new_url = _FIXED_TITLE_TO_URL[it.title]
                if new_url != it.external_url:
                    it.external_url = new_url
                    counts["items_updated"] += 1

    # 2) Per-lecture note text (refresh Axler chapter ref if the source page changes).
    for m in course.modules:
        for it in m.items:
            mn = _LECTURE_NOTE_RE.match(it.title or "")
            if not mn:
                continue
            n = int(mn.group(1))
            spec = LECTURE_TOPICS.get(n)
            if spec is None:
                continue
            topic, axler_ref = spec
            new_text = f"**{axler_ref}.** {topic}."
            if it.text_md != new_text:
                it.text_md = new_text
                counts["items_updated"] += 1

    # 3) Assignment description_md + lecture coverage.
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

    db.commit()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the MIT 18.700 course.")
    parser.add_argument(
        "--force", action="store_true", help="delete an existing MIT 18.700 course first"
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
