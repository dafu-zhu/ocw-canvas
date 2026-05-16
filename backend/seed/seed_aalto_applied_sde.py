"""Seed the Aalto MS-E1602 — Applied Stochastic Differential Equations course.

Source: https://users.aalto.fi/~ssarkka/course_s2014/  (Sarkka & Solin, Autumn 2014)
Run:    cd backend && uv run python -m seed.seed_aalto_applied_sde [--force] [--update-urls]

Idempotent: if a course with code "Aalto MS-E1602" already exists this is a
no-op, unless ``--force`` (which deletes it first — the cascade on Course
removes its modules / assignment groups / assignments / announcements).

Pattern differences vs the Aalto BDA seed:
  - Every graded assignment is project-mode (``requires_solution_key=False``).
    Aalto publishes no solution keys for MS-E1602 — exercises were worked
    through in-person at the exercise session. First seed where *all* graded
    assignments are project-mode (Aalto BDA uses project-mode for the
    capstone only).
  - No exam group (course has no exams). Single assignment group: "Exercise
    Rounds" with weight=100.
  - No capstone (course doesn't publish one — faithful to source).
  - No Storage interaction, no ``--refresh-solutions`` flag.
"""
from __future__ import annotations

import argparse

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Assignment, AssignmentGroup, Course, Module, ModuleItem

CODE = "Aalto MS-E1602"
BASE = "https://users.aalto.fi/~ssarkka/course_s2014"

HOME = BASE + "/"
BOOKLET_URL = BASE + "/sde_course_booklet.pdf"
SARKKA_HOMEPAGE = "https://users.aalto.fi/~ssarkka/"
SOLIN_HOMEPAGE = "https://arno.solin.fi/"
CAMBRIDGE_BOOK_URL = (
    "https://www.cambridge.org/core/books/applied-stochastic-differential-equations/"
    "0F1F3D5A0E64E73E2F87DAEB57B620E2"
)
COMPANION_CODE_URL = "https://github.com/AaltoML/SDE"


def _exercise_url(n: int) -> str:
    return f"{BASE}/ex{n}.pdf"


def _handout_url(n: int) -> str:
    return f"{BASE}/handout{n}.pdf"


# 8 booklet chapters — all present in the published booklet.
# (chapter_number, display_title)
CHAPTERS: list[tuple[int, str]] = [
    (1, "Background on ordinary differential equations"),
    (2, "Pragmatic introduction to stochastic differential equations"),
    (3, "Itô calculus and stochastic differential equations"),
    (4, "Probability distributions and statistics of SDEs (FPK)"),
    (5, "Linearization and Itô–Taylor series of SDEs"),
    (6, "Stochastic Runge–Kutta methods"),
    (7, "Bayesian estimation of SDEs"),
    (8, "Further topics: martingales, Girsanov, Feynman–Kac, Fourier"),
]


# 6 lecture handouts — chapter mapping inferred from booklet TOC.
# (handout_number, display_title)
HANDOUTS: list[tuple[int, str]] = [
    (1, "Handout 1 — ODE refresher + pragmatic SDE intro (Chs 1–2)"),
    (2, "Handout 2 — Itô calculus (Ch 3)"),
    (3, "Handout 3 — FPK, transition densities, moments (Ch 4)"),
    (4, "Handout 4 — Itô–Taylor series; weak/strong approximations (Ch 5)"),
    (5, "Handout 5 — Stochastic Runge–Kutta (Ch 6)"),
    (6, "Handout 6 — Bayesian estimation + further topics (Chs 7–8)"),
]


# 6 exercise rounds. Tuple:
#   (n, title_stem, chapter_reading, lec_from, lec_to, points_possible).
# All rounds use points_possible=100 (uniform within the single group).
EXERCISE_ROUNDS: list[tuple[int, str, str, int, int, int]] = [
    (
        1,
        "Mean/covariance equations; Ornstein–Uhlenbeck; Euler–Maruyama",
        "Booklet Ch 2", 1, 1, 100,
    ),
    (
        2,
        "Itô formula; SDE solutions; mean/variance derivation",
        "Booklet Ch 3", 2, 2, 100,
    ),
    (
        3,
        "Fokker–Planck–Kolmogorov; numerical FPK; Langevin Brownian motion",
        "Booklet Ch 4", 3, 3, 100,
    ),
    (
        4,
        "Milstein method; strong/weak Itô–Taylor approximations; Gaussian approx",
        "Booklet Ch 5", 4, 4, 100,
    ),
    (
        5,
        "Stochastic Runge–Kutta (strong + weak); stochastic flow on the torus",
        "Booklet Ch 6", 5, 5, 100,
    ),
    (
        6,
        "Kalman filter + RTS smoother; Kushner–Stratonovich; extended Kalman–Bucy",
        "Booklet Ch 7", 6, 6, 100,
    ),
]


DESCRIPTION = (
    "Applied stochastic differential equations: ODE background, Itô calculus, "
    "Fokker–Planck–Kolmogorov, Itô–Taylor and stochastic Runge–Kutta numerics, "
    "Bayesian filtering for SDEs, Girsanov / Feynman–Kac. Companion to Särkkä "
    "& Solin's 2019 Cambridge textbook (2014 lecture-notes precursor is free)."
)

TEXTBOOK = (
    "Särkkä & Solin — Lecture Notes on Applied Stochastic Differential "
    "Equations, v1.1 (Dec 4, 2014), free PDF at the course source URL. "
    "Published successor: Applied Stochastic Differential Equations "
    "(Cambridge IMS Textbooks, 2019, paid; not used as primary)."
)

HOME_MD = """**Aalto MS-E1602 — Applied Stochastic Differential Equations
(Simo Särkkä & Arno Solin).**

Course materials mirrored from Aalto's public 2014 course site
(<https://users.aalto.fi/~ssarkka/course_s2014/>). The term shown above is
*your* self-study term — edit it from the course settings when your plan
shifts.

A 6-session applied SDE course aimed at probabilistic-modelling and
engineering applications rather than measure-theoretic rigour. Brownian
motion → Itô calculus → SDEs → Fokker–Planck–Kolmogorov → numerical
schemes (Euler–Maruyama, Milstein, Itô–Taylor, stochastic Runge–Kutta) →
Bayesian estimation of SDEs (Kalman–Bucy, Kushner–Stratonovich) →
martingales, Girsanov, Feynman–Kac.

The textbook is the 2014 lecture-notes booklet (119 pages, free) — the
direct precursor to Särkkä & Solin's *Applied Stochastic Differential
Equations* (Cambridge IMS, 2019). Each lecture session is paired with a
handout PDF; the 6 exercise rounds drive the grade.

Aalto did not publish solutions for the exercise rounds — they were
worked through in-person at the exercise session. For self-study, every
round is graded in **project mode**: the AI scores your worked solution
on quality / correctness / depth / clarity against the booklet's
content, without comparing to a reference key.

Jump to **Syllabus**, **Modules**, or **Assignments**.
"""

SYLLABUS_MD = """## Prerequisites
Calculus, linear algebra, probability (distributions, expectations,
multivariate normal). Comfort with ordinary differential equations and a
scientific programming language (the lecture notes use Matlab; Python +
SciPy works fine). Measure theory is *not* assumed — the booklet trades
rigour for readability and points at Øksendal (2003) and Karatzas–Shreve
(1991) for the measure-theoretic foundation.

## Textbook
- **Primary** — Särkkä & Solin, *Lecture Notes on Applied Stochastic
  Differential Equations*, v1.1 (Dec 4, 2014). Free PDF linked under
  **Direct links** in Modules.
- **Successor (paid)** — Särkkä & Solin, *Applied Stochastic Differential
  Equations* (Cambridge IMS Textbooks, 2019). Same content, polished and
  expanded.
- **Background references** cited by the booklet:
  - Øksendal, *Stochastic Differential Equations*, 6th ed (2003).
  - Karatzas & Shreve, *Brownian Motion and Stochastic Calculus* (1991).

## Grading
| Component | Weight |
|---|---|
| Exercise Rounds (6) | 100% |

Aalto's published scheme weights the exercise rounds against an in-person
final exam. There is no public exam to mirror, so for self-study the 6
rounds carry the whole grade — uniform 100 points each.

## Exercise policy
Each round corresponds to one booklet chapter (Ch 2 through Ch 7):

| Round | Booklet chapter | Topic |
|---|---|---|
| E1 | Ch 2 | Pragmatic SDE intro: mean/covariance, Ornstein–Uhlenbeck, Euler–Maruyama |
| E2 | Ch 3 | Itô calculus: Itô formula, explicit linear-SDE solutions |
| E3 | Ch 4 | FPK + numerical FPK, Langevin Brownian motion |
| E4 | Ch 5 | Itô–Taylor: Milstein, strong/weak approximations, Gaussian approx |
| E5 | Ch 6 | Stochastic Runge–Kutta: strong + weak, stochastic flow on the torus |
| E6 | Ch 7 | Bayesian estimation: Kalman + RTS, Kushner–Stratonovich, extended Kalman–Bucy |

The AI grades each submission in **project mode** — no reference
solution is generated. It scores on quality of derivation,
correctness against the booklet's notation and results, code quality
for simulation problems, and clarity of presentation. Re-attempts are
allowed; the latest counts.

## What's not here
- **No public exam.** Aalto's exam was in-person only. The booklet has
  no answer appendix.
- **No videos.** The 2014 offering wasn't recorded.
- **Chapter 8** (martingales, Girsanov, Feynman–Kac, Fourier methods)
  has no exercise round in the Aalto offering. It ships as a module
  reading only — faithful to the source.
"""


# --------------------------------------------------------------------------- modules


def _direct_links_items() -> list[dict]:
    return [
        {"kind": "link", "title": "Aalto MS-E1602 course home (Särkkä)",
         "url": HOME},
        {"kind": "link", "title": "Lecture notes booklet (119 pp PDF)",
         "url": BOOKLET_URL},
        {"kind": "link", "title": "Simo Särkkä — homepage",
         "url": SARKKA_HOMEPAGE},
        {"kind": "link", "title": "Arno Solin — homepage",
         "url": SOLIN_HOMEPAGE},
        {"kind": "link", "title": "Applied SDE — Cambridge book (paid successor)",
         "url": CAMBRIDGE_BOOK_URL},
        {"kind": "link", "title": "Companion MATLAB/Python code (AaltoML/SDE)",
         "url": COMPANION_CODE_URL},
    ]


def _chapter_items() -> list[dict]:
    """All 8 chapter items point at the booklet PDF — there's no per-chapter
    PDF. Chapter number + topic in the title carries the navigation hint."""
    return [
        {"kind": "link", "title": f"Chapter {n} — {topic}", "url": BOOKLET_URL}
        for n, topic in CHAPTERS
    ]


def _handout_items() -> list[dict]:
    return [
        {"kind": "link", "title": title, "url": _handout_url(n)}
        for n, title in HANDOUTS
    ]


def _modules() -> list[tuple[str, list[dict]]]:
    """Three modules mirroring the natural shape of Aalto's published page:

      1. "Direct links" — top-of-course navigation (booklet, authors,
         Cambridge book, companion code).
      2. "Booklet chapters" — 8 chapter readings, all linking to the same
         booklet PDF (no per-chapter PDFs exist).
      3. "Lecture handouts" — 6 handout PDFs paired with the chapters.

    No per-lecture unit modules and no kind='video' items — the 2014
    offering had no recordings. See feedback memory
    ``feedback-module-content-chapter-readings``.
    """
    return [
        ("Direct links", _direct_links_items()),
        ("Booklet chapters", _chapter_items()),
        ("Lecture handouts", _handout_items()),
    ]


# --------------------------------------------------------------------------- descriptions


# Per-round transcribed problem text, drawn verbatim from ex{N}.pdf
# (Sarkka & Solin, Autumn 2014). The AI grader reads this directly — the
# source PDF is also linked for cross-reference, but we do not rely on the
# grader fetching it at runtime.
ROUND_PROBLEMS: dict[int, str] = {
    1: """**Exercise 1 (Mean and covariance equations).**
(a) Complete the missing steps in the derivation of the covariance (eq. 2.37).
(b) Derive the mean and covariance ODEs (eq. 2.38) by differentiating
(2.36) and (2.37).

**Exercise 2 (Solution of an Ornstein–Uhlenbeck process).**
(a) Find $x(t)$, $m(t)$, $P(t)$ for the scalar SDE
$\\frac{dx(t)}{dt} = -\\lambda\\, x(t) + w(t),\\ x(0)=x_0,$
where $x_0$, $\\lambda>0$ are given and $w(t)$ has spectral density $q$.
(b) Compute the limits as $t\\to\\infty$ (i) directly via $\\lim_t P(t)$,
and (ii) by solving the stationary variance ODE $dP/dt=0$.

**Exercise 3 (Euler–Maruyama for the O–U process).**
Simulate 1000 trajectories on $t\\in[0,1]$ from the above process using
Euler–Maruyama with $\\lambda=1/2$, $q=1$, $\\Delta t=1/100$, $x_0=1$,
and check that the mean and covariance trajectories approximately match
the theoretical values.""",
    2: """**Exercise 1 (Usage of the Itô formula).** Compute the Itô differential of
(a) $\\phi(\\beta) = t + \\exp(\\beta)$, where $\\beta(t)$ has diffusion $q$.
(b) $\\phi(x) = x^2$, where $x$ solves $dx = f(x)\\,dt + \\sigma\\,d\\beta$,
$\\sigma$ constant, $\\beta$ standard ($q=1$).
(c) $\\phi(\\mathbf{x}) = \\mathbf{x}^\\top\\mathbf{x}$, where
$d\\mathbf{x}=\\mathbf{F}\\mathbf{x}\\,dt + d\\boldsymbol{\\beta}$,
$\\mathbf{F}$ constant, joint diffusion of $\\boldsymbol{\\beta}$ is $\\mathbf{Q}$.

**Exercise 2 (Stochastic differential equations).**
(a) Check that $x(t)=\\exp(\\beta(t))$ solves $dx=\\tfrac{1}{2}x\\,dt + x\\,d\\beta$
($\\beta$ standard).
(b) Solve $dx = -c\\,x\\,d\\beta$ ($c>0$) by changing variables to $y=\\ln x$.
(c) Convert the Stratonovich SDE $dx_1 = -x_2\\circ d\\beta$,
$dx_2 = x_1\\circ d\\beta$ ($\\beta$ scalar) to the equivalent Itô SDE.

**Exercise 3 (Mean and variance of differential equations).** For
$dx = f(x)\\,dt + \\sigma(x)\\,d\\beta$ with diffusion $q$:
(a) Conclude from the definition of the Itô integral that
$\\mathbb{E}\\!\\left[\\int_u^v \\sigma(x(t))\\,d\\beta(t)\\right] = 0$.
(b) Take expectations of both sides and divide formally by $dt$ to get
the ODE for $m(t)$.
(c) Apply Itô's formula to $\\phi(x,t)=(x-m(t))^2$ and take expectations
to derive the variance ODE.
(d) Write the mean & variance ODEs for $dx=-\\lambda x\\,dt + d\\beta$
($\\lambda>0$); solve with $x(0)=x_0$.""",
    3: """**Exercise 1 (FPK equation).** Consider $dx=\\tanh(x)\\,dt + d\\beta$,
$x(0)=0$, $\\beta$ standard.
(a) Write down the FPK and check that
$p(x,t) = \\tfrac{1}{\\sqrt{2\\pi t}}\\,\\cosh(x)\\,\\exp(-t/2)\\,\\exp(-x^2/(2t))$
solves it.
(b) Plot the evolution of the density for $t\\in[0,5]$.
(c) Simulate 1000 trajectories with Euler–Maruyama and check the
histogram matches at $t=5$.

**Exercise 2 (Numerical solution of FPK).** Use finite differences on
$x\\in[-L,L]$ with Dirichlet BCs $p(\\pm L,t)=0$.
(a) Divide the range into $n$ grid points with $h=1/(n+1)$; approximate
$\\partial_x p$ and $\\partial_{xx} p$ via the standard 2nd-order central
differences.
(b) Form the vector ODE $d\\mathbf{p}/dt = \\mathbf{F}\\mathbf{p}$ where
$\\mathbf{p}=(p(h,t),\\ldots,p(nh,t))^\\top$.
(c) Solve via (i) backward Euler, (ii) numerical $\\exp(\\mathbf{F}t)$,
(iii) forward Euler. Check against Exercise 1.

**Exercise 3 (Langevin's physical Brownian motion).** Model
$\\ddot{x} = -c\\dot{x} + w$, $x(0)=\\dot{x}(0)=0$, $c=6\\pi\\eta r$, white
noise $w$ with spectral density $q$.
(a) Interpret as an Itô SDE; write the 2D state-space form.
(b) Write ODEs for the mean and the covariance entries
$P_{11},P_{12},P_{21},P_{22}$. Find the closed-form covariance solutions
(start with $P_{22}$).
(c) Compute $\\lim_{t\\to\\infty} P_{22}(t)$ and use
$m\\,\\mathbb{E}[(\\dot{x})^2] = RT/N$ to determine $q$.
(d) Plot $P_{11}(t)$ and show it asymptotically approaches a straight
line; compute the asymptotic slope and conclude it recovers Langevin's
result.""",
    4: """**Exercise 1 (Milstein's method).** Consider
$dx = -c\\,x\\,dt + g\\,x\\,d\\beta$, $x(0)=x_0>0$, $\\beta$ standard.
(a) Check via the Itô formula that
$x(t) = x_0\\,\\exp\\!\\big[(-c - g^2/2)t + g\\,\\beta(t)\\big]$ is the exact
solution. *Hint:* $\\phi(\\beta,t) = x_0\\exp[(-c-g^2/2)t + g\\beta]$.
(b) Simulate trajectories with Milstein's method using $x_0=1$,
$c=1/10$, $g=1/10$, and check that the histogram at $t=1$ matches
sampling from the exact solution.

**Exercise 2 (Strong and weak approximations).** Consider
$dx=\\tanh(x)\\,dt + d\\beta$, $x(0)=0$, with exact density $p(x,t)$ as
in Round 3.
(a) Simulate 1000 trajectories with the **strong order 1.5** Itô–Taylor
method (from the lecture notes); compare the histogram to the exact
density at $t=5$.
(b) Simulate 1000 trajectories with the **weak order 2.0** Itô–Taylor
method using (i) Gaussian increments and (ii) three-point distributed
increments; compare to the exact density at $t=5$.
(c) Comment on the behavior of the simulated trajectories for
$t\\in[0,5]$ across methods.

**Exercise 3 (Gaussian approximation of SDEs).**
(a) Form a Gaussian assumed-density approximation to the SDE in
Exercise 2 for $t\\in[0,5]$ and compare to the exact density (compute
Gaussian integrals numerically on a uniform grid).
(b) Form a Gaussian assumed-density approximation to the SDE in
Exercise 1 and compare numerically to the histogram from 1(b).""",
    5: """**Exercise 1 (A strong stochastic Runge–Kutta method).** Consider the
strong order 1.0 method with the extended Butcher tableau given in the
lecture notes (booklet Ch 6).
(a) Write down the iteration equations corresponding to the tableau.
(b) For the Duffing–van der Pol oscillator
$dx_1 = x_2\\,dt,\\ dx_2 = (x_1(\\alpha - x_1^2) - x_2)\\,dt + x_1\\,d\\beta,$
$\\beta$ a 1D Brownian motion with $q=0.5^2$ and $\\alpha=1$, use the
method to draw trajectories starting from $x_2(0)=0$,
$x_1(0)=-4,-3.9,\\ldots,-2$, on $t\\in[0,10]$. Plot in the $(x_1,x_2)$
plane.
(c) Experiment with step sizes $\\Delta t = 2^{-k}$, $k=0,2,4,6$ and
visually compare to Euler–Maruyama.

**Exercise 2 (A weak stochastic Runge–Kutta method).** Consider the 2D
SDE
$dx_1 = \\tfrac{3}{2} x_1\\,dt + \\tfrac{1}{10}x_1\\,d\\beta_1$,
$dx_2 = \\tfrac{3}{2} x_2\\,dt + \\tfrac{1}{10}x_2\\,d\\beta_2$,
$\\mathbf{x}(0)=(1/10,1/10)$, $\\beta_i$ independent standard Brownians.
(a) Implement Euler–Maruyama for the system.
(b) Implement the weak order 2.0 Runge–Kutta scheme from the lecture
notes (Alg. 6.4), with the tableau given in the round PDF.
(c) Simulate 1000 trajectories with both methods for
$\\Delta t = 2^{-k}$, $k=0,\\ldots,6$. Compare to the expected value
$\\mathbb{E}[x_i(t)] = (1/10)\\exp(3t/2)$ and plot absolute errors
vs step size.

**Exercise 3 (Stochastic flow).** Consider the SDE on a torus
$d\\mathbf{x} = \\mathbf{L}(\\mathbf{x})\\,d\\boldsymbol{\\beta}$
($d=2$, $m=4$) with the diffusion columns
$\\mathbf{L}^1(\\mathbf{x}) = (\\cos\\alpha,\\sin\\alpha)^\\top \\sin(x_1)$,
$\\mathbf{L}^2 = (\\cos\\alpha,\\sin\\alpha)^\\top \\cos(x_1)$,
$\\mathbf{L}^3 = (-\\sin\\alpha,\\cos\\alpha)^\\top \\sin(x_2)$,
$\\mathbf{L}^4 = (-\\sin\\alpha,\\cos\\alpha)^\\top \\cos(x_2)$ ($\\alpha=1$).
(a) Use Euler–Maruyama with the same Brownian-motion realization
(reset seed) on a $15\\times 15$ grid of initial points in $[0,2\\pi]^2$
at step size $\\Delta t=2^{-4}$. Plot at $t=0.5,1.0,2.0,4.0$ (take $x_i$
mod $2\\pi$).
(b) Repeat with the weak order 2.0 SRK from the lecture notes
(Alg. 6.5).""",
    6: """**Exercise 1 (Kalman filter and RTS smoother for OU).** Consider
$dx = -\\lambda x\\,dt + d\\beta$, $y_k = x(t_k) + \\varepsilon_k$, with
$\\lambda=1/2$, $q=1$, $x(0)\\sim N(0,P_\\infty)$, $\\varepsilon_k\\sim N(0,1)$,
$P_\\infty$ the stationary variance.
(a) Simulate data with Euler–Maruyama ($\\Delta t=1/100$, $t\\in[0,10]$),
measurements at $t_j=j$, $j=1,\\ldots,10$.
(b) Implement a Kalman filter; plot simulated data, observations, and
filter mean together.
(c) Implement an RTS smoother; plot data, observations, and smoother
mean together.
(d) How would you compute the smoothing solution at an arbitrary $t$?

**Exercise 2 (Continuous-time filtering).** For
$dx=-\\lambda x\\,dt + d\\beta$, $dy = x\\,dt + d\\eta$ ($\\beta,\\eta$
independent standard Brownians):
(a) Write down the Kushner–Stratonovich equation.
(b) Write down the corresponding Zakai equation.
(c) Write down the Kalman–Bucy filter for the model.
(d) Show that the filters in (a)–(c) are equivalent.

**Exercise 3 (Continuous-time approximate non-linear filtering).** For
$dx=\\tanh(x)\\,dt + d\\beta$, $dy=\\sin(x)\\,dt + d\\eta$ with $Q=1$ and
$R=0.01$:
(a) Write down the extended Kalman–Bucy filter.
(b) Simulate data over $[0,5]$ with $\\Delta t=1/100$ and try implementing
the filter numerically. How does it work?""",
}


def _round_description(
    n: int, title_stem: str, chapter: str, lec_from: int, lec_to: int
) -> str:
    """Full description for one exercise round — transcribed problem text,
    source PDF link, booklet chapter reading pointer, and an explicit note
    about project-mode grading."""
    src_url = _exercise_url(n)
    lec_phrase = (
        f"Covers lecture {lec_from}" if lec_from == lec_to
        else f"Covers lectures {lec_from}–{lec_to}"
    )
    return (
        f"**Exercise Round {n}** ({title_stem}). {lec_phrase}. Reading: {chapter}.\n\n"
        f"- Source PDF: [ex{n}.pdf (Aalto)]({src_url})\n"
        f"- Reading: {chapter} of the lecture-notes booklet — see "
        "the *Booklet chapters* module.\n\n"
        "## Problems\n\n"
        f"{ROUND_PROBLEMS[n]}\n\n"
        "---\n\n"
        "**Grading.** Aalto did not publish solutions for this round — "
        "exercises were worked through in person at the exercise session. "
        "The AI grades your submission in **project mode**: it scores on "
        "quality of derivation, correctness against the booklet's notation "
        "and results, code quality for simulation problems, and clarity of "
        "presentation. There is no reference solution to compare against. "
        "Re-attempts are allowed; the latest counts."
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
        title="Applied Stochastic Differential Equations",
        institution="Aalto University",
        term_label="Spring 2029",
        instructor="Profs. Simo Särkkä & Arno Solin",
        external_home_url=HOME,
        status="planned",
        color="#2D7A47",
        display_order=_next_display_order(db),
        textbook=TEXTBOOK,
        home_page_md=HOME_MD,
        syllabus_md=SYLLABUS_MD,
        description=DESCRIPTION,
    )
    db.add(course)
    db.flush()

    g_rounds = AssignmentGroup(
        course_id=course.id,
        name="Exercise Rounds",
        weight=100,
        drop_lowest_n=0,
        position=0,
    )
    db.add(g_rounds)
    db.flush()

    for n, title_stem, chapter, lec_from, lec_to, pts in EXERCISE_ROUNDS:
        a = Assignment(
            course_id=course.id,
            assignment_group_id=g_rounds.id,
            title=f"Exercise Round {n} — {title_stem}",
            description_md=_round_description(
                n, title_stem, chapter, lec_from, lec_to
            ),
            points_possible=pts,
            accepts_files=True,
            accepts_text=True,
            position=n - 1,
            published=True,
            covers_lecture_from=lec_from,
            covers_lecture_to=lec_to,
            requires_solution_key=False,
        )
        db.add(a)

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


def _fixed_title_to_url() -> dict[str, str]:
    """Map a module-item title to the URL it should always point to."""
    out: dict[str, str] = {
        "Aalto MS-E1602 course home (Särkkä)": HOME,
        "Lecture notes booklet (119 pp PDF)": BOOKLET_URL,
        "Simo Särkkä — homepage": SARKKA_HOMEPAGE,
        "Arno Solin — homepage": SOLIN_HOMEPAGE,
        "Applied SDE — Cambridge book (paid successor)": CAMBRIDGE_BOOK_URL,
        "Companion MATLAB/Python code (AaltoML/SDE)": COMPANION_CODE_URL,
    }
    for n, topic in CHAPTERS:
        out[f"Chapter {n} — {topic}"] = BOOKLET_URL
    for n, title in HANDOUTS:
        out[title] = _handout_url(n)
    return out


def update_urls(db: Session) -> dict:
    """Refresh URLs on the live Aalto MS-E1602 course in place — module-item
    URLs and assignment description_md / coverage. Preserves submissions /
    AI solutions / announcements / grades.

    Counter semantics:
      - ``items_examined`` / ``items_updated``: per module-item.
      - ``assignments_updated``: count of *distinct* assignments with any
        field change (description_md). An assignment with multiple field
        changes is counted once.
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
            if it.title in fixed:
                new_url = fixed[it.title]
                if new_url != it.external_url:
                    it.external_url = new_url
                    counts["items_updated"] += 1

    dirty_assignments: set[str] = set()
    by_title = {a.title: a for a in course.assignments}
    for n, title_stem, chapter, lec_from, lec_to, _pts in EXERCISE_ROUNDS:
        a = next(
            (
                x for t, x in by_title.items()
                if t.startswith(f"Exercise Round {n} ")
            ),
            None,
        )
        if a is None:
            continue
        new_desc = _round_description(n, title_stem, chapter, lec_from, lec_to)
        if a.description_md != new_desc:
            a.description_md = new_desc
            dirty_assignments.add(a.id)
        if a.covers_lecture_from != lec_from or a.covers_lecture_to != lec_to:
            a.covers_lecture_from = lec_from
            a.covers_lecture_to = lec_to
            counts["coverage_updated"] += 1

    counts["assignments_updated"] = len(dirty_assignments)

    db.commit()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed the Aalto MS-E1602 (Applied SDE) course.",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="delete an existing Aalto MS-E1602 course first",
    )
    parser.add_argument(
        "--update-urls", action="store_true",
        help="only refresh module_item external_url + assignment fields on "
             "the existing course (no deletions)",
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
            f"Seeded {c.code} — {c.title}: {n_modules} modules, {n_items} "
            f"items, {n_assign} assignments."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
