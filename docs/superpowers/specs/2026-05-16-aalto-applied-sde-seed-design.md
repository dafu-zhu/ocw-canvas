# Aalto Applied SDE — Seed Course Design

**Date:** 2026-05-16
**Status:** Approved (user gave go-ahead on 2026-05-16 after picking the Aalto course as a replacement for the dead Stanford MATH 236 slot and ruling out the broken Bath MA50251 source).
**Scope:** Add a seed course covering the JHU 625.714 SDE slot using Särkkä & Solin's freely available 2014 Aalto course materials. Every graded assignment uses `requires_solution_key=False` (project-mode AI grading) — the course publishes no solutions, so this is the second seed (after Aalto BDA's capstone) to exercise the project-mode flow shipped in PRs #6 / #7, and the **first** seed where *every* graded assignment is project-mode.
**Source:** <https://users.aalto.fi/~ssarkka/course_s2014/>
**Branch:** `feat/seed-aalto-applied-sde`

---

## 1. Purpose

Seed `Aalto MS-E1602 — Applied Stochastic Differential Equations` (Simo Särkkä & Arno Solin, Aalto Autumn 2014). Sits in the 2029 SDE slot of [[study-sequencing-2027-2030]] (originally listed as "Stanford MATH 236" in the JHU-replacement plan; Stanford has no OCW and MATH 236 was unrecoverable). Idempotent loader at `python -m seed.seed_aalto_applied_sde [--force] [--update-urls]`, mirroring the existing seeds in shape.

Pattern differences vs. prior seeds:

- **All assignments are project-mode.** All 6 exercise rounds use `requires_solution_key=False`. Aalto's exercises explicitly say "solutions will be gone through during the exercise session" — no solution PDFs are published, none are recoverable, and the booklet has no answer appendix. First seed where every graded assignment is project-mode.
- **No exam group.** The course has no exams. Single assignment group, "Exercise Rounds," weight 100%.
- **No Storage interaction.** Same as Aalto BDA — no official-solution PDFs to upload. No `--refresh-solutions` CLI flag.
- **One textbook spine; precursor to a paid book.** The 2014 booklet (119 pages, free) is the precursor to Särkkä & Solin's 2019 Cambridge University Press textbook of the same title. The booklet covers Chapter 1–8 of the published book minus measure theory, which matches what the user wants (applied / mathematical-maturity, not measure-theoretic).

## 2. Source-page structure (verified)

Course directory: `https://users.aalto.fi/~ssarkka/course_s2014/`

All files HEAD-check 200. URL audit performed 2026-05-16:

| File | URL | Status |
|---|---|---|
| Booklet (lecture notes) | `https://users.aalto.fi/~ssarkka/course_s2014/sde_course_booklet.pdf` | 200, 119 pp, 2.0 MB |
| Handouts (slides) | `https://users.aalto.fi/~ssarkka/course_s2014/handout{N}.pdf` for N ∈ {1..6} | 200 |
| Exercise rounds | `https://users.aalto.fi/~ssarkka/course_s2014/ex{N}.pdf` for N ∈ {1..6} | 200 |
| `exercises/` subdir | `https://users.aalto.fi/~ssarkka/course_s2014/exercises/` | listing exists, empty (no solution PDFs) |

**No solution PDFs.** Confirmed by directory listing + sample reads of `ex1.pdf` ("The solutions will be gone through during the exercise session in room F255"). No appendix in the booklet (TOC ends with `References` on page 119).

**No videos.** The Autumn 2014 offering was in-person only; no recordings exist on Aalto Panopto or YouTube for this course.

## 3. Course meta

| Field | Value |
|---|---|
| `code` | `"Aalto MS-E1602"` |
| `title` | `"Applied Stochastic Differential Equations"` |
| `institution` | `"Aalto University"` |
| `instructor` | `"Profs. Simo Särkkä & Arno Solin"` |
| `external_home_url` | `https://users.aalto.fi/~ssarkka/course_s2014/` |
| `term_label` | `"Spring 2029"` (user's self-study term — editable via teacher mode; matches the 2029 SDE slot in [[study-sequencing-2027-2030]]) |
| `status` | `"planned"` |
| `color` | `"#2D7A47"` (forest green — distinct from teal/cardinal/navy/tartan/purple/Aalto-blue) |
| `display_order` | next free slot — assigned at seed time as `max(existing) + 1` (or hard-coded `9` if Aalto BDA lands first at `8`) |
| `textbook` | Särkkä & Solin — *Lecture Notes on Applied Stochastic Differential Equations*, v1.1 (Dec 4, 2014), free PDF at the source URL above. Published successor: *Applied Stochastic Differential Equations* (Cambridge IMS Textbooks, 2019) — paid, not used as primary. |

`home_page_md` and `syllabus_md` written in the same voice as the other seeds. `term_label` and `home_page_md` are user-customised; `--update-urls` will not touch them (per the `term_label` semantics rule in CLAUDE.md).

## 4. Grading (100% — exercise rounds; no exams)

Aalto's published grading scheme for MS-E1602 weights the exercise rounds against an in-person final exam. We drop the exam half and let the 6 rounds carry the whole grade — faithful to "use what's published, don't fabricate exams" ([[feedback-seed-flexibility]]).

### Assignment groups

| Group | Weight | Assignments | `drop_lowest_n` |
|---|---|---|---|
| Exercise Rounds | 100 | 6 (E1–E6) | 0 |

## 5. Assignments (6 total)

All 6 use `requires_solution_key=False` (project-mode AI grading). `description_md` for each transcribes the exercise problems from the source PDF (or, for problems with long LaTeX, summarises and links to the source PDF) plus a reading pointer to the relevant booklet chapter(s).

Within-group weighting is uniform: `points_possible=100` each. The booklet's chapter structure tracks the rounds closely (Round k mostly covers chapter k+1, with Round 1 starting at Chapter 2 because Chapter 1 is ODE refresher).

| # | Title | Reading | `points_possible` | `covers_lec` | `requires_solution_key` |
|---|---|---|---|---|---|
| E1 | Mean/covariance equations; Ornstein–Uhlenbeck; Euler–Maruyama simulation | Booklet Ch 2 | 100 | 1–1 | **False** |
| E2 | Itô integrals; Itô's formula; explicit linear-SDE solutions | Booklet Ch 3 | 100 | 2–2 | **False** |
| E3 | Fokker–Planck–Kolmogorov; transition densities; moments of SDEs | Booklet Ch 4 | 100 | 3–3 | **False** |
| E4 | Itô–Taylor series; weak / strong approximations | Booklet Ch 5 | 100 | 4–4 | **False** |
| E5 | Stochastic Runge–Kutta methods (strong / weak) | Booklet Ch 6 | 100 | 5–5 | **False** |
| E6 | Bayesian filtering for SDEs; Kushner–Stratonovich, Kalman–Bucy | Booklet Ch 7 | 100 | 6–6 | **False** |

Each `description_md` includes:

- A link to the source PDF: `ex{N}.pdf`
- The transcribed problem statements (LaTeX preserved — front-end already supports KaTeX)
- A reading pointer to the booklet chapter and section numbers
- An explicit note that the AI grades on quality / correctness / depth / clarity (no reference solution), per project-mode

The exercise rounds use the existing `covers_lecture_from/to` schema (P6) for the schedule-generator: each Ex covers one "lecture-week" mapping to one booklet chapter.

**Chapter 8 (Further topics — martingales, Girsanov, Feynman–Kac, Fourier methods) has no exercise round** in the Aalto offering. It ships as a module reading only, not as a graded assignment. This is faithful to the source.

## 6. Modules (3 — mirrors the natural shape; no per-lecture unit modules)

Per [[feedback-module-content-chapter-readings]] Rules 1 + 2.

### 6.1 "Direct links" (~6 items)

| # | Title | URL |
|---|---|---|
| 1 | Course home (Simo Särkkä) | `https://users.aalto.fi/~ssarkka/course_s2014/` |
| 2 | Lecture notes booklet (119 pp PDF) | `https://users.aalto.fi/~ssarkka/course_s2014/sde_course_booklet.pdf` |
| 3 | Simo Särkkä's homepage | `https://users.aalto.fi/~ssarkka/` |
| 4 | Arno Solin's homepage | `https://arno.solin.fi/` |
| 5 | Cambridge book product page (paid successor) | `https://www.cambridge.org/core/books/applied-stochastic-differential-equations/0F1F3D5A0E64E73E2F87DAEB57B620E2` |
| 6 | Companion MATLAB/Python code | `https://github.com/AaltoML/SDE` |

### 6.2 "Booklet chapters" (8 items)

`kind="link"` items, one per chapter (all pointing at the same `sde_course_booklet.pdf` with section numbers in the title for navigation; the booklet has internal anchors but they aren't guaranteed stable, so the title carries the section info).

| Ch | Topic |
|---|---|
| 1 | Background on ordinary differential equations |
| 2 | Pragmatic introduction to stochastic differential equations |
| 3 | Itô calculus and stochastic differential equations |
| 4 | Probability distributions and statistics of SDEs (FPK) |
| 5 | Linearization and Itô–Taylor series of SDEs |
| 6 | Stochastic Runge–Kutta methods |
| 7 | Bayesian estimation of SDEs |
| 8 | Further topics: martingales, Girsanov, Feynman–Kac, Fourier |

### 6.3 "Lecture handouts" (6 items)

`kind="link"` items, one per handout PDF. Title format: `"Handout {N} — {topic}"`. The handout-to-chapter mapping is inferred from the booklet TOC: 6 handouts for 8 chapters means the first handout pairs with Chs 1+2 (ODE bg + pragmatic SDE intro) and the last pairs with Chs 7+8 (Bayesian + further topics).

| N | Topic |
|---|---|
| 1 | ODE refresher + pragmatic SDE intro (Chs 1–2) |
| 2 | Itô calculus (Ch 3) |
| 3 | FPK, transition densities, moments (Ch 4) |
| 4 | Itô–Taylor series; weak/strong approximations (Ch 5) |
| 5 | Stochastic Runge–Kutta (Ch 6) |
| 6 | Bayesian estimation + further topics (Chs 7–8) |

## 7. CLI

Two subcommands, matching prior seeds without solution PDFs:

```
uv run python -m seed.seed_aalto_applied_sde                 # idempotent seed (no-op if exists)
uv run python -m seed.seed_aalto_applied_sde --force         # delete + re-create
uv run python -m seed.seed_aalto_applied_sde --update-urls   # refresh URLs + descriptions in place
```

No `--refresh-solutions` — there are no official solution PDFs to refresh.

`update_urls(db)` rewrites module-item URLs, assignment `description_md`, and assignment coverage in place; preserves submissions / AI solutions / announcements / grades. Returns a counts dict (`{course_found, items_examined, items_updated, assignments_updated, coverage_updated}`).

## 8. Tests

`backend/tests/test_seed_aalto_applied_sde.py`, mirroring `test_seed_aalto_bda.py` / `test_seed_6_262.py`:

- Idempotency: second `seed()` is a no-op (returns existing course).
- `--force` recreates cleanly.
- Module + assignment counts match the spec (3 modules with 6 / 8 / 6 items; 6 assignments in 1 group).
- Group weight is 100; per-assignment `points_possible=100` and **all 6** assignments have `requires_solution_key=False`.
- `update_urls()` is no-op on a freshly seeded course; rewrites titles ↔ URLs after a tampered URL.
- Autouse fixture mocks `httpx.get` / `httpx.post` so no test makes a real network call (matching the existing test conventions). Storage isn't touched, but the fixture still patches `app.services.storage` defensively.

## 9. Out of scope for this seed

- Live seed runs against the Supabase DB (user runs `python -m seed.seed_aalto_applied_sde` on Render or locally after merge).
- A `--refresh-solutions` flag (no PDFs to refresh).
- Adding an exam group (course has no exams).
- Rendering handout PDFs as inline images / readings (per Rule 1 — link items only).
- Pulling exercises from a different source (e.g. Pavliotis, Klebaner) to give AI grading a reference key — out of scope; the user chose to use project-mode for all 6 rounds.

## 10. Risks

| Risk | Mitigation |
|---|---|
| Aalto user-page drift (`~ssarkka/course_s2014/` rename or removal) | `--update-urls` lets us refresh in place. As a hedge, also document the Wayback Machine snapshot path in `home_page_md`. |
| Project-mode grading on 6 problem sets is uncharted territory (Aalto BDA only used project-mode for the capstone) | First-run risk; we'll find out empirically whether the AI gives useful feedback on math-heavy problem sets without a key. The booklet's content is detailed enough that the AI should ground itself, but if quality is bad post-seed, the fallback is to disable AI grading on E1–E6 and use the platform purely for submission tracking. |
| Transcribed LaTeX in `description_md` drifts from the source PDF | `--update-urls` re-reads the source PDFs and rewrites the descriptions. Source PDFs are stable (last modified 2014). |
| Stanford MATH 236 slot is now mis-named in [[study-plan-jhu-replacement]] | Update that memory after merge to record the substitution. |
