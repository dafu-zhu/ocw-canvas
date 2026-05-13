from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import Assignment, Course
from app.schemas.assignment import (
    AssignmentBase,
    AssignmentCreate,
    AssignmentDetailOut,
    AssignmentOut,
    AssignmentUpdate,
)

router = APIRouter(tags=["assignments"], dependencies=[Depends(get_current_user)])

_VALID_LATE = {"none", "flag_only", "percent_per_day"}


def _validate(payload: AssignmentBase) -> None:
    if payload.late_policy not in _VALID_LATE:
        raise HTTPException(422, f"invalid late_policy {payload.late_policy!r}")


def _get(db: Session, assignment_id: str) -> Assignment:
    a = db.get(Assignment, assignment_id)
    if a is None:
        raise HTTPException(404, "assignment not found")
    return a


@router.get("/courses/{course_id}/assignments", response_model=list[AssignmentOut])
def list_assignments(course_id: str, db: Session = Depends(get_db)) -> list[Assignment]:
    if db.get(Course, course_id) is None:
        raise HTTPException(404, "course not found")
    return (
        db.query(Assignment)
        .filter(Assignment.course_id == course_id)
        .order_by(Assignment.position, Assignment.title)
        .all()
    )


@router.post("/courses/{course_id}/assignments", response_model=AssignmentOut, status_code=201)
def create_assignment(
    course_id: str, payload: AssignmentCreate, db: Session = Depends(get_db)
) -> Assignment:
    if db.get(Course, course_id) is None:
        raise HTTPException(404, "course not found")
    _validate(payload)
    a = Assignment(course_id=course_id, **payload.model_dump())
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


@router.get("/assignments/{assignment_id}", response_model=AssignmentDetailOut)
def get_assignment(assignment_id: str, db: Session = Depends(get_db)) -> Assignment:
    return _get(db, assignment_id)


@router.put("/assignments/{assignment_id}", response_model=AssignmentOut)
def update_assignment(
    assignment_id: str, payload: AssignmentUpdate, db: Session = Depends(get_db)
) -> Assignment:
    a = _get(db, assignment_id)
    _validate(payload)
    for k, v in payload.model_dump().items():
        setattr(a, k, v)
    db.commit()
    db.refresh(a)
    return a


@router.delete("/assignments/{assignment_id}", status_code=204)
def delete_assignment(assignment_id: str, db: Session = Depends(get_db)) -> None:
    db.delete(_get(db, assignment_id))
    db.commit()
