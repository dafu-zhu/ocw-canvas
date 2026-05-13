import io


def _setup(client):
    cid = client.post("/api/courses", json={"code": "X", "title": "X"}).json()["id"]
    g = client.post(
        f"/api/courses/{cid}/assignment-groups", json={"name": "PS", "weight": 100}
    ).json()
    aid = client.post(
        f"/api/courses/{cid}/assignments",
        json={"title": "PS1", "points_possible": 100, "assignment_group_id": g["id"]},
    ).json()["id"]
    return aid


def test_submit_and_manual_grade(logged_in_client, tmp_path, monkeypatch):
    from app.services import storage

    monkeypatch.setattr(storage, "_LOCAL_ROOT", tmp_path)
    monkeypatch.setattr(storage, "_supabase_configured", lambda: False)
    client = logged_in_client
    aid = _setup(client)

    # submit with text + a file
    r = client.post(
        f"/api/assignments/{aid}/submissions",
        data={"text_body": "see attached"},
        files={"files": ("proof.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
    )
    assert r.status_code == 201
    sub = r.json()
    assert sub["attempt_number"] == 1
    assert sub["text_body"] == "see attached"
    assert sub["file_paths"][0].endswith("proof.pdf")

    # the file is downloadable via the local route
    fr = client.get(f"/api/files/submissions/{sub['file_paths'][0]}")
    assert fr.status_code == 200 and fr.content == b"%PDF-1.4 fake"

    # manual grade
    gr = client.post(
        f"/api/submissions/{sub['id']}/grade", data={"score": "92", "feedback_md": "Nice."}
    )
    assert gr.status_code == 200
    assert gr.json()["final_score"] == 92.0 and gr.json()["percentage"] == 92.0

    # detail tree shows the graded submission
    detail = client.get(f"/api/assignments/{aid}").json()
    assert detail["submissions"][0]["status"] == "graded"
    assert detail["submissions"][0]["grade"]["feedback_md"] == "Nice."


def test_submit_text_only_late_flag(logged_in_client, tmp_path, monkeypatch):
    from app.services import storage

    monkeypatch.setattr(storage, "_LOCAL_ROOT", tmp_path)
    monkeypatch.setattr(storage, "_supabase_configured", lambda: False)
    client = logged_in_client
    cid = client.post("/api/courses", json={"code": "Y", "title": "Y"}).json()["id"]
    # due in the past -> late
    aid = client.post(
        f"/api/courses/{cid}/assignments",
        json={
            "title": "Late one",
            "points_possible": 100,
            "due_at": "2000-01-01T00:00:00Z",
            "late_policy": "percent_per_day",
            "late_value": 10,
        },
    ).json()["id"]
    sub = client.post(f"/api/assignments/{aid}/submissions", data={"text_body": "x"}).json()
    assert sub["is_late"] is True
    # huge number of days late -> penalty clamps at points_possible -> final 0
    gr = client.post(f"/api/submissions/{sub['id']}/grade", data={"score": "90"}).json()
    assert gr["late_penalty_applied"] == 100.0
    assert gr["final_score"] == 0.0
