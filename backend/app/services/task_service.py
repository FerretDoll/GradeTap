from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import delete, or_, select, update

from app.services.access import error, now
from app.core.config import settings
from app.db.models import (
    GradeRelease, EvaluationVersion, Offering, Course, CourseAssignment, ClassGroup,
    AdaptiveGradingRule,
    AnswerEvidence,
    AnswerGroup,
    AnswerGroupMember,
    AuditLog,
    GradingDeduction,
    GradingReflection,
    GradingResult,
    GradingTask,
    PlagiarismCheck,
    PlagiarismMatch,
    Question,
    QuestionRubric,
    StudentAnswer,
    StudentPlagiarismSummary,
    StudentSubmission,
    TeacherRevision,
    UploadedFile,
)
from app.db.session import SessionLocal
from app.models.task import GradingTaskStatus
from app.schemas.task import GradingTaskCreate, GradingTaskRead


class TaskService:
    def create_task(self, payload: GradingTaskCreate, owner_id: int) -> GradingTaskRead:
        with SessionLocal() as db:
            offering = self._offering(db, payload.offering_id, owner_id)
            assignment = db.get(CourseAssignment, payload.assignment_id) if payload.assignment_id else None
            if payload.assignment_id and (assignment is None or assignment.course_id != offering.course_id):
                raise error(404, "not_found", "课程作业不存在")
            task = GradingTask(
                offering_id=offering.id, course_id=offering.course_id,
                class_group_id=offering.class_group_id, assignment_id=payload.assignment_id,
                task_name=payload.task_name,
                course_name=db.get(Course, offering.course_id).course_name,
                assignment_name=assignment.assignment_name if assignment else payload.assignment_name,
                class_name=db.get(ClassGroup, offering.class_group_id).class_name,
                status=GradingTaskStatus.CREATED,
                grading_instruction=payload.grading_instruction,
            )
            db.add(task)
            db.flush()
            db.add(AuditLog(task_id=task.id, target_id=task.id, actor_id=owner_id, action="create_task", target_type="task"))
            db.commit()
            db.refresh(task)
            return self._to_read_schema(task)

    def list_tasks(self, owner_id: int, offering_id: int | None, include_archived: bool) -> list[GradingTaskRead]:
        with SessionLocal() as db:
            query = select(GradingTask).join(Offering).where(Offering.owner_id == owner_id)
            if offering_id is not None:
                self._offering(db, offering_id, owner_id)
                query = query.where(GradingTask.offering_id == offering_id)
            if not include_archived:
                query = query.where(GradingTask.archived_at.is_(None))
            tasks = db.scalars(query.order_by(GradingTask.id.desc())).all()
            return [self._to_read_schema(task) for task in tasks]

    def _offering(self, db, offering_id, owner_id):
        offering = db.get(Offering, offering_id)
        if offering is None or offering.owner_id != owner_id:
            raise error(404, "not_found", "授课班不存在")
        return offering

    def archive(self, task_id, owner_id):
        with SessionLocal() as db:
            task = db.get(GradingTask, task_id)
            if task.archived_at is None:
                task.archived_at = now()
                db.add(AuditLog(task_id=task_id, target_id=task_id, actor_id=owner_id, action="archive_task", target_type="task"))
                db.commit()
            return self._to_read_schema(task)

    def get_task(self, task_id: int) -> Optional[GradingTaskRead]:
        with SessionLocal() as db:
            task = db.get(GradingTask, task_id)
            if task is None:
                return None
            return self._to_read_schema(task)

    def ensure_task_exists(self, task_id: int) -> GradingTaskRead:
        task = self.get_task(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return task

    def delete_task(self, task_id: int, actor_id: int) -> None:
        with SessionLocal() as db:
            if db.get(GradingTask, task_id, with_for_update=True) is None:
                raise HTTPException(status_code=404, detail="Task not found")

            protected = [
                select(TeacherRevision.id).where(TeacherRevision.task_id == task_id),
                select(GradeRelease.id).where(GradeRelease.task_id == task_id),
                select(EvaluationVersion.id).where(EvaluationVersion.task_id == task_id, EvaluationVersion.has_review),
            ]
            if any(db.scalar(query.limit(1)) for query in protected):
                raise error(409, "task_delete_protected", "已有师评，请归档任务")

            files = db.scalars(select(UploadedFile).where(UploadedFile.task_id == task_id)).all()
            storage_paths = [f.storage_path for f in files if f.storage_path]

            result_ids = select(GradingResult.id).where(GradingResult.task_id == task_id)
            db.execute(delete(GradingDeduction).where(GradingDeduction.grading_result_id.in_(result_ids)))
            db.execute(
                delete(GradingReflection).where(
                    or_(
                        GradingReflection.grading_result_id.in_(result_ids),
                        GradingReflection.task_id == task_id,
                    ),
                ),
            )
            db.execute(delete(GradingResult).where(GradingResult.task_id == task_id))

            db.execute(delete(AnswerEvidence).where(AnswerEvidence.task_id == task_id))

            group_ids = select(AnswerGroup.id).where(AnswerGroup.task_id == task_id)
            db.execute(delete(AnswerGroupMember).where(AnswerGroupMember.answer_group_id.in_(group_ids)))
            db.execute(delete(AnswerGroup).where(AnswerGroup.task_id == task_id))

            db.execute(delete(StudentAnswer).where(StudentAnswer.task_id == task_id))
            db.execute(delete(PlagiarismMatch).where(PlagiarismMatch.task_id == task_id))
            db.execute(delete(StudentPlagiarismSummary).where(StudentPlagiarismSummary.task_id == task_id))
            db.execute(delete(PlagiarismCheck).where(PlagiarismCheck.task_id == task_id))
            db.execute(delete(StudentSubmission).where(StudentSubmission.task_id == task_id))

            question_ids = select(Question.id).where(Question.task_id == task_id)
            db.execute(
                delete(AdaptiveGradingRule).where(
                    or_(
                        AdaptiveGradingRule.task_id == task_id,
                        AdaptiveGradingRule.question_id.in_(question_ids),
                    ),
                ),
            )
            db.execute(delete(QuestionRubric).where(QuestionRubric.question_id.in_(question_ids)))
            db.execute(delete(Question).where(Question.task_id == task_id))

            db.execute(delete(UploadedFile).where(UploadedFile.task_id == task_id))
            db.execute(update(AuditLog).where(AuditLog.task_id == task_id).values(task_id=None, deleted_task_id=task_id))
            db.add(AuditLog(deleted_task_id=task_id, target_id=task_id, actor_id=actor_id, target_type="task", action="delete_task"))
            db.execute(delete(EvaluationVersion).where(EvaluationVersion.task_id == task_id))
            db.execute(delete(GradingTask).where(GradingTask.id == task_id))
            db.commit()

        for path in storage_paths:
            try:
                Path(path).unlink(missing_ok=True)
            except OSError:
                pass
        task_dir = Path(settings.local_storage_root).expanduser().resolve() / "tasks" / str(task_id)
        shutil.rmtree(task_dir, ignore_errors=True)

    def _to_read_schema(self, task: GradingTask) -> GradingTaskRead:
        return GradingTaskRead(
            id=task.id, offering_id=task.offering_id, course_id=task.course_id,
            assignment_id=task.assignment_id, class_group_id=task.class_group_id,
            submission_round=task.submission_round, is_archived=task.archived_at is not None, archived_at=task.archived_at,
            task_name=task.task_name,
            course_name=task.course_name,
            assignment_name=task.assignment_name or "",
            class_name=task.class_name,
            status=task.status,
            grading_instruction=task.grading_instruction,
            created_at=self._ensure_datetime(task.created_at),
            updated_at=self._ensure_datetime(task.updated_at),
        )

    def _ensure_datetime(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value



task_service = TaskService()
