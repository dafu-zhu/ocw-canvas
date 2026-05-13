from datetime import UTC, datetime

from app.services.schedule import (
    AssignmentLite,
    ScheduleParams,
    compute_due,
    compute_schedule,
    parse_start_date,
)


def _lite(id_: str, **kw):
    base = dict(id=id_, title=id_, position=0, assignment_group_id=None,
                covers_lecture_from=None, covers_lecture_to=None)
    base.update(kw)
    return AssignmentLite(**base)


def test_due_is_day_before_next_non_covered_lecture():
    # Lecture 1 = 2027-01-15, cadence 3 days → lec 4 = 2027-01-24, due = 2027-01-23
    p = ScheduleParams(
        start_date=datetime(2027, 1, 15, tzinfo=UTC),
        lecture_cadence_days=3,
        homework_cadence_days=14,
        num_lectures=23,
    )
    a = _lite("a1", covers_lecture_from=1, covers_lecture_to=3)
    due = compute_due(a, p)
    assert due.date() == datetime(2027, 1, 23).date()
    assert (due.hour, due.minute) == (23, 59)


def test_final_falls_after_last_lecture_with_buffer():
    p = ScheduleParams(
        start_date=datetime(2027, 1, 15, tzinfo=UTC),
        lecture_cadence_days=3,
        homework_cadence_days=14,
        num_lectures=23,
        buffer_after_last_lecture_days=7,
    )
    a = _lite("final", covers_lecture_from=1, covers_lecture_to=23)
    # lec 23 = 2027-01-15 + 22*3 = 2027-01-15 + 66d = 2027-03-22
    # +7d buffer = 2027-03-29
    assert compute_due(a, p).date() == datetime(2027, 3, 29).date()


def test_no_coverage_uses_homework_cadence_by_position():
    p = ScheduleParams(
        start_date=datetime(2027, 1, 15, tzinfo=UTC),
        lecture_cadence_days=3,
        homework_cadence_days=14,
        num_lectures=23,
    )
    a = _lite("a", position=0)  # first → +14d
    b = _lite("b", position=1)  # second → +28d
    assert compute_due(a, p) == datetime(2027, 1, 29, 23, 59, tzinfo=UTC)
    assert compute_due(b, p) == datetime(2027, 2, 12, 23, 59, tzinfo=UTC)


def test_compute_schedule_returns_one_due_per_assignment():
    p = ScheduleParams(
        start_date=datetime(2027, 1, 15, tzinfo=UTC),
        lecture_cadence_days=3,
        homework_cadence_days=14,
        num_lectures=23,
    )
    rows = [
        _lite("ps1", covers_lecture_from=1, covers_lecture_to=2),
        _lite("ps2", covers_lecture_from=3, covers_lecture_to=5),
        _lite("mid", covers_lecture_from=1, covers_lecture_to=11),
        _lite("fin", covers_lecture_from=1, covers_lecture_to=23),
    ]
    out = compute_schedule(rows, p)
    assert set(out) == {"ps1", "ps2", "mid", "fin"}
    # ps1 before ps2 before mid before fin
    assert out["ps1"] < out["ps2"] < out["mid"] < out["fin"]


def test_parse_start_date_accepts_date_and_iso():
    d = parse_start_date("2027-01-15")
    assert d == datetime(2027, 1, 15, tzinfo=UTC)
    d2 = parse_start_date("2027-01-15T09:30:00+00:00")
    assert d2 == datetime(2027, 1, 15, 9, 30, tzinfo=UTC)


def test_api_preview_and_apply(logged_in_client):
    """End-to-end via the API."""
    client = logged_in_client
    cid = client.post(
        "/api/courses", json={"code": "X", "title": "X", "status": "planned"}
    ).json()["id"]
    g = client.post(
        f"/api/courses/{cid}/assignment-groups", json={"name": "PS", "weight": 100}
    ).json()
    aids = []
    for k in range(1, 4):
        r = client.post(
            f"/api/courses/{cid}/assignments",
            json={
                "title": f"PS{k}",
                "points_possible": 100,
                "assignment_group_id": g["id"],
                "position": k - 1,
                "covers_lecture_from": 2 * k - 1,
                "covers_lecture_to": 2 * k,
            },
        )
        assert r.status_code == 201
        aids.append(r.json()["id"])

    # Preview (apply=False) — no DB writes
    preview = client.post(
        f"/api/courses/{cid}/schedule",
        json={
            "start_date": "2027-01-15",
            "lecture_cadence_days": 3,
            "homework_cadence_days": 14,
            "apply": False,
        },
    ).json()
    assert preview["num_lectures"] == 6  # max covers_lecture_to = 6, no Lecture-N module items
    assert len(preview["rows"]) == 3
    assert preview["applied"] is False
    # Database still has due_at = null
    for aid in aids:
        assert client.get(f"/api/assignments/{aid}").json()["due_at"] is None

    # Apply
    applied = client.post(
        f"/api/courses/{cid}/schedule",
        json={"start_date": "2027-01-15", "apply": True, "activate": True},
    ).json()
    assert applied["applied"] is True
    assert applied["activated"] is True
    # Now due_at is populated and the course is "active"
    for aid in aids:
        assert client.get(f"/api/assignments/{aid}").json()["due_at"] is not None
    assert client.get(f"/api/courses/{cid}").json()["status"] == "active"
