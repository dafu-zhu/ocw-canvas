"""Turn homework-loop events into an in-app announcement + an email. Never raises."""
from __future__ import annotations

import re
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Announcement, AppUser, Assignment, Grade, Submission
from app.services import email

_settings = get_settings()


def frontend_link(path: str) -> str:
    return _settings.frontend_base_url.rstrip("/") + path


def _excerpt(md: str, max_sentences: int = 2, max_chars: int = 280) -> str:
    text = re.sub(r"\s+", " ", (md or "").strip())
    if not text:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    out = " ".join(sentences[:max_sentences])
    return out[: max_chars - 1] + "…" if len(out) > max_chars else out


def _owner_email(db: Session) -> str | None:
    user = db.query(AppUser).first()
    return user.email if user else None


def _assignment_path(assignment: Assignment) -> str:
    return f"/courses/{assignment.course_id}/assignments/{assignment.id}"


def announce_graded(
    db: Session, submission: Submission, assignment: Assignment, grade: Grade
) -> Announcement | None:
    try:
        from app.models import Course

        course = db.get(Course, assignment.course_id)
        code = course.code if course else "course"
        excerpt = _excerpt(grade.feedback_md)
        link = frontend_link(_assignment_path(assignment))
        body = (
            f"**{assignment.title}** has been graded: "
            f"**{grade.final_score} / {grade.score_out_of}** ({grade.percentage:.1f}%)."
        )
        if grade.late_penalty_applied:
            body += f" A late penalty of {grade.late_penalty_applied} points was applied."
        if excerpt:
            body += f"\n\n> {excerpt}"
        body += f"\n\n[Open the assignment]({link})"
        ann = Announcement(
            course_id=assignment.course_id,
            kind="graded",
            title=f"Graded: {assignment.title}",
            body_md=body,
            related_assignment_id=assignment.id,
        )
        db.add(ann)
        db.flush()
        to = _owner_email(db)
        if to:
            subject, html, text = email.render_graded(
                course_code=code,
                assignment_title=assignment.title,
                final_score=float(grade.final_score),
                points=float(grade.score_out_of),
                feedback_excerpt=excerpt,
                link=link,
            )
            log = email.send(
                db,
                to=to,
                subject=subject,
                template="graded",
                html=html,
                text=text,
                payload={"assignment_id": assignment.id, "submission_id": submission.id},
            )
            ann.emailed_at = log.sent_at
        db.commit()
        db.refresh(ann)
        return ann
    except Exception:  # noqa: BLE001 — notifications must never break grading
        db.rollback()
        return None


def announce_deadline(db: Session, assignment: Assignment, hours: int) -> Announcement | None:
    try:
        from app.models import Course

        course = db.get(Course, assignment.course_id)
        code = course.code if course else "course"
        due_str = assignment.due_at.isoformat() if assignment.due_at else "soon"
        link = frontend_link(_assignment_path(assignment))
        body = (
            f"**{assignment.title}** is due {due_str} (about {hours} hours from now) and you "
            f"haven't submitted yet.\n\n[Open the assignment]({link})"
        )
        ann = Announcement(
            course_id=assignment.course_id,
            kind="deadline",
            title=f"Reminder: {assignment.title} due in ~{hours}h",
            body_md=body,
            related_assignment_id=assignment.id,
        )
        db.add(ann)
        db.flush()
        to = _owner_email(db)
        if to:
            subject, html, text = email.render_deadline(
                course_code=code,
                assignment_title=assignment.title,
                due_at=due_str,
                hours=hours,
                link=link,
            )
            log = email.send(
                db,
                to=to,
                subject=subject,
                template="deadline",
                html=html,
                text=text,
                payload={"assignment_id": assignment.id, "hours": hours},
            )
            ann.emailed_at = log.sent_at
        else:
            ann.emailed_at = datetime.now(UTC)
        db.commit()
        db.refresh(ann)
        return ann
    except Exception:  # noqa: BLE001
        db.rollback()
        return None
