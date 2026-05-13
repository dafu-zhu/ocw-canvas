from fastapi.testclient import TestClient

from app.main import app


def test_requires_auth():
    fresh = TestClient(app)
    assert fresh.get("/api/courses").status_code == 401


def test_course_crud_and_tree(logged_in_client):
    client = logged_in_client

    # create
    r = client.post(
        "/api/courses", json={"code": "MIT 18.100B", "title": "Real Analysis", "color": "#8B0000"}
    )
    assert r.status_code == 201
    cid = r.json()["id"]

    # list
    assert [c["code"] for c in client.get("/api/courses").json()] == ["MIT 18.100B"]

    # add a module + items
    m = client.post(f"/api/courses/{cid}/modules", json={"title": "Unit 1", "position": 0}).json()
    client.post(
        f"/api/modules/{m['id']}/items",
        json={"kind": "link", "title": "OCW", "external_url": "https://ocw.mit.edu", "position": 0},
    )
    bad = client.post(
        f"/api/modules/{m['id']}/items", json={"kind": "bogus", "title": "x", "position": 1}
    )
    assert bad.status_code == 422

    # add an assignment group
    g = client.post(
        f"/api/courses/{cid}/assignment-groups",
        json={"name": "Problem Sets", "weight": 50, "drop_lowest_n": 1, "position": 0},
    )
    assert g.status_code == 201

    # detail tree
    detail = client.get(f"/api/courses/{cid}").json()
    assert detail["title"] == "Real Analysis"
    assert detail["modules"][0]["items"][0]["title"] == "OCW"
    assert detail["assignment_groups"][0]["name"] == "Problem Sets"

    # update + delete course
    client.put(
        f"/api/courses/{cid}",
        json={"code": "MIT 18.100B", "title": "Real Analysis (Spring 2025)"},
    )
    assert client.get(f"/api/courses/{cid}").json()["title"] == "Real Analysis (Spring 2025)"
    assert client.delete(f"/api/courses/{cid}").status_code == 204
    assert client.get(f"/api/courses/{cid}").status_code == 404
