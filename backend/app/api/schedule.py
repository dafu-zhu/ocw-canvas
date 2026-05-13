from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import Course
from app.services.schedule import (
    AssignmentLite,
    ScheduleParams,
    compute_schedule,
    parse_start_date,
)

router = APIRouter(tags=["schedule"], dependencies=[Depends(get_current_user)])


class ScheduleRequest(BaseModel):
    start_date: str  # "YYYY-MM-DD" or ISO
    lecture_cadence_days: int = 3
    homework_cadence_days: int = 14
    buffer_after_last_lecture_days: int = 7
    apply: bool = False  # if True, write the proposed due_at to each assignment
    activate: bool = False  # if True (and apply), also set course.status = "active"


class ScheduleRow(BaseModel):
    assignment_id: str
    title: str
    due_at: datetime
    covers_lecture_from: int | None
    covers_lecture_to: int | None


class ScheduleResponse(BaseModel):
    course_id: str
    start_date: datetime
    num_lectures: int
    lecture_cadence_days: int
    homework_cadence_days: int
    applied: bool
    activated: bool
    rows: list[ScheduleRow]


def _max_lecture_number(course: Course) -> int:
    """Find the highest 'Lecture N' module-item title across the course."""
    import re

    pat = re.compile(r"^Lecture (\d+):")
    nums: list[int] = []
    for m in course.modules:
        for it in m.items:
            mt = pat.match(it.title or "")
            if mt:
                nums.append(int(mt.group(1)))
    return max(nums) if nums else 0


@router.post("/courses/{course_id}/schedule", response_model=ScheduleResponse)
def schedule_course(
    course_id: str, payload: ScheduleRequest, db: Session = Depends(get_db)
) -> ScheduleResponse:
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(404, "course not found")

    start = parse_start_date(payload.start_date)
    num_lectures = _max_lecture_number(course)
    if num_lectures == 0:
        # No "Lecture N:" items in modules; fall back to max covers_lecture_to across
        # all assignments (or 1 if nobody declares coverage).
        covers = [a.covers_lecture_to for a in course.assignments if a.covers_lecture_to]
        num_lectures = max(covers) if covers else 1

    # Order assignments by group position then in-group position for stable output.
    sorted_a = sorted(
        course.assignments,
        key=lambda a: (
            (a.group.position if a.group else 999),
            a.position,
            a.title,
        ),
    )
    lites = [
        AssignmentLite(
            id=a.id,
            title=a.title,
            position=a.position,
            assignment_group_id=a.assignment_group_id,
            covers_lecture_from=a.covers_lecture_from,
            covers_lecture_to=a.covers_lecture_to,
        )
        for a in sorted_a
    ]
    params = ScheduleParams(
        start_date=start,
        lecture_cadence_days=payload.lecture_cadence_days,
        homework_cadence_days=payload.homework_cadence_days,
        num_lectures=num_lectures,
        buffer_after_last_lecture_days=payload.buffer_after_last_lecture_days,
    )
    proposed = compute_schedule(lites, params)

    applied = False
    activated = False
    if payload.apply:
        for a in sorted_a:
            a.due_at = proposed[a.id]
        if payload.activate and course.status != "active":
            course.status = "active"
            activated = True
        db.commit()
        applied = True

    return ScheduleResponse(
        course_id=course.id,
        start_date=start,
        num_lectures=num_lectures,
        lecture_cadence_days=payload.lecture_cadence_days,
        homework_cadence_days=payload.homework_cadence_days,
        applied=applied,
        activated=activated,
        rows=[
            ScheduleRow(
                assignment_id=a.id,
                title=a.title,
                due_at=proposed[a.id],
                covers_lecture_from=a.covers_lecture_from,
                covers_lecture_to=a.covers_lecture_to,
            )
            for a in sorted_a
        ],
    )
