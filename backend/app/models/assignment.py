from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.base import TimestampMixin, _uuid

if TYPE_CHECKING:
    from app.models.ai_solution import AiSolution
    from app.models.course import Course
    from app.models.submission import Submission


class AssignmentGroup(Base, TimestampMixin):
    __tablename__ = "assignment_group"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    course_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("course.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    weight: Mapped[float | None] = mapped_column(Numeric(6, 3), nullable=True)
    drop_lowest_n: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    course: Mapped["Course"] = relationship(back_populates="assignment_groups")
    assignments: Mapped[list["Assignment"]] = relationship(
        back_populates="group", order_by="Assignment.position"
    )


class Assignment(Base, TimestampMixin):
    __tablename__ = "assignment"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    course_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("course.id", ondelete="CASCADE"), nullable=False
    )
    assignment_group_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("assignment_group.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(400), nullable=False)
    description_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    points_possible: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False, default=100)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    available_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accepts_files: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    accepts_text: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    official_solution_url: Mapped[str] = mapped_column(Text, nullable=False, default="")
    official_solution_file_path: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # none | flag_only | percent_per_day
    late_policy: Mapped[str] = mapped_column(String(20), nullable=False, default="flag_only")
    late_value: Mapped[float | None] = mapped_column(Numeric(6, 3), nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    course: Mapped["Course"] = relationship(back_populates="assignments")
    group: Mapped["AssignmentGroup | None"] = relationship(back_populates="assignments")
    submissions: Mapped[list["Submission"]] = relationship(
        back_populates="assignment",
        cascade="all, delete-orphan",
        order_by="Submission.attempt_number",
    )
    ai_solution: Mapped["AiSolution | None"] = relationship(
        back_populates="assignment", uselist=False, cascade="all, delete-orphan"
    )
