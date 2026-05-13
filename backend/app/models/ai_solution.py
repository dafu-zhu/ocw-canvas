from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.base import TimestampMixin, _uuid

if TYPE_CHECKING:
    from app.models.assignment import Assignment


class AiSolution(Base, TimestampMixin):
    __tablename__ = "ai_solution"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    assignment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assignment.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    # pending | generating | ready | failed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    content_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    pdf_path: Mapped[str] = mapped_column(Text, nullable=False, default="")
    model: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    prompt_log_path: Mapped[str] = mapped_column(Text, nullable=False, default="")
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    assignment: Mapped["Assignment"] = relationship(back_populates="ai_solution")
