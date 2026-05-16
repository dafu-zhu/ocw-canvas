# Columbia IEOR 6711 (Stochastic Models I) — Seed Course Design

**Date:** 2026-05-16
**Status:** Draft for review (revised post-source-probe)
**Scope:** Add the sixth seed course to `backend/seed/`. First seed sourced outside MIT OCW.
**Source:** <https://www.columbia.edu/~ww2040/6711F13/IEOR6711F13.html>

---

## 1. Purpose

Seed `COLUMBIA IEOR 6711 — Stochastic Models I` (Ward Whitt, Columbia Fall 2013). Sits in the [[study-sequencing-2027-2030]] 2028 slot as the second half of the year-long stochastic-processes pair (Gallager 6.262 → Whitt 6711). Idempotent loader at `python -m seed.seed_ieor_6711 [--force] [--update-urls] [--refresh-solutions]`, mirroring the existing `seed_6_262.py` shape.

Reuses the 6.262 solution-PDF pipeline: 16 official solution PDFs (13 problem sets + 2 midterms + 1 final, all published by Whitt) are downloaded and uploaded to Supabase Storage under `solutions/official/ieor_6711/`, and wired to `assignment.official_solution_file_path` so the AI grader reads Whitt's real reference rather than regenerating one.

> **Revised 2026-05-16 (post-source-probe):** initial spec assumed one midterm and 26 lecture meetings. Probing `lectures6711.html` and `homework6711.html` with a browser UA revealed Whitt's Fall 2013 actually ran *two* midterms (First on Oct 6, Ch 1–2; Second on Nov 17, Ch 3–4), and only ~20 of the class meetings have published lecture PDFs (the rest reference Ross / a consolidated CTMC notes PDF). Grading split adjusted from 30/30/40 to 30/20/20/30.

## 2. Source-page structure (verified post-probe)

Course base: `https://www.columbia.edu/~ww2040/6711F13/`

Confirmed reachable with browser UA (`Mozilla/5.0 ... Chrome/120`):
- `IEOR6711F13.html` — index
- `lectures6711.html` — lecture-notes index
- `homework6711.html` — homework index
- 20 primary lecture PDFs (see table in §7)
- 13 problem-set PDFs (`homewk{N}.pdf`) + 13 solutions (`homewk{N}Sols.pdf`)
- 6 exam PDFs: `midtermOne6711F13.pdf` / `midtermOne6711F13sols.pdf` / `midtermTwo6711F13.pdf` / `midtermTwo6711F13sols.pdf` / `final6711F13.pdf` / `final6711F13sols.pdf`
- Supplementary: `homewkLTnotes.pdf` (Laplace transforms)

Course met Tuesdays/Thursdays 10:10–11:25 in Room 1220 Mudd. Textbook: Sheldon Ross, *Stochastic Processes* 2e (Wiley 1996). Topics: Ch 1 probability review, Ch 2 Poisson, Ch 3 renewal theory, Ch 4 DTMC, Ch 5 CTMC, plus martingales / Brownian motion (Whitt's own notes, not in Ross).

**Still not published by Whitt:** exact grading-weight split. The seed uses 30/20/20/30 as a defensible doctoral default and documents this in `syllabus_md`.

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
| `textbook` | `Ross, Stochastic Processes 2e (Wiley 1996) — primary. Whitt's lecture notes (linked in the Lecture notes module) supplement with martingales and Brownian motion not covered in Ross.` |

`home_page_md` and `syllabus_md` written in the same voice as the other seeds.

**Key wording difference from 6.262:** `home_page_md` must call out that Ross is not freely available (unlike Gallager, which OCW mirrors chapter-by-chapter). User needs a print or PDF copy from Wiley.

## 4. Grading (30 / 20 / 20 / 30 — defensible default for two-midterm structure)

| Group | Weight | Assignments | `drop_lowest_n` |
|---|---|---|---|
| Problem Sets | 30 | 13 (HW1–HW13) | 0 |
| First Midterm | 20 | 1 (F13 paper, Ch 1–2) | 0 |
| Second Midterm | 20 | 1 (F13 paper, Ch 3–4) | 0 |
| Final Exam | 30 | 1 (F13 paper, cumulative Ch 1–5) | 0 |

`syllabus_md` flags this as approximate. Per [[feedback_seed_flexibility]] — adjust to match what's actually published, but don't fabricate detail we can't verify.

## 5. Assignments (16 total)

### 5.1 Problem Sets (13)

URLs follow `homewk{N}.pdf` and `homewk{N}Sols.pdf` (1-indexed, no zero pad). Topic + chapter mapping comes from `homework6711.html`. HW5 and HW11 are marked "not required to be turned in" by Whitt; we keep them as graded for self-study.

| HW | Lec from | Lec to | Topic | Paper | Solution |
|---|---|---|---|---|---|
| 1 | 1 | 2 | Probability, Ch 1 | `homewk1.pdf` | `homewk1Sols.pdf` |
| 2 | 3 | 4 | More probability, Ch 1 | `homewk2.pdf` | `homewk2Sols.pdf` |
| 3 | 5 | 6 | Poisson process, Ch 2 | `homewk3.pdf` | `homewk3Sols.pdf` |
| 4 | 7 | 8 | More Poisson process, Ch 2 | `homewk4.pdf` | `homewk4Sols.pdf` |
| 5 | 8 | 9 | Even more Poisson, Ch 2 (optional turn-in) | `homewk5.pdf` | `homewk5Sols.pdf` |
| 6 | 10 | 12 | Renewal theory, Ch 3 | `homewk6.pdf` | `homewk6Sols.pdf` |
| 7 | 12 | 14 | Even more renewal | `homewk7.pdf` | `homewk7Sols.pdf` |
| 8 | 14 | 16 | Still more renewal | `homewk8.pdf` | `homewk8Sols.pdf` |
| 9 | 15 | 18 | Markov chains, Ch 4 | `homewk9.pdf` | `homewk9Sols.pdf` |
| 10 | 17 | 19 | Markov chains, Ch 4 (continued) | `homewk10.pdf` | `homewk10Sols.pdf` |
| 11 | 19 | 19 | Markov chains, Ch 4 (optional turn-in) | `homewk11.pdf` | `homewk11Sols.pdf` |
| 12 | 20 | 20 | CTMC, Ch 5 | `homewk12.pdf` | `homewk12Sols.pdf` |
| 13 | 20 | 20 | More CTMC, Ch 5 | `homewk13.pdf` | `homewk13Sols.pdf` |

Lecture numbers refer to the 20-PDF `LECTURE_NOTES` list (§7). Each assignment: `points_possible=100`, `accepts_files=True`, `accepts_text=True`, `requires_solution_key=True`.

### 5.2 First Midterm (Ch 1–2)

- Title: `"First Midterm (Fall 2013 paper)"`
- Coverage: `covers_lecture_from=1, covers_lecture_to=9` (probability review + Poisson; sat Sun 2013-10-06)
- Paper: `midtermOne6711F13.pdf`
- Solution: `midtermOne6711F13sols.pdf`

### 5.3 Second Midterm (Ch 3–4)

- Title: `"Second Midterm (Fall 2013 paper)"`
- Coverage: `covers_lecture_from=10, covers_lecture_to=19` (renewal + DTMC; sat Sun 2013-11-17)
- Paper: `midtermTwo6711F13.pdf`
- Solution: `midtermTwo6711F13sols.pdf`

### 5.4 Final Exam (cumulative)

- Title: `"Final Exam (Fall 2013 paper)"`
- Coverage: `covers_lecture_from=1, covers_lecture_to=20` (cumulative Ch 1–5; sat Sun 2013-12-15)
- Paper: `final6711F13.pdf`
- Solution: `final6711F13sols.pdf`

## 6. Solution-PDF download & upload pipeline (reuse of 6.262 pattern)

Identical shape to `seed_6_262._attach_official_solution`, with two differences:

1. **Storage namespace:** `solutions/official/ieor_6711/` (not `6_262/`).
2. **URL construction:** Whitt's URLs are flat — `{BASE}/homewk{N}Sols.pdf` directly, no content-hash prefix to scrape. The seed builds the URL string and `httpx.get`s it directly.

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
        if not resp.content.startswith(b"%PDF"):
            raise RuntimeError("not a PDF")
        storage.upload_bytes("solutions", storage_key, resp.content, "application/pdf")
        a.official_solution_file_path = storage_key
        a.official_solution_url = ""
    except Exception as exc:
        a.official_solution_url = f"{BASE}/{filename}"
        print(f"warn(seed_ieor_6711): solution upload failed for {filename}: {exc}")
```

### Cloudflare risk and mitigation

Probe confirmed: Cloudflare gates HTML when fetched without a browser-style UA, but accepts requests with a real UA. The seed sends `Mozilla/5.0 (compatible; ocw-canvas-seed/1.0)` and inspects bytes (`%PDF` prefix) before treating a response as a PDF. If a future Cloudflare ruleset blocks everything, the URL-only fallback keeps the seed functional.

## 7. Modules (2)

1. **Direct links** — course home, lecture-notes index, homework index, Laplace-transform supplement (`homewkLTnotes.pdf`), Ross textbook publisher page.
2. **Lecture notes (Whitt)** — 20 items, one per primary lecture PDF, titled `"Lecture NN (YYYY-MM-DD) — <topic>"` with the Ross chapter named in the title or item-level reading hint. Filenames + dates verified from `lectures6711.html`:

| # | Date | Slug | Topic | Ross ref |
|---|---|---|---|---|
| 1 | 2013-09-03 | `lect0903` | LLN; random variables | Ch 1 |
| 2 | 2013-09-05 | `lect0905` | Modes of convergence; SLLN proof | Ch 1 |
| 3 | 2013-09-10 | `lectCLT` | Normal approximation; CLT | Ch 1 |
| 4 | 2013-09-12 | `lect0912` | Transforms | Ch 1 |
| 5 | 2013-09-17 | `lect0917` | Exponential distribution | Ch 2 §2.1 |
| 6 | 2013-09-19 | `lect091913` | Poisson as a special case | Ch 2 §2.2 |
| 7 | 2013-09-26 | `lect0926` | Infinite-server queue | Ch 2 §§2.3–2.4 |
| 8 | 2013-10-01 | `lect1001` | Compound Poisson | Ch 2 §2.5 |
| 9 | 2013-10-03 | `lect1003` | Simulating NHPPs | Ch 2 §2.4 |
| 10 | 2013-10-08 | `lect1008` | Renewal-reward theory | Ch 3 §3.6 |
| 11 | 2013-10-10 | `lect1010` | Renewal function; renewal equation | Ch 3 §§3.3–3.5 |
| 12 | 2013-10-15 | `lect1015` | Inspection paradox; excess/age | Ch 3 §3.5 |
| 13 | 2013-10-17 | `lect1017` | Patterns | Ch 3 |
| 14 | 2013-10-22 | `lect1022` | Blackwell's renewal theorem (coupling proof) | Ch 3 §3.5 |
| 15 | 2013-10-24 | `lect1024` | Markov chains — introduction | Ch 4 §§4.1–4.3 |
| 16 | 2013-10-29 | `lect1029` | Contraction approach | Ch 4 §4.4 |
| 17 | 2013-10-31 | `lect1031` | M/G/1 queue | Ch 4 §4.5 |
| 18 | 2013-11-07 | `lect1107` | Reversibility | Ch 4 §4.7 |
| 19 | 2013-11-12 | `lect1112` | Regenerative & semi-Markov processes | Ch 3 §3.7 + Ch 4 §4.8 |
| 20 | 2013-11-19 | `CTMCnotes120413` | CTMCs — comprehensive notes | Ch 5 |

**No "Practice exams" module** — F13 publishes the F13 papers themselves; no clean earlier-year archive on Whitt's page. Per [[feedback_seed_flexibility]] (don't fabricate exams).

**No per-unit modules.** Mirrors the 6.262 refactor (commit 2862cb9, PR #9) consolidating unit modules into Course-Notes only. Whitt's lecture PDFs are the natural Course-Notes analogue.

## 8. `update_urls()` semantics

Standard updater (mirrors `seed_6_262.update_urls`):
- Refreshes module-item `external_url` for all fixed-title items.
- Refreshes assignment `description_md`.
- Refreshes `covers_lecture_from/to`.
- Refreshes `official_solution_url` **only when `official_solution_file_path` is empty** — preserves the successful-seed clear from `_attach_official_solution` (see commit 2d1cf1c rationale).

Separate `--refresh-solutions` flag clears `official_solution_file_path` and re-runs `_attach_official_solution` for every assignment.

## 9. CLI

```bash
python -m seed.seed_ieor_6711
python -m seed.seed_ieor_6711 --force
python -m seed.seed_ieor_6711 --update-urls
python -m seed.seed_ieor_6711 --refresh-solutions
```

## 10. Tests

Follow the existing seed pattern: no dedicated unit tests (matches `seed_6_262.py`, which has none). Verification is manual seed against local sqlite + `uv run pytest -q` + `uv run ruff check .`.

## 11. Memory updates after this lands

- [[study-sequencing-2027-2030]]: advance `Columbia IEOR 6711` from `⏳ Next up` to `✅ seeded`; promote MIT 18.336 to next-up.

## 12. Non-goals

- Not seeding Fall 2012 papers as practice.
- Not adding a Ross-chapter overview module (the lecture-notes module already encodes chapter mapping).
- Not changing any backend model, migration, API, or frontend file.
- Not modifying existing seeds for consistency.

## 13. Risks

- **Cloudflare policy change.** If Whitt's host hardens its Cloudflare rules, server-side fetches could break. Mitigation: graceful URL-only fallback + `--refresh-solutions` for manual retry.
- **Whitt's host could disappear.** Personal faculty pages have shorter lifetimes than OCW. Supabase-uploaded PDFs survive that scenario; only the live links rot. `--update-urls` is the patch point.
- **Grading split is a guess.** 30/20/20/30 is documented as approximate in `syllabus_md`. Easy one-line edit if real split surfaces.
- **Optional turn-in homeworks.** HW5 and HW11 are listed as not-required by Whitt; we keep them as graded so the gradebook structure is uniform. The descriptions note their optional status — user can skip them and the gradebook stays consistent if `drop_lowest_n` is later raised.

## 14. Branch & merge plan

- Branch: `feat/seed-ieor-6711` off master.
- Single new file: `backend/seed/seed_ieor_6711.py`.
- Plus spec + plan files under `docs/superpowers/`.
- No existing files modified.
- `git status` clean before PR; `git diff master...HEAD` shows only the three new files.
- Merge via `--no-ff` PR (per CLAUDE.md branching convention).
