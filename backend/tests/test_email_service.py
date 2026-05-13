import pytest

from app.models import EmailLog
from app.services import email


def test_templates():
    s, h, t = email.render_graded(
        course_code="MIT 18.100B",
        assignment_title="Problem Set 1",
        final_score=92,
        points=100,
        feedback_excerpt="Solid work overall.",
        link="https://x/y",
    )
    assert s == "[MIT 18.100B] Problem Set 1 graded — 92/100"
    assert "92 / 100" in t and "Solid work overall." in t and "https://x/y" in t

    s, h, t = email.render_deadline(
        course_code="X", assignment_title="PS3", due_at="Apr 2", hours=48, link="L"
    )
    assert s == "[X] PS3 due in ~48h"
    assert "PS3" in t and "48 hours" in t and "L" in t

    s, h, t = email.render_password_reset(name="Dafu", reset_link="https://app/reset?token=abc")
    assert s == "Reset your OCW Canvas password"
    assert "https://app/reset?token=abc" in t


def test_send_not_configured_no_http(db, monkeypatch):
    monkeypatch.setattr(email._settings, "resend_api_key", "")

    def boom(*a, **k):
        raise AssertionError("httpx.post should not be called when RESEND_API_KEY is unset")

    monkeypatch.setattr(email.httpx, "post", boom)
    log = email.send(db, to="me@x", subject="S", template="graded", html="<p>", text="t")
    assert isinstance(log, EmailLog)
    assert log.status == "sent"
    assert log.resend_id == ""
    assert "_note" in log.payload
    assert db.query(EmailLog).count() == 1


def test_send_configured_success(db, monkeypatch):
    monkeypatch.setattr(email._settings, "resend_api_key", "re_key")

    class FakeResp:
        status_code = 200
        content = b'{"id": "re_123"}'

        def raise_for_status(self):
            pass

        def json(self):
            return {"id": "re_123"}

    monkeypatch.setattr(email.httpx, "post", lambda *a, **k: FakeResp())
    log = email.send(db, to="me@x", subject="S", template="graded", html="<p>", text="t")
    assert log.status == "sent"
    assert log.resend_id == "re_123"


def test_send_configured_failure(db, monkeypatch):
    monkeypatch.setattr(email._settings, "resend_api_key", "re_key")

    def boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr(email.httpx, "post", boom)
    log = email.send(db, to="me@x", subject="S", template="deadline", html="<p>", text="t")
    assert log.status == "failed"
    assert "network down" in log.error
    # never raises


@pytest.mark.parametrize("configured", [True, False])
def test_send_always_writes_log(db, monkeypatch, configured):
    monkeypatch.setattr(email._settings, "resend_api_key", "re_x" if configured else "")
    if configured:
        class R:
            content = b"{}"

            def raise_for_status(self):
                pass

            def json(self):
                return {}

        monkeypatch.setattr(email.httpx, "post", lambda *a, **k: R())
    email.send(db, to="a@b", subject="x", template="graded", html="h", text="t")
    assert db.query(EmailLog).count() == 1
