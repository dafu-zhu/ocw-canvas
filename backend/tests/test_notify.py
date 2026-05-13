import json

import pytest

from app.models import Announcement, Assignment, Course, EmailLog, Submission
from app.services import ai, ai_jobs, notify, storage


@pytest.fixture(autouse=True)
def _env(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "_LOCAL_ROOT", tmp_path)
    monkeypatch.setattr(storage, "_supabase_configured", lambda: False)
    monkeypatch.setattr(ai._settings, "anthropic_api_key", "sk-test")
    monkeypatch.setattr(ai._settings, "ai_solution_generation_enabled", True)


def test_autograde_produces_graded_announcement_and_email(logged_in_client, monkeypatch):
    client = logged_in_client
    cid = client.post(
        "/api/courses", json={"code": "MIT 18.100B", "title": "Real Analysis"}
    ).json()["id"]
    aid = client.post(
        f"/api/courses/{cid}/assignments", json={"title": "PS1", "points_possible": 100}
    ).json()["id"]
    monkeypatch.setattr(ai, "_invoke", lambda s, u, f: (json.dumps({"content_md": "# key"}), "T"))
    client.post(f"/api/assignments/{aid}/generate-solution")
    gpayload = json.dumps(
        {"score": 92, "feedback_md": "Solid. Part 3 a bit terse.", "rubric_breakdown": []}
    )
    monkeypatch.setattr(ai, "_invoke", lambda s, u, f: (gpayload, "GT"))
    sub = client.post(f"/api/assignments/{aid}/submissions", data={"text_body": "proof"}).json()
    assert sub["status"] == "graded"

    anns = client.get("/api/announcements").json()
    graded = [a for a in anns if a["kind"] == "graded"]
    assert len(graded) == 1
    assert graded[0]["related_assignment_id"] == aid
    assert graded[0]["emailed_at"] is not None
    # email_log written (not actually sent — RESEND_API_KEY unset in tests)


def test_manual_grade_produces_graded_announcement(logged_in_client):
    client = logged_in_client
    cid = client.post("/api/courses", json={"code": "X", "title": "X"}).json()["id"]
    aid = client.post(
        f"/api/courses/{cid}/assignments", json={"title": "PS2", "points_possible": 100}
    ).json()["id"]
    sid = client.post(f"/api/assignments/{aid}/submissions", data={"text_body": "x"}).json()["id"]
    client.post(f"/api/submissions/{sid}/grade", data={"score": "75", "feedback_md": "ok"})
    anns = client.get("/api/announcements").json()
    assert any(a["kind"] == "graded" and a["related_assignment_id"] == aid for a in anns)


def test_announce_graded_without_owner_row(db):
    """No AppUser present -> the announcement is still created, just no email."""
    c = Course(code="X", title="X")
    db.add(c)
    db.flush()
    a = Assignment(course_id=c.id, title="PS3", points_possible=100)
    db.add(a)
    db.flush()
    s = Submission(assignment_id=a.id, attempt_number=1, file_paths=[], status="submitted")
    db.add(s)
    db.flush()
    g = ai_jobs.record_grade(db, s, a, score=88, feedback_md="great", graded_by="manual")
    db.commit()
    ann = notify.announce_graded(db, s, a, g)
    assert ann is not None
    assert ann.kind == "graded"
    assert ann.emailed_at is None  # no owner -> no email
    assert db.query(EmailLog).count() == 0
    assert db.query(Announcement).count() == 1
