from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import Module, ModuleItem
from app.schemas.course import ModuleItemCreate, ModuleItemOut, ModuleItemUpdate

router = APIRouter(tags=["module-items"], dependencies=[Depends(get_current_user)])

_VALID_KINDS = {"link", "video", "assignment", "note", "header"}


def _validate_kind(kind: str) -> None:
    if kind not in _VALID_KINDS:
        raise HTTPException(422, f"invalid module item kind {kind!r}")


@router.post("/modules/{module_id}/items", response_model=ModuleItemOut, status_code=201)
def create_item(
    module_id: str, payload: ModuleItemCreate, db: Session = Depends(get_db)
) -> ModuleItem:
    if db.get(Module, module_id) is None:
        raise HTTPException(404, "module not found")
    _validate_kind(payload.kind)
    item = ModuleItem(module_id=module_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def _get_item(db: Session, item_id: str) -> ModuleItem:
    item = db.get(ModuleItem, item_id)
    if item is None:
        raise HTTPException(404, "module item not found")
    return item


@router.put("/module-items/{item_id}", response_model=ModuleItemOut)
def update_item(
    item_id: str, payload: ModuleItemUpdate, db: Session = Depends(get_db)
) -> ModuleItem:
    item = _get_item(db, item_id)
    _validate_kind(payload.kind)
    for k, v in payload.model_dump().items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/module-items/{item_id}", status_code=204)
def delete_item(item_id: str, db: Session = Depends(get_db)) -> None:
    db.delete(_get_item(db, item_id))
    db.commit()
