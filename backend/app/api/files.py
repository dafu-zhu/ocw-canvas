from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.auth import get_current_user
from app.services import storage

router = APIRouter(prefix="/files", tags=["files"], dependencies=[Depends(get_current_user)])


@router.get("/{bucket}/{key:path}")
def get_file(bucket: str, key: str) -> Response:
    if bucket not in ("submissions", "solutions"):
        raise HTTPException(404, "unknown bucket")
    try:
        data = storage.read_bytes(bucket, key)
    except FileNotFoundError as exc:
        raise HTTPException(404, "file not found") from exc
    return Response(content=data, media_type="application/octet-stream")
