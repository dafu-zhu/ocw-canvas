from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.base import TimestampMixin, _uuid

if TYPE_CHECKING:
    from app.models.course import Course


class Module(Base, TimestampMixin):
    __tablename__ = "module"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    course_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("course.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    course: Mapped["Course"] = relationship(back_populates="modules")
    items: Mapped[list["ModuleItem"]] = relationship(
        back_populates="module", cascade="all, delete-orphan", order_by="ModuleItem.position"
    )


class ModuleItem(Base, TimestampMixin):
    __tablename__ = "module_item"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    module_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("module.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    indent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # link | video | assignment | note | header
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(400), nullable=False)
    external_url: Mapped[str] = mapped_column(Text, nullable=False, default="")
    assignment_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("assignment.id", ondelete="SET NULL"), nullable=True
    )
    text_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    module: Mapped["Module"] = relationship(back_populates="items")
