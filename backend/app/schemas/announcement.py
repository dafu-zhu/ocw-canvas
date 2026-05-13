from datetime import datetime

from app.schemas.common import ORMModel


class AnnouncementOut(ORMModel):
    id: str
    course_id: str | None
    kind: str
    title: str
    body_md: str
    related_assignment_id: str | None
    read_at: datetime | None
    emailed_at: datetime | None
    created_at: datetime
