"""The hourly tick: deadline reminders + stuck-AI-job re-drives. Idempotent via cron_marker."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Assignment, CronMarker, Submission
from app.services import ai_jobs, notify

DEADLINE_THRESHOLDS_H = (48, 24)


def _aware(dt: datetime | None) -> datetime | None:
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _marker_exists(db: Session, key: str) -> bool:
    return db.get(CronMarker, key) is not None


def _set_marker(db: Session, key: str) -> None:
    db.add(CronMarker(key=key, created_at=datetime.now(UTC)))
    db.commit()


def run_tick(db: Session) -> dict:
    now = datetime.now(UTC)
    counts: dict = {"deadline_reminders": 0}

    # 1. Deadline reminders for published, dated assignments with no submission yet.
    pending = (
        db.query(Assignment)
        .filter(Assignment.published.is_(True), Assignment.due_at.isnot(None))
        .all()
    )
    for a in pending:
        due = _aware(a.due_at)
        if due is None or due <= now:
            continue
        has_sub = (
            db.query(Submission).filter(Submission.assignment_id == a.id).first() is not None
        )
        if has_sub:
            continue
        for hours in DEADLINE_THRESHOLDS_H:
            if due <= now + timedelta(hours=hours):
                key = f"deadline-{hours}h:{a.id}"
                if not _marker_exists(db, key):
                    notify.announce_deadline(db, a, hours)
                    _set_marker(db, key)
                    counts["deadline_reminders"] += 1

    # 2. Re-drive stalled AI work.
    redrive = ai_jobs.retry_stuck(db)
    counts.update(redrive)
    return counts
