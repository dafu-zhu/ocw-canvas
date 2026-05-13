from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import Assignment, Grade, Submission
from app.schemas.assignment import GradeOut, SubmissionOut
from app.services import ai_jobs, storage

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
    # If a solution key already exists, kick off AI grading immediately. The submission is
    # already saved, so a model failure must never 500 the submit — ai_jobs never raises.
    if ai_jobs.has_key(db, a):
        ai_jobs.grade_with_ai(db, sub.id)
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
    g = ai_jobs.record_grade(db, sub, a, score=score, feedback_md=feedback_md, graded_by="manual")
    db.commit()
    db.refresh(g)
    return g
