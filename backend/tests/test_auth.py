from app.auth import create_token, decode_token, hash_password, verify_password


def test_password_hash_roundtrip():
    h = hash_password("hunter2")
    assert h != "hunter2"
    assert verify_password("hunter2", h)
    assert not verify_password("wrong", h)


def test_token_roundtrip():
    token = create_token("user-123")
    assert decode_token(token) == "user-123"


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_login_me_logout_flow(client, owner):
    # unauthenticated /me
    assert client.get("/api/auth/me").status_code == 401

    # bad password
    r = client.post("/api/auth/login", json={"email": "me@example.com", "password": "nope"})
    assert r.status_code == 401

    # good login sets cookie
    r = client.post("/api/auth/login", json={"email": "me@example.com", "password": "pw"})
    assert r.status_code == 200
    assert r.json()["email"] == "me@example.com"

    # now /me works (TestClient persists cookies on the same instance)
    r2 = client.get("/api/auth/me")
    assert r2.status_code == 200
    assert r2.json()["display_name"] == "Me"

    # logout clears it
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401
