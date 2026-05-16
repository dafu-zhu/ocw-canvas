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

from sqlalchemy.orm import Session  # noqa: F401 — used in later tasks

from app.db import SessionLocal  # noqa: F401 — used in later tasks
from app.models import (  # noqa: F401 — used in later tasks
    Assignment,
    AssignmentGroup,
    Course,
    Module,
    ModuleItem,
)
from app.services import storage  # noqa: F401 — used in later tasks

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
