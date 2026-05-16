# MIT 6.231 (Dynamic Programming and Stochastic Control) — Seed Course Design

**Date:** 2026-05-16
**Status:** Approved (user gave go-ahead on 2026-05-16; this seed replaces the previously-planned Princeton ORF 544 + Stanford EE 364B pair, neither of which has an OCW mirror)
**Scope:** Add the eleventh seeded course to `backend/seed/`. Reuses the `seed_6_262` solution-PDF pipeline (PSets 1–8 + 2015 midterm uploaded to Supabase Storage) and the `seed_18_336` project-mode assignment pattern (Course Project graded with `requires_solution_key=False`).
**Source:** <https://ocw.mit.edu/courses/6-231-dynamic-programming-and-stochastic-control-fall-2015/>
**Branch:** `feat/seed-mit-6-231`

---

## 1. Purpose

Seed `MIT 6.231 — Dynamic Programming and Stochastic Control` (Bertsekas, Fall 2015). Fills the **last remaining slot** in the [[study-plan-jhu-replacement]] sequence apart from the 2026 pre-job refreshers (18.02SC, 18.440): replaces the JHU 625.743 Stochastic Optimization course. Per [[study-sequencing-2027-2030]], slots at the very end of 2030 as the decision-theoretic capstone after Aalto BDA.

Why this OCW course over the original Princeton ORF 544 + Stanford EE 364B pairing:

- Princeton ORF 544 has no OCW or open mirror (only the Castle Lab personal page).
- Stanford EE 364B's recordings are off-OCW (Boyd's personal videos).
- 6.231 covers the same DP / stochastic-control / approximate DP territory under the standard `ocw.mit.edu/courses/<slug>/resources/<slug>` URL pattern the seed pipeline expects.

Idempotent loader at `python -m seed.seed_mit_6_231 [--force] [--update-urls] [--refresh-solutions]`, mirroring `seed_6_262` exactly.

## 2. Source-page structure (verified via WebFetch 2026-05-16)

Course base: `https://ocw.mit.edu/courses/6-231-dynamic-programming-and-stochastic-control-fall-2015/`

Nav pages present:

- `pages/syllabus/`
- `pages/lecture-notes/` — 23 lecture slide decks
- `pages/assignments/` — 9 problem sets (PSets 1–7, 9 are textbook references; PSet 8 has a custom homework PDF)
- `pages/exams/` — 2015 midterm + 3 historical (2008, 2009, 2011)
- `pages/projects/` — project description + topics-list PDF
- `pages/related-video-lectures/` — links to Bertsekas's 2014 ASU course (no MIT-internal videos)

Nav pages **absent**:

- `pages/calendar/` — redirects, no calendar published. No per-PSet due dates exist; lecture-coverage ranges below are derived by topical match to Bertsekas's four-unit syllabus.

### Resource URL slugs

- Lecture slides: `mit6_231f15_lec{N}` for N=1..23 (not zero-padded)
- PSet solutions: `mit6_231f15_solution{N}` for N=1..8 (PSet 9 has **no** published solution)
- PSet 8 custom homework: `mit6_231f15_homework8`
- Midterm papers + solutions: `mit6_231f15_mid_{year}` and `mit6_231f15_mid_{year}_sol` for year ∈ {2008, 2009, 2011, 2015}
- Project topics list: `mit6_231f15_references`

OCW PDF URLs are content-hash-prefixed (e.g. `c12643..._MIT6_231F15_solution1.pdf`); the hash is not derivable from the slug. The seed scrapes `/resources/{slug}/` for the matching PDF link — same pattern as `seed_6_262._resolve_pdf_url`.

## 3. Course meta

| Field | Value |
|---|---|
| `code` | `"MIT 6.231"` |
| `title` | `"Dynamic Programming and Stochastic Control"` |
| `institution` | `"Massachusetts Institute of Technology"` |
| `instructor` | `"Prof. Dimitri P. Bertsekas"` |
| `external_home_url` | `https://ocw.mit.edu/courses/6-231-dynamic-programming-and-stochastic-control-fall-2015/` |
| `term_label` | `"Fall 2030"` (placeholder — user edits via teacher mode per [[feedback-seed-flexibility]]) |
| `status` | `"planned"` |
| `color` | `"#1F7A4D"` (forest green — distinct from existing 18.100B/36-705/18.700/18.065/6.262/18.336/CS-4220/IEOR-6711/Aalto-SDE/Aalto-BDA palette) |
| `display_order` | `6` (next free slot) |
| `textbook` | Bertsekas, *Dynamic Programming and Optimal Control*, Vol I (3rd ed., 2005) + Vol II: Approximate Dynamic Programming (4th ed., 2012), Athena Scientific |

`home_page_md` and `syllabus_md` in the same voice as the other seeds. `term_label` and `home_page_md` are user-customised; `--update-urls` does NOT touch them (per the `term_label` semantics rule in CLAUDE.md).

## 4. Grading (30 / 30 / 40)

Matches the OCW syllabus exactly: Homework 30%, Quizzes/Midterm 30%, Project 40%.

| Group | Weight | Assignments | `drop_lowest_n` |
|---|---|---|---|
| Problem Sets | 30 | 9 (PS1–PS9) | 0 |
| Midterm | 30 | 1 (2015 paper) | 0 |
| Course Project | 40 | 1 (Project — project mode) | 0 |

## 5. Problem-set table

| # | Title | Problems | covers_lec | Homework slug | Solution slug |
|---|---|---|---|---|---|
| 1 | Introduction & basic problem | Vol I — 1.2, 1.3, 1.22, 2.1, 2.7, 2.9 | 1–2 | — | `mit6_231f15_solution1` |
| 2 | Deterministic & stochastic finite-horizon | Vol I — 4.1, 4.2, 4.29, 4.33, 4.34 | 3–5 | — | `mit6_231f15_solution2` |
| 3 | Stopping problems | Vol I — 5.2(a), 5.7, 5.14 | 5–6 | — | `mit6_231f15_solution3` |
| 4 | Imperfect state info | Vol I — 6.2 (skip first two sentences), 6.10, 6.16, 6.20 | 6–7 | — | `mit6_231f15_solution4` |
| 5 | Suboptimal control | Vol I — 7.2 | 8 | — | `mit6_231f15_solution5` |
| 6 | Rollout & limited lookahead | Vol I — 7.3, 7.5, 7.7, 7.8a, 7.10, 7.11 | 8–9 | — | `mit6_231f15_solution6` |
| 7 | Approximate DP | Vol I — 7.20, 7.22, 7.23, 7.24, 7.25, 7.26 | 9 | — | `mit6_231f15_solution7` |
| 8 | Infinite-horizon (custom homework) | See attached PDF | 10–13 | `mit6_231f15_homework8` | `mit6_231f15_solution8` |
| 9 | Approximate DP (Vol II) | Vol II — 4.12 and 4.17 | 19–22 | — | **no solution published** |

### Solution-key strategy per PSet

- **PSets 1–8:** `requires_solution_key=True`, official-solution PDF uploaded to Supabase Storage under `solutions/official/6_231/`. AI grader reads the PDF.
- **PSet 9:** `requires_solution_key=True`, no `official_solution_*` populated → AI grader generates its own key (like CMU 36-705 and Aalto BDA weeklies).
- **PSet 8 homework PDF:** the assignment statement (not from textbook). Downloaded? No — only the solution PDF is uploaded as `official_solution_file_path`. The homework URL goes into `description_md` for the human user. The solution PDF restates the problems, so the AI grader has what it needs.

### Midterm

- 2015 paper graded (slug `mit6_231f15_mid_2015`, official solution uploaded). Covers Lec 1–9 (finite + imperfect-info horizon).
- Historical 2008/2009/2011 papers + solutions live in the **Practice Midterms** Module, not as Assignment rows (per [[feedback-module-content-chapter-readings]] Rule 3 — past papers as study aids).

### Course Project

`requires_solution_key=False` (project mode, shipped in PRs #6/#7). `description_md` summarises Bertsekas's proposal:
- Choice between **theoretical** (read & critically evaluate 2–3 papers in a stochastic-control subarea with original commentary on extensions) and **applied** (formulate + computationally solve a stochastic-control problem).
- ≤15 pp 12pt single-spaced + figures, appendices allowed.
- Proposal (1 page) ~ end of Week 11; presentation in Week 15.
- Links to `mit6_231f15_references` as a starting-points list.

## 6. Modules (4 modules)

1. **Direct links** — 7 items: home, syllabus, lecture-notes, assignments, exams, projects, related-video-lectures.
2. **Lecture Slides** — 23 link items, slug `mit6_231f15_lec{N}`. Each item titled `"Lecture N: {topic}"` from the lecture-notes index.
3. **Project Resources** — 1 item: "List of project topics (with references)" → `mit6_231f15_references`.
4. **Practice Midterms** — 6 items: 3 historical years (2008/2009/2011) × {paper, indented solution}.

No per-lecture readings module (Bertsekas's textbooks aren't on OCW; readings are inline in the `LECTURE_TOPICS` table for use by the home page, but not exposed as Module items). See [[feedback-module-content-chapter-readings]] — Rule 1.

## 7. Implementation pattern

Single file `backend/seed/seed_mit_6_231.py` modelled directly on `seed_6_262.py`:

- Constants block (CODE, BASE, page-level URL constants).
- URL helpers (`_lec_url`, `_ps_sol_url`, `_hw8_url`, `_midterm_url`, `_midterm_sol_url`, `_project_topics_url`).
- `_PDF_HREF_RE` + `_resolve_pdf_url(slug)` — re-implemented locally (not pulled into shared util; matches per-seed precedent).
- `_storage_key_for(slug)` → `official/6_231/{slug}.pdf`.
- `_attach_official_solution(db, a, slug)` — download + Supabase upload with graceful URL-only fallback on failure.
- Data tables: `LECTURE_TOPICS`, `PROBLEM_SETS`, `MIDTERM_SPEC`, `PROJECT_SPEC`, `_PRACTICE_MIDTERM_YEARS`.
- Module builders: `_direct_links_items`, `_lecture_slides_items`, `_project_resources_items`, `_practice_midterms_items`, `_modules`.
- Core: `_build_course`, `_build_groups`, `_build_assignments`, `_build_modules`, `seed(db)`.
- `update_urls(db)` for non-destructive URL refresh.
- `main()` argparse: `--force`, `--update-urls`, `--refresh-solutions`.

Tests in `backend/tests/test_seed_mit_6_231.py` (~20 small unit tests, mirroring `test_seed_aalto_bda.py` style). Defensive autouse `_mock_network_for_seed` fixture to block accidental httpx calls; explicit monkeypatches per-test for the solution-pipeline tests.

## 8. Out of scope

- Bertsekas Vol I / Vol II PDFs (paywalled — Athena Scientific).
- Per-lecture videos (OCW only links to Bertsekas's 2014 ASU recordings; no MIT-internal videos for this offering).
- Final exam (does not exist — 6.231 has only a midterm + project).
- Per-PSet due-date population (no OCW calendar — `due_at` left `NULL`; `ScheduleCourseModal` populates dates when the user flips status `planned → active`).
