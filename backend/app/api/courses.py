from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import Course
from app.schemas.course import CourseCreate, CourseDetailOut, CourseOut, CourseUpdate

router = APIRouter(prefix="/courses", tags=["courses"], dependencies=[Depends(get_current_user)])


def _get_course(db: Session, course_id: str) -> Course:
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="course not found")
    return course


@router.get("", response_model=list[CourseOut])
def list_courses(db: Session = Depends(get_db)) -> list[Course]:
    return db.query(Course).order_by(Course.display_order, Course.code).all()


@router.post("", response_model=CourseOut, status_code=201)
def create_course(payload: CourseCreate, db: Session = Depends(get_db)) -> Course:
    course = Course(**payload.model_dump())
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@router.get("/{course_id}", response_model=CourseDetailOut)
def get_course(course_id: str, db: Session = Depends(get_db)) -> Course:
    return _get_course(db, course_id)


@router.put("/{course_id}", response_model=CourseOut)
def update_course(course_id: str, payload: CourseUpdate, db: Session = Depends(get_db)) -> Course:
    course = _get_course(db, course_id)
    for k, v in payload.model_dump().items():
        setattr(course, k, v)
    db.commit()
    db.refresh(course)
    return course


@router.delete("/{course_id}", status_code=204)
def delete_course(course_id: str, db: Session = Depends(get_db)) -> None:
    course = _get_course(db, course_id)
    db.delete(course)
    db.commit()
