from datetime import UTC, datetime, timedelta

from app.models import AppUser, EmailLog


def test_forgot_unknown_email_is_noop(logged_in_client, db):
    r = logged_in_client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"})
    assert r.status_code == 200 and r.json() == {"ok": True}
    assert db.query(EmailLog).count() == 0


def test_full_reset_flow(client, owner, db):
    # owner fixture created "me@example.com" / "pw"
    r = client.post("/api/auth/forgot-password", json={"email": "me@example.com"})
    assert r.status_code == 200
    db.expire_all()
    u = db.query(AppUser).filter(AppUser.email == "me@example.com").first()
    assert u.reset_token
    assert db.query(EmailLog).filter(EmailLog.template == "password_reset").count() == 1
    token = u.reset_token

    # reset with the token -> logged in, can use the new password
    rr = client.post(
        "/api/auth/reset-password", json={"token": token, "new_password": "newpw123"}
    )
    assert rr.status_code == 200
    assert rr.json()["email"] == "me@example.com"
    # old password no longer works; new one does
    old = client.post("/api/auth/login", json={"email": "me@example.com", "password": "pw"})
    assert old.status_code == 401
    new = client.post("/api/auth/login", json={"email": "me@example.com", "password": "newpw123"})
    assert new.status_code == 200


def test_reset_bad_token(client, owner):
    r = client.post("/api/auth/reset-password", json={"token": "garbage", "new_password": "x"})
    assert r.status_code == 400


def test_reset_expired_token(client, owner, db):
    db.expire_all()
    u = db.query(AppUser).first()
    u.reset_token = "expiredtoken"
    u.reset_expires = datetime.now(UTC) - timedelta(hours=1)
    db.commit()
    assert (
        client.post(
            "/api/auth/reset-password", json={"token": "expiredtoken", "new_password": "x"}
        ).status_code
        == 400
    )
