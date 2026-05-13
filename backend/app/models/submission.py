from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.base import TimestampMixin, _uuid

if TYPE_CHECKING:
    from app.models.assignment import Assignment


class Submission(Base, TimestampMixin):
    __tablename__ = "submission"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    assignment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assignment.id", ondelete="CASCADE"), nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_late: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    text_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_paths: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # me | ai_demo
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="me")
    # submitted | grading | graded | grading_failed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="submitted")

    assignment: Mapped["Assignment"] = relationship(back_populates="submissions")
    grade: Mapped["Grade | None"] = relationship(
        back_populates="submission", uselist=False, cascade="all, delete-orphan"
    )


class Grade(Base, TimestampMixin):
    __tablename__ = "grade"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    submission_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("submission.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    score: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    score_out_of: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False, default=100)
    late_penalty_applied: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    final_score: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    percentage: Mapped[float] = mapped_column(Numeric(8, 3), nullable=False, default=0)
    feedback_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    rubric_breakdown: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # manual | ai
    graded_by: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    model: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    prompt_log_path: Mapped[str] = mapped_column(Text, nullable=False, default="")
    graded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    submission: Mapped["Submission"] = relationship(back_populates="grade")
