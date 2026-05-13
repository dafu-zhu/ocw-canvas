"""Tests for services/ai_jobs — the DB-side AI orchestration. The model seam
(``ai._invoke``) is monkeypatched; Storage uses the local on-disk fallback."""
import json
from datetime import UTC, datetime, timedelta

import pytest

from app.models import AiSolution, Assignment, Course, Submission
from app.services import ai, ai_jobs, storage


@pytest.fixture(autouse=True)
def _local_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "_LOCAL_ROOT", tmp_path)
    monkeypatch.setattr(storage, "_supabase_configured", lambda: False)
    # Pretend a credential is configured so ai_available()/solution_generation_available() are True
    monkeypatch.setattr(ai._settings, "anthropic_api_key", "sk-test")
    monkeypatch.setattr(ai._settings, "ai_solution_generation_enabled", True)


def _course_assignment(db, **akw):
    c = Course(code="X", title="X")
    db.add(c)
    db.flush()
    a = Assignment(course_id=c.id, title="PS1", points_possible=100, **akw)
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def _sub(db, assignment, **kw):
    s = Submission(
        assignment_id=assignment.id,
        attempt_number=1,
        submitted_at=datetime.now(UTC),
        text_body="my proof",
        file_paths=[],
        status="submitted",
        **kw,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def test_resolve_key_priority(db):
    a = _course_assignment(db)
    assert ai_jobs.resolve_key(db, a)[0] == "none"
    db.add(AiSolution(assignment_id=a.id, status="ready", content_md="# key"))
    db.commit()
    db.refresh(a)
    assert ai_jobs.resolve_key(db, a)[0] == "ai"
    a.official_solution_file_path = "solutions/a.pdf"
    db.commit()
    assert ai_jobs.resolve_key(db, a)[0] == "official_file"
    a.official_solution_url = "https://example.com/sol"
    db.commit()
    assert ai_jobs.resolve_key(db, a)[0] == "official_url"


def test_run_solution_generation_ok(db, monkeypatch):
    a = _course_assignment(db)
    monkeypatch.setattr(
        ai, "_invoke", lambda s, u, f: (json.dumps({"content_md": "# Worked\n..."}), "TRANSCRIPT")
    )
    sol = ai_jobs.run_solution_generation(db, a.id)
    assert sol.status == "ready"
    assert sol.content_md.startswith("# Worked")
    assert sol.attempts == 1
    assert sol.prompt_log_path
    assert storage.read_bytes("solutions", sol.prompt_log_path) == b"TRANSCRIPT"


def test_run_solution_generation_disabled(db, monkeypatch):
    a = _course_assignment(db)
    monkeypatch.setattr(ai._settings, "ai_solution_generation_enabled", False)
    called = []
    monkeypatch.setattr(ai, "_invoke", lambda *args, **kw: called.append(1) or ("{}", ""))
    sol = ai_jobs.run_solution_generation(db, a.id)
    assert sol.status == "pending"
    assert "disabled" in sol.error
    assert called == []


def test_run_solution_generation_failure(db, monkeypatch):
    a = _course_assignment(db)

    def boom(*args, **kw):
        raise RuntimeError("model exploded")

    monkeypatch.setattr(ai, "_invoke", boom)
    sol = ai_jobs.run_solution_generation(db, a.id)
    assert sol.status == "failed"
    assert "model exploded" in sol.error


def test_grade_with_ai_against_ai_key(db, monkeypatch):
    a = _course_assignment(db)
    db.add(AiSolution(assignment_id=a.id, status="ready", content_md="# key"))
    db.commit()
    s = _sub(db, a)
    monkeypatch.setattr(
        ai,
        "_invoke",
        lambda sys, u, f: (
            json.dumps({"score": 91, "feedback_md": "Solid.", "rubric_breakdown": []}),
            "GTRANSCRIPT",
        ),
    )
    g = ai_jobs.grade_with_ai(db, s.id)
    assert g is not None
    assert g.graded_by == "ai"
    assert g.final_score == 91.0
    assert g.percentage == 91.0
    db.refresh(s)
    assert s.status == "graded"
    assert g.prompt_log_path
    assert storage.read_bytes("solutions", g.prompt_log_path) == b"GTRANSCRIPT"


def test_grade_with_ai_no_key(db, monkeypatch):
    a = _course_assignment(db)
    s = _sub(db, a)
    called = []
    monkeypatch.setattr(ai, "_invoke", lambda *a, **k: called.append(1) or ("{}", ""))
    assert ai_jobs.grade_with_ai(db, s.id) is None
    db.refresh(s)
    assert s.status == "submitted"
    assert called == []


def test_grade_with_ai_late_penalty(db, monkeypatch):
    due = datetime.now(UTC) - timedelta(days=3, hours=1)  # 4 days late
    a = _course_assignment(db, due_at=due, late_policy="percent_per_day", late_value=10)
    db.add(AiSolution(assignment_id=a.id, status="ready", content_md="# key"))
    db.commit()
    s = _sub(db, a, is_late=True)
    payload = json.dumps({"score": 90, "feedback_md": "x", "rubric_breakdown": []})
    monkeypatch.setattr(ai, "_invoke", lambda sys, u, f: (payload, "T"))
    g = ai_jobs.grade_with_ai(db, s.id)
    # 4 days * 10%/day = 40 points off -> final 50
    assert g.late_penalty_applied == 40.0
    assert g.final_score == 50.0


def test_retry_stuck_redrives(db, monkeypatch):
    a = _course_assignment(db)
    db.add(AiSolution(assignment_id=a.id, status="ready", content_md="# key"))
    db.commit()
    s = _sub(db, a)  # submitted, key now exists
    # a failed solution on another assignment with attempts < MAX
    a2 = Assignment(course_id=a.course_id, title="PS2", points_possible=100)
    db.add(a2)
    db.commit()
    db.add(AiSolution(assignment_id=a2.id, status="failed", attempts=1, content_md=""))
    db.commit()
    payload = json.dumps(
        {"score": 70, "feedback_md": "y", "rubric_breakdown": [], "content_md": "# sol"}
    )
    monkeypatch.setattr(ai, "_invoke", lambda sys, u, f: (payload, "T"))
    counts = ai_jobs.retry_stuck(db)
    assert counts["submitted_now_keyed"] == 1
    db.refresh(s)
    assert s.status == "graded"
    sol2 = db.query(AiSolution).filter(AiSolution.assignment_id == a2.id).first()
    assert sol2.status == "ready"
