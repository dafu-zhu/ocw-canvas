import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.auth import create_token, get_current_user, hash_password, verify_password
from app.config import get_settings
from app.db import get_db
from app.models import AppUser
from app.services import email as email_svc

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    token: str
    new_password: str


class UserOut(BaseModel):
    id: str
    email: str
    display_name: str


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.jwt_ttl_days * 24 * 3600,
        path="/",
    )


@router.post("/login", response_model=UserOut)
def login(payload: LoginIn, response: Response, db: Session = Depends(get_db)) -> AppUser:
    user = db.query(AppUser).filter(AppUser.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid email or password"
        )
    _set_session_cookie(response, create_token(user.id))
    return user


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(settings.cookie_name, path="/")
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user: AppUser = Depends(get_current_user)) -> AppUser:
    return user


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordIn, db: Session = Depends(get_db)) -> dict:
    user = db.query(AppUser).filter(AppUser.email == payload.email).first()
    if user is not None:
        token = secrets.token_urlsafe(32)
        user.reset_token = token
        user.reset_expires = datetime.now(UTC) + timedelta(hours=1)
        db.commit()
        reset_link = settings.frontend_base_url.rstrip("/") + f"/reset?token={token}"
        subject, html, text = email_svc.render_password_reset(
            name=user.display_name, reset_link=reset_link
        )
        email_svc.send(
            db,
            to=user.email,
            subject=subject,
            template="password_reset",
            html=html,
            text=text,
            payload={"reset_link": reset_link},
        )
    # Never reveal whether the email exists.
    return {"ok": True}


@router.post("/reset-password", response_model=UserOut)
def reset_password(
    payload: ResetPasswordIn, response: Response, db: Session = Depends(get_db)
) -> AppUser:
    user = (
        db.query(AppUser)
        .filter(AppUser.reset_token == payload.token, AppUser.reset_token.isnot(None))
        .first()
    )
    now = datetime.now(UTC)
    expires = user.reset_expires if user else None
    if expires is not None and expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if user is None or expires is None or expires < now:
        raise HTTPException(status_code=400, detail="invalid or expired token")
    user.password_hash = hash_password(payload.new_password)
    user.reset_token = None
    user.reset_expires = None
    db.commit()
    db.refresh(user)
    _set_session_cookie(response, create_token(user.id))
    return user
