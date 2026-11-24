from fastapi.encoders import jsonable_encoder
from sqlalchemy import select

from app.db.models import (
    AnswerEvidence, EvaluationVersion, GradingDeduction, GradingReflection, GradingResult,
    GradingTask, Question, QuestionRubric, StudentAnswer, StudentSubmission, TeacherRevision,
    UploadedFile, PlagiarismCheck, PlagiarismMatch, StudentPlagiarismSummary,
)


def preserve_evaluation(db, task_id, reason):
    """Keep a consistent historical view before replacing current evaluation rows."""
    task = db.get(GradingTask, task_id)
    questions = select(Question.id).where(Question.task_id == task_id)
    results = select(GradingResult.id).where(GradingResult.task_id == task_id)
    queries = [(model, model.task_id == task_id) for model in (
        Question, StudentSubmission, StudentAnswer, AnswerEvidence, GradingResult,
        GradingReflection, TeacherRevision, UploadedFile, PlagiarismCheck, PlagiarismMatch, StudentPlagiarismSummary,
    )]
    queries.extend([(QuestionRubric, QuestionRubric.question_id.in_(questions)),
                    (GradingDeduction, GradingDeduction.grading_result_id.in_(results))])
    if not db.scalar(select(StudentSubmission.id).where(StudentSubmission.task_id == task_id).limit(1)):
        return
    data = {}
    for model, condition in queries:
        rows = db.scalars(select(model).where(condition).order_by(model.id))
        data[model.__tablename__] = [jsonable_encoder({
            column.key: getattr(row, column.key) for column in model.__table__.columns
        }) for row in rows]
    db.add(EvaluationVersion(task_id=task_id, reason=reason, submission_round=task.submission_round,
                             has_review=bool(data["teacher_revision"]), snapshot=data))
