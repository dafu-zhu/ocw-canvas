def test_gradebook_rollup(logged_in_client, tmp_path, monkeypatch):
    from app.services import storage

    monkeypatch.setattr(storage, "_LOCAL_ROOT", tmp_path)
    monkeypatch.setattr(storage, "_supabase_configured", lambda: False)
    client = logged_in_client

    cid = client.post("/api/courses", json={"code": "X", "title": "X"}).json()["id"]
    ps = client.post(
        f"/api/courses/{cid}/assignment-groups",
        json={"name": "Problem Sets", "weight": 50, "drop_lowest_n": 1},
    ).json()
    mid = client.post(
        f"/api/courses/{cid}/assignment-groups", json={"name": "Midterm", "weight": 50}
    ).json()

    # 3 problem sets, scores 100/80/40 (the 40 is dropped) -> PS pct = 90
    ps_ids = []
    for i in range(3):
        aid = client.post(
            f"/api/courses/{cid}/assignments",
            json={"title": f"PS{i + 1}", "points_possible": 100, "assignment_group_id": ps["id"]},
        ).json()["id"]
        ps_ids.append(aid)
    for aid, sc in zip(ps_ids, [100, 80, 40], strict=True):
        sid = client.post(f"/api/assignments/{aid}/submissions", data={"text_body": "x"}).json()[
            "id"
        ]
        client.post(f"/api/submissions/{sid}/grade", data={"score": str(sc)})

    # midterm scored 70
    maid = client.post(
        f"/api/courses/{cid}/assignments",
        json={"title": "Midterm", "points_possible": 100, "assignment_group_id": mid["id"]},
    ).json()["id"]
    msid = client.post(f"/api/assignments/{maid}/submissions", data={"text_body": "x"}).json()["id"]
    client.post(f"/api/submissions/{msid}/grade", data={"score": "70"})

    gb = client.get(f"/api/courses/{cid}/gradebook").json()
    # PS 50% @ 90, Midterm 50% @ 70 -> 80.0
    assert round(gb["total_percentage"], 2) == 80.0
    ps_group = next(g for g in gb["groups"] if g["name"] == "Problem Sets")
    assert round(ps_group["percentage"], 2) == 90.0
    assert len(gb["rows"]) == 4

    # only_graded toggle: with an extra ungraded weighted assignment it changes nothing here
    # (Final group doesn't exist), so just check the flag round-trips
    gb2 = client.get(f"/api/courses/{cid}/gradebook?only_graded=false").json()
    assert gb2["only_graded"] is False
