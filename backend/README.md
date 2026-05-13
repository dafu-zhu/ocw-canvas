# OCW Canvas — backend

FastAPI + SQLAlchemy + Alembic. Single-user; JWT in an httpOnly cookie.

## Run locally

```bash
cd backend
uv sync
cp .env.example .env          # edit JWT_SECRET; DATABASE_URL defaults to local sqlite
uv run alembic upgrade head
uv run python -m app.manage create-owner --email you@example.com --name "Your Name"
uv run uvicorn app.main:app --reload --port 8000
```

API at <http://localhost:8000>; interactive docs at <http://localhost:8000/docs>.

## Tests / lint

```bash
uv run pytest -q
uv run ruff check .
```
