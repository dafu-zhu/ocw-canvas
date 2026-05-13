from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()


def _normalize_db_url(url: str) -> str:
    # Supabase / Heroku-style "postgres://" and bare "postgresql://" -> use psycopg (v3),
    # which is the Postgres driver we actually ship. Leave sqlite and explicit drivers alone.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


DATABASE_URL = _normalize_db_url(settings.database_url)
if DATABASE_URL.startswith("sqlite"):
    _connect_args: dict = {"check_same_thread": False}
elif "+psycopg" in DATABASE_URL:
    # Disable client-side prepared statements so we work behind a transaction-mode pooler
    # (e.g. Supabase Supavisor on port 6543). Harmless on direct connections / session pooler.
    _connect_args = {"prepare_threshold": None}
else:
    _connect_args = {}
engine = create_engine(
    DATABASE_URL, connect_args=_connect_args, future=True, pool_pre_ping=True
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
