"""Outbound email via Resend, plus the small template renderers.

Every send writes an ``email_log`` row (even when ``RESEND_API_KEY`` is unset — in that
case nothing is actually sent, the row just records the intent). ``send`` never raises.
"""
from __future__ import annotations

from datetime import UTC, datetime

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import EmailLog

_settings = get_settings()
_RESEND_URL = "https://api.resend.com/emails"


def email_configured() -> bool:
    return bool(_settings.resend_api_key)


# --------------------------------------------------------------------------- templates


def _wrap_html(body: str) -> str:
    return (
        '<div style="font-family:system-ui,sans-serif;font-size:14px;line-height:1.5;color:#222">'
        f"{body}</div>"
    )


def render_graded(
    *,
    course_code: str,
    assignment_title: str,
    final_score: float,
    points: float,
    feedback_excerpt: str,
    link: str,
) -> tuple[str, str, str]:
    subject = f"[{course_code}] {assignment_title} graded — {final_score}/{points}"
    text = (
        f"{assignment_title} has been graded.\n\n"
        f"Score: {final_score} / {points}\n\n"
        f"{feedback_excerpt}\n\n"
        f"See the full feedback and rubric: {link}\n"
    )
    html = _wrap_html(
        f"<p><strong>{assignment_title}</strong> has been graded.</p>"
        f"<p>Score: <strong>{final_score} / {points}</strong></p>"
        f"<p>{feedback_excerpt}</p>"
        f'<p><a href="{link}">See the full feedback and rubric</a></p>'
    )
    return subject, html, text


def render_deadline(
    *, course_code: str, assignment_title: str, due_at: str, hours: int, link: str
) -> tuple[str, str, str]:
    subject = f"[{course_code}] {assignment_title} due in ~{hours}h"
    text = (
        f"Reminder: {assignment_title} is due {due_at} (about {hours} hours from now) "
        f"and you haven't submitted yet.\n\n{link}\n"
    )
    html = _wrap_html(
        f"<p>Reminder: <strong>{assignment_title}</strong> is due {due_at} "
        f"(about {hours} hours from now) and you haven't submitted yet.</p>"
        f'<p><a href="{link}">Open the assignment</a></p>'
    )
    return subject, html, text


def render_password_reset(*, name: str, reset_link: str) -> tuple[str, str, str]:
    subject = "Reset your OCW Canvas password"
    text = (
        f"Hi {name},\n\nUse this link to set a new password (valid for 1 hour):\n{reset_link}\n\n"
        "If you didn't request this, ignore this email.\n"
    )
    html = _wrap_html(
        f"<p>Hi {name},</p>"
        f'<p>Use this link to set a new password (valid for 1 hour): <a href="{reset_link}">'
        "Reset password</a></p>"
        "<p>If you didn't request this, ignore this email.</p>"
    )
    return subject, html, text


# --------------------------------------------------------------------------- send


def send(
    db: Session,
    *,
    to: str,
    subject: str,
    template: str,
    html: str,
    text: str,
    payload: dict | None = None,
) -> EmailLog:
    log = EmailLog(
        to=to,
        subject=subject,
        template=template,
        payload=payload or {},
        status="sent",
        sent_at=datetime.now(UTC),
    )
    if not email_configured():
        log.payload = {**log.payload, "_note": "email not sent — RESEND_API_KEY unset"}
        db.add(log)
        db.commit()
        db.refresh(log)
        return log
    last_err = ""
    for _attempt in range(2):
        try:
            resp = httpx.post(
                _RESEND_URL,
                headers={
                    "Authorization": f"Bearer {_settings.resend_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": _settings.owner_email_from,
                    "to": [to],
                    "subject": subject,
                    "html": html,
                    "text": text,
                },
                timeout=20,
            )
            resp.raise_for_status()
            body = resp.json() if resp.content else {}
            log.resend_id = str(body.get("id", "")) if isinstance(body, dict) else ""
            log.status = "sent"
            log.error = ""
            db.add(log)
            db.commit()
            db.refresh(log)
            return log
        except Exception as exc:  # noqa: BLE001
            last_err = f"{type(exc).__name__}: {exc}"
    log.status = "failed"
    log.error = last_err
    log.sent_at = None
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
