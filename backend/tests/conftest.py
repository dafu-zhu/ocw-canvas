import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Force a throwaway sqlite db before app modules import settings.
_tmp_db_fd, _tmp_db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_db_path}"
os.environ["JWT_SECRET"] = "test-secret-test-secret-test-secret-0123456789"

from app import models  # noqa: E402,F401  (import side effect: register all models on Base)
from app.db import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

_engine = create_engine(
    os.environ["DATABASE_URL"], connect_args={"check_same_thread": False}, future=True
)
_TestSession = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)


@pytest.fixture(autouse=True)
def _fresh_schema():
    Base.metadata.drop_all(_engine)
    Base.metadata.create_all(_engine)
    yield
    Base.metadata.drop_all(_engine)


@pytest.fixture
def db():
    session = _TestSession()
    try:
        yield session
    finally:
        session.close()


def _override_get_db():
    session = _TestSession()
    try:
        yield session
    finally:
        session.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def owner(db):
    """Create the single owner account and return it."""
    from app.auth import hash_password
    from app.models import AppUser

    user = AppUser(
        id="u1", email="me@example.com", password_hash=hash_password("pw"), display_name="Me"
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def logged_in_client(client, owner):
    """A TestClient already authenticated as the owner."""
    resp = client.post("/api/auth/login", json={"email": "me@example.com", "password": "pw"})
    assert resp.status_code == 200
    return client
