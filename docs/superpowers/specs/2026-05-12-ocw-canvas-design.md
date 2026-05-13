# OCW Canvas — Design Spec

**Date:** 2026-05-12
**Status:** Draft for review
**Repo:** `ocw-canvas` (new, public, GitHub)
**Related prior art:** `education-log` (single-user React+Supabase dashboard; this project reuses its patterns and adds a real backend)
**UI reference:** real Canvas screenshots (UChicago Canvas) live in [`assets/`](assets/) next to this spec and are the visual source of truth — `canvas-dashboard.png`, `canvas-course-home-syllabus.png`, `canvas-modules-1/2/3.png`, `canvas-assignments-list-1/2.png`, `canvas-assignment-detail.png`, `canvas-grades-page-1/2.png`, `canvas-announcements.png`. The implementation should match Canvas's chrome (dark narrow left icon rail, breadcrumb bar, course-nav rail), spacing, fonts, and colors closely; where prose here disagrees with a screenshot, the screenshot wins.

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
   ├── REST API     courses · modules · module_items · assignment_groups · assignments ·
   │                submissions · grades · announcements · auth · teacher-mode mutations
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
| home_page_md | text | the course "front page" markdown (intro + jump links) — shown on the Home page |
| syllabus_md | text | the syllabus body markdown — shown on the Syllabus page (above the auto Course Summary table) |
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

### `assignment_group` — Canvas "assignment group" (weight + drop rules)
| field | type | notes |
|---|---|---|
| id | uuid PK | |
| course_id | uuid FK → course | cascade delete |
| name | text | `Problem Sets`, `Midterm`, `Final Exam` |
| weight | numeric | nullable; % of the course grade. If every group in a course has a weight, the course grade is the weighted sum of group percentages; if none do, it's a flat points total. |
| drop_lowest_n | int | default 0; drop the N lowest-scoring graded assignments in this group before averaging (18.100B drops 1 from Problem Sets) |
| position | int | order on the Assignments / Grades pages |

### `assignment`
| field | type | notes |
|---|---|---|
| id | uuid PK | |
| course_id | uuid FK → course | cascade delete |
| assignment_group_id | uuid FK → assignment_group | which group it belongs to |
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
| position | int | order within its group |
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
- **Group percentage** = over the group's `graded` assignments, drop the `drop_lowest_n` lowest by percentage, then `Σ final_score / Σ score_out_of` of the rest.
- **Course grade (Grades page)** = if every `assignment_group` in the course has a `weight`, the weighted sum of group percentages (normalized by the weights of groups that have any graded work, when "calculate based only on graded assignments" is on); otherwise the flat `Σ final_score / Σ score_out_of` over all graded assignments. Ungraded / missing assignments are shown in the table but excluded from the Total (Canvas's editable "what-if" scores are out of scope). For 18.100B: Problem Sets 50% (drop lowest 1) / Midterm 20% / Final Exam 30%.
- **Dashboard "To Do"** = published assignments with `due_at` in the future and no submission, soonest first; plus unread announcements.

### Storage (Supabase)

- Private bucket `submissions`. Paths: `submissions/<assignment_id>/<submission_id>/<filename>`.
- Private bucket `solutions`. Paths: `solutions/<assignment_id>.pdf` and `logs/<...>.txt` for prompt transcripts.
- Frontend never touches Storage directly; the backend issues short-lived signed URLs for download links.

---

## 4. Pages (Canvas look & feel)

The screenshots in `assets/canvas-*.png` are the visual source of truth — match Canvas's chrome, spacing, fonts, and colors closely. Where this section and a screenshot disagree, the screenshot wins.

**Global chrome** (every authenticated page): a fixed **dark, narrow left rail** of stacked icon+label buttons — a small institution crest block at the very top (we use a generic "OCW" mark), then **Account · Dashboard · Courses · Calendar · Inbox · History · Help**; the active item is highlighted. (Some of these are thin in v1 — see below.) To its right, a thin **top breadcrumb bar** (`Course Name › Section › Subsection`, links in blue). Content area is white with generous padding. A small grey term label (e.g. `2026.02` in Canvas; we'd show the course term) sits just above the per-course nav. Body type ≈ 14-15px system sans; headings a larger lighter weight. Course-color accents on course-card header bands and the course banner. The unread-announcement count badges the Inbox icon. **Not replicated:** Canvas's "Ally" score circles ("S"/"A" badges) on items — those are an external integration, skip them.

**Left-rail items in v1:** Dashboard, Courses, Calendar, Inbox (= Announcements), Account (menu: display name, "Teacher mode" toggle, Log out). `History` and `Help` are decorative/optional (can be omitted or stubbed). Below the rail there's the collapse arrow Canvas shows — optional.

### 1. Login — `/login` (public)
Centered card: email + password → `POST /auth/login` (sets the JWT cookie). "Forgot password?" → enter email → emailed reset link → `/reset?token=…` set-new-password page → submit → logged in. No public signup; the one account is provisioned by `manage.py create-owner`.

### 2. Dashboard — `/` (`canvas-dashboard.png`)
Header: large **"Dashboard"** title (+ a `⋮` options menu), and the institution wordmark top-right. Below: a **3-column grid of course cards**, ordered by `display_order`. Each card = a **colored header band** (the course `color`; optionally a background image later — not v1), a `⋮` menu in the band's corner, then in the white lower half: the **course title** as a blue link (`code (term) title`), a greyer **nickname/subtitle** line, the **term label**, and a **footer row of small icons** linking into that course — Announcements (bullhorn, with a red unread-count badge when >0), Modules (folder), Assignments (pencil), Grades. **Right sidebar:** a **"To Do"** list — each entry has a type icon (assignment pencil / announcement bullhorn / calendar event), the title as a link, the course name, the due date/time, and for assignments `"<N> points | <due>"`, plus an `✕` to dismiss; a **"Show All"** link at the bottom. Below To Do, a **"Recent Feedback"** section (recently graded assignments with their score). Empty state: "Add your first course" (teacher mode shows a `+` card).

### 3. Calendar — `/calendar`
Month grid; each assignment `due_at` appears as a course-colored chip on its day; today highlighted; click a chip → the assignment. Month view only in v1 (no week/agenda views). This is the same mini-calendar shown in the course-home sidebar, full-size.

### 4. Announcements / Inbox — `/announcements` and `/courses/:id/announcements` (`canvas-announcements.png`)
A filter dropdown (`All` / per-course), a search box, a **"Mark All as Read"** button. Then a reverse-chron list of `announcement` rows: a round avatar with initials (the "instructor" — we use a fixed AI/system avatar), the **title** (bold), `body_md` preview text (truncated), and **"Posted on: <date>"** on the right; unread rows get a small dot. Click → full announcement view (renders `body_md`, marks `read_at`, links to the related assignment if any). The course-scoped version filters to one course. Low-priority surface — the *email* is the primary delivery; this page just mirrors them.

### 5. Course Home — `/courses/:id` (`canvas-course-home-syllabus.png`)
Course banner area (code · title · term · instructor). Body: the rendered `home_page_md` "front page" (intro + jump links). Left **course-nav rail** below the term label: **Home · Syllabus · Modules · Assignments · Grades · Video Lectures · Announcements** (active item bolded with a left accent bar). **Right sidebar:** buttons **"View Course Stream" · "View Course Calendar" · "View Course Notifications"** (these can be light: Stream → recent activity list, Calendar → the calendar filtered to this course, Notifications → noop/stub in v1), then a **"To Do"** list scoped to this course, then a **mini month calendar** with today highlighted and **deadline days highlighted** (clicking a day jumps the calendar). (Per the user: course home "has a calendar, has events (deadlines)" — that's this mini-calendar.)

### 6. Syllabus — `/courses/:id/syllabus` (same `canvas-course-home-syllabus.png`)
Top: a **"Recent Announcements"** block (the latest few, collapsible). Then the **syllabus body** (rendered markdown — held in a `course.syllabus_md` field; for 18.100B: prerequisites, textbooks, the 50/20/30 grading split, problem-set & exam policies). Then an auto-built **"Course Summary"** table — every assignment with its due date and points, sorted by date — exactly what Canvas generates. Same right sidebar as Course Home (Stream/Calendar/Notifications buttons, To Do, mini calendar). A "Jump to Today" link anchors the summary table to the current date.

### 7. Modules — `/courses/:id/modules` (`canvas-modules-1/2/3.png`)
Top-right buttons: **"Collapse All"** (toggles all modules) and **"Export Course Content"** (decorative/optional in v1 — or a JSON dump). Then a stack of **module sections**, each a **light-grey header bar** with a collapse triangle + the module `title` (e.g. `Direct links`, `Midterm Exam`, `Optional reading`, `Lecture 1`, …). Inside each, **module-item rows** (white, hairline-separated), each = a **kind icon** + the item title:
- `link` → chain-link icon, **blue** title, a small **external-link arrow** after it; opens `external_url` in a new tab.
- `video` → same as `link` (chain-link/external-arrow), used for lecture-video pages.
- `note` (a "page") → document icon, **dark** title; clicking expands/opens the rendered `text_md` inline (or a simple page view).
- `header` → rendered as a sub-heading row inside the module (no icon, or a small marker), `indent`-able.
- `assignment` → assignment/pencil icon, **dark** title, with a small subtitle line `"<due date>  ·  <points> pts"`; clicking goes to the in-app assignment page.

`indent` (0–2) nests rows visually. **This is where all course materials live, and every `link`/`video` points outward to the university's real page — nothing is re-hosted.** Teacher mode adds: `+ Module`, `+ Item` (per module), drag-to-reorder, edit/delete, publish toggles.

### 8a. Assignments list — `/courses/:id/assignments` (`canvas-assignments-list-1/2.png`)
A search box; a **"SHOW BY DATE" / "SHOW BY TYPE"** toggle (the active one filled). **By date:** grey-header groups in order **Overdue Assignments · Upcoming Assignments · Undated Assignments · Past Assignments** (an assignment past `available_at`-window or with submissions disabled shows a `Closed` prefix). **By type:** grouped under `assignment_group` headers (each showing its weight). Each row: assignment/pencil icon, **title** (bold link), and a subtitle `"Due <date> at <time>  |  <score-or-–>/<points> pts  |  <Not Yet Graded?>"` — `–/100 pts` = not yet graded/submitted, `100/100 pts` = graded. Teacher mode: `+ Assignment`, edit/delete, and per-row "Generate solution" / "Re-grade" actions.

### 8b. Assignment detail — `/courses/:id/assignments/:aid` (`canvas-assignment-detail.png`)
Header: assignment **title**; subtitle **"Due: &lt;full date&gt;"**; **"&lt;N&gt; Points Possible"** large, top-right; an **"Add Comment"** button top-right (attaches a note to the current attempt). Below the title: an **"Attempt N" dropdown** (switch between submission attempts) next to a small status ring — `In Progress — NEXT UP: Submit Assignment` before you submit, `Submitted` / `Graded` after; **"Unlimited Attempts Allowed"** text (resubmission is allowed). A **"Details"** collapsible block renders `description_md` (which embeds the link to the source problem-set PDF). Then **"Choose a submission type"** — **Text** (a text/LaTeX entry box), **Upload** (a drag-drop file zone: "Drag a file here, or Choose a file to upload", plus "Webcam Photo" — optional — and a files picker), and **More** (extra types — none in v1). A sticky bottom-right **"Submit Assignment"** button creates the `submission` and kicks off grading.

After grading, the page also shows (in the right column / below): the **score** (`final_score / points_possible`, with the late penalty broken out if any), the **rubric breakdown** table (`criterion · awarded / possible · note`), the AI's **`feedback_md`**, any attempt comments, and a **"View reference solution"** toggle → the `official_solution_url` link if set, else the rendered `ai_solution.content_md`. If `ai_solution.status` is `generating`/`failed`, show that state and (teacher mode) a **"Retry"** button. The "Attempt N" dropdown lets you view the grade for each past attempt.

### 9. Grades — `/courses/:id/grades` (`canvas-grades-page-1/2.png`)
Match the screenshots. Page title **"Grades for &lt;name&gt;"**; top-right a **"Print Grades"** button (`window.print()`). Toolbar: a **Course** dropdown (just this course), an **"Arrange By"** dropdown (`Due Date` / `Module` / `Assignment Group`) + an **Apply** button. A single **"Assignments"** tab (Canvas's "Learning Mastery" tab is out of scope). Then the **gradebook table**:

| column | content |
|---|---|
| **Name** | assignment title (link → assignment); the `assignment_group` name as a small grey subtitle |
| **Due** | `Apr 2 by 11:59pm` (blank if undated) |
| **Submitted** | timestamp of the latest submission, or blank |
| **Status** | a red `missing` pill when past due with no submission; a `late` pill when the submission is late; otherwise blank |
| **Score** | `92 / 100`; a struck-through-eye icon + `/ 100` when not yet graded |
| (trailing) | a rubric/details icon (expands the rubric breakdown inline) and, when the AI left feedback, a comment-bubble icon with a count (expands `feedback_md`) |

Below the rows: per-`assignment_group` **subtotal rows** (`Homework   100%   400.00 / 400.00`, `Final Exam   N/A   0.00 / 0.00`, …) then a bold **Total** row with the overall percentage. **Right sidebar:** **"Total: NN%"** at top; a **"Show All Details"** toggle (expands every row's rubric + feedback); an **"Assignments are weighted by group:"** mini-table (Group / Weight rows + a `Total 100%` row); a **"Calculate based only on graded assignments"** checkbox (default checked — ungraded rows excluded from the Total); and Canvas's standard explanatory blurb about what-if scores (we keep the text but the what-if editing itself is out of scope). The Total uses the §3 rollup, including `drop_lowest_n` within a group (Problem Sets for 18.100B).

### 10. Video Lectures — `/courses/:id/videos`
A list/grid of lecture entries (lecture number, title, optional thumbnail) each linking to the external video page (OCW / YouTube). Backed by the course's `module_item`s with `kind=video`, in module/position order. Just a convenience view over what's already in Modules.

**Teacher mode:** a toggle in the Account menu. When on, `+` / edit / delete / publish / reorder affordances appear on courses, modules, module items, assignment groups, and assignments; clicking opens a plain-form modal (education-log style — required fields marked `*`, no multi-step wizards). Off by default so day-to-day use is pure "student". Also exposes the per-assignment "Generate solution" and "Re-grade" actions and the AI-job "Retry" buttons.

**Empty states:** no courses → "Add your first course"; course with no modules → "No modules yet"; assignment with no submissions → "You haven't submitted yet."

**Responsive:** content collapses to a single column on narrow screens; the course-nav rail becomes a top dropdown. Desktop is the primary target — mobile is best-effort.

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
ocw-canvas/                           (new git repo · public · MIT license)
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
    specs/2026-05-12-ocw-canvas-design.md     (this file)
    specs/assets/                     Canvas UI reference screenshots
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
- *Midterm* (review session + exam): the midterm PDF as an `assignment` in the `Midterm` group, the review-session video as a `module_item`.
- *Unit 4 — Differentiation* (Lectures 15–17): derivatives, differentiation laws, Rolle/MVT/L'Hôpital, Taylor expansion & remainder. Readings §7.x.
- *Unit 5 — Riemann Integration* (Lectures 17–19): Riemann integrals, integrable functions, Fundamental Theorem of Calculus. Readings §8.3, §8.6.
- *Unit 6 — Sequences of Functions & ODEs* (Lectures 20–23): pointwise vs uniform convergence, integrals/derivatives under uniform convergence, differentiating/integrating power series, Picard–Lindelöf existence & uniqueness. Readings §9.x, §13.11.4.
- *Final Exam* (review session + exam): the final PDF as an `assignment` in the `Final Exam` group, the review-session video as a `module_item`.

**Assignment groups:** `Problem Sets` (weight 50, `drop_lowest_n=1`), `Midterm` (weight 20), `Final Exam` (weight 30).

**Assignments** — the 10 problem sets, each: title `Problem Set k — <topic>`, `description_md` containing the link to that problem set's OCW PDF, `points_possible=100`, group `Problem Sets`, `due_at` left null (or filled from a notional schedule when you start the course), `accepts_files=true`, `accepts_text=true`, `official_solution_url` left empty (OCW 18.100B does not publish PS solutions) → so the **AI generates the reference solution** for each. Plus the **Midterm** (group `Midterm`) and **Final Exam** (group `Final Exam`) as assignments linking the exam PDFs. (Exam files: include if present on the OCW page; otherwise just the two exam-style assignments and the review-session videos.)

**Video Lectures** — all 23 lecture videos (+ the 2 review sessions) as `module_item kind=video` rows under their units, surfaced together on the Video Lectures page, each linking the corresponding OCW video page.

After 18.100B is in, the other courses from the brief (Linear Algebra → MIT 18.700/18.065; Multivariate Stats → CMU 36-705; Bayesian → Aalto BDA; Stochastic Processes I/II → MIT 6.262 / Columbia IEOR 6711; Numerical ODE/PDE → MIT 18.336 + Cornell CS 4220; SDEs → Stanford MATH 236; Stochastic Optimization → Princeton ORF 544) get added the same way over time — `seed/` grows one file per course, or they're authored through teacher mode.

---

## 10. Open Operational Questions (resolve during implementation, not now)

- Custom domain vs `dafu-zhu.github.io/ocw-canvas/` for the frontend — defer until deployed.
- Resend sender: onboarding domain initially vs verifying a custom domain — start with whatever Resend allows fastest; revisit if deliverability matters.
- Rendering AI solutions to PDF (Storage) vs just showing the markdown in-app — start with in-app markdown; add the PDF render only if it feels needed.
- Whether to keep `app_user` as a table or hold the owner credential purely in env — leaning table (makes password reset clean); decide at P1.
- Exact Render free-tier behavior (cold starts after inactivity) — acceptable for a personal tool; if it bites, the cron tick doubles as a keep-warm ping.
