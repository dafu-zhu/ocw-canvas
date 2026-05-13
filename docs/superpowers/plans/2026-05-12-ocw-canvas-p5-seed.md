# OCW Canvas — Phase 5 (Seed Course + Polish) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or superpowers:executing-plans. Checkbox steps.

**Goal:** Ship the first/seed course end-to-end — **MIT 18.100B — Real Analysis (Spring 2025)** — as a faithful Canvas course you can study from: the course record, the syllabus, the modules grouping the 23 lectures + 2 reviews + exams (every lecture row links out to OCW), the 3 assignment groups (Problem Sets 50% drop-1 / Midterm 20% / Final 30%), the 10 problem-set assignments + Midterm + Final, and the Video Lectures convenience view (already a view over `kind=video` items). Plus a light Canvas-styling polish pass and a finished top-level README + run docs.

**Architecture:** Builds on P1–P4. New: `backend/seed/__init__.py`, `backend/seed/seed_template_course.py` (idempotent: skips if a course with code `MIT 18.100B` already exists; `--force` recreates it). It opens a session via `app.db.SessionLocal` and writes `Course` → `AssignmentGroup`s → `Module`s → `ModuleItem`s → `Assignment`s using the ORM (no raw SQL). Run with `cd backend && uv run python -m seed.seed_template_course` (kept under `backend/` so it shares the `app.*` import path and `uv` env — a small, deliberate deviation from the spec's repo-root `seed/`). Tested by a pytest that runs it against the test DB and asserts the shape. The styling polish touches `frontend/src/styles/canvas.css` only; the README work touches `README.md`, `backend/README.md`, `frontend/README.md`.

**Tech Stack:** unchanged. The OCW URLs use the stable section-index pages on `ocw.mit.edu/courses/18-100b-real-analysis-spring-2025/` (`pages/video-lectures/`, `pages/lecture-notes/`, `pages/assignments/`, `pages/syllabus/`, `pages/exams/`) plus the course home; per-resource deep links can be refined later — the important property (every item links *out* to MIT's real page, nothing re-hosted) holds.

**Conventions:** branch `feat/p5-seed` (from `master`). Commit per task. Tests mock nothing here (the seed is pure DB writes).

---

### Task 1: The seed script

**Files:** Create `backend/seed/__init__.py` (empty), `backend/seed/seed_template_course.py`; test `backend/tests/test_seed.py`.

**`seed_template_course.py` shape:**

```python
"""Seed the MIT 18.100B — Real Analysis (Spring 2025) course.

Run:  cd backend && uv run python -m seed.seed_template_course [--force]
Source: https://ocw.mit.edu/courses/18-100b-real-analysis-spring-2025/
Idempotent: if a course with code "MIT 18.100B" exists, does nothing unless --force
(which deletes it first — cascades modules / groups / assignments).
"""
import argparse

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Assignment, AssignmentGroup, Course, Module, ModuleItem

CODE = "MIT 18.100B"
OCW = "https://ocw.mit.edu/courses/18-100b-real-analysis-spring-2025"
VIDEOS = f"{OCW}/pages/video-lectures/"
NOTES = f"{OCW}/pages/lecture-notes/"
ASSIGNMENTS_PAGE = f"{OCW}/pages/assignments/"
EXAMS_PAGE = f"{OCW}/pages/exams/"

# (lecture_number, title) for the 23 lectures + named review/exam sessions.
LECTURES = [
    (1, "The real numbers"),
    (2, "How to write a proof"),
    (3, "Archimedean property; supremum & infimum"),
    (4, "Sequences and convergence"),
    (5, "Monotone sequences; the monotone convergence theorem"),
    (6, "Cauchy sequences; completeness of R"),
    (7, "Bolzano–Weierstrass; subsequences"),
    (8, "Series; convergence tests"),
    (9, "Power series; limsup and liminf"),
    (10, "Continuous functions"),
    (11, "The exponential function; properties of continuity"),
    (12, "Extreme value theorem; intermediate value theorem"),
    (13, "Metric spaces; open and closed sets"),
    (14, "Compactness; sequential compactness"),
    (15, "Derivatives; differentiation rules"),
    (16, "Rolle's theorem; the mean value theorem; L'Hôpital"),
    (17, "Taylor's theorem; introduction to the Riemann integral"),
    (18, "Riemann integrable functions"),
    (19, "The fundamental theorem of calculus"),
    (20, "Pointwise and uniform convergence of sequences of functions"),
    (21, "Interchanging limits with integrals and derivatives"),
    (22, "Differentiating and integrating power series"),
    (23, "Picard–Lindelöf: existence & uniqueness for ODEs"),
]

# Modules: (title, [items]) where each item is a dict {kind, title, url?/text_md?, indent?}
UNITS = [
    ("Direct links", [
        {"kind": "link", "title": "18.100B course home (MIT OpenCourseWare)", "url": OCW + "/"},
        {"kind": "link", "title": "Syllabus", "url": OCW + "/pages/syllabus/"},
        {"kind": "link", "title": "Lecture notes (all)", "url": NOTES},
        {"kind": "link", "title": "Video lectures (all)", "url": VIDEOS},
        {"kind": "link", "title": "Problem sets (all)", "url": ASSIGNMENTS_PAGE},
        {"kind": "link", "title": "Exams", "url": EXAMS_PAGE},
    ]),
    ("Unit 1 — The Real Numbers (Lectures 1–3)", _unit_items(1, 3, "Readings: §1.1–1.7 (Thomson/Bruckner/Bruckner).")),
    ("Unit 2 — Sequences & Series (Lectures 4–9)", _unit_items(4, 9, "Readings: ch. 2–3, §10.2.")),
    ("Unit 3 — Continuity & Metric Spaces (Lectures 10–14)", _unit_items(10, 14, "Readings: §5.x, ch. 13.")),
    ("Midterm Exam", [
        {"kind": "video", "title": "Midterm review session (video)", "url": VIDEOS},
        {"kind": "assignment", "title": "Midterm Exam", "_assignment": "Midterm Exam"},
        {"kind": "link", "title": "Exam materials (MIT OCW)", "url": EXAMS_PAGE},
    ]),
    ("Unit 4 — Differentiation (Lectures 15–17)", _unit_items(15, 17, "Readings: §7.x.")),
    ("Unit 5 — Riemann Integration (Lectures 17–19)", _unit_items(17, 19, "Readings: §8.3, §8.6.")),
    ("Unit 6 — Sequences of Functions & ODEs (Lectures 20–23)", _unit_items(20, 23, "Readings: §9.x, §13.11.4.")),
    ("Final Exam", [
        {"kind": "video", "title": "Final review session (video)", "url": VIDEOS},
        {"kind": "assignment", "title": "Final Exam", "_assignment": "Final Exam"},
        {"kind": "link", "title": "Exam materials (MIT OCW)", "url": EXAMS_PAGE},
    ]),
]

# 10 problem sets — title topic per the unit progression.
PROBLEM_SETS = [
    (1, "The real numbers & writing proofs"),
    (2, "Sequences & convergence"),
    (3, "Cauchy sequences; Bolzano–Weierstrass"),
    (4, "Series & convergence tests"),
    (5, "Power series; limsup/liminf"),
    (6, "Continuity; EVT/IVT"),
    (7, "Metric spaces; compactness"),
    (8, "Differentiation; the mean value theorem"),
    (9, "Riemann integration & the FTC"),
    (10, "Sequences of functions; uniform convergence; ODEs"),
]

SYLLABUS_MD = """## Prerequisites
18.02 Multivariable Calculus.

## Textbooks
- Thomson, Bruckner & Bruckner, *Elementary Real Analysis*, 2nd ed. (2008) — free PDF (primary).
- Rudin, *Principles of Mathematical Analysis*, 3rd ed. — secondary.

## Grading
| Component | Weight |
|---|---|
| Problem Sets (≈10, weekly; lowest dropped) | 50% |
| Midterm Exam | 20% |
| Final Exam | 30% |

## Problem-set policy
About ten weekly problem sets. Individual submission; collaboration on ideas is encouraged but
write up your own solutions. The lowest score is dropped.

## Exam rules
One page of handwritten notes allowed; no computer or textbook.
"""

HOME_MD = """**18.100B — Real Analysis (Spring 2025), MIT OpenCourseWare.**

Two goals: (1) learn to write rigorous proofs; (2) put single-variable calculus on a rigorous
footing — sequences, series, continuity, differentiation, the Riemann integral, sequences of
functions, and a first existence/uniqueness theorem for ODEs.

Prerequisite: 18.02. Jump to **Syllabus**, **Modules**, or **Video Lectures**.
"""


def _unit_items(lo, hi, reading_note):
    items = []
    for n, title in LECTURES:
        if lo <= n <= hi:
            items.append({"kind": "video", "title": f"Lecture {n}: {title} (video)", "url": VIDEOS})
            items.append({"kind": "link", "title": f"Lecture {n} notes", "url": NOTES, "indent": 1})
    items.append({"kind": "note", "title": "Readings", "text_md": reading_note})
    return items


def _delete_existing(db: Session) -> None:
    existing = db.query(Course).filter(Course.code == CODE).all()
    for c in existing:
        db.delete(c)
    db.commit()


def seed(db: Session, force: bool = False) -> Course:
    if db.query(Course).filter(Course.code == CODE).first() is not None:
        if not force:
            return db.query(Course).filter(Course.code == CODE).first()
        _delete_existing(db)

    course = Course(
        code=CODE, title="Real Analysis", institution="MIT OpenCourseWare",
        term_label="Spring 2025", instructor="Prof. Tobias Holck Colding",
        external_home_url=OCW + "/", status="planned", color="#A31F34", display_order=0,
        textbook=("Thomson, Bruckner & Bruckner, Elementary Real Analysis, 2nd ed. (2008) — "
                  "free PDF; Rudin, Principles of Mathematical Analysis, 3rd ed. — secondary."),
        home_page_md=HOME_MD, syllabus_md=SYLLABUS_MD,
        description="Rigorous single-variable analysis: proofs, sequences/series, continuity, "
                    "differentiation, Riemann integration, sequences of functions, ODE existence.",
    )
    db.add(course); db.flush()

    g_ps = AssignmentGroup(course_id=course.id, name="Problem Sets", weight=50, drop_lowest_n=1, position=0)
    g_mid = AssignmentGroup(course_id=course.id, name="Midterm", weight=20, drop_lowest_n=0, position=1)
    g_fin = AssignmentGroup(course_id=course.id, name="Final Exam", weight=30, drop_lowest_n=0, position=2)
    db.add_all([g_ps, g_mid, g_fin]); db.flush()

    # Assignments: 10 PS + Midterm + Final. No solution key attached (OCW doesn't publish PS
    # solutions) -> the AI generates the reference solution on demand. due_at left null.
    by_name: dict[str, Assignment] = {}
    for k, topic in PROBLEM_SETS:
        a = Assignment(
            course_id=course.id, assignment_group_id=g_ps.id, title=f"Problem Set {k} — {topic}",
            description_md=(f"Problem Set {k}. Find this set's PDF on the MIT OCW assignments page: "
                           f"[{ASSIGNMENTS_PAGE}]({ASSIGNMENTS_PAGE}). Upload your worked solutions; "
                           "the AI generates a reference solution and grades against it."),
            points_possible=100, accepts_files=True, accepts_text=True, position=k - 1, published=True,
        )
        db.add(a); by_name[a.title] = a
    mid = Assignment(
        course_id=course.id, assignment_group_id=g_mid.id, title="Midterm Exam",
        description_md=(f"Midterm exam. Materials on the MIT OCW exams page: [{EXAMS_PAGE}]({EXAMS_PAGE})."),
        points_possible=100, accepts_files=True, accepts_text=True, position=0, published=True,
    )
    fin = Assignment(
        course_id=course.id, assignment_group_id=g_fin.id, title="Final Exam",
        description_md=(f"Final exam. Materials on the MIT OCW exams page: [{EXAMS_PAGE}]({EXAMS_PAGE})."),
        points_possible=100, accepts_files=True, accepts_text=True, position=0, published=True,
    )
    db.add_all([mid, fin]); by_name["Midterm Exam"] = mid; by_name["Final Exam"] = fin
    db.flush()

    # Modules + items.
    for mpos, (mtitle, items) in enumerate(UNITS):
        m = Module(course_id=course.id, title=mtitle, position=mpos, published=True)
        db.add(m); db.flush()
        for ipos, it in enumerate(items):
            kind = it["kind"]
            kwargs = dict(
                module_id=m.id, position=ipos, indent=it.get("indent", 0), kind=kind,
                title=it["title"], external_url=it.get("url", ""), text_md=it.get("text_md", ""),
                published=True, assignment_id=None,
            )
            if kind == "assignment":
                kwargs["assignment_id"] = by_name[it["_assignment"]].id
                kwargs["title"] = by_name[it["_assignment"]].title
            db.add(ModuleItem(**kwargs))
    db.commit()
    db.refresh(course)
    return course


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--force", action="store_true", help="delete an existing MIT 18.100B course first")
    args = p.parse_args()
    db = SessionLocal()
    try:
        c = seed(db, force=args.force)
        n_modules = len(c.modules)
        n_items = sum(len(m.items) for m in c.modules)
        n_assign = len(c.assignments)
        print(f"Seeded {c.code} — {c.title}: {n_modules} modules, {n_items} items, {n_assign} assignments.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
```

> Order matters in the module list: `_unit_items` is called *inside* the `UNITS` literal, so define `_unit_items`, `LECTURES`, etc. **before** `UNITS`. (Re-order the module: constants → `_unit_items` → `UNITS`. The snippet above is illustrative; in the real file put helpers first.)

- [ ] **Step 1:** Write `backend/seed/__init__.py` (empty) and `backend/seed/seed_template_course.py` (helpers/constants first, then `UNITS`, then `seed`/`main`).
- [ ] **Step 2:** `backend/tests/test_seed.py`:
  - `from seed.seed_template_course import seed, CODE` — call `seed(db)` → returns a Course with `code == "MIT 18.100B"`, `status == "planned"`, weighted groups summing to 100, exactly 12 assignments (10 PS + Midterm + Final), ≥ 8 modules, and at least one `module_item` of `kind == "assignment"` whose `assignment_id` resolves.
  - calling `seed(db)` again (no force) → returns the *same* course id, still 12 assignments (idempotent, no duplication).
  - `seed(db, force=True)` → still exactly one `MIT 18.100B` course, 12 assignments.
  - the gradebook endpoint on the seeded course returns `total_percentage is None` (nothing graded yet) and lists the 12 assignment rows — *(skip this sub-check if it needs the API client; the model-level checks above are enough).*
- [ ] **Step 3:** `cd backend && uv run pytest -q && uv run ruff check .` → pass.
- [ ] **Step 4:** Manual: `uv run alembic upgrade head` (if needed) then `uv run python -m seed.seed_template_course` prints the summary; run it twice to confirm idempotency. *(Optional — the test covers it.)*
- [ ] **Step 5:** Commit `feat: seed script — MIT 18.100B Real Analysis (Spring 2025)`.

---

### Task 2: Canvas-styling polish pass

**Files:** `frontend/src/styles/canvas.css` (only).

A light pass — the screenshots in `docs/superpowers/specs/assets/` are the reference. Concretely:
- ensure tables (`table.data`), the gradebook subtotal/total rows, and the rubric tables read cleanly (zebra striping or hairline rows; right-align numeric columns where it helps);
- the `.badge-pill.missing` / `.late` pills, the unread dot, and the `rail-badge` look like Canvas's;
- the course-nav rail active item has the left accent bar; the breadcrumb links are Canvas-blue;
- `@media print` (for the Grades "Print Grades" button): hide the left rail / course-nav / sidebars, expand the main column. Add a `@media print { .left-rail, .course-nav, .col-side, .breadcrumb { display: none } .main, .col-main { width: 100% } }` block.
- a small responsive tweak: on narrow screens the `.page-with-sidebar` stacks (already?) — verify and fix if needed.

Keep it CSS-only; no component changes. Don't chase pixel-perfection — just close the obvious gaps.

- [ ] **Step 1:** Edit `canvas.css` per the above (especially the `@media print` block — that's the one with functional impact).
- [ ] **Step 2:** `cd frontend && npm run build` → pass (CSS-only, can't really break TS, but build catches gross errors).
- [ ] **Step 3:** Commit `style(frontend): Canvas polish pass + print styles for the Grades page`.

---

### Task 3: Finish the docs

**Files:** `README.md` (root), `backend/README.md`, `frontend/README.md`.

- Root `README.md`: a "Quick start" section that walks the full one-time setup end-to-end (clone → backend `uv sync` → `.env` → `alembic upgrade head` → `python -m app.manage create-owner` → `python -m seed.seed_template_course` → `uvicorn`; frontend `npm i` → `.env` → `npm run dev`); a short "How the homework loop works" paragraph (author → key (official or AI-generated) → submit → AI grades → announcement + email); a "Deployment" pointer to `backend/render.yaml` and the GitHub Pages action; and the `**Status:**` line bumped to "P1–P5 complete — the seed course (MIT 18.100B) is loaded".
- `backend/README.md`: add the seed command to the "Run locally" block; everything else (AI / email / cron / docker) is already there from P3–P4.
- `frontend/README.md`: confirm it documents `VITE_API_BASE_URL` and `npm run dev/build/typecheck/lint` (add anything missing).

- [ ] **Step 1:** Update the three READMEs.
- [ ] **Step 2:** Commit `docs: quick-start, homework-loop overview, seed command`.

---

### Task 4: Full check + merge

- [ ] **Step 1:** `cd backend && uv run pytest -q && uv run ruff check .`; `cd frontend && npm run typecheck && npm run lint && npm run build` → all green.
- [ ] **Step 2:** `git checkout master && git merge --no-ff feat/p5-seed -m "feat: P5 — seed course (MIT 18.100B) + polish"`.
- [ ] **Step 3:** Bump root README `**Status:**` to "P1–P5 complete"; commit on `master`.
- [ ] **Step 4:** `git log --oneline -10` + `git status`. (Push only if asked.)

---

## Self-Review notes
- **Spec coverage (P5 slice):** the 18.100B course record + `external_home_url` + `textbook` + `home_page_md` (§9) → Task 1; the syllabus markdown with the 50/20/30 split + policies (§9) → Task 1 (`SYLLABUS_MD`); modules grouping 23 lectures + 2 reviews + exams, every lecture row a `kind=video` linking OCW, plus `link` rows for notes/readings (§9) → Task 1 (`UNITS`/`_unit_items`); the 3 assignment groups Problem Sets 50% drop-1 / Midterm 20% / Final 30% (§9) → Task 1; the 10 problem-set assignments + Midterm + Final, no key attached so the AI generates the reference solution (§9) → Task 1; Video Lectures page is already a view over `kind=video` items (§4 #10) — no new code; styling polish pass (§7 P5) → Task 2; `manage.py create-owner` + seed command in the README one-time-setup (§6) → Task 3. Deviations: `seed/` lives under `backend/` (shares the `app.*` import path / `uv` env) rather than at repo root — noted; per-lecture OCW deep links use the stable section-index pages rather than fabricated per-resource slugs (the "links out, nothing re-hosted" property holds) — noted; exam PDFs are referenced via the OCW exams page rather than re-hosted.
- **Idempotency:** `seed(db)` is a no-op when `MIT 18.100B` already exists; `--force` deletes-then-recreates; the cascade on `Course` (modules / assignment_groups / assignments / announcements) keeps it clean.
- **No new model/migration:** P5 is pure data + CSS + docs; the schema is frozen at migration 0004.
