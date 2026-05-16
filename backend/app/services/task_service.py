from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import delete, inspect, or_, select, text

from app.core.config import settings
from app.db.models import (
    AdaptiveGradingRule,
    AnswerEvidence,
    AnswerGroup,
    AnswerGroupMember,
    AuditLog,
    GradingDeduction,
    GradingReflection,
    GradingResult,
    GradingTask,
    Question,
    QuestionRubric,
    StudentAnswer,
    StudentSubmission,
    TeacherRevision,
    UploadedFile,
)
from app.db.session import SessionLocal
from app.models.task import GradingTaskStatus
from app.schemas.task import GradingTaskCreate, GradingTaskRead


class TaskService:
    def create_task(self, payload: GradingTaskCreate) -> GradingTaskRead:
        self._ensure_task_schema()
        with SessionLocal() as db:
            task = GradingTask(
                task_name=payload.task_name,
                course_name=payload.course_name,
                assignment_name=payload.assignment_name,
                class_name=payload.class_name,
                status=GradingTaskStatus.CREATED,
                grading_instruction=payload.grading_instruction,
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            return self._to_read_schema(task)

    def list_tasks(self) -> list[GradingTaskRead]:
        self._ensure_task_schema()
        with SessionLocal() as db:
            tasks = db.scalars(select(GradingTask).order_by(GradingTask.id.desc())).all()
            return [self._to_read_schema(task) for task in tasks]

    def get_task(self, task_id: int) -> Optional[GradingTaskRead]:
        self._ensure_task_schema()
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

    def delete_task(self, task_id: int) -> None:
        with SessionLocal() as db:
            if db.get(GradingTask, task_id) is None:
                raise HTTPException(status_code=404, detail="Task not found")

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
            db.execute(
                delete(TeacherRevision).where(
                    or_(
                        TeacherRevision.grading_result_id.in_(result_ids),
                        TeacherRevision.task_id == task_id,
                    ),
                ),
            )
            db.execute(delete(GradingResult).where(GradingResult.task_id == task_id))

            db.execute(delete(AnswerEvidence).where(AnswerEvidence.task_id == task_id))

            group_ids = select(AnswerGroup.id).where(AnswerGroup.task_id == task_id)
            db.execute(delete(AnswerGroupMember).where(AnswerGroupMember.answer_group_id.in_(group_ids)))
            db.execute(delete(AnswerGroup).where(AnswerGroup.task_id == task_id))

            db.execute(delete(StudentAnswer).where(StudentAnswer.task_id == task_id))
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
            db.execute(delete(AuditLog).where(AuditLog.task_id == task_id))
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
            id=task.id,
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

    def _ensure_task_schema(self) -> None:
        table_name = GradingTask.__tablename__
        with SessionLocal() as db:
            existing_columns = {column["name"] for column in inspect(db.bind).get_columns(table_name)}
            if "assignment_name" not in existing_columns:
                db.execute(text(f"ALTER TABLE {table_name} ADD COLUMN assignment_name VARCHAR(255) NOT NULL DEFAULT ''"))
                db.commit()


task_service = TaskService()
