import json

import pytest

from app.services import ai, storage


@pytest.fixture(autouse=True)
def _ai_env(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "_LOCAL_ROOT", tmp_path)
    monkeypatch.setattr(storage, "_supabase_configured", lambda: False)
    monkeypatch.setattr(ai._settings, "anthropic_api_key", "sk-test")
    monkeypatch.setattr(ai._settings, "ai_solution_generation_enabled", True)


def _course_assignment(client):
    cid = client.post("/api/courses", json={"code": "X", "title": "X"}).json()["id"]
    aid = client.post(
        f"/api/courses/{cid}/assignments", json={"title": "PS1", "points_possible": 100}
    ).json()["id"]
    return cid, aid


def test_solution_lifecycle_and_autograde(logged_in_client, monkeypatch):
    client = logged_in_client
    _cid, aid = _course_assignment(client)

    # fresh assignment -> no key
    info = client.get(f"/api/assignments/{aid}/solution").json()
    assert info["key_kind"] == "none"
    assert info["ai_solution"] is None
    assert info["ai_available"] is True

    # generate the AI solution
    monkeypatch.setattr(
        ai, "_invoke", lambda s, u, f: (json.dumps({"content_md": "# Worked solution\n..."}), "T")
    )
    sol = client.post(f"/api/assignments/{aid}/generate-solution").json()
    assert sol["status"] == "ready"
    assert sol["content_md"].startswith("# Worked")

    info = client.get(f"/api/assignments/{aid}/solution").json()
    assert info["key_kind"] == "ai"
    assert info["ai_solution"]["status"] == "ready"

    # submitting now auto-grades against the AI key
    gpayload = json.dumps(
        {"score": 87, "feedback_md": "Good but part 3 is thin.", "rubric_breakdown": []}
    )
    monkeypatch.setattr(ai, "_invoke", lambda s, u, f: (gpayload, "GT"))
    r = client.post(f"/api/assignments/{aid}/submissions", data={"text_body": "my proof"})
    assert r.status_code == 201
    sub = r.json()
    assert sub["status"] == "graded"
    assert sub["grade"]["graded_by"] == "ai"
    assert sub["grade"]["final_score"] == 87.0


def test_submit_without_key_is_pending(logged_in_client):
    client = logged_in_client
    _cid, aid = _course_assignment(client)
    sub = client.post(f"/api/assignments/{aid}/submissions", data={"text_body": "x"}).json()
    assert sub["status"] == "submitted"
    assert sub["grade"] is None
    # regrade with no key -> 409
    rr = client.post(f"/api/submissions/{sub['id']}/regrade")
    assert rr.status_code == 409


def test_generate_solution_disabled(logged_in_client, monkeypatch):
    client = logged_in_client
    _cid, aid = _course_assignment(client)
    monkeypatch.setattr(ai._settings, "ai_solution_generation_enabled", False)
    called = []
    monkeypatch.setattr(ai, "_invoke", lambda *a, **k: called.append(1) or ("{}", ""))
    sol = client.post(f"/api/assignments/{aid}/generate-solution").json()
    assert sol["status"] == "pending"
    assert "disabled" in sol["error"]
    assert called == []
