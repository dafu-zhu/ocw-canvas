from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import Course, Module
from app.schemas.course import ModuleCreate, ModuleOut, ModuleUpdate

router = APIRouter(tags=["modules"], dependencies=[Depends(get_current_user)])


@router.get("/courses/{course_id}/modules", response_model=list[ModuleOut])
def list_modules(course_id: str, db: Session = Depends(get_db)) -> list[Module]:
    if db.get(Course, course_id) is None:
        raise HTTPException(404, "course not found")
    return db.query(Module).filter(Module.course_id == course_id).order_by(Module.position).all()


@router.post("/courses/{course_id}/modules", response_model=ModuleOut, status_code=201)
def create_module(course_id: str, payload: ModuleCreate, db: Session = Depends(get_db)) -> Module:
    if db.get(Course, course_id) is None:
        raise HTTPException(404, "course not found")
    module = Module(course_id=course_id, **payload.model_dump())
    db.add(module)
    db.commit()
    db.refresh(module)
    return module


def _get_module(db: Session, module_id: str) -> Module:
    module = db.get(Module, module_id)
    if module is None:
        raise HTTPException(404, "module not found")
    return module


@router.put("/modules/{module_id}", response_model=ModuleOut)
def update_module(module_id: str, payload: ModuleUpdate, db: Session = Depends(get_db)) -> Module:
    module = _get_module(db, module_id)
    for k, v in payload.model_dump().items():
        setattr(module, k, v)
    db.commit()
    db.refresh(module)
    return module


@router.delete("/modules/{module_id}", status_code=204)
def delete_module(module_id: str, db: Session = Depends(get_db)) -> None:
    db.delete(_get_module(db, module_id))
    db.commit()
