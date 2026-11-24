from collections import OrderedDict
from threading import Lock
from time import monotonic

import logging
import secrets
from datetime import timedelta
from typing import Literal

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Account, AuditLog, LoginSession
from app.db.session import get_db
from app.services.access import admin, current_user, digest, error, now

router = APIRouter()
hasher = PasswordHasher()
dummy_hash = hasher.hash(secrets.token_urlsafe(32))


# Local, single-worker development guard. Use a shared limiter when workers are distributed.
_attempts = OrderedDict()
_attempt_lock = Lock()


def limit_auth(request: Request):
    key = (request.client.host if request.client else "", request.url.path)
    moment = monotonic()
    with _attempt_lock:
        while _attempts and next(iter(_attempts.values()))[0] <= moment:
            _attempts.popitem(last=False)
        if key not in _attempts:
            if len(_attempts) >= 10000:
                raise error(429, "rate_limited", "请求频繁，请稍后重试")
            _attempts[key] = [moment + 60, 0]
        if _attempts[key][1] >= 20:
            raise error(429, "rate_limited", "请求频繁，请稍后重试")
        _attempts[key][1] += 1


class Profile(BaseModel):
    user_id: int
    display_name: str
    platform_role: Literal["teacher", "admin"]
    account_status: Literal["pending_verification", "pending_approval", "active", "rejected", "disabled"]
    status_reason: str | None


class Teacher(BaseModel):
    user_id: int
    display_name: str
    email: EmailStr
    account_status: str
    status_reason: str | None
    version: int


class Message(BaseModel):
    message: str


class CsrfToken(BaseModel):
    csrf_token: str


class Email(BaseModel):
    email: EmailStr


class Login(Email):
    password: str = Field(min_length=1, max_length=1024)


class Register(Login):
    password: str = Field(min_length=8, max_length=1024)
    display_name: str = Field(min_length=1, max_length=255, pattern=r"\S")
    note: str = Field("", max_length=4096)


class Verification(BaseModel):
    token: str = Field(min_length=1, max_length=256)


class Resubmit(BaseModel):
    note: str = Field(min_length=1, max_length=4096, pattern=r"\S")
    display_name: str | None = Field(None, min_length=1, max_length=255, pattern=r"\S")


class Action(BaseModel):
    action: Literal["approve", "reject", "disable"]
    expected_version: int = Field(ge=1)
    reason: str = Field("", max_length=4096)


def me(user):
    return dict(user_id=user.id, display_name=user.display_name, account_status=user.account_status,
                status_reason=user.status_reason, platform_role=user.platform_role)


def teacher(user):
    data = me(user)
    del data["platform_role"]
    return dict(**data, email=user.email, version=user.version)


def cookie(response, name, value, seconds):
    response.set_cookie(name, value, max_age=seconds, httponly=True, samesite="lax",
                        secure=settings.app_env not in {"local", "test", "development"})


@router.get("/auth/csrf", response_model=CsrfToken)
def csrf(request: Request, response: Response):
    token = request.cookies.get("gradetap_csrf") or secrets.token_urlsafe(32)
    cookie(response, "gradetap_csrf", token, 43200)
    response.headers["Cache-Control"] = "no-store"
    return {"csrf_token": token}


def issue_verification(db, user):
    token = secrets.token_urlsafe(32)
    user.verification_hash = digest(token)
    user.verification_expires = now() + timedelta(minutes=30)
    db.commit()
    if settings.app_env in {"local", "test", "development"}:
        logging.getLogger("uvicorn.error").info("本地邮箱验证 %s /verify-email?token=%s", user.email, token)


@router.post("/auth/register", response_model=Message, dependencies=[Depends(limit_auth)], status_code=202)
def register(body: Register, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.scalar(select(Account.id).where(Account.email == email)) is None:
        user = Account(email=email, password_hash=hasher.hash(body.password),
                       display_name=body.display_name.strip(), note=body.note)
        db.add(user)
        try:
            issue_verification(db, user)
        except IntegrityError:
            db.rollback()
            if db.scalar(select(Account.id).where(Account.email == email)) is None:
                raise
    return {"message": "注册申请已提交，请验证邮箱"}


@router.post("/auth/resend-verification", response_model=Message, dependencies=[Depends(limit_auth)], status_code=202)
def resend(body: Email, db: Session = Depends(get_db)):
    user = db.scalar(select(Account).where(Account.email == body.email.lower(),
                                          Account.account_status == "pending_verification"))
    if user:
        issue_verification(db, user)
    return {"message": "如果该邮箱尚待验证，已重新生成验证链接"}


@router.post("/auth/verify-email", response_model=Message, dependencies=[Depends(limit_auth)])
def verify(body: Verification, db: Session = Depends(get_db)):
    user = db.scalar(select(Account).where(Account.verification_hash == digest(body.token),
                                           Account.verification_expires > now(),
                                           Account.account_status == "pending_verification"))
    if user is None:
        raise error(422, "verification_token_invalid", "验证链接无效或已过期")
    user.verification_hash = user.verification_expires = None
    user.account_status = "pending_approval"
    db.commit()
    return {"message": "邮箱验证成功，请登录查看审核进度"}


@router.post("/auth/login", response_model=Profile, dependencies=[Depends(limit_auth)])
def login(body: Login, request: Request, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(Account).where(Account.email == body.email.lower()))
    try:
        hasher.verify(user.password_hash if user else dummy_hash, body.password)
    except VerifyMismatchError:
        raise error(401, "invalid_credentials", "邮箱或密码错误")
    if user.account_status == "pending_verification":
        raise error(403, "email_verification_required", "请先验证邮箱")
    if user.account_status == "disabled":
        raise error(403, "account_disabled", "账号已停用", status_reason=user.status_reason)
    db.execute(delete(LoginSession).where(LoginSession.token_hash == digest(request.cookies.get("gradetap_session", ""))))
    token = secrets.token_urlsafe(32)
    db.add(LoginSession(token_hash=digest(token), user_id=user.id, expires_at=now()+timedelta(hours=12)))
    db.commit()
    cookie(response, "gradetap_session", token, 43200)
    response.delete_cookie("gradetap_csrf")
    return me(user)


@router.get("/auth/me", response_model=Profile)
def profile(user: Account = Depends(current_user)):
    return me(user)


@router.post("/auth/logout", status_code=204)
def logout(request: Request, db: Session = Depends(get_db)):
    db.execute(delete(LoginSession).where(LoginSession.token_hash == digest(request.cookies.get("gradetap_session", ""))))
    db.commit()
    response = Response(status_code=204)
    for name in ("gradetap_session", "gradetap_csrf"):
        response.delete_cookie(name)
    return response


@router.post("/auth/resubmit", response_model=Profile)
def resubmit(body: Resubmit, user: Account = Depends(current_user), db: Session = Depends(get_db)):
    if user.account_status != "rejected":
        raise error(409, "invalid_state", "仅已驳回申请可重提")
    user.note = body.note.strip()
    if body.display_name:
        user.display_name = body.display_name.strip()
    user.account_status = "pending_approval"
    user.status_reason = None
    db.commit()
    return me(user)


@router.get("/admin/teachers", response_model=list[Teacher], dependencies=[Depends(admin)])
def teachers(status: str | None = None, db: Session = Depends(get_db)):
    query = select(Account).where(Account.platform_role == "teacher").order_by(Account.id)
    if status:
        query = query.where(Account.account_status == status)
    return [teacher(u) for u in db.scalars(query)]


@router.post("/admin/teachers/{user_id}/actions", response_model=Teacher)
def change_status(user_id: int, body: Action, actor: Account = Depends(admin), db: Session = Depends(get_db)):
    user = db.get(Account, user_id)
    if user is None or user.platform_role != "teacher":
        raise error(404, "not_found", "教师不存在")
    previous = "active" if body.action == "disable" else "pending_approval"
    if user.version != body.expected_version or user.account_status != previous:
        raise error(409, "version_conflict", "状态已变更，请刷新")
    if body.action != "approve" and not body.reason.strip():
        raise error(422, "validation_error", "请填写原因")
    user.account_status = {"approve": "active", "disable": "disabled", "reject": "rejected"}[body.action]
    user.status_reason = None if body.action == "approve" else body.reason.strip()
    if body.action == "disable":
        db.execute(delete(LoginSession).where(LoginSession.user_id == user_id))
    db.add(AuditLog(actor_id=actor.id, action=body.action, target_type="account", target_id=user_id, detail=user.status_reason))
    db.commit()
    return teacher(user)
