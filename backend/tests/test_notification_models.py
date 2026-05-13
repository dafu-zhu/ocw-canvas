from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Announcement, Course, CronMarker, EmailLog


def test_announcement_course_cascade(db):
    c = Course(code="X", title="X")
    db.add(c)
    db.flush()
    db.add(Announcement(course_id=c.id, kind="graded", title="Graded: PS1", body_md="..."))
    db.add(Announcement(course_id=None, kind="system", title="Welcome", body_md="hi"))
    db.commit()
    assert db.query(Announcement).count() == 2
    db.delete(c)
    db.commit()
    assert db.query(Announcement).count() == 1  # the global one survives


def test_email_log_and_cron_marker(db):
    db.add(
        EmailLog(
            to="me@example.com",
            subject="[X] PS1 graded — 90/100",
            template="graded",
            payload={"final_score": 90},
            status="sent",
            sent_at=datetime.now(UTC),
        )
    )
    db.add(CronMarker(key="deadline-48h:abc", created_at=datetime.now(UTC)))
    db.commit()
    assert db.query(EmailLog).count() == 1
    db.add(CronMarker(key="deadline-48h:abc", created_at=datetime.now(UTC)))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
