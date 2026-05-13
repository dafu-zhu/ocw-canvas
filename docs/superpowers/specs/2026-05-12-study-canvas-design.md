# Study Canvas — Design Spec

**Date:** 2026-05-12
**Status:** Draft for review
**Repo:** `study-canvas` (new, public, GitHub)
**Related prior art:** `education-log` (single-user React+Supabase dashboard; this project reuses its patterns and adds a real backend)

---

## 1. Purpose & Scope

A personal, **Canvas-like LMS for self-studying open courseware** (MIT OCW, CMU/Stanford/Princeton course pages, etc.). It does three things:

1. **Tracks course materials** the way Canvas does — each course has **Modules**, and every module item is a *link out* to the university's real page (lecture notes PDF, problem-set PDF, video playlist). The site never re-hosts course PDFs; it stores the link and redirects.
2. **Runs a homework loop.** An assignment has a deadline. If it has no published official solution, the AI writes a complete reference solution (the answer key). You upload your work. The AI grades it against the key, assigns a score, writes feedback. The system creates an in-app **Announcement** and **emails** you the result.
3. **Feels exactly like Canvas.** Global left rail (Dashboard, Courses, Calendar, Inbox/Announcements, Account), course-card grid, and a per-course left nav: **Home · Syllabus · Modules · Assignments · Grades · Video Lectures · Announcements.**

**Single user** (the owner). There is one real account. The UI presents a student view (you) while the AI plays the roles of instructor / grader / announcer. A lightweight "teacher mode" toggle reveals the editing affordances (add/edit course, module, item, assignment) — you author the course, you study it, the AI grades it.

**The first/seed course** built end-to-end: **MIT 18.100B — Real Analysis (Spring 2025)**. See §9.

### Out of scope (v1)

Real multi-user accounts & RBAC; discussion boards; quizzes / auto-graded multiple choice; SpeedGrader-style inline PDF annotation; mobile native app; calendar feed (.ics) sync; re-hosting course PDFs; peer review; group assignments; rich-text WYSIWYG (markdown is fine); analytics dashboards. Revisit only if a real itch appears.

---

## 2. Architecture

```
Browser ── React SPA (Vite + TypeScript, Canvas-styled)
   │   fetch() + JWT in httpOnly cookie
   ▼
FastAPI  (Python 3.12, on Render Web Service — free tier)
   ├── REST API     courses · modules · module_items · assignments · submissions ·
   │                grades · announcements · auth · teacher-mode mutations
   ├── AI service   ──►  Anthropic API (Claude)   solution-key generation + grading
   ├── Email service──►  Resend                   graded / deadline-reminder / password-reset emails
   ├── Storage svc  ──►  Supabase Storage          submission uploads, AI-solution PDFs (private bucket, signed URLs)
   └── /cron/tick   ◄──  Render Cron Job (hourly, X-Cron-Secret header)
                         deadline-approaching scan · retry stuck AI jobs · idempotent

   Postgres ──►  Supabase (free tier, persistent)   all relational data, via SQLAlchemy + Alembic

Frontend hosting: GitHub Pages (gh-pages branch, built by a GitHub Action) — same model as education-log
```

**Why this shape**
- The AI/email API keys and the grading logic *cannot* live in a static frontend → there must be a server → FastAPI (matches the user's Python tooling: uv, ruff, pytest).
- Supabase gives free **persistent** Postgres + Storage with zero DB ops (Render's free Postgres is deleted after 30 days; Supabase's is not).
- Render gives a free always-reachable Python host and a free Cron Job for the deadline ticks.
- Frontend stays static → free on GitHub Pages, same deploy story as education-log.

**Resolved forks (from brainstorming)**
- **Auth:** FastAPI-native, single account. No Supabase Auth SDK in the frontend. Email + bcrypt-hashed password (hash in an env var, or in the single `app_user` row), JWT in an httpOnly+SameSite cookie, ~30-day expiry. Password reset = emailed signed token (Resend) → set-new-password page. Rationale: keeps *all* server logic in one place; one fewer SDK in the browser.
- **Deadline checks:** Render Cron Job hitting `POST /cron/tick` hourly (not an in-process APScheduler). Rationale: survives backend restarts/sleeps, no scheduler state to reason about, trivially testable as a plain endpoint.

---

## 3. Data Model

Postgres via SQLAlchemy ORM; migrations via Alembic. All `id` are UUID PKs; all tables carry `created_at` / `updated_at` (timestamptz). Since there is one user, there is **no per-row `user_id` / RLS** — the security boundary is the FastAPI auth layer, and Supabase is reached only with the service key from the backend (never from the browser).

### `app_user` — exactly one row
| field | type | notes |
|---|---|---|
| id | uuid PK | |
| email | text | the owner's email; recipient of all announcement emails |
| password_hash | text | bcrypt |
| display_name | text | shown in the UI ("Dafu Zhu") |
| reset_token | text | nullable; signed token for password reset |
| reset_expires | timestamptz | nullable |

### `course`
| field | type | notes |
|---|---|---|
| id | uuid PK | |
| code | text | e.g. `MIT 18.100B` |
| title | text | `Real Analysis` |
| institution | text | `MIT OpenCourseWare` |
| term_label | text | `Spring 2025` |
| instructor | text | `Prof. Tobias Holck Colding` |
| external_home_url | text | the OCW (or other) course landing page |
| textbook | text | free text, e.g. `Thomson/Bruckner/Bruckner, Elementary Real Analysis 2e (free PDF); Rudin, PMA 3e (secondary)` |
| home_page_md | text | the course "front page" markdown (intro + jump links) |
| description | text | short blurb for the course card |
| color | text | hex; the Canvas course-card accent |
| status | enum `active` `completed` `planned` | drives card placement / styling |
| display_order | int | manual sort on the dashboard |

### `module` — Canvas "module"
| field | type | notes |
|---|---|---|
| id | uuid PK | |
| course_id | uuid FK → course | cascade delete |
| title | text | e.g. `Unit 1 — The Real Numbers (Lectures 1–3)` |
| position | int | order within the course |
| published | bool | default true |

### `module_item` — one row per material; **points elsewhere**
| field | type | notes |
|---|---|---|
| id | uuid PK | |
| module_id | uuid FK → module | cascade delete |
| position | int | order within the module |
| indent | int | 0–2; Canvas-style nesting |
| kind | enum `link` `video` `assignment` `note` `header` | |
| title | text | display label |
| external_url | text | for `link` / `video` — the university's page (opens new tab) |
| assignment_id | uuid FK → assignment | for `kind=assignment` |
| text_md | text | for `note` / `header` |
| published | bool | default true |

### `assignment`
| field | type | notes |
|---|---|---|
| id | uuid PK | |
| course_id | uuid FK → course | cascade delete |
| title | text | e.g. `Problem Set 3 — Series` |
| description_md | text | markdown; embeds the link to the source problem-set PDF + any instructions |
| points_possible | numeric | e.g. `100` |
| due_at | timestamptz | nullable |
| available_at | timestamptz | nullable; if set, assignment hidden/locked before this |
| accepts_files | bool | default true |
| accepts_text | bool | default true (text / LaTeX entry box) |
| official_solution_url | text | nullable; if present, this is the answer key and no AI solution is generated |
| late_policy | enum `none` `flag_only` `percent_per_day` | default `flag_only` |
| late_value | numeric | nullable; % per day when `percent_per_day` |
| group_name | text | nullable; Canvas "assignment group" header (`Problem Sets`, `Exams`) |
| weight | numeric | nullable; group weight toward course grade (see §3 rollup) |
| position | int | |
| published | bool | default true |

### `ai_solution`
| field | type | notes |
|---|---|---|
| id | uuid PK | |
| assignment_id | uuid FK → assignment | unique; 1:1 |
| status | enum `pending` `generating` `ready` `failed` | |
| content_md | text | the full worked solution |
| pdf_path | text | nullable; Storage path of a rendered PDF copy |
| model | text | model id used |
| prompt_log_path | text | nullable; Storage path of the prompt+response transcript |
| generated_at | timestamptz | nullable |
| error | text | nullable |

### `submission`
| field | type | notes |
|---|---|---|
| id | uuid PK | |
| assignment_id | uuid FK → assignment | cascade delete |
| attempt_number | int | 1-based; resubmission allowed |
| submitted_at | timestamptz | |
| is_late | bool | computed from `due_at` at submit time |
| text_body | text | nullable; the typed/LaTeX entry |
| file_paths | jsonb | array of Storage paths (PDFs / images) |
| source | enum `me` `ai_demo` | always `me` in v1; `ai_demo` reserved for a future "let AI do this one" |
| status | enum `submitted` `grading` `graded` `grading_failed` | |

### `grade` — 1:1 with a `submission` (one grade row per graded attempt; "current grade" = the highest-attempt one)
| field | type | notes |
|---|---|---|
| id | uuid PK | |
| submission_id | uuid FK → submission | unique |
| score | numeric | points awarded *before* late penalty |
| score_out_of | numeric | copy of `points_possible` at grade time |
| late_penalty_applied | numeric | points deducted (0 if none) |
| final_score | numeric | `max(0, score - late_penalty_applied)` |
| percentage | numeric | `final_score / score_out_of * 100` |
| feedback_md | text | the AI's written comments |
| rubric_breakdown | jsonb | list of `{criterion, points_awarded, points_possible, note}` |
| graded_by | enum `ai` | (reserved for future `manual`) |
| model | text | |
| prompt_log_path | text | nullable; transcript path |
| graded_at | timestamptz | |

### `announcement`
| field | type | notes |
|---|---|---|
| id | uuid PK | |
| course_id | uuid FK → course | nullable = global announcement |
| kind | enum `graded` `deadline` `manual` `system` | |
| title | text | |
| body_md | text | |
| related_assignment_id | uuid FK → assignment | nullable |
| created_at | timestamptz | |
| read_at | timestamptz | nullable; powers the unread badge |
| emailed_at | timestamptz | nullable; set once the email is sent |

### `email_log`
| field | type | notes |
|---|---|---|
| id | uuid PK | |
| to | text | |
| subject | text | |
| template | text | `graded` / `deadline` / `password_reset` |
| payload | jsonb | rendered template variables |
| resend_id | text | nullable; id returned by Resend |
| status | enum `sent` `failed` | |
| sent_at | timestamptz | |

### `cron_marker` — idempotency for the hourly tick
| field | type | notes |
|---|---|---|
| key | text PK | e.g. `deadline-48h:<assignment_id>` |
| created_at | timestamptz | presence ⇒ "already handled, don't repeat" |

### Computed (not stored)

- **Assignment current grade** = the `grade` row of the highest `attempt_number` `graded` submission.
- **Course grade (Grades page)** = if any assignments carry a `weight`, weighted sum of group percentages; otherwise simple `Σ final_score / Σ score_out_of` over graded assignments. Ungraded/missing assignments are shown but excluded from the running total (Canvas's "show what-if" behavior is out of scope). For 18.100B the groups are Problem Sets 50% / Midterm 20% / Final 30%.
- **Dashboard "To Do"** = published assignments with `due_at` in the future and no submission, soonest first; plus unread announcements.

### Storage (Supabase)

- Private bucket `submissions`. Paths: `submissions/<assignment_id>/<submission_id>/<filename>`.
- Private bucket `solutions`. Paths: `solutions/<assignment_id>.pdf` and `logs/<...>.txt` for prompt transcripts.
- Frontend never touches Storage directly; the backend issues short-lived signed URLs for download links.

---

## 4. Pages (Canvas look & feel)

**Global chrome:** dark slate left rail with stacked icon buttons — Dashboard, Courses, Calendar, Inbox (Announcements), Account — plus a top breadcrumb bar. White content area, generous spacing, Canvas-ish typography (system sans, ~14px base), course-color accents on banners and cards. Unread-announcement count badges the Inbox icon.

| # | Route | Page | Notes |
|---|---|---|---|
| 1 | `/login` | **Login** | email + password card; "Forgot password?" → email reset link (Resend) → `/reset?token=…` set-new-password page. No public signup. |
| 2 | `/` | **Dashboard** | Course-card grid (color header bar + `CODE` + title + "next due" pill). Right sidebar: "To Do" (upcoming due dates across courses) + "Recent" (latest announcements). Mirrors Canvas's card dashboard. |
| 3 | `/calendar` | **Calendar** | Month grid; assignment due dates rendered as course-colored chips. Month view only in v1. |
| 4 | `/announcements` | **Announcements / Inbox** | Reverse-chron list of all announcements; click → read view (marks `read_at`); per-course filter. This is the in-app mirror of the emails. |
| 5 | `/courses/:id` | **Course Home** | Course-color banner (code, title, term, instructor), rendered `home_page_md` front page, a "Recent activity" feed. Left **course nav rail**: Home · Syllabus · Modules · Assignments · Grades · Video Lectures · Announcements. |
| 6 | `/courses/:id/syllabus` | **Syllabus** | Rendered syllabus markdown (held in `home_page_md` or a dedicated field) **plus** an auto-built "Course Summary" table listing every assignment with its due date — exactly what Canvas's syllabus page does. |
| 7 | `/courses/:id/modules` | **Modules** | Collapsible module sections. Each `module_item` is a row with a kind icon: `link`/`video` → opens `external_url` in a new tab; `assignment` → in-app assignment page; `note`/`header` → inline markdown. **This is the home of all course materials, and they all point outward.** |
| 8a | `/courses/:id/assignments` | **Assignments list** | Grouped by `group_name` (Canvas "assignment groups"), each row: title, due date, points, submission status badge (Not submitted / Submitted / Graded N/M / Late). |
| 8b | `/courses/:id/assignments/:aid` | **Assignment detail** | Rendered `description_md` (with the source-PDF link), due date, points, late policy. **Submit panel:** drag-drop file zone (PDF/images) + optional text/LaTeX box → creates a `submission`. Submission history list. After grading: score + late penalty + rubric breakdown table + AI `feedback_md`, and a "View reference solution" toggle showing the official link if present, else the rendered `ai_solution.content_md`. If the AI solution is still `generating` / `failed`, show status + a "Retry" button (teacher mode). |
| 9 | `/courses/:id/grades` | **Grades** | Gradebook table: assignment · group · due · status · score · out of · % ; running course total (weighted per §3) pinned at the top. |
| 10 | `/courses/:id/videos` | **Video Lectures** | List/grid of lecture entries (number, title, optional thumbnail) each linking to the external video. Backed by `module_item kind=video` across the course (or a `video` filter). |

**Teacher mode:** a toggle in the Account menu. When on, `+`/edit/delete affordances appear on courses, modules, module items, and assignments; clicking opens a modal (same plain-form style as education-log — required fields marked `*`, no multi-step wizards). Off by default so day-to-day use is pure "student".

**Empty states:** no courses → "Add your first course"; course with no modules → "No modules yet"; assignment with no submissions → "You haven't submitted yet."

**Responsive:** content area collapses to single column on narrow screens; the course nav rail becomes a top dropdown. Not a priority — desktop is the primary target.

---

## 5. The Homework Loop (the heart of it)

1. **Author the assignment** (teacher mode): title, `description_md` with the link to the real problem-set PDF, `points_possible`, `due_at`, submission types, `late_policy`, and `official_solution_url` if the course publishes one. Adds a `module_item kind=assignment` under the right module.
2. **AI solution key.** On create (and via a "Generate solution" button): if `official_solution_url` is empty → create `ai_solution(status=generating)`, call Claude with the assignment description (+ any pasted text) and a "produce a complete, rigorous, well-explained worked solution" system prompt → store `content_md`, optionally render a PDF to Storage, set `status=ready`, log the transcript. If an official solution **is** present → skip; that URL is the key.
3. **Submit.** You upload PDFs/images (→ Storage) and/or text. Create `submission(attempt_number=n, is_late = due_at and now > due_at, status=submitted)`. Immediately kick off grading.
4. **AI grades.** Backend calls Claude with: the assignment (title, description, `points_possible`), the answer key (the `ai_solution.content_md`, **or** "the official solution is published at `<url>`; grade against standard real-analysis rigor on these criteria"), and your submission — **PDFs/images attached as document/image content blocks, text inline**. The prompt asks for structured output: a rubric breakdown (`[{criterion, points_awarded, points_possible, note}]`), a total `score`, and `feedback_md` (specific, constructive, points out exactly where a proof gap or error is). Persist a `grade` row; compute `late_penalty_applied` from `late_policy`; set `submission.status=graded`.
5. **Announce + email.** Create `announcement(kind=graded, course, related_assignment, title="Graded: <assignment>", body_md=summary+score+top feedback points)`. Send a Resend email to `app_user.email` (subject `[<course code>] <assignment> graded — N/M`, body = score, rubric summary, first paragraph of feedback, link to the assignment page). Set `announcement.emailed_at`; write `email_log`.
6. **Deadline reminders** (hourly `POST /cron/tick`, `X-Cron-Secret`): for each published assignment with `due_at` within the next 48h (then again within 24h) and **no submission** → if no `cron_marker` for that `(threshold, assignment)` → create `announcement(kind=deadline)`, email it, write the marker. Same tick also: re-drives any `ai_solution` stuck `generating`/`failed` (bounded retries), and any `submission` stuck `grading`.

**Failure handling.** Every Claude/Resend call is wrapped with a timeout + bounded retry (exponential backoff). Hard failure → the relevant status goes to `*_failed` / `email_log.status=failed` and is **surfaced in the UI** with a Retry control — nothing fails silently. Every AI prompt+response is logged (transcript in Storage, path on the row) so you can see *why* a submission got the score it got.

**Cost control.** AI solution generation happens once per assignment (cached on `ai_solution`). Grading happens once per submission attempt. Both are explicit, user-triggered events (creating an assignment / submitting), not background polling — the cron tick only sends emails and retries, it never originates AI work on its own except to retry an already-started job.

---

## 6. Repo & Deployment

```
study-canvas/                         (new git repo · public · MIT license)
  backend/
    pyproject.toml                    uv-managed deps; ruff config
    app/
      main.py                         FastAPI app factory, router mount, CORS
      config.py                       env settings (pydantic-settings)
      db.py                           SQLAlchemy engine/session
      models/                         ORM models (one file per area or grouped)
      schemas/                        pydantic request/response models
      api/                            routers: auth, courses, modules, assignments,
                                      submissions, grades, announcements, cron, teacher
      auth.py                         password hashing, JWT issue/verify, cookie deps
      services/
        ai.py                         Anthropic client; solution-gen + grading prompt builders
        grading.py                    late-penalty + rollup math (pure functions, well-tested)
        email.py                      Resend client; templates
        storage.py                    Supabase Storage upload + signed-URL helpers
      cron.py                         the /cron/tick logic
    alembic/                          versioned migrations
    tests/                            pytest (see §8)
    render.yaml                       Render: 1 Web Service + 1 Cron Job
    Dockerfile                        (if Render needs it; else native Python build)
  frontend/
    package.json                      Vite + React + TypeScript
    src/
      api/                            typed fetch client
      pages/                          one file per page in §4
      components/                     left rail, course nav rail, cards, modals, gradebook…
      styles/                         Canvas-like CSS (hand-rolled; no heavy UI kit)
    .github/workflows/deploy.yml      build → publish dist/ to gh-pages
    .env.example                      VITE_API_BASE_URL
  seed/
    seed_template_course.py           creates the 18.100B course + modules + items + assignments
  docs/superpowers/
    specs/2026-05-12-study-canvas-design.md   (this file)
    plans/                            implementation plan goes here
  README.md                           one-time setup: Supabase project, Render services,
                                      env vars, alembic upgrade, seed command, owner password
  .env.example  .gitignore
```

- **Frontend deploy:** GitHub Action on push to `main` → `npm ci && npm run build` → publish `frontend/dist/` to `gh-pages` (peaceiris/actions-gh-pages). `VITE_API_BASE_URL` injected at build time = the Render backend URL. Same model as education-log.
- **Backend deploy:** `render.yaml` declares a Web Service (`uvicorn app.main:app --host 0.0.0.0 --port $PORT`) and a Cron Job (`curl -fsS -X POST "$SELF_URL/cron/tick" -H "X-Cron-Secret: $CRON_SECRET"`, schedule `0 * * * *`). Env vars in the Render dashboard: `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `ANTHROPIC_API_KEY`, `RESEND_API_KEY`, `JWT_SECRET`, `CRON_SECRET`, `FRONTEND_ORIGIN` (for CORS allow-list), `OWNER_EMAIL`. CORS allows only the GitHub Pages origin.
- **Database:** Supabase project (US region). `alembic upgrade head` on first setup and as a Render pre-deploy step. Storage buckets `submissions` and `solutions` created private. `app_user` row created by a small `manage.py create-owner` command that prompts for email + password (or reads from env), bcrypt-hashing the password.
- **Secrets** never committed; `.env.example` documents the full list.

### One-time setup (README)

1. Create Supabase project; copy `DATABASE_URL`, project URL, service key; create the two private Storage buckets.
2. Create the Anthropic API key and Resend API key (verify a sender domain or use Resend's onboarding domain for now).
3. `cd backend && uv sync && alembic upgrade head && python -m app.manage create-owner`.
4. `python -m seed.seed_template_course` to load 18.100B.
5. Push the repo; the GitHub Action deploys the frontend to Pages; create the Render Web Service + Cron Job from `render.yaml`; set env vars.

---

## 7. Phasing (drives the implementation plan)

1. **P1 — skeleton + read-mostly Canvas.** New repo; FastAPI + SQLAlchemy + Alembic + config + native auth; CRUD for `course` / `module` / `module_item`; React shell with the global rail + Dashboard + Course Home / Syllabus / Modules / Video pages; teacher-mode editing for those entities. **Outcome:** a working "Canvas without homework" where all materials link out — already useful.
2. **P2 — assignments & submissions.** `assignment` CRUD; Assignments list + detail; file upload to Supabase Storage; submission flow; late flagging; Grades page + rollup math. Manual score entry allowed (no AI yet). **Outcome:** full homework tracking, AI-less.
3. **P3 — AI.** `ai_solution` generation; AI grading producing rubric + score + feedback; Retry handling; prompt/response transcript logging; the "view reference solution" toggle. **Outcome:** the homework loop closes itself.
4. **P4 — email & cron.** Resend integration (graded / password-reset emails); Announcements page + unread badge; `/cron/tick` for 48h/24h deadline reminders + stuck-job retries; `cron_marker` idempotency; `render.yaml` cron job. **Outcome:** "AI announces you" works end to end.
5. **P5 — seed + polish.** Build the 18.100B course fully (all modules, all 10 problem sets as assignments with the real PDF links, the 23 video lectures, the syllabus, the exams); tighten the Canvas styling pass; finish the README. **Outcome:** the seed course is a faithful Canvas course you can actually study from.

Each phase ends in something runnable; each becomes its own section of the implementation plan with its own review checkpoint.

---

## 8. Testing & Quality

- **Backend unit tests (pytest):** the grading-math pure functions (late penalty under each policy; assignment current-grade selection; course grade rollup, weighted and unweighted); `cron/tick` idempotency (running it twice sends no duplicate emails / creates no duplicate announcements); the AI prompt-builder functions (given an assignment + key + submission, the assembled message blocks are correct — content kinds, order, that PDFs become document blocks); auth (JWT issue/verify, expired token rejected, password hash round-trips); Storage path construction. **Anthropic and Resend calls are mocked** in all unit tests.
- **Optional live smoke scripts** (gated on `ANTHROPIC_API_KEY` / `RESEND_API_KEY` being set; not run in CI): generate one solution, grade one toy submission, send one test email — for manual sanity only.
- **Frontend:** TypeScript across the app; a typed API client. Verification is a manual browser pass — the app is mostly CRUD plus the homework flow, which is walked through by hand (author an assignment → generate solution → submit → see grade + email). ESLint + Prettier defaults.
- **Backend lint/format:** ruff.
- **CI:** a GitHub Action runs `ruff check`, `pytest`, and the frontend `tsc --noEmit` + `eslint` on push/PR.

---

## 9. Seed Course — MIT 18.100B Real Analysis (Spring 2025)

Source: <https://ocw.mit.edu/courses/18-100b-real-analysis-spring-2025/>

**Course record**
- code `MIT 18.100B` · title `Real Analysis` · institution `MIT OpenCourseWare` · term_label `Spring 2025` · instructor `Prof. Tobias Holck Colding` · status `planned` (your study plan starts later) · color a deep red.
- `external_home_url` → the OCW page above.
- `textbook` → "Thomson, Bruckner & Bruckner, *Elementary Real Analysis*, 2nd ed. (2008) — free PDF; Rudin, *Principles of Mathematical Analysis*, 3rd ed. — secondary."
- `home_page_md` → short intro: two goals (rigorous proof-writing; rigorous calculus), prerequisite 18.02, links to Syllabus / Modules / Video Lectures.

**Syllabus** (rendered markdown): prerequisites (18.02), the two textbooks, **grading: Problem Sets 50% · Midterm 20% · Final 30%**, problem-set policy (≈10 sets, weekly, lowest dropped, individual submission, collaboration encouraged), exam rules (one page of notes, no computer/textbook), plus the auto-built Course Summary table of assignments.

**Modules** (group the 23 lectures + 2 reviews + exams into Canvas-style units; each lecture row is a `module_item kind=video` linking the OCW video page, plus `link` rows for that lecture's notes and the relevant reading):
- *Unit 1 — The Real Numbers* (Lectures 1–3): real numbers, how to write a proof, Archimedean property. Readings §1.1–1.7.
- *Unit 2 — Sequences & Series* (Lectures 4–9): convergence, monotone & Cauchy convergence theorems, Bolzano–Weierstrass, series & convergence tests, power series, limsup/liminf. Readings ch. 2–3, §10.2.
- *Unit 3 — Continuity & Metric Spaces* (Lectures 9–14): continuous functions, exponential function, EVT/IVT, metric spaces, open/closed sets, compactness, sequential compactness. Readings §5.x, ch. 13.
- *Midterm* (review session + exam): the midterm PDF as an `assignment` (`group_name=Exams`, weight 20), the review-session video as a `module_item`.
- *Unit 4 — Differentiation* (Lectures 15–17): derivatives, differentiation laws, Rolle/MVT/L'Hôpital, Taylor expansion & remainder. Readings §7.x.
- *Unit 5 — Riemann Integration* (Lectures 17–19): Riemann integrals, integrable functions, Fundamental Theorem of Calculus. Readings §8.3, §8.6.
- *Unit 6 — Sequences of Functions & ODEs* (Lectures 20–23): pointwise vs uniform convergence, integrals/derivatives under uniform convergence, differentiating/integrating power series, Picard–Lindelöf existence & uniqueness. Readings §9.x, §13.11.4.
- *Final Exam* (review session + exam): the final PDF as an `assignment` (`group_name=Exams`, weight 30), the review-session video as a `module_item`.

**Assignments** — the 10 problem sets, each: title `Problem Set k — <topic>`, `description_md` containing the link to that problem set's OCW PDF, `points_possible=100`, `group_name=Problem Sets` (weight 50, lowest dropped), `due_at` left null (or filled from a notional schedule when you start the course), `accepts_files=true`, `accepts_text=true`, `official_solution_url` left empty (OCW 18.100B does not publish PS solutions) → so the **AI generates the reference solution** for each. Plus the **Midterm** and **Final** as `Exams`-group assignments linking the exam PDFs. (Exam files: include if present on the OCW page; otherwise just the two problem-set-style assignments and the review videos.)

**Video Lectures** — all 23 lecture videos (+ the 2 review sessions) as `module_item kind=video` rows under their units, surfaced together on the Video Lectures page, each linking the corresponding OCW video page.

After 18.100B is in, the other courses from the brief (Linear Algebra → MIT 18.700/18.065; Multivariate Stats → CMU 36-705; Bayesian → Aalto BDA; Stochastic Processes I/II → MIT 6.262 / Columbia IEOR 6711; Numerical ODE/PDE → MIT 18.336 + Cornell CS 4220; SDEs → Stanford MATH 236; Stochastic Optimization → Princeton ORF 544) get added the same way over time — `seed/` grows one file per course, or they're authored through teacher mode.

---

## 10. Open Operational Questions (resolve during implementation, not now)

- Repo name `study-canvas` — fine to rename (`ocw-canvas`, `selfstudy-lms`, …) before the first push.
- Custom domain vs `dafu-zhu.github.io/study-canvas/` for the frontend — defer until deployed.
- Resend sender: onboarding domain initially vs verifying a custom domain — start with whatever Resend allows fastest; revisit if deliverability matters.
- Rendering AI solutions to PDF (Storage) vs just showing the markdown in-app — start with in-app markdown; add the PDF render only if it feels needed.
- Whether to keep `app_user` as a table or hold the owner credential purely in env — leaning table (makes password reset clean); decide at P1.
- Exact Render free-tier behavior (cold starts after inactivity) — acceptable for a personal tool; if it bites, the cron tick doubles as a keep-warm ping.
