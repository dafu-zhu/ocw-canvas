# OCW Canvas

A personal, Canvas-like LMS for self-studying open courseware (MIT OCW, etc.). Tracks course materials under **Modules** (every item links out to the university's real page — nothing is re-hosted), and runs a homework loop: an assignment has a deadline; if no official solution exists the AI writes a reference solution key; you upload your work; the AI grades it against the key, leaves written feedback and a score; you get an in-app announcement and an email.

Single user. React + Vite frontend (GitHub Pages), FastAPI backend (Render), Supabase Postgres + Storage, the Claude Agent SDK (Claude subscription via OAuth token; Anthropic API as fallback) for AI, Resend for email. The UI mirrors Canvas (dark left rail, course-card dashboard, per-course nav: Home · Syllabus · Modules · Assignments · Grades · Video Lectures · Announcements).

**Status:** P1 complete — a runnable "Canvas without homework": single-user auth; CRUD for courses / modules / module-items / assignment-groups; Dashboard, Course Home, Syllabus, Modules, Video Lectures pages; teacher-mode editing. Backend: [`backend/README.md`](backend/README.md). Frontend: [`frontend/README.md`](frontend/README.md). Design spec: [`docs/superpowers/specs/2026-05-12-ocw-canvas-design.md`](docs/superpowers/specs/2026-05-12-ocw-canvas-design.md). Plans: [`docs/superpowers/plans/`](docs/superpowers/plans/). Homework + AI grading + email come in phases 2–4; the 18.100B seed course in phase 5.

First seed course: **MIT 18.100B — Real Analysis (Spring 2025)**.
