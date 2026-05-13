from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.cron import run_tick
from app.db import get_db

router = APIRouter(tags=["cron"])
_settings = get_settings()


@router.post("/cron/tick")
def tick(
    x_cron_secret: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict:
    if not x_cron_secret or x_cron_secret != _settings.cron_secret:
        raise HTTPException(403, "bad cron secret")
    return run_tick(db)
