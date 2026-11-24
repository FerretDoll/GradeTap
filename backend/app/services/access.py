from datetime import datetime, timezone
from hashlib import sha256
from secrets import compare_digest

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Account, ClassGroup, Course, CourseAssignment, GradingTask, LoginSession, Offering, StudentSubmission, StudentAnswer
from app.db.session import get_db


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def digest(token):
    return sha256(token.encode()).hexdigest()


def error(status, code, message, **extra):
    return HTTPException(status, {"code": code, "message": message, **extra})


def csrf_guard(request: Request):
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    cookie = request.cookies.get("gradetap_csrf", "")
    header = request.headers.get("X-CSRF-Token", "")
    if not cookie or not compare_digest(cookie.encode(), header.encode()):
        raise error(403, "csrf_invalid", "表单令牌已失效")


def session_account(db, token):
    return db.scalar(select(Account).join(LoginSession).where(
        LoginSession.token_hash == digest(token),
        LoginSession.expires_at > now(), Account.account_status != "disabled",
    ))


def current_user(request: Request, db: Session = Depends(get_db)) -> Account:
    user = session_account(db, request.cookies.get("gradetap_session", ""))
    if user is None:
        raise error(401, "session_required", "请先登录")
    return user


def active_user(user: Account = Depends(current_user)) -> Account:
    if user.account_status != "active":
        raise error(403, "approval_required", "账号尚未启用")
    return user


def admin(user: Account = Depends(active_user)) -> Account:
    if user.platform_role != "admin":
        raise error(403, "permission_denied", "需要管理员权限")
    return user


def workspace_access(request: Request, user: Account = Depends(active_user), db: Session = Depends(get_db)):
    params = request.path_params
    if "task_id" in params:
        query = select(GradingTask.id).join(Offering).where(
            GradingTask.id == params["task_id"], Offering.owner_id == user.id)
    elif "course_id" in params:
        query = select(Course.id).where(Course.id == params["course_id"], Course.owner_id == user.id)
    elif "class_group_id" in params:
        query = select(ClassGroup.id).where(ClassGroup.id == params["class_group_id"], ClassGroup.owner_id == user.id)
    else:
        return
    if db.scalar(query) is None:
        raise error(404, "not_found", "记录不存在或无权访问")
    if "assignment_id" in params:
        query = select(CourseAssignment.id).where(CourseAssignment.course_id == params["course_id"],
                                                CourseAssignment.id == params["assignment_id"])
    elif "submission_id" in params or "student_submission_id" in params:
        query = select(StudentSubmission.id).where(StudentSubmission.task_id == params["task_id"],
                        StudentSubmission.id == params.get("submission_id", params.get("student_submission_id")))
    elif "answer_id" in params:
        query = select(StudentAnswer.id).where(StudentAnswer.task_id == params["task_id"],
                                             StudentAnswer.id == params["answer_id"])
    else:
        return
    if db.scalar(query) is None:
        raise error(404, "not_found", "记录不存在或无权访问")
