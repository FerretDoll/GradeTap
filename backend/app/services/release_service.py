from base64 import b64encode
from sqlalchemy import select

from app.db.models import AuditLog, GradeRelease, GradingResult, GradingTask, Question, StudentSubmission
from app.models.grading import ReviewStatus
from app.services.access import error
from app.utils.excel_export import render_grades


def publish_grades(db, task_id, actor_id):
    db.get(GradingTask, task_id, with_for_update=True)
    students = db.scalars(select(StudentSubmission.id).where(StudentSubmission.task_id == task_id)).all()
    questions = db.scalars(select(Question.id).where(Question.task_id == task_id)).all()
    expected = {(student, question) for student in students for question in questions}
    results = db.scalars(select(GradingResult).where(GradingResult.task_id == task_id).with_for_update()).all()
    confirmed = {ReviewStatus.TEACHER_CONFIRMED, ReviewStatus.TEACHER_MODIFIED}
    if (not expected or len(results) != len(expected)
        or {(r.student_submission_id, r.question_id) for r in results} != expected
        or any(r.final_score is None or r.review_status not in confirmed for r in results)):
        raise error(409, "review_required", "请先确认全部单题成绩")
    item = GradeRelease(task_id=task_id, actor_id=actor_id,
                        workbook=b64encode(render_grades(db, task_id)).decode("ascii"))
    db.add(item)
    db.flush()
    db.add(AuditLog(task_id=task_id, actor_id=actor_id, target_type="release", target_id=item.id, action="release"))
    db.commit()
    return {"task_id": task_id, "release_id": item.id}
