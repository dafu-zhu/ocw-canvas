from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import Assignment, Grade, Submission
from app.schemas.assignment import GradeOut, SubmissionOut
from app.services import storage
from app.services.grading import apply_late_penalty, days_late

router = APIRouter(tags=["submissions"], dependencies=[Depends(get_current_user)])


def _aware(dt: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes even from timezone=True columns; assume UTC."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _next_attempt(db: Session, assignment_id: str) -> int:
    n = (
        db.query(Submission)
        .filter(Submission.assignment_id == assignment_id)
        .order_by(Submission.attempt_number.desc())
        .first()
    )
    return (n.attempt_number + 1) if n else 1


@router.post(
    "/assignments/{assignment_id}/submissions", response_model=SubmissionOut, status_code=201
)
async def create_submission(
    assignment_id: str,
    text_body: str | None = Form(default=None),
    files: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
) -> Submission:
    a = db.get(Assignment, assignment_id)
    if a is None:
        raise HTTPException(404, "assignment not found")
    now = datetime.now(UTC)
    due = _aware(a.due_at)
    is_late = due is not None and now > due
    sub = Submission(
        assignment_id=assignment_id,
        attempt_number=_next_attempt(db, assignment_id),
        submitted_at=now,
        is_late=is_late,
        text_body=text_body,
        file_paths=[],
        status="submitted",
    )
    db.add(sub)
    db.flush()  # need sub.id for file paths
    paths: list[str] = []
    for f in files or []:
        data = await f.read()
        key = storage.submission_path(assignment_id, sub.id, f.filename or "file")
        storage.upload_bytes("submissions", key, data, f.content_type or "application/octet-stream")
        paths.append(key)
    sub.file_paths = paths
    db.commit()
    db.refresh(sub)
    return sub


@router.get("/assignments/{assignment_id}/submissions", response_model=list[SubmissionOut])
def list_submissions(assignment_id: str, db: Session = Depends(get_db)) -> list[Submission]:
    return (
        db.query(Submission)
        .filter(Submission.assignment_id == assignment_id)
        .order_by(Submission.attempt_number)
        .all()
    )


@router.post("/submissions/{submission_id}/grade", response_model=GradeOut)
def manual_grade(
    submission_id: str,
    score: float = Form(...),
    feedback_md: str = Form(default=""),
    db: Session = Depends(get_db),
) -> Grade:
    sub = db.get(Submission, submission_id)
    if sub is None:
        raise HTTPException(404, "submission not found")
    a = db.get(Assignment, sub.assignment_id)
    points = float(a.points_possible)
    due, submitted_at = _aware(a.due_at), _aware(sub.submitted_at)
    dl = days_late(due, submitted_at) if (due and submitted_at) else 0
    _, penalty = apply_late_penalty(
        score=score,
        points=points,
        is_late=sub.is_late,
        policy=a.late_policy,
        value=float(a.late_value) if a.late_value is not None else None,
        days_late=dl,
    )
    final = max(0.0, score - penalty)
    g = sub.grade or Grade(submission_id=sub.id)
    g.score = score
    g.score_out_of = points
    g.late_penalty_applied = penalty
    g.final_score = final
    g.percentage = (final / points * 100.0) if points else 0.0
    g.feedback_md = feedback_md
    g.graded_by = "manual"
    g.graded_at = datetime.now(UTC)
    if sub.grade is None:
        db.add(g)
    sub.status = "graded"
    db.commit()
    db.refresh(g)
    return g
