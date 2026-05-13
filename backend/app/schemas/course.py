from datetime import datetime

from app.schemas.common import ORMModel


# ---- Course ----
class CourseBase(ORMModel):
    code: str
    title: str
    institution: str = ""
    term_label: str = ""
    instructor: str = ""
    external_home_url: str = ""
    textbook: str = ""
    home_page_md: str = ""
    syllabus_md: str = ""
    description: str = ""
    color: str = "#394B58"
    status: str = "active"
    display_order: int = 0


class CourseCreate(CourseBase):
    pass


class CourseUpdate(CourseBase):
    pass


class CourseOut(CourseBase):
    id: str


# ---- Module ----
class ModuleBase(ORMModel):
    title: str
    position: int = 0
    published: bool = True


class ModuleCreate(ModuleBase):
    pass


class ModuleUpdate(ModuleBase):
    pass


class ModuleItemBase(ORMModel):
    position: int = 0
    indent: int = 0
    kind: str  # link|video|assignment|note|header
    title: str
    external_url: str = ""
    assignment_id: str | None = None
    text_md: str = ""
    published: bool = True


class ModuleItemCreate(ModuleItemBase):
    pass


class ModuleItemUpdate(ModuleItemBase):
    pass


class ModuleItemOut(ModuleItemBase):
    id: str
    module_id: str


class ModuleOut(ModuleBase):
    id: str
    course_id: str
    items: list[ModuleItemOut] = []


# ---- Assignment group ----
class AssignmentGroupBase(ORMModel):
    name: str
    weight: float | None = None
    drop_lowest_n: int = 0
    position: int = 0


class AssignmentGroupCreate(AssignmentGroupBase):
    pass


class AssignmentGroupUpdate(AssignmentGroupBase):
    pass


class AssignmentGroupOut(AssignmentGroupBase):
    id: str
    course_id: str


# ---- Composite ----
class AssignmentSummaryOut(ORMModel):
    id: str
    title: str
    points_possible: float
    due_at: datetime | None = None
    assignment_group_id: str | None = None
    published: bool = True


class CourseDetailOut(CourseOut):
    modules: list[ModuleOut] = []
    assignment_groups: list[AssignmentGroupOut] = []
    assignments: list[AssignmentSummaryOut] = []
