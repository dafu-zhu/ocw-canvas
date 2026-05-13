from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.base import TimestampMixin, _uuid

if TYPE_CHECKING:
    from app.models.course import Course


class Announcement(Base, TimestampMixin):
    __tablename__ = "announcement"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    course_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("course.id", ondelete="CASCADE"), nullable=True
    )  # null = global
    # graded | deadline | manual | system
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    title: Mapped[str] = mapped_column(String(400), nullable=False)
    body_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    related_assignment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    emailed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    course: Mapped["Course | None"] = relationship()


class EmailLog(Base, TimestampMixin):
    __tablename__ = "email_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    to: Mapped[str] = mapped_column(String(320), nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    # graded | deadline | password_reset
    template: Mapped[str] = mapped_column(String(40), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    resend_id: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="sent")  # sent | failed
    error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CronMarker(Base):
    __tablename__ = "cron_marker"

    key: Mapped[str] = mapped_column(String(200), primary_key=True)  # "deadline-48h:<assignment_id>"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
