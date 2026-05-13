"""File storage for submissions and AI solutions.

Backend = Supabase Storage REST API when configured, else a local on-disk store
(so the app runs without any cloud setup). All paths are bucket-relative.
"""
from __future__ import annotations

from pathlib import Path

import httpx

from app.config import get_settings

_settings = get_settings()
_LOCAL_ROOT = Path(__file__).resolve().parents[2] / "_local_storage"


def _supabase_configured() -> bool:
    return bool(_settings.supabase_url and _settings.supabase_service_key)


def submission_path(assignment_id: str, submission_id: str, filename: str) -> str:
    # Treat "/" as a path separator (take the last segment) and "\" as an illegal
    # character (replace it). Platform-independent — does not depend on os.path.basename.
    safe = filename.rsplit("/", 1)[-1].replace("\\", "_")
    return f"submissions/{assignment_id}/{submission_id}/{safe}"


def solution_path(assignment_id: str) -> str:
    return f"solutions/{assignment_id}.md"


def upload_bytes(
    bucket: str, key: str, data: bytes, content_type: str = "application/octet-stream"
) -> str:
    """Store ``data`` at bucket/key. Returns the bucket-relative key."""
    if _supabase_configured():
        url = f"{_settings.supabase_url}/storage/v1/object/{bucket}/{key}"
        headers = {
            "Authorization": f"Bearer {_settings.supabase_service_key}",
            "Content-Type": content_type,
            "x-upsert": "true",
        }
        resp = httpx.post(url, headers=headers, content=data, timeout=30)
        resp.raise_for_status()
    else:
        dest = _LOCAL_ROOT / bucket / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    return key


def read_bytes(bucket: str, key: str) -> bytes:
    if _supabase_configured():
        url = f"{_settings.supabase_url}/storage/v1/object/{bucket}/{key}"
        headers = {"Authorization": f"Bearer {_settings.supabase_service_key}"}
        resp = httpx.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.content
    return (_LOCAL_ROOT / bucket / key).read_bytes()


def signed_url(bucket: str, key: str, expires_in: int = 3600) -> str:
    """A short-lived download URL. For the local backend, returns an /api route the app serves."""
    if _supabase_configured():
        url = f"{_settings.supabase_url}/storage/v1/object/sign/{bucket}/{key}"
        headers = {
            "Authorization": f"Bearer {_settings.supabase_service_key}",
            "Content-Type": "application/json",
        }
        resp = httpx.post(url, headers=headers, json={"expiresIn": expires_in}, timeout=30)
        resp.raise_for_status()
        signed = resp.json()["signedURL"]
        return f"{_settings.supabase_url}/storage/v1{signed}"
    # local: served by the backend (see api/files.py)
    return f"/api/files/{bucket}/{key}"
