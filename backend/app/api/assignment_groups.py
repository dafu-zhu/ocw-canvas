from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import AssignmentGroup, Course
from app.schemas.course import AssignmentGroupCreate, AssignmentGroupOut, AssignmentGroupUpdate

router = APIRouter(tags=["assignment-groups"], dependencies=[Depends(get_current_user)])


@router.get("/courses/{course_id}/assignment-groups", response_model=list[AssignmentGroupOut])
def list_groups(course_id: str, db: Session = Depends(get_db)) -> list[AssignmentGroup]:
    if db.get(Course, course_id) is None:
        raise HTTPException(404, "course not found")
    return (
        db.query(AssignmentGroup)
        .filter(AssignmentGroup.course_id == course_id)
        .order_by(AssignmentGroup.position)
        .all()
    )


@router.post(
    "/courses/{course_id}/assignment-groups",
    response_model=AssignmentGroupOut,
    status_code=201,
)
def create_group(
    course_id: str, payload: AssignmentGroupCreate, db: Session = Depends(get_db)
) -> AssignmentGroup:
    if db.get(Course, course_id) is None:
        raise HTTPException(404, "course not found")
    group = AssignmentGroup(course_id=course_id, **payload.model_dump())
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


def _get_group(db: Session, group_id: str) -> AssignmentGroup:
    group = db.get(AssignmentGroup, group_id)
    if group is None:
        raise HTTPException(404, "assignment group not found")
    return group


@router.put("/assignment-groups/{group_id}", response_model=AssignmentGroupOut)
def update_group(
    group_id: str, payload: AssignmentGroupUpdate, db: Session = Depends(get_db)
) -> AssignmentGroup:
    group = _get_group(db, group_id)
    for k, v in payload.model_dump().items():
        setattr(group, k, v)
    db.commit()
    db.refresh(group)
    return group


@router.delete("/assignment-groups/{group_id}", status_code=204)
def delete_group(group_id: str, db: Session = Depends(get_db)) -> None:
    db.delete(_get_group(db, group_id))
    db.commit()
