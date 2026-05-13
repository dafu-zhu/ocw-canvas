from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import Announcement
from app.schemas.announcement import AnnouncementOut

router = APIRouter(tags=["announcements"], dependencies=[Depends(get_current_user)])


def _get(db: Session, announcement_id: str) -> Announcement:
    a = db.get(Announcement, announcement_id)
    if a is None:
        raise HTTPException(404, "announcement not found")
    return a


@router.get("/announcements", response_model=list[AnnouncementOut])
def list_announcements(
    course_id: str | None = None, db: Session = Depends(get_db)
) -> list[Announcement]:
    q = db.query(Announcement)
    if course_id is not None:
        q = q.filter(Announcement.course_id == course_id)
    return q.order_by(Announcement.created_at.desc()).all()


@router.get("/announcements/unread-count")
def unread_count(db: Session = Depends(get_db)) -> dict:
    n = db.query(Announcement).filter(Announcement.read_at.is_(None)).count()
    return {"count": n}


@router.post("/announcements/mark-all-read")
def mark_all_read(course_id: str | None = None, db: Session = Depends(get_db)) -> dict:
    q = db.query(Announcement).filter(Announcement.read_at.is_(None))
    if course_id is not None:
        q = q.filter(Announcement.course_id == course_id)
    rows = q.all()
    now = datetime.now(UTC)
    for a in rows:
        a.read_at = now
    db.commit()
    return {"count": len(rows)}


@router.get("/announcements/{announcement_id}", response_model=AnnouncementOut)
def get_announcement(announcement_id: str, db: Session = Depends(get_db)) -> Announcement:
    a = _get(db, announcement_id)
    if a.read_at is None:
        a.read_at = datetime.now(UTC)
        db.commit()
        db.refresh(a)
    return a


@router.post("/announcements/{announcement_id}/read", response_model=AnnouncementOut)
def mark_read(announcement_id: str, db: Session = Depends(get_db)) -> Announcement:
    a = _get(db, announcement_id)
    if a.read_at is None:
        a.read_at = datetime.now(UTC)
        db.commit()
        db.refresh(a)
    return a
