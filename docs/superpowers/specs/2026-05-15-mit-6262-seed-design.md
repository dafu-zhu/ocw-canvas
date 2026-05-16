# MIT 6.262 (Discrete Stochastic Processes) — Seed Course Design

**Date:** 2026-05-15
**Status:** Draft for review
**Scope:** Add the fifth seed course to `backend/seed/`. First seed to ship official solution PDFs alongside the course tree.
**Source:** <https://ocw.mit.edu/courses/6-262-discrete-stochastic-processes-spring-2011/>

---

## 1. Purpose

Seed `MIT 6.262 — Discrete Stochastic Processes` (Robert Gallager, MIT Spring 2011). Sits in the [[study-sequencing-2027-2030]] Q2 2028 slot — first course in the year-long stochastic-processes pair. Idempotent loader at `python -m seed.seed_6_262 [--force] [--update-urls]`, mirroring the existing seeds in shape.

This seed extends the pattern in one direction the others don't: **OCW publishes official solution PDFs**. We upload one solution PDF per *graded* assignment (14 PDFs: 12 PSets + 1 midterm + 1 final) into Supabase Storage and wire them into the AI grading pipeline via `assignment.official_solution_file_path` so the AI grades against Gallager's real solutions instead of regenerating its own. The remaining historical-exam PDFs (2009/2010 midterm, 2009 final) are linked from descriptions as practice papers but **not** uploaded — they're just browseable resources, not graded.

## 2. Source-page structure (verified)

Course base: `https://ocw.mit.edu/courses/6-262-discrete-stochastic-processes-spring-2011/`

Nav sections present:
- `/pages/syllabus/` — grading + textbook + homework policy
- `/pages/calendar/` — lecture topics + PSet due dates (no per-lecture readings)
- `/pages/course-notes/` — Gallager's textbook chapter-by-chapter PDFs (Ch 1–7 + front/back matter)
- `/pages/assignments/` — 12 PSets, all with published solutions
- `/pages/exams/` — 5 historical exams (3 midterms 2009/2010/2011, 2 finals 2009/2011), all with solutions
- `/video_galleries/video-lectures/` — 25 recorded lectures

Resource slugs follow `mit6_262s11_*` convention. PDF URLs are content-hash-prefixed (`<32-hex>_<NAME>.pdf`), so the seed must scrape each resource landing page to discover the actual PDF URL.

**Textbook URL:** Gallager's draft notes (the basis of his 2013 Cambridge book *Stochastic Processes: Theory for Applications*) are mirrored on OCW as `mit6_262s11_chap01` … `chap07`. The "updated and improved version" lives at <https://web.archive.org/web/20230107224918/https:/www.rle.mit.edu/rgallager/notes.htm>.

## 3. Course meta

| Field | Value |
|---|---|
| `code` | `"MIT 6.262"` |
| `title` | `"Discrete Stochastic Processes"` |
| `institution` | `"Massachusetts Institute of Technology"` |
| `instructor` | `"Prof. Robert Gallager"` |
| `external_home_url` | `https://ocw.mit.edu/courses/6-262-discrete-stochastic-processes-spring-2011/` |
| `term_label` | `"Summer 2028"` (user's self-study term — editable) |
| `status` | `"planned"` |
| `color` | `"#4A2C82"` (deep purple — distinct from cardinal/teal/navy/tartan-red) |
| `display_order` | `4` (after 18.100B=0, CMU 36-705=1, 18.700=2, 18.065=3) |
| `textbook` | `Gallager, Stochastic Processes: Theory for Applications (Cambridge 2013) — primary. The 2011 draft notes are mirrored on OCW chapter-by-chapter. Bertsekas-Tsitsiklis Introduction to Probability (Athena 2008) is the prereq probability text.` |

`home_page_md` and `syllabus_md` written in the same voice as the other seeds. Syllabus markdown reproduces grading + textbook + homework policy from the OCW syllabus verbatim.

## 4. Grading (Mirror OCW: 20 / 35 / 45)

Original 6.262 grading: Quiz 35% / Final 45% / Homework 20%. We mirror exactly, with the simplification that **one** midterm and **one** final are the graded assignments (Spring 2011 papers), while the 2009/2010 midterms and 2009 final are linked from the description as practice papers.

### Assignment groups

| Group | Weight | Assignments | `drop_lowest_n` |
|---|---|---|---|
| Problem Sets | 20 | 12 (PS1–PS12) | 0 |
| Midterm Quiz | 35 | 1 (Midterm Exam — 2011 paper) | 0 |
| Final Exam | 45 | 1 (Final Exam — 2011 paper) | 0 |

**Why one midterm + one final, not five separate assignments:** Original 6.262 had one quiz + one final. OCW publishing 3 historical midterms is convenience, not an instruction to take all three. Listing only one of each as a graded assignment keeps the gradebook honest while making the practice papers discoverable from the assignment description. (User can duplicate in teacher mode if they later want all three midterms scored separately.)

## 5. Assignments (14 total)

### 5.1 Problem Sets (12)

URLs follow `mit6_262s11_assn{NN}` (zero-padded). Solution URL is `_sol` suffix.

| PS | Lec from | Lec to | OCW PSet slug | OCW solution slug |
|---|---|---|---|---|
| 1 | 1 | 3 | `mit6_262s11_assn01` | `mit6_262s11_assn01_sol` |
| 2 | 4 | 5 | `mit6_262s11_assn02` | `mit6_262s11_assn02_sol` |
| 3 | 6 | 7 | `mit6_262s11_assn03` | `mit6_262s11_assn03_sol` |
| 4 | 8 | 9 | `mit6_262s11_assn04` | `mit6_262s11_assn04_sol` |
| 5 | 10 | 11 | `mit6_262s11_assn05` | `mit6_262s11_assn05_sol` |
| 6 | 12 | 13 | `mit6_262s11_assn06` | `mit6_262s11_assn06_sol` |
| 7 | 14 | 15 | `mit6_262s11_assn07` | `mit6_262s11_assn07_sol` |
| 8 | 16 | 18 | `mit6_262s11_assn08` | `mit6_262s11_assn08_sol` |
| 9 | 19 | 19 | `mit6_262s11_assn09` | `mit6_262s11_assn09_sol` |
| 10 | 20 | 21 | `mit6_262s11_assn10` | `mit6_262s11_assn10_sol` |
| 11 | 22 | 23 | `mit6_262s11_assn11` | `mit6_262s11_assn11_sol` |
| 12 | 24 | 25 | `mit6_262s11_assn12` | `mit6_262s11_assn12_sol` |

PSet due dates from calendar: after Lec 3 / 5 / 7 / 9 / 11 / 13 / 15 / 18 / 19 / 21 / 23. Calendar publishes 11 due dates; PS12 is inferred to land after Lec 25 to cover the tail (24–25).

Each assignment has `points_possible=100`, `accepts_files=True`, `accepts_text=True`, `requires_solution_key=True`.

### 5.2 Midterm Exam (1)

- Title: `"Midterm Exam (2011 paper)"`
- Coverage: `covers_lecture_from=1, covers_lecture_to=14` (due after the Lec 14 review)
- PDF: `mit6_262s11_mid11` (solution `mit6_262s11_mid11_sol`)
- Description body lists 2010 + 2009 midterm papers as practice (with links to both paper and solution PDFs).

### 5.3 Final Exam (1)

- Title: `"Final Exam (2011 paper)"`
- Coverage: `covers_lecture_from=15, covers_lecture_to=25`
- PDF: `mit6_262s11_final11` (solution `mit6_262s11_final11_sol`)
- Description body lists the 2009 final as practice (with links).

## 6. Solution-PDF download & upload pipeline (new pattern)

This is the part that's never been done before in this repo.

### 6.1 Storage layout

PDFs land in the `solutions` Supabase Storage bucket (same bucket the AI uses for transcripts and generated solutions). To avoid collision with AI-generated content, namespace under `official/`:

```
solutions/official/6_262/mit6_262s11_assn01_sol.pdf
solutions/official/6_262/mit6_262s11_assn02_sol.pdf
…
solutions/official/6_262/mit6_262s11_final11_sol.pdf
```

The `assignment.official_solution_file_path` stores the bucket-relative key (e.g. `"official/6_262/mit6_262s11_assn01_sol.pdf"`). `ai_jobs.grade_with_ai` then calls `storage.read_bytes("solutions", ref)` and feeds the bytes into the AI's working directory as `solution.pdf`. The CLI reads the PDF with its whitelisted `Read` tool.

### 6.2 OCW PDF resolution

Each OCW resource landing page (`/resources/{slug}/`) embeds the actual PDF URL with a content-hash prefix, e.g.:
```
/courses/6-262-…-spring-2011/c12643e48449ee92da0cba905e0ba5ca_MIT6_262S11_assn01_sol.pdf
```

The hash is per-file, stable, but **not** derivable from the slug — we must fetch the landing page HTML and parse it. The seed implements:

```python
def _resolve_pdf_url(slug: str) -> str:
    """Scrape /resources/{slug}/ for the actual hash-prefixed PDF URL."""
    page = httpx.get(f"{BASE}/resources/{slug}/", timeout=30).text
    # PDFs are referenced as href="/courses/.../<hash>_<NAME>.pdf"
    m = re.search(r'href="(/courses/[^"]+\.pdf)"', page)
    if m is None:
        raise RuntimeError(f"no PDF link found on /resources/{slug}/")
    return urljoin("https://ocw.mit.edu", m.group(1))
```

### 6.3 Per-assignment flow

In the assignment-creation loop, after creating each PSet / exam Assignment row:

```python
def _attach_official_solution(a: Assignment, slug: str) -> None:
    """Idempotent: skip if already populated AND readable."""
    storage_key = f"official/6_262/{slug}.pdf"
    if a.official_solution_file_path == storage_key:
        try:
            storage.read_bytes("solutions", storage_key)
            return  # already uploaded; skip network
        except Exception:
            pass  # fall through to re-fetch
    try:
        pdf_url = _resolve_pdf_url(slug)
        pdf_bytes = httpx.get(pdf_url, timeout=60).content
        storage.upload_bytes("solutions", storage_key, pdf_bytes, "application/pdf")
        a.official_solution_file_path = storage_key
    except Exception as exc:
        # Graceful degradation: log, keep official_solution_url set, continue
        print(f"warn: solution download failed for {slug}: {exc}")
    a.official_solution_url = f"{BASE}/resources/{slug}/"
```

Both `official_solution_file_path` and `official_solution_url` are set whenever possible. If the download fails, the URL alone provides the fallback (AI gets the "official solution at URL" note; user can still browse it via teacher mode).

### 6.4 `--update-urls` mode

For URL-only refresh (the existing pattern), `update_urls()` updates `official_solution_url` on each assignment but does **not** re-download PDFs. A separate explicit flag `--refresh-solutions` triggers re-download if OCW hashes ever drift.

## 7. Modules (9 total)

Order, titles, and content:

1. **Direct links** — home, syllabus, calendar, course-notes, assignments, exams, video gallery, Gallager textbook archive (web.archive.org link)
2. **Unit 1 — Probability review & Bernoulli** (Lec 1–3, Gallager Ch 1)
3. **Unit 2 — Poisson processes** (Lec 4–5, Gallager Ch 2)
4. **Unit 3 — Finite-state Markov chains** (Lec 6–9, Gallager Ch 3–4)
5. **Unit 4 — Renewal processes** (Lec 10–15, Gallager Ch 5)
6. **Unit 5 — Countable-state Markov chains & processes** (Lec 16–20, Gallager Ch 6–7)
7. **Unit 6 — Random walks & martingales** (Lec 21–25, Gallager Ch 7+ / back matter)
8. **Gallager course notes** — direct links to each chapter PDF (Ch 1–7 + front/back matter, all hosted on OCW)
9. **Practice exams** — links to all 5 historical papers + solutions (2009/2010/2011 midterms, 2009/2011 finals), so the user can browse them outside the gradebook flow

Per-lecture module items follow [[feedback_module_content_chapter_readings]]: each lecture is a `note` with `**Gallager Ch N (topic).** {one-line lecture topic}` as the text, immediately followed by a `link` child item titled `[Watch video →]` pointing to the video page.

## 8. `update_urls()` semantics

Standard updater (mirrors `seed_18_700.update_urls`):
- Refreshes module-item `external_url` for all fixed-title items (home, syllabus, calendar, video gallery, Gallager chapter notes, exam links)
- Refreshes per-lecture note text (Gallager chapter mapping)
- Refreshes assignment `description_md` (so PSet/exam descriptions stay in sync with OCW URL changes)
- Refreshes `covers_lecture_from/to`
- Refreshes `official_solution_url` (URL only — does **not** re-download PDFs)

Separate `--refresh-solutions` flag re-runs `_attach_official_solution` for every assignment unconditionally (used if OCW rotates the hash prefix on a PDF).

## 9. CLI

```bash
# Initial seed
python -m seed.seed_6_262

# Force-replace (drops course + cascade; storage PDFs stay — gc'd separately)
python -m seed.seed_6_262 --force

# Refresh URLs only (no DB structure changes, no PDF re-download)
python -m seed.seed_6_262 --update-urls

# Re-download all 14 solution PDFs (if OCW hash drift breaks them)
python -m seed.seed_6_262 --refresh-solutions
```

## 10. Tests

Match the existing seed-test pattern. Use `sqlite:///:memory:` and monkeypatch the storage + httpx layers:

- `app.services.storage._supabase_configured` → False (uses local tmp dir)
- `httpx.get` → fixture returning a stub HTML page + stub PDF bytes
- After `seed()`, assert: 1 course, 9 modules, expected item counts per module, 14 assignments split across the 3 groups with correct weights, and 14 `official_solution_file_path` values pointing at the right storage keys.
- A separate test exercises `_resolve_pdf_url` against a fixture HTML to confirm the regex.
- `update_urls()` test: change a URL constant in-memory, run updater, assert items are rewritten while submissions/grades are preserved.

## 11. Memory updates after this lands

- [[study-sequencing-2027-2030]]: move `MIT 6.262` from "⏳ Next up" to "✅ seeded", advance the next ⏳ to Columbia IEOR 6711.
- No new feedback memories expected unless something surprising surfaces during implementation.

## 12. Non-goals

- Not seeding the 2009/2010 midterm or 2009 final as separate gradable assignments (user can duplicate later if desired).
- Not adding a UI for browsing official-solution PDFs from the student view — they're available via teacher mode and the AI grader. Adding student-facing solution browsing is a separate UI feature, not part of this seed.
- Not adding lecture videos as standalone module items — they remain inline `[Watch video →]` links beneath each per-lecture note (per [[feedback_module_content_chapter_readings]]).
- Not back-filling `official_solution_file_path` on existing seeded courses (18.100B / 18.700 / 18.065 / CMU 36-705) — those courses don't have published OCW solutions, so the field stays empty there.

## 13. Risks

- **OCW PDF hash drift.** If MIT republishes a PDF, its content hash changes. Mitigation: graceful degradation in `_attach_official_solution` (keeps URL-only mode working) + `--refresh-solutions` flag for explicit re-fetch.
- **Supabase Storage availability at seed time.** If Storage is misconfigured (`SUPABASE_URL`/`SUPABASE_SERVICE_KEY` unset), the local fallback in `storage.py` kicks in and PDFs go to `backend/_local_storage/solutions/official/6_262/`. Fine for dev; the user must seed against the same backend used at runtime. Document this in the script's docstring.
- **Test fragility around HTML parsing.** The `_resolve_pdf_url` regex is OCW-specific. If OCW restructures their resource pages, every seed that uses this pattern breaks at once. Mitigation: keep the regex as narrow as possible (`href="(/courses/[^"]+\.pdf)"`), and have a unit test that locks the expected HTML shape.
