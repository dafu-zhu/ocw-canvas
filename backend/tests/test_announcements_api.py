from datetime import UTC, datetime, timedelta

from app.models import Announcement, Course


def _seed(db):
    c = Course(code="X", title="X")
    db.add(c)
    db.flush()
    base = datetime.now(UTC)
    db.add(
        Announcement(
            course_id=None, kind="system", title="Welcome", body_md="hi", created_at=base
        )
    )
    db.add(
        Announcement(
            course_id=c.id, kind="graded", title="Graded: PS1", body_md="...",
            related_assignment_id="a1", created_at=base + timedelta(minutes=1),
        )
    )
    db.add(
        Announcement(
            course_id=c.id, kind="deadline", title="Reminder: PS2", body_md="due",
            created_at=base + timedelta(minutes=2),
        )
    )
    db.commit()
    return c.id


def test_announcements_flow(logged_in_client, db):
    cid = _seed(db)
    client = logged_in_client

    rows = client.get("/api/announcements").json()
    assert [r["title"] for r in rows] == ["Reminder: PS2", "Graded: PS1", "Welcome"]  # newest first

    course_rows = client.get(f"/api/announcements?course_id={cid}").json()
    assert {r["kind"] for r in course_rows} == {"graded", "deadline"}

    assert client.get("/api/announcements/unread-count").json()["count"] == 3

    # opening one marks it read
    one = rows[0]
    got = client.get(f"/api/announcements/{one['id']}").json()
    assert got["read_at"] is not None
    assert client.get("/api/announcements/unread-count").json()["count"] == 2

    # mark all read
    flipped = client.post("/api/announcements/mark-all-read").json()["count"]
    assert flipped == 2
    assert client.get("/api/announcements/unread-count").json()["count"] == 0
