from typing import TYPE_CHECKING

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.base import TimestampMixin, _uuid

if TYPE_CHECKING:
    from app.models.assignment import Assignment, AssignmentGroup
    from app.models.module import Module


class Course(Base, TimestampMixin):
    __tablename__ = "course"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    institution: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    term_label: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    instructor: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    external_home_url: Mapped[str] = mapped_column(Text, nullable=False, default="")
    textbook: Mapped[str] = mapped_column(Text, nullable=False, default="")
    home_page_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    syllabus_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    color: Mapped[str] = mapped_column(String(9), nullable=False, default="#394B58")
    # active | completed | planned
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    modules: Mapped[list["Module"]] = relationship(
        back_populates="course", cascade="all, delete-orphan", order_by="Module.position"
    )
    assignment_groups: Mapped[list["AssignmentGroup"]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="AssignmentGroup.position",
    )
    assignments: Mapped[list["Assignment"]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="Assignment.position",
    )
