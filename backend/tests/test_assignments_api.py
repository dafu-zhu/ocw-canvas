def _course(client):
    return client.post("/api/courses", json={"code": "X", "title": "X"}).json()["id"]


def test_assignment_crud(logged_in_client):
    client = logged_in_client
    cid = _course(client)
    g = client.post(
        f"/api/courses/{cid}/assignment-groups", json={"name": "PS", "weight": 100}
    ).json()

    r = client.post(
        f"/api/courses/{cid}/assignments",
        json={"title": "Problem Set 1", "points_possible": 100, "assignment_group_id": g["id"]},
    )
    assert r.status_code == 201
    aid = r.json()["id"]

    bad = client.post(
        f"/api/courses/{cid}/assignments", json={"title": "bad", "late_policy": "weird"}
    )
    assert bad.status_code == 422

    assert [a["title"] for a in client.get(f"/api/courses/{cid}/assignments").json()] == [
        "Problem Set 1"
    ]
    detail = client.get(f"/api/assignments/{aid}").json()
    assert detail["title"] == "Problem Set 1"
    assert detail["submissions"] == []

    client.put(
        f"/api/assignments/{aid}",
        json={"title": "Problem Set 1 — Sequences", "points_possible": 100},
    )
    assert client.get(f"/api/assignments/{aid}").json()["title"] == "Problem Set 1 — Sequences"
    assert client.delete(f"/api/assignments/{aid}").status_code == 204
    assert client.get(f"/api/assignments/{aid}").status_code == 404
