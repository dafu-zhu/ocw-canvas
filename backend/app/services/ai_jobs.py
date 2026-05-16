"""DB-side orchestration for the AI homework loop.

Wraps ``services.ai`` (the model interface) with: solution-key resolution, the
``ai_solution`` row lifecycle, AI grading of a submission, bounded retries, and
transcript logging to Storage. Every public function here is written to never raise:
on failure it records the error on the relevant row and returns.
"""
from __future__ import annotations

import os
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models import AiSolution, Assignment, Grade, Submission
from app.services import ai, storage
from app.services.grading import days_late_between, finalize_score

MAX_AUTO_RETRIES = 3

# Used as `key_note` when grading a project-style assignment (one with
# requires_solution_key=False). The grading prompt builder already handles
# empty key_text gracefully; this note tells the grader to evaluate on
# quality / depth / clarity / effort rather than match-against-key.
PROJECT_KEY_NOTE = (
    "This is a project-style assignment with no fixed correct answer. Grade "
    "the submission on the quality of the chosen approach, depth of the "
    "analysis, clarity of the writeup, and overall effort — not by comparison "
    "to a reference. Award partial credit generously where the work shows "
    "real engagement; deduct only for unclear writing, sloppy reasoning, "
    "or missing components called for in the assignment description."
)


# --------------------------------------------------------------------------- keys


def resolve_key(db: Session, assignment: Assignment) -> tuple[str, str | None]:
    """Returns (kind, ref). kind ∈ {official_url, official_file, ai, project, none}.

    "project" means the assignment is project-style (requires_solution_key=False);
    grading proceeds without a reference key — see PROJECT_KEY_NOTE.
    """
    if assignment.official_solution_url:
        return "official_url", assignment.official_solution_url
    if assignment.official_solution_file_path:
        return "official_file", assignment.official_solution_file_path
    sol = (
        assignment.ai_solution
        if assignment.ai_solution is not None
        else db.query(AiSolution).filter(AiSolution.assignment_id == assignment.id).first()
    )
    if sol is not None and sol.status == "ready" and sol.content_md.strip():
        return "ai", sol.id
    if not assignment.requires_solution_key:
        return "project", None
    return "none", None


def has_key(db: Session, assignment: Assignment) -> bool:
    """True iff the assignment is ready to be graded — either a real key
    exists, or it's a project-style assignment that grades without one."""
    return resolve_key(db, assignment)[0] != "none"


# --------------------------------------------------------------------------- transcripts


def _save_transcript(name: str, transcript: str) -> str:
    key = f"solutions/logs/{name}.txt"
    try:
        storage.upload_bytes("solutions", key, transcript.encode("utf-8"), "text/plain")
        return key
    except Exception:  # noqa: BLE001 — never let logging failure break the job
        return ""


# --------------------------------------------------------------------------- solutions


def ensure_ai_solution(db: Session, assignment_id: str) -> AiSolution:
    sol = db.query(AiSolution).filter(AiSolution.assignment_id == assignment_id).first()
    if sol is None:
        sol = AiSolution(assignment_id=assignment_id, status="pending")
        db.add(sol)
        db.commit()
        db.refresh(sol)
    return sol


def run_solution_generation(db: Session, assignment_id: str) -> AiSolution:
    a = db.get(Assignment, assignment_id)
    sol = ensure_ai_solution(db, assignment_id)
    if a is not None and not a.requires_solution_key:
        sol.status = "not_required"
        sol.error = (
            "project-style assignment (requires_solution_key=False) — "
            "no reference solution generated; AI grades on quality/effort"
        )
        sol.content_md = ""
        db.commit()
        db.refresh(sol)
        return sol
    if not ai.solution_generation_available():
        sol.status = "pending"
        sol.error = (
            "AI solution generation is disabled "
            "(no credential, or AI_SOLUTION_GENERATION_ENABLED=false)"
        )
        db.commit()
        db.refresh(sol)
        return sol
    sol.status = "generating"
    sol.attempts = (sol.attempts or 0) + 1
    sol.error = ""
    db.commit()
    try:
        result, transcript = ai.generate_reference_solution(
            title=a.title,
            description_md=a.description_md,
            points_possible=float(a.points_possible),
        )
        sol.content_md = result["content_md"]
        sol.model = ai.model_id()
        sol.generated_at = datetime.now(UTC)
        sol.prompt_log_path = _save_transcript(f"{assignment_id}-solution", transcript)
        sol.status = "ready"
        sol.error = ""
    except Exception as exc:  # noqa: BLE001
        sol.status = "failed"
        sol.error = f"{type(exc).__name__}: {exc}"
    db.commit()
    db.refresh(sol)
    return sol


# --------------------------------------------------------------------------- grading


def record_grade(
    db: Session,
    submission: Submission,
    assignment: Assignment,
    *,
    score: float,
    feedback_md: str,
    rubric_breakdown: list | None = None,
    graded_by: str = "manual",
    model: str = "",
    prompt_log_path: str = "",
) -> Grade:
    """Upsert the 1:1 grade row for ``submission`` using the single finalisation path."""
    points = float(assignment.points_possible)
    dl = days_late_between(assignment.due_at, submission.submitted_at)
    penalty, final, pct = finalize_score(
        score=score,
        points=points,
        is_late=submission.is_late,
        policy=assignment.late_policy,
        value=float(assignment.late_value) if assignment.late_value is not None else None,
        days_late=dl,
    )
    g = submission.grade or Grade(submission_id=submission.id)
    g.score = score
    g.score_out_of = points
    g.late_penalty_applied = penalty
    g.final_score = final
    g.percentage = pct
    g.feedback_md = feedback_md
    g.rubric_breakdown = rubric_breakdown or []
    g.graded_by = graded_by
    g.model = model
    g.prompt_log_path = prompt_log_path
    g.graded_at = datetime.now(UTC)
    if submission.grade is None:
        db.add(g)
    submission.status = "graded"
    return g


def grade_with_ai(db: Session, submission_id: str) -> Grade | None:
    sub = db.get(Submission, submission_id)
    if sub is None:
        return None
    a = db.get(Assignment, sub.assignment_id)
    kind, ref = resolve_key(db, a)
    if kind == "none":
        if sub.status not in ("graded",):
            sub.status = "submitted"
            db.commit()
        return None
    sub.status = "grading"
    db.commit()
    try:
        key_text = ""
        key_note = ""
        sub_files: dict[str, bytes] = {}
        if kind == "ai":
            sol = db.query(AiSolution).filter(AiSolution.id == ref).first()
            key_text = sol.content_md if sol else ""
        elif kind == "official_file":
            ext = os.path.splitext(ref)[1] or ".bin"
            try:
                sub_files[f"solution{ext}"] = storage.read_bytes("solutions", ref)
                key_note = f"The attached file solution{ext} is the official answer key."
            except Exception:  # noqa: BLE001
                key_note = (
                    "(the official solution file could not be read; "
                    "grade against standard rigor)"
                )
        elif kind == "official_url":
            key_note = (
                f"The official solution is published at {ref}; grade against standard rigor."
            )
        elif kind == "project":
            key_note = PROJECT_KEY_NOTE
        for p in sub.file_paths or []:
            try:
                sub_files[os.path.basename(p)] = storage.read_bytes("submissions", p)
            except Exception:  # noqa: BLE001
                pass
        result, transcript = ai.grade_submission(
            title=a.title,
            description_md=a.description_md,
            points_possible=float(a.points_possible),
            key_text=key_text,
            key_note=key_note,
            submission_text=sub.text_body or "",
            submission_files=sub_files,
        )
        log_path = _save_transcript(f"{submission_id}-grade", transcript)
        g = record_grade(
            db,
            sub,
            a,
            score=result["score"],
            feedback_md=result["feedback_md"],
            rubric_breakdown=result["rubric_breakdown"],
            graded_by="ai",
            model=ai.model_id(),
            prompt_log_path=log_path,
        )
        db.commit()
        db.refresh(g)
        from app.services import notify  # local import: notify -> email -> models (no cycle)

        notify.announce_graded(db, sub, a, g)
        return g
    except Exception:  # noqa: BLE001
        sub.status = "grading_failed"
        db.commit()
        return None


# --------------------------------------------------------------------------- cron sweep


def retry_stuck(db: Session) -> dict:
    """Re-drive stalled AI work. Returns a small counts dict (for the cron tick / tests)."""
    counts = {"solutions": 0, "submitted_now_keyed": 0, "stuck_grading": 0}
    for sol in (
        db.query(AiSolution)
        .filter(AiSolution.status.in_(("generating", "failed")))
        .all()
    ):
        if (sol.attempts or 0) < MAX_AUTO_RETRIES:
            run_solution_generation(db, sol.assignment_id)
            counts["solutions"] += 1
    for sub in db.query(Submission).filter(Submission.status == "submitted").all():
        a = db.get(Assignment, sub.assignment_id)
        if a is not None and has_key(db, a):
            grade_with_ai(db, sub.id)
            counts["submitted_now_keyed"] += 1
    for sub in db.query(Submission).filter(Submission.status == "grading").all():
        grade_with_ai(db, sub.id)
        counts["stuck_grading"] += 1
    return counts
