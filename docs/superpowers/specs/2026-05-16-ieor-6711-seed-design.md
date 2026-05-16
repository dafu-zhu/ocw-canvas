# Columbia IEOR 6711 (Stochastic Models I) — Seed Course Design

**Date:** 2026-05-16
**Status:** Draft for review
**Scope:** Add the sixth seed course to `backend/seed/`. First seed sourced outside MIT OCW; first time pulling PDFs from a Cloudflare-protected origin.
**Source:** <https://www.columbia.edu/~ww2040/6711F13/IEOR6711F13.html>

---

## 1. Purpose

Seed `COLUMBIA IEOR 6711 — Stochastic Models I` (Ward Whitt, Columbia Fall 2013). Sits in the [[study-sequencing-2027-2030]] 2028 slot as the second-half of the year-long stochastic-processes pair (Gallager 6.262 → Whitt 6711). Idempotent loader at `python -m seed.seed_ieor_6711 [--force] [--update-urls] [--refresh-solutions]`, mirroring the existing `seed_6_262.py` shape.

Reuses the 6.262 solution-PDF pipeline: ~15 official solution PDFs (13 problem sets + 1 midterm + 1 final, all published by Whitt) are downloaded and uploaded to Supabase Storage under `solutions/official/ieor_6711/`, and wired to `assignment.official_solution_file_path` so the AI grader reads Whitt's real reference rather than regenerating one.

## 2. Source-page structure (partially verified)

Course base: `https://www.columbia.edu/~ww2040/6711F13/`

Confirmed-via-search URLs:
- Index: `IEOR6711F13.html`
- Lecture-notes index: `lectures6711.html`
- Homework index: `homework6711.html`
- Sample lecture PDFs: `lect0905.pdf`, `lect1011.pdf`, `lect1018.pdf`, `lect1129.pdf`, `lectCLT.pdf`
- Sample homework solutions: `homewk1Sols.pdf`, `homewk3Sols.pdf`, `homewk7Sols.pdf`, `homewk13Sols.pdf` (implies 13 problem sets)
- Midterm: `midtermOne6711F13.pdf` + `midtermOne6711F13sols.pdf`
- Final: `final6711F13.pdf` + `final6711F13sols.pdf`
- Side reference: `homewkLTnotes.pdf` (Laplace transforms supplement)

Course meets Tu/Th 10:10–11:25 in Room 1220 Mudd. Textbook: Sheldon Ross, *Stochastic Processes* 2e (Wiley 1996). Topics: Ch 1 probability review, Ch 2 Poisson, Ch 3 renewal theory, Ch 4 DTMC, Ch 5 CTMC, plus martingales / Brownian motion (Whitt's own notes, not in Ross).

**Unverified (Cloudflare-gated, must scrape at implementation time):**
- Exact date list of all ~26 lecture PDFs (`lectMMDD.pdf` filenames)
- Exact per-PSet chapter coverage (the homework index lists this; search confirmed PS4=Ch 2, PS12=Ch 5)
- Exact grading-weight split published by Whitt

The implementation will need to fetch `homework6711.html` and `lectures6711.html` once (via curl with a browser UA, or a manual one-time download if Cloudflare's challenge wall blocks server-side fetches) and hardcode the resulting structure into the seed module — same way `seed_6_262.py` hardcodes its 25-lecture map.

## 3. Course meta

| Field | Value |
|---|---|
| `code` | `"COLUMBIA IEOR 6711"` |
| `title` | `"Stochastic Models I"` (Whitt's actual title; the [[study-plan-jhu-replacement]] "Stochastic Processes II" label is the JHU slot it fills, not the source) |
| `institution` | `"Columbia University"` |
| `instructor` | `"Prof. Ward Whitt"` |
| `external_home_url` | `https://www.columbia.edu/~ww2040/6711F13/IEOR6711F13.html` |
| `term_label` | `"Fall 2028"` (user's self-study term — editable via teacher mode) |
| `status` | `"planned"` |
| `color` | `"#75AADB"` (Columbia light blue — distinct from cardinal/teal/navy/tartan-red/deep-purple) |
| `display_order` | `5` (after 6.262=4) |
| `textbook` | `Ross, Stochastic Processes 2e (Wiley 1996) — primary. Whitt's lecture notes (PDFs linked in the Lecture notes module) supplement with martingales and Brownian motion not covered in Ross.` |

`home_page_md` and `syllabus_md` written in the same voice as the other seeds.

**Key wording difference from 6.262:** `home_page_md` must call out that Ross is not freely available (unlike Gallager, which OCW mirrors chapter-by-chapter). User needs a print or PDF copy from Wiley.

## 4. Grading (30 / 30 / 40 — defensible default)

Whitt's page doesn't publish exact weights in any of the search-result snippets reachable. We use a defensible doctoral-course default:

| Group | Weight | Assignments | `drop_lowest_n` |
|---|---|---|---|
| Problem Sets | 30 | 13 (PS1–PS13) | 0 |
| Midterm Exam | 30 | 1 (Midterm — Fall 2013 paper, covers Ch 1–2) | 0 |
| Final Exam | 40 | 1 (Final — Fall 2013 paper, cumulative) | 0 |

`syllabus_md` flags this explicitly: *"Approximate weighting — Whitt's published grading split for 6711F13 isn't reproduced verbatim here; 30/30/40 is a defensible default. Adjust via teacher mode if you confirm the actual split."* Per [[feedback_seed_flexibility]] — adjust to match what's actually published, but don't fabricate detail we can't verify.

**Why one midterm and one final, not multiple historical years:** Unlike 6.262, Whitt's page only publishes Fall 2013's papers in clean form (search results don't surface earlier-year midterms / finals as cleanly indexed). We use the F13 papers as the graded assignments; no practice-exams module.

## 5. Assignments (15 total)

### 5.1 Problem Sets (13)

URLs follow `homewk{N}.pdf` and `homewk{N}Sols.pdf` (1-indexed, no zero pad confirmed by search results).

| PS | Lec from | Lec to | Topic (Ross chapter) | Paper URL fragment | Solution URL fragment |
|---|---|---|---|---|---|
| 1 | 1 | 2 | Probability review (Ch 1) | `homewk1.pdf` | `homewk1Sols.pdf` |
| 2 | 3 | 4 | Probability review continued (Ch 1) | `homewk2.pdf` | `homewk2Sols.pdf` |
| 3 | 5 | 6 | Probability review / Poisson intro (Ch 1–2) | `homewk3.pdf` | `homewk3Sols.pdf` |
| 4 | 7 | 8 | Poisson process (Ch 2) — **confirmed via search** | `homewk4.pdf` | `homewk4Sols.pdf` |
| 5 | 9 | 10 | Poisson process continued (Ch 2) | `homewk5.pdf` | `homewk5Sols.pdf` |
| 6 | 11 | 12 | Renewal theory (Ch 3) | `homewk6.pdf` | `homewk6Sols.pdf` |
| 7 | 13 | 14 | Renewal theory continued (Ch 3) | `homewk7.pdf` | `homewk7Sols.pdf` |
| 8 | 15 | 16 | DTMC (Ch 4) | `homewk8.pdf` | `homewk8Sols.pdf` |
| 9 | 17 | 18 | DTMC continued (Ch 4) | `homewk9.pdf` | `homewk9Sols.pdf` |
| 10 | 19 | 20 | DTMC / CTMC transition (Ch 4–5) | `homewk10.pdf` | `homewk10Sols.pdf` |
| 11 | 21 | 22 | CTMC (Ch 5) | `homewk11.pdf` | `homewk11Sols.pdf` |
| 12 | 23 | 24 | CTMC continued (Ch 5) — **confirmed via search** | `homewk12.pdf` | `homewk12Sols.pdf` |
| 13 | 25 | 26 | Martingales / Brownian (Whitt notes) | `homewk13.pdf` | `homewk13Sols.pdf` |

**Lecture-range columns are approximate** and will be tightened during implementation once the homework page is scrapeable. Topics labelled "confirmed via search" come directly from search-result text; the rest are interpolated by Ross chapter ordering.

Each assignment: `points_possible=100`, `accepts_files=True`, `accepts_text=True`, `requires_solution_key=True`.

### 5.2 Midterm Exam (1)

- Title: `"Midterm Exam (Fall 2013 paper)"`
- Coverage: `covers_lecture_from=1, covers_lecture_to=10` (Ch 1–2 per search confirmation; midterm fell on 2013-10-06)
- Paper: `midtermOne6711F13.pdf`
- Solution: `midtermOne6711F13sols.pdf`

### 5.3 Final Exam (1)

- Title: `"Final Exam (Fall 2013 paper)"`
- Coverage: `covers_lecture_from=1, covers_lecture_to=26` (cumulative)
- Paper: `final6711F13.pdf`
- Solution: `final6711F13sols.pdf`

## 6. Solution-PDF download & upload pipeline (reuse of 6.262 pattern)

Identical shape to `seed_6_262._attach_official_solution`, with two differences:

1. **Storage namespace:** `solutions/official/ieor_6711/` (not `6_262/`).
2. **URL construction:** Whitt's URLs are flat — `{BASE}/homewk{N}Sols.pdf` directly, no content-hash prefix to scrape. So no `_resolve_pdf_url` step is needed. The seed builds the URL string and `httpx.get`s it directly.

```python
def _attach_official_solution(db, a, filename):
    storage_key = f"official/ieor_6711/{filename}"
    if a.official_solution_file_path == storage_key:
        try:
            storage.read_bytes("solutions", storage_key)
            return
        except Exception:
            pass
    try:
        resp = httpx.get(f"{BASE}/{filename}", timeout=60, follow_redirects=True,
                         headers={"User-Agent": "Mozilla/5.0 (compatible; ocw-canvas-seed)"})
        resp.raise_for_status()
        storage.upload_bytes("solutions", storage_key, resp.content, "application/pdf")
        a.official_solution_file_path = storage_key
        a.official_solution_url = ""
    except Exception as exc:
        a.official_solution_url = f"{BASE}/{filename}"
        print(f"warn(seed_ieor_6711): solution upload failed for {filename}: {exc}")
```

### Cloudflare risk and mitigation

Cloudflare's bot-challenge wall blocked `WebFetch` against `columbia.edu/~ww2040/` during research, but **static PDFs typically bypass the challenge** because Cloudflare scopes the JS challenge to HTML pages, not to direct file requests. The seed will try `httpx.get` with a browser UA; if that fails for one PDF, the graceful-degradation branch keeps the seed running URL-only mode (same as 6.262's degradation path). One probe download during early implementation will confirm whether the full mirror works.

If Cloudflare blocks all 15 PDFs, the seed completes in URL-only mode (no `official_solution_file_path` set) and the AI grader uses the URL-aware branch ("official solution exists at this URL; grade against standard rigor"). User loses zero functionality compared to 18.700 / 18.065 / 36-705 seeds, which don't ship solution PDFs at all.

## 7. Modules (2)

1. **Direct links** — course home (`IEOR6711F13.html`), lecture-notes index (`lectures6711.html`), homework index (`homework6711.html`), Ross textbook publisher page (<https://www.wiley.com/en-us/Stochastic+Processes%2C+2nd+Edition-p-9780471120629>), Laplace-transform supplement (`homewkLTnotes.pdf`).
2. **Lecture notes (Whitt)** — ~26 items, one per `lectMMDD.pdf`, titled `"Lecture YYYY-MM-DD — <topic>"`. Each item maps to a Ross chapter section. Implementation-time scrape of `lectures6711.html` produces the exact filename list.

**No "Practice exams" module** — F13 publishes only one midterm + one final, both used as graded assignments. Per [[feedback_seed_flexibility]] (don't fabricate exams).

**No per-unit modules.** Mirrors the 6.262 refactor (commit 2862cb9, PR #9) that consolidated unit modules into a single Course-Notes module. Whitt's lecture PDFs are the natural Course-Notes analogue.

## 8. `update_urls()` semantics

Standard updater (mirrors `seed_6_262.update_urls`):
- Refreshes module-item `external_url` for all fixed-title items (home, lecture index, homework index, Ross page, Laplace supplement, every lecture PDF).
- Refreshes assignment `description_md` (so PSet/exam descriptions stay in sync).
- Refreshes `covers_lecture_from/to`.
- Refreshes `official_solution_url` **only when `official_solution_file_path` is empty** — preserves the successful-seed clear from `_attach_official_solution` (see [[feedback]] commit 2d1cf1c rationale).

Separate `--refresh-solutions` flag clears `official_solution_file_path` and re-runs `_attach_official_solution` for every assignment.

## 9. CLI

```bash
# Initial seed
python -m seed.seed_ieor_6711

# Force-replace (drops course + cascade; storage PDFs stay)
python -m seed.seed_ieor_6711 --force

# Refresh URLs only (no DB structure changes, no PDF re-download)
python -m seed.seed_ieor_6711 --update-urls

# Re-download all 15 solution PDFs (if Whitt's host changes / rotates files)
python -m seed.seed_ieor_6711 --refresh-solutions
```

## 10. Tests

Follow the existing seed pattern: no dedicated unit tests (matches `seed_6_262.py`, which has none — the integration boundary is `app.services.storage` + `httpx`, both already mockable at higher layers). Verification is:

- Manual: `cd backend && uv run python -m seed.seed_ieor_6711` against a local sqlite DB; check counts and one solution-PDF readback.
- CI: `uv run pytest -q` must still pass (no new test failures introduced).
- CI: `uv run ruff check .` clean.

## 11. Memory updates after this lands

- [[study-sequencing-2027-2030]]: advance `Columbia IEOR 6711` from `⏳ Next up` to `✅ seeded`; promote MIT 18.336 to next-up.
- No new feedback memories expected unless Cloudflare interaction surfaces a surprise.

## 12. Non-goals

- Not seeding Fall 2012 papers as practice (user declined the hybrid option).
- Not adding a Ross-chapter overview module (the lecture-notes module already encodes chapter mapping in each item's title).
- Not changing any backend model, migration, API, or frontend file.
- Not modifying existing seeds (`seed_6_262.py`, `seed_18_700.py`, etc.) for consistency — they stay as-is.

## 13. Risks

- **Cloudflare blocks server-side PDF download.** Mitigation: graceful URL-only fallback (same path as 6.262 documents). One probe download during implementation determines whether the full-mirror or URL-only path is used. Either path produces a working seed.
- **Lecture date scrape requires manual one-time fetch.** If Cloudflare blocks the seed-time fetch of `lectures6711.html` and `homework6711.html`, the dev (i.e. me) downloads them once manually in a real browser and hardcodes the lecture map into the seed module — same shape as `LECTURE_VIDEO_SLUGS` in `seed_6_262.py`.
- **Whitt's host could disappear.** `columbia.edu/~ww2040/` is a personal faculty page; if Whitt retires or Columbia migrates, every URL breaks. The Supabase-uploaded PDFs survive that scenario; only the live links rot. `--update-urls` becomes the failure-mode patch point if the user wants to repoint to a web-archive mirror.
- **Grading split is a guess.** 30/30/40 is documented as approximate in `syllabus_md`. If the user finds Whitt's real split, a one-line edit fixes it without re-seeding.

## 14. Branch & merge plan

- Branch: `feat/seed-ieor-6711` off master.
- Single new file: `backend/seed/seed_ieor_6711.py`.
- Single new spec: this file.
- No existing files modified.
- `git status` clean before PR; `git diff master...HEAD` shows only the two new files.
- Merge via `--no-ff` PR (per CLAUDE.md branching convention).
