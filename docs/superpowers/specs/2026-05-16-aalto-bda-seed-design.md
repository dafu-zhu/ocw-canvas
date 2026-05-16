# Aalto BDA (Bayesian Data Analysis) — Seed Course Design

**Date:** 2026-05-16
**Status:** Approved (user gave go-ahead on 2026-05-16 for design + unattended implementation)
**Scope:** Add the sixth seed course to `backend/seed/`. First seed where the AI grades against its own generated key for *every* graded assignment (Aalto publishes none) and first to ship a capstone project assignment using the project-mode AI grading shipped in PRs #6/#7.
**Source:** <https://avehtari.github.io/BDA_course_Aalto/>
**Branch:** `feat/seed-aalto-bda`

---

## 1. Purpose

Seed `Aalto BDA — Bayesian Data Analysis` (Aki Vehtari, Aalto CS-E5710). Sits in the [[study-sequencing-2027-2030]] 2030 slot as the decision-theoretic capstone of the JHU-replacement plan. Idempotent loader at `python -m seed.seed_aalto_bda [--force] [--update-urls]`, mirroring the existing seeds in shape.

Pattern differences vs. prior seeds:

- **No exam group.** Aalto BDA has 9 weekly assignments + 1 capstone project, no exams. Grading mirrors that.
- **No official-solution PDFs.** Aalto runs peer grading via peergrade.io / FeedbackFruits — no public solution keys are published. Every weekly assignment uses `requires_solution_key=True` and the AI generates its own reference key (like CMU 36-705). No Storage uploads, no `--refresh-solutions` CLI flag.
- **First project-mode assignment.** The capstone uses `requires_solution_key=False`, exercising the project-mode AI grading shipped in PRs #6 / #7.
- **Within-group weighting via `points_possible`.** Aalto publishes per-assignment weights (GSU 2023 scheme: 6/6/19/12/12/12/12/12/6 percent across the 9 weeklies). Since the `Assignment` model has no per-assignment weight field, we encode the relative weights as `points_possible` (×10 for round numbers: 60/60/190/120/120/120/120/120/60).

## 2. Source-page structure (verified)

Course base: `https://avehtari.github.io/BDA_course_Aalto/` (a Quarto-rendered site backed by `github.com/avehtari/BDA_course_Aalto`).

Nav pages present (verified via `gh api`):

- `index.html` — general info, prerequisites, BDA3 chapter list, R/Stan resources
- `Aalto2025.html` — current Aalto-iteration page (schedule + weekly-rhythm)
- `BDA3_notes.html` — index of the BDA3 chapter notes (the actual readings)
- `assignments.html` / `assignments_gsu.html` — assignment overview (weighting, peer-grading policy)
- `project.html` / `project_gsu.html` — capstone project description
- `project_rubric.html` — FeedbackFruits rubric (criteria the AI grades against)
- `demos.html` — R + Python demos
- `FAQ.html`

Linked from outside the Quarto site:

- `users.aalto.fi/~ave/BDA3.pdf` — BDA3 free PDF
- `github.com/avehtari/BDA_course_Aalto` — GitHub repo (slides, demos, raw files)
- `github.com/avehtari/BDA_R_demos`, `github.com/avehtari/BDA_py_demos` — companion demo repos
- `aalto.cloud.panopto.eu/Panopto/Pages/Sessions/List.aspx#folderID=...` — Panopto video gallery
- `mc-stan.org` — Stan home

**Chapter notes URLs:** `https://avehtari.github.io/BDA_course_Aalto/chapter_notes/BDA_notes_ch{N}.pdf` for `N ∈ {1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12}` (11 PDFs; ch 8 is omitted by the course).

**Slides URLs:** `https://github.com/avehtari/BDA_course_Aalto/raw/master/slides/BDA_lecture_{slug}.pdf` for slugs `{1a, 1b, 2, 3, 4, 5, 6, 7, 8a, 8b, 9, 10a, 10b, 10c, 11a, 11b, 11c}` (17 PDFs).

**Assignment URLs:** `https://avehtari.github.io/BDA_course_Aalto/assignments/assignment{N}.html` for `N ∈ {1..9}`.

**No exam URLs** — Aalto BDA has no exams.

## 3. Course meta

| Field | Value |
|---|---|
| `code` | `"Aalto BDA"` |
| `title` | `"Bayesian Data Analysis"` |
| `institution` | `"Aalto University"` |
| `instructor` | `"Prof. Aki Vehtari"` |
| `external_home_url` | `https://avehtari.github.io/BDA_course_Aalto/` |
| `term_label` | `"Spring 2030"` (user's self-study term — editable; matches the 2030 slot in [[study-sequencing-2027-2030]]) |
| `status` | `"planned"` |
| `color` | `"#0066B3"` (Aalto blue — distinct from teal/cardinal/navy/tartan/purple) |
| `display_order` | `5` (after 18.100B=0, 36-705=1, 18.700=2, 18.065=3, 6.262=4; IEOR 6711 design doc is a draft only, no seed yet, so slot 5 is open) |
| `textbook` | Gelman, Carlin, Stern, Dunson, Vehtari, Rubin — *Bayesian Data Analysis*, 3rd ed (CRC 2013). Free PDF at `users.aalto.fi/~ave/BDA3.pdf`. Secondary: Gelman, Hill, Vehtari — *Regression and Other Stories* (Cambridge 2020). |

`home_page_md` and `syllabus_md` written in the same voice as the other seeds. `term_label` and `home_page_md` are user-customised; `--update-urls` will not touch them (per the `term_label` semantics rule in CLAUDE.md).

## 4. Grading (70 / 30 — assignments / project)

Aalto's own published scheme uses peer grading and weights the project separately (peer report 30% + presentation 70% within the project; the overall PSets-vs-project split is not published as a single percentage). For self-study we adopt a simple **70% Weekly Assignments / 30% Capstone Project** split — the weekly assignments are the main grade driver while the capstone is sizable.

### Assignment groups

| Group | Weight | Assignments | `drop_lowest_n` |
|---|---|---|---|
| Weekly Assignments | 70 | 9 (A1–A9) | 0 |
| Capstone Project | 30 | 1 (Project — Bayesian workflow) | 0 |

## 5. Assignments (10 total)

### 5.1 Weekly assignments (9)

Within-group weighting follows the **GSU 2023** published scheme (`assignments_gsu.Rmd`: "max points 3, 3, 9, 6, 6, 6, 6, 6, 3 → weights ≈ 6/6/19/12/12/12/12/12/6 %", sum=99). Encoded as `points_possible × 10` for round numbers. We pick GSU 2023 over the Aalto 2025 alternative (5/5/10/10/15/20/15/10/10) because the GSU scheme is the one Aalto explicitly designed for self-study iterations — and it weights A3 (multiparameter) as the proof-of-concept block, which matches a self-study learner's experience. All use `requires_solution_key=True` — the AI generates its own reference solution (no published key to compare against).

| # | Title | Reading | Lecture | `points_possible` | `covers_lec` |
|---|---|---|---|---|---|
| A1 | Introduction & basics of Bayesian inference | BDA3 Ch 1 | 1 | 60  | 1–1 |
| A2 | Single-parameter models | BDA3 Ch 2 | 2 | 60  | 2–2 |
| A3 | Multidimensional posterior (multiparameter models) | BDA3 Ch 3 | 3 | 190 | 3–3 |
| A4 | Monte Carlo methods | BDA3 Ch 10 | 4 | 120 | 4–4 |
| A5 | Markov chain Monte Carlo | BDA3 Ch 11 | 5 | 120 | 5–5 |
| A6 | Stan, HMC & probabilistic programming | BDA3 Ch 12 | 6 | 120 | 6–6 |
| A7 | Hierarchical models & exchangeability | BDA3 Ch 5 | 7 | 120 | 7–7 |
| A8 | Model checking & comparison (LOO-CV / WAIC) | BDA3 Chs 6 + 7 | 8–9 | 120 | 8–9 |
| A9 | Decision analysis | BDA3 Ch 9 | 10 | 60  | 10–10 |

A6 and A7 each have a two-week hand-in window in Aalto's calendar (a midterm break sits between weeks 6 and 7). For our schedule-generator semantics each still "covers" only its own lecture; the extended hand-in window is an Aalto calendar artefact, not a coverage statement. If we later want explicit two-week dues, the cadence picker in `ScheduleCourseModal` handles that at activation time.

Each `description_md` includes:
- Paper link: `assignments/assignment{N}.html`
- A note that the AI generates its own reference solution and grades against it (no published Aalto key)
- Reading pointer: BDA3 chapter
- Optional companion: the matching R/Python demo

### 5.2 Capstone project (1)

| Field | Value |
|---|---|
| Title | `"Capstone Project — Bayesian workflow end-to-end"` |
| Group | Capstone Project |
| `points_possible` | 100 |
| `requires_solution_key` | **False** (project-mode AI grading) |
| `covers_lecture_from / to` | `1 / 12` (covers everything; spans the whole course) |

`description_md` quotes the 12-step report rubric from `project.html` (introduction → data description → ≥2 models → priors → MCMC inference + diagnostics → posterior predictive checks → optional predictive performance → sensitivity analysis → model comparison via LOO-CV → discussion → conclusion → self-reflection), plus a link to `project_rubric.html`. Includes an explicit note that the AI grades on quality / coverage of workflow steps / clarity, with no reference solution.

## 6. Modules (3 — mirror the natural shape; no per-lecture units, no inline video links)

Per [[feedback-module-content-chapter-readings]] Rules 1 + 2.

### 6.1 "Direct links" (~13 items)

| # | Title | URL |
|---|---|---|
| 1 | Course home (Aki Vehtari) | `https://avehtari.github.io/BDA_course_Aalto/` |
| 2 | Aalto 2025 iteration page | `https://avehtari.github.io/BDA_course_Aalto/Aalto2025.html` |
| 3 | BDA3 free PDF (textbook) | `https://users.aalto.fi/~ave/BDA3.pdf` |
| 4 | BDA3 chapter notes (index) | `https://avehtari.github.io/BDA_course_Aalto/BDA3_notes.html` |
| 5 | Assignments overview | `https://avehtari.github.io/BDA_course_Aalto/assignments.html` |
| 6 | Project description | `https://avehtari.github.io/BDA_course_Aalto/project.html` |
| 7 | Project rubric | `https://avehtari.github.io/BDA_course_Aalto/project_rubric.html` |
| 8 | Demos (R + Python) | `https://avehtari.github.io/BDA_course_Aalto/demos.html` |
| 9 | BDA R demos (GitHub) | `https://github.com/avehtari/BDA_R_demos` |
| 10 | BDA Python demos (GitHub) | `https://github.com/avehtari/BDA_py_demos` |
| 11 | Lecture videos (Panopto) | `https://aalto.cloud.panopto.eu/Panopto/Pages/Sessions/List.aspx?folderID=b6f169ef-a8b4-4a04-983b-b1df009838f8` (2024 folder — latest stable) |
| 12 | Stan home | `https://mc-stan.org/` |
| 13 | FAQ | `https://avehtari.github.io/BDA_course_Aalto/FAQ.html` |

### 6.2 "BDA3 Chapter notes" (11 items)

`kind="link"` items, one per chapter notes PDF. Title format: `"Chapter {N} — {topic}"`.

| N | Topic |
|---|---|
| 1 | Background |
| 2 | Single-parameter models |
| 3 | Multiparameter models |
| 4 | Normal approximation & frequency properties |
| 5 | Hierarchical models |
| 6 | Model checking |
| 7 | Evaluating and comparing models |
| 9 | Decision analysis |
| 10 | Computational methods |
| 11 | Markov chain Monte Carlo |
| 12 | Stan & probabilistic programming |

### 6.3 "Lecture slides" (17 items)

`kind="link"` items, one per slide PDF. Title format: `"Lecture {slug} — {topic}"`. Ordered by `(lecture-number, sub-deck)`:

| Slug | Topic |
|---|---|
| 1a | Course intro + computational probabilistic modelling |
| 1b | Uncertainty & modelling |
| 2  | Single-parameter models |
| 3  | Multiparameter models |
| 4  | Monte Carlo |
| 5  | Markov chain Monte Carlo |
| 6  | Stan, HMC, probabilistic programming |
| 7  | Hierarchical models |
| 8a | Model checking |
| 8b | Cross-validation |
| 9  | Model comparison & selection (LOO, WAIC) |
| 10a | Decision analysis (intro) |
| 10b | Decision analysis (continued) |
| 10c | Decision analysis (extra) |
| 11a | Normal approximation |
| 11b | Frequency properties |
| 11c | Laplace approximation |

## 7. CLI

Three subcommands, matching prior seeds:

```
uv run python -m seed.seed_aalto_bda                 # idempotent seed (no-op if exists)
uv run python -m seed.seed_aalto_bda --force         # delete + re-create
uv run python -m seed.seed_aalto_bda --update-urls   # refresh URLs + descriptions in place
```

No `--refresh-solutions` — there are no official solution PDFs to refresh.

`update_urls(db)` rewrites module-item URLs, assignment `description_md`, and assignment coverage in place; preserves submissions / AI solutions / announcements / grades. Returns a counts dict (`{course_found, items_examined, items_updated, assignments_updated, coverage_updated}`).

## 8. Tests

`backend/tests/test_seed_aalto_bda.py`, mirroring `test_seed_6_262.py`:

- Idempotency: second `seed()` is a no-op (returns existing course).
- `--force` recreates cleanly.
- Module + assignment counts match the spec (3 modules with 13 / 11 / 17 items; 10 assignments across 2 groups).
- Group weights sum to 100; per-assignment `points_possible` and `requires_solution_key` match the tables in §5.
- Project assignment has `requires_solution_key=False`.
- `update_urls()` is no-op on a freshly seeded course; rewrites titles ↔ URLs after a tampered URL.
- Autouse fixture mocks `httpx.get` / `httpx.post` so no test makes a real network call (matching the existing test conventions). Storage isn't touched (no PDFs uploaded), but the fixture should still patch `app.services.storage` defensively.

## 9. Out of scope for this seed

- Real seed runs against the live Supabase DB (user does that manually after merge, via `python -m seed.seed_aalto_bda` on Render or local).
- A `--refresh-solutions` flag (no PDFs to refresh).
- Adding an exam group (Aalto BDA has no exams).
- Rendering the slide-deck videos as items in Modules (per Rule 1 — the Panopto link in Direct links is the single navigation entry).

## 10. Risks

| Risk | Mitigation |
|---|---|
| Aalto URL drift (chapter-note PDF paths rename) | `--update-urls` lets us refresh in place without touching submissions / AI keys. |
| `points_possible` scale (60–190 looks odd in the UI) | Acceptable — the values encode weighting that the user sees on the gradebook anyway. Documented in `syllabus_md`. |
| Project-mode AI grading flow newly shipped (PR #6) — first live use | Test coverage in `test_seed_aalto_bda.py` confirms the `requires_solution_key=False` wiring. Live behaviour will be exercised when the user actually uploads a capstone draft. |
| Panopto video-folder ID may rotate between iterations | Pin to the 2024 stable folder ID; `--update-urls` can switch later. |
