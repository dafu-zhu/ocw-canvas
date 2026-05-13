from datetime import datetime

from app.schemas.common import ORMModel


class AssignmentBase(ORMModel):
    assignment_group_id: str | None = None
    title: str
    description_md: str = ""
    points_possible: float = 100
    due_at: datetime | None = None
    available_at: datetime | None = None
    accepts_files: bool = True
    accepts_text: bool = True
    official_solution_url: str = ""
    official_solution_file_path: str = ""
    late_policy: str = "flag_only"  # none | flag_only | percent_per_day
    late_value: float | None = None
    position: int = 0
    published: bool = True


class AssignmentCreate(AssignmentBase):
    pass


class AssignmentUpdate(AssignmentBase):
    pass


class AssignmentOut(AssignmentBase):
    id: str
    course_id: str


class RubricItem(ORMModel):
    criterion: str
    points_awarded: float
    points_possible: float
    note: str = ""


class GradeOut(ORMModel):
    id: str
    submission_id: str
    score: float
    score_out_of: float
    late_penalty_applied: float
    final_score: float
    percentage: float
    feedback_md: str
    rubric_breakdown: list[RubricItem] = []
    graded_by: str
    model: str
    graded_at: datetime | None = None


class SubmissionOut(ORMModel):
    id: str
    assignment_id: str
    attempt_number: int
    submitted_at: datetime | None = None
    is_late: bool
    text_body: str | None = None
    file_paths: list[str] = []
    source: str
    status: str
    grade: GradeOut | None = None


class AssignmentDetailOut(AssignmentOut):
    submissions: list[SubmissionOut] = []
