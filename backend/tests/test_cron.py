import json
from datetime import UTC, datetime, timedelta

import pytest

from app.models import Announcement, CronMarker, EmailLog
from app.services import ai, storage


@pytest.fixture(autouse=True)
def _env(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "_LOCAL_ROOT", tmp_path)
    monkeypatch.setattr(storage, "_supabase_configured", lambda: False)
    monkeypatch.setattr(ai._settings, "anthropic_api_key", "sk-test")
    monkeypatch.setattr(ai._settings, "ai_solution_generation_enabled", True)


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat()


def test_tick_requires_secret(logged_in_client):
    assert logged_in_client.post("/api/cron/tick").status_code == 403
    assert (
        logged_in_client.post("/api/cron/tick", headers={"X-Cron-Secret": "wrong"}).status_code
        == 403
    )


def test_tick_deadline_reminder_idempotent(logged_in_client, db):
    client = logged_in_client
    cid = client.post("/api/courses", json={"code": "MIT 18.100B", "title": "RA"}).json()["id"]
    due = datetime.now(UTC) + timedelta(hours=30)  # within 48h, not within 24h
    aid = client.post(
        f"/api/courses/{cid}/assignments",
        json={"title": "PS1", "points_possible": 100, "due_at": _iso(due)},
    ).json()["id"]

    headers = {"X-Cron-Secret": "dev-cron-secret"}
    out1 = client.post("/api/cron/tick", headers=headers).json()
    assert out1["deadline_reminders"] == 1
    assert db.query(CronMarker).filter(CronMarker.key == f"deadline-48h:{aid}").count() == 1
    assert db.query(Announcement).filter(Announcement.kind == "deadline").count() == 1
    assert db.query(EmailLog).filter(EmailLog.template == "deadline").count() == 1

    out2 = client.post("/api/cron/tick", headers=headers).json()
    assert out2["deadline_reminders"] == 0
    assert db.query(Announcement).filter(Announcement.kind == "deadline").count() == 1
    assert db.query(EmailLog).filter(EmailLog.template == "deadline").count() == 1


def test_tick_skips_assignment_with_submission(logged_in_client, db):
    client = logged_in_client
    cid = client.post("/api/courses", json={"code": "X", "title": "X"}).json()["id"]
    due = datetime.now(UTC) + timedelta(hours=10)
    aid = client.post(
        f"/api/courses/{cid}/assignments",
        json={"title": "PS1", "points_possible": 100, "due_at": _iso(due)},
    ).json()["id"]
    client.post(f"/api/assignments/{aid}/submissions", data={"text_body": "x"})
    out = client.post("/api/cron/tick", headers={"X-Cron-Secret": "dev-cron-secret"}).json()
    assert out["deadline_reminders"] == 0


def test_tick_grades_now_keyed_submission(logged_in_client, monkeypatch):
    client = logged_in_client
    cid = client.post("/api/courses", json={"code": "X", "title": "X"}).json()["id"]
    aid = client.post(
        f"/api/courses/{cid}/assignments", json={"title": "PS1", "points_possible": 100}
    ).json()["id"]
    # submit before any key exists -> stays "submitted"
    sub = client.post(f"/api/assignments/{aid}/submissions", data={"text_body": "proof"}).json()
    assert sub["status"] == "submitted"
    # now generate the key
    monkeypatch.setattr(ai, "_invoke", lambda s, u, f: (json.dumps({"content_md": "# key"}), "T"))
    client.post(f"/api/assignments/{aid}/generate-solution")
    # the tick grades the now-keyed submission
    gpayload = json.dumps({"score": 80, "feedback_md": "ok", "rubric_breakdown": []})
    monkeypatch.setattr(ai, "_invoke", lambda s, u, f: (gpayload, "GT"))
    out = client.post("/api/cron/tick", headers={"X-Cron-Secret": "dev-cron-secret"}).json()
    assert out["submitted_now_keyed"] == 1
    detail = client.get(f"/api/assignments/{aid}").json()
    assert detail["submissions"][0]["status"] == "graded"
    assert detail["submissions"][0]["grade"]["graded_by"] == "ai"


def test_tick_empty_db(logged_in_client):
    out = logged_in_client.post(
        "/api/cron/tick", headers={"X-Cron-Secret": "dev-cron-secret"}
    ).json()
    assert out["deadline_reminders"] == 0
