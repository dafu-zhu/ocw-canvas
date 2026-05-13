from datetime import datetime

from app.schemas.assignment import RubricItem
from app.schemas.common import ORMModel


class GradebookRow(ORMModel):
    assignment_id: str
    title: str
    group_name: str
    points_possible: float
    due_at: datetime | None = None
    submitted_at: datetime | None = None
    status: str  # not_submitted | submitted | graded | missing | late
    score: float | None = None
    feedback_md: str = ""
    rubric_breakdown: list[RubricItem] = []


class GradebookGroup(ORMModel):
    name: str
    weight: float | None
    drop_lowest_n: int
    percentage: float | None
    earned: float
    possible: float


class GradebookOut(ORMModel):
    course_id: str
    rows: list[GradebookRow]
    groups: list[GradebookGroup]
    total_percentage: float | None
    only_graded: bool
