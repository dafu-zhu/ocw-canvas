# Cornell CS 4220 (Numerical Analysis: Linear & Nonlinear Problems) — Seed Course Design

**Date:** 2026-05-16
**Status:** Draft for review
**Scope:** Add a seed for Bindel's Cornell CS 4220 / MATH 4260 (Spring 2024). Mirrors `seed_cmu_36705.py`'s shape (notes-only source, no exams, no video), with the additional twist that two assignments are project-style (`requires_solution_key=False`).
**Source:** <https://www.cs.cornell.edu/courses/cs4220/2024sp/>

---

## 1. Purpose

Seed a sixth course end-to-end: `Cornell CS 4220 — Numerical Analysis: Linear and Nonlinear Problems`, instructor David Bindel. Idempotent loader (`python -m seed.seed_cornell_cs4220 [--force] [--update-urls]`) that builds the Course → Modules → Module Items → Assignment Groups → Assignments tree pointing out to Cornell-hosted URLs. Nothing is re-hosted.

This is the second seed (after CMU 36-705) modelled on a personal/course-page-hosted source rather than OCW. It is also the first seed whose graded items mix answer-key and project-mode assignments in a single course — exercising the `requires_solution_key=False` path that 18.065's Final Project introduced for a single project.

**Note on course-number confusion.** An earlier study-plan memory listed "Cornell CS 4220 / MATH 4250" as "ODE numerics" — that conflates two distinct Bindel courses. CS 4220 / MATH 4260 is *Numerical Analysis: Linear & Nonlinear Problems* (no ODEs); ODE numerics is CS 4210 / MATH 4250. This seed targets **CS 4220 / MATH 4260**.

## 2. Source-page structure (verified)

Course homepage `https://www.cs.cornell.edu/courses/cs4220/2024sp/` lists everything inline (no separate `lec.html` / `hw.html`; those return 404). HEAD-checked all PDF URLs below; all return 200.

Homework PDFs (6 total):

```
hw1.pdf  hw2.pdf  hw3.pdf  hw4.pdf  hw5.pdf  hw6.pdf
```

with companion `hwN.tex` source files and `hw2_data.zip` for HW2 only.

Project PDFs (2 total):

```
P1.pdf   P2.pdf
```

with companion `PN.tex` source files and `P1data.zip` for P1 only.

Additional in-page references cited by specific lectures:

- Lec 1: Trefethen 1992 — `https://people.maths.ox.ac.uk/trefethen/publication/PDF/1992_55.pdf`
- Lec 16: Perturbation handout — `https://www.cs.cornell.edu/courses/cs4220/2024sp/Perturbation.pdf`
- Lec 38: Berkeley opt4ml book — `https://people.eecs.berkeley.edu/~brecht/opt4ml_book/`
- Lec 39–41: SIAM RNLA paper — `https://epubs.siam.org/doi/10.1137/090771806`

Other resources:

- **No per-lecture notes PDF.** The 42-row lecture table on the homepage gives only date + topic + Ascher & Greif chapter pointers ("AG: 5.6, 5.7") for most lectures.
- **No syllabus PDF.** Syllabus content is on the homepage itself.
- **No exam papers, no exam solutions.** Midterm and Final are described as take-home, released 3/13 and 5/9, but the papers are distributed via Gradescope and not hosted publicly.
- **No homework or project solutions** posted publicly.
- **No video lectures.** Bindel does not record.
- **Paper review** (grad section CS 5223) — irrelevant to a self-study seed; skipped.

## 3. Course meta

| Field | Value |
|---|---|
| `code` | `"Cornell CS 4220"` |
| `title` | `"Numerical Analysis: Linear and Nonlinear Problems"` |
| `institution` | `"Cornell University"` |
| `instructor` | `"Prof. David Bindel"` |
| `external_home_url` | `https://www.cs.cornell.edu/courses/cs4220/2024sp/` |
| `term_label` | `"Spring 2030"` (placeholder; CS 4220 isn't in the explicit 2027–2029 sequencing — user edits in teacher mode when scheduled) |
| `status` | `"planned"` |
| `color` | `"#B31B1B"` (Cornell Big Red) |
| `display_order` | `5` (after 18.100B=0, 36-705=1, 18.700=2, 18.065=3, 6.262=4) |
| `textbook` | Ascher & Greif, *A First Course in Numerical Methods* (SIAM, 2011) — referenced throughout as "AG: §X.Y" |

`home_page_md` and `syllabus_md` written in the same voice as the other seeds. Syllabus markdown reproduces the homepage's grading + collaboration policy + textbook info, **adapted for self-study** (no Gradescope, no Ed Discussion, no proctored exams — see §4 and §5.3 for the adaptation).

## 4. Assignment groups

Two groups. The original Cornell course has four components (HW 30% / Projects 30% / Midterm 20% / Final 20%); since the midterm and final have no published paper or solution, they're dropped entirely (per `feedback-seed-flexibility`) and the remaining HW + Project weights renormalize to 60% / 40%.

| Position | Name | Weight | drop_lowest_n | Items |
|---:|---|---:|---:|---:|
| 0 | Homework | 60 | 0 | 6 |
| 1 | Projects | 40 | 0 | 2 |

`drop_lowest_n = 0` everywhere. Bindel's grading section is silent on drops.

## 5. Assignments

### 5.1 Homeworks 1–6 (answer-key graded)

Each HW links to its `hw{N}.pdf`, with HW2 also linking to `hw2_data.zip`. `requires_solution_key=True` (default) — the AI generates a reference solution and grades against it. No `official_solution_url` is set (Bindel publishes none).

`covers_lecture_from / covers_lecture_to` (calendar-derived from the published due dates):

| HW | Due (2024) | covers LN | Topic block |
|---:|:---|:---|:---|
| 1 | 2/5  | 1–7   | Intro · LA background · numerical algorithms & error · sensitivity · floating point |
| 2 | 2/19 | 8–11  | LU, pivoting, Cholesky, sparse |
| 3 | 3/8  | 12–20 | Least squares & QR · ill-posedness · eigenvalue problems · QR alg · SVD |
| 4 | 4/12 | 21–29 | Classical/Krylov iterations · nonlinear & optim intro · gradient/Newton · line search · quasi-Newton |
| 5 | 4/26 | 30–36 | BFGS · Gauss-Newton · IRLS · constraints |
| 6 | 5/7  | 37–42 | Constraints (cont.) · stochastic opt · randomized NLA · review |

`description_md` for each HW: links the source PDF (and data zip when applicable), reproduces the homepage's collaboration policy in one line ("Discuss freely; write solutions independently."), notes the AI-grader convention.

### 5.2 Project 1 and Project 2 (project mode)

Both projects are open-ended ("explore X — choose a direction, write up your findings"). Setting `requires_solution_key=False` so the AI grades on quality / depth / clarity / effort without comparing to a reference solution (verified flag implemented in `migration 0006`, `assignment.py:56`, used by `seed_18_065.py:449` for the 18.065 Final Project, and branched on in `services/ai_jobs.py` + `services/ai.py`).

| # | Due (2024) | covers LN | Source |
|---:|:---|:---|:---|
| 1 | 3/11 | 1–20 | `P1.pdf` + `P1data.zip` — through eigenvalues / SVD |
| 2 | 5/1  | 21–37 | `P2.pdf` — iterative methods + nonlinear/optimization |

`description_md` for each project: links the source PDF (and data zip when applicable), states "Open-ended; graded in project mode — the AI evaluates depth, clarity, and effort, no reference key."

### 5.3 No midterm, no final

The original course has a take-home midterm (released 3/13, due 3/20) and final (released 5/9, due 5/16), but **neither paper nor any solution is posted publicly** — they're distributed via Cornell's Gradescope. Per `feedback-seed-flexibility`, the seed does not include phantom assignments that point nowhere. If the user later wants to attempt them in teacher mode, they can add the assignments by hand after uploading a self-written problem set.

## 6. Modules (8 total, topic-grouped)

42 lectures grouped by topic, mirroring the natural arc of Bindel's table. No per-lecture URL exists for most lectures; each module item is a `kind="note"` block whose body lists its lectures with the AG chapter reference (and, where Bindel cites one, an external URL). One module per topic block plus a Direct-links module.

| # | Title | Lectures | Notes |
|---:|---|:---|---|
| 0 | Direct links | — | Course home · Homework PDFs (6) · Project PDFs (2) · Ascher & Greif reference · Bindel's faculty page |
| 1 | Background & error analysis | 1–7 | LA review (AG ch 4) · numerical algorithms & error (AG ch 1) · sensitivity (AG ch 1–2) · floating point (AG ch 2). Note item for Lec 1 includes the Trefethen 1992 link. |
| 2 | Direct linear solvers | 8–11 | LU, pivoting, Cholesky, sparse (AG §5.1–5.7) |
| 3 | Least squares & QR | 12–15 | QR factorization, ill-posedness, regularization (AG §6.1–6.3, §8.2) |
| 4 | Eigenvalue problems | 16–20 | Perturbation, power/orthogonal/QR iteration, SVD (AG §8.1, §8.3). Note item for Lec 16 includes the Perturbation.pdf link. |
| 5 | Iterative methods | 21–24 | Classical iterations, Krylov subspace, preconditioning (AG §7.2–7.5) |
| 6 | Nonlinear systems & optimization | 25–37 | Nonlinear equations, gradient/Newton, line search, quasi-Newton, BFGS, Gauss-Newton, IRLS, constraints (AG §9.1–9.3) |
| 7 | Advanced topics | 38–41 | Stochastic optimization (opt4ml book) · Randomized NLA (SIAM 2011 paper). Note items embed those URLs. |

Lecture 42 ("Review") is mentioned but produces no separate item (it's a course-wide wrap-up).

Module item structure inside each topic module:
- one `kind="note"` per lecture block (lectures grouped naturally — e.g. "Lec 8–9: LU & pivoting (AG §5.1–5.3)" is a single note item, not two)
- where Bindel cites an external URL on a specific lecture, that URL appears in the note's `external_url` field and the body text mentions it
- no `kind="video"` items anywhere (Bindel publishes none — per `feedback-module-content-chapter-readings` Rule 1)

This is the chief structural divergence from `seed_cmu_36705.py`, where each lecture had its own published PDF and warranted a `kind="link"` item.

## 7. URL helpers (Python sketch)

```python
BASE = "https://www.cs.cornell.edu/courses/cs4220/2024sp"
HOME = BASE + "/"

# Six homeworks (uniform "hw{N}.pdf"). HW2 also has a data zip.
def _hw_url(n: int) -> str:
    return f"{BASE}/hw{n}.pdf"

HW_DATA_URL: dict[int, str] = {2: f"{BASE}/hw2_data.zip"}

# Two projects (uniform "P{N}.pdf"). P1 also has a data zip.
def _proj_url(n: int) -> str:
    return f"{BASE}/P{n}.pdf"

PROJ_DATA_URL: dict[int, str] = {1: f"{BASE}/P1data.zip"}

# Inline references for specific lectures (note bodies set external_url here).
LECTURE_REFS: dict[int, str] = {
    1:  "https://people.maths.ox.ac.uk/trefethen/publication/PDF/1992_55.pdf",
    16: f"{BASE}/Perturbation.pdf",
    38: "https://people.eecs.berkeley.edu/~brecht/opt4ml_book/",
    39: "https://epubs.siam.org/doi/10.1137/090771806",
    40: "https://epubs.siam.org/doi/10.1137/090771806",
    41: "https://epubs.siam.org/doi/10.1137/090771806",
}
```

## 8. File layout

Two new files:

- `backend/seed/seed_cornell_cs4220.py` — the seed module
- `backend/tests/test_seed_cornell_cs4220.py` — pytest covering seed → idempotence → `--force` recreate → `--update-urls` no-op, mirroring `tests/test_seed_6_262.py`'s structure with the network-mocking autouse fixture

Public surface mirrors the other seeds:

- module-level constants (URLs, topic groupings, markdown blobs)
- `seed(db, force=False) -> Course`
- `update_urls(db) -> dict` (idempotent in-place URL/description refresh)
- `main()` argparse wrapper exposing `--force` and `--update-urls`

No changes to `app/`, ORM models, migrations, or frontend. Strictly additive.

## 9. Differences from `seed_cmu_36705.py` (cheat sheet)

| Concern | 36-705 | CS 4220 (new) |
|---|---|---|
| Per-lecture notes PDF | yes (27 PDFs) | **no** — only AG chapter pointers |
| Lecture module items | `kind="link"` to each LN PDF | `kind="note"` per lecture block, body lists AG sections |
| Homework count | 13 | 6 |
| Homework URL pattern | mixed case (`homework1` lowercase, rest Title-case) | uniform lowercase (`hw{N}.pdf`) |
| HW data files | none | `hw2_data.zip` only |
| Projects | none | 2 (project-mode, `requires_solution_key=False`) |
| Exam materials | none (also dropped) | none (also dropped) |
| Assignment groups | 4 (Homework / Test I / Test II / Final) | 2 (Homework / Projects) |
| Grading weights | 50 / 10 / 10 / 30 | 60 / 40 |
| `term_label` default | `""` | `"Spring 2030"` placeholder |
| Module count | 11 | 8 |

## 10. Testing

Mirror `tests/test_seed_6_262.py`'s shape: autouse fixture mocks any network calls, in-memory SQLite, pytest fixtures for `db_session` and the seed module under test.

Cases:

1. `test_seed_creates_expected_structure` — counts course/modules/items/groups/assignments
2. `test_seed_is_idempotent` — second `seed()` is a no-op
3. `test_seed_force_recreates` — `--force` deletes + re-creates
4. `test_update_urls_is_idempotent` — second `update_urls()` returns zero changes
5. `test_projects_have_requires_solution_key_false` — guards the project-mode flag

Plus the standard ruff + pytest invocations (`uv run ruff check .`, `uv run pytest -q`) must pass before commit.

## 11. Open / deferred

- **Lecture-block grouping inside each module is editorial.** I'm grouping adjacent lectures that share an AG section into a single note item ("Lec 8–9: LU & pivoting (AG §5.1–5.3)"). If the user later wants one note per lecture, that's a `--update-urls` edit, not a re-seed.
- **No homework or project solutions are uploaded** — Bindel publishes none. The AI generates a reference solution for each of the 6 HWs at active-time; projects skip that step (project mode).
- **No video lecture gallery** — Bindel publishes none.

## 12. Out of scope

- No new ORM models or migrations (`requires_solution_key` already exists from migration 0006).
- No backend API changes.
- No frontend changes.
- No re-organization of existing seed files; the new file coexists with the others.
- No paper-review or take-home-exam scaffolding (graduate-only / not publicly distributed).
