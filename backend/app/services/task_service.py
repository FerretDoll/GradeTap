from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select

from app.db.models import GradingTask
from app.db.session import SessionLocal
from app.models.task import GradingTaskStatus
from app.schemas.task import GradingTaskCreate, GradingTaskRead


class TaskService:
    def create_task(self, payload: GradingTaskCreate) -> GradingTaskRead:
        with SessionLocal() as db:
            task = GradingTask(
                task_name=payload.task_name,
                course_name=payload.course_name,
                class_name=payload.class_name,
                status=GradingTaskStatus.CREATED,
                grading_instruction=payload.grading_instruction,
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            return self._to_read_schema(task)

    def list_tasks(self) -> list[GradingTaskRead]:
        with SessionLocal() as db:
            tasks = db.scalars(select(GradingTask).order_by(GradingTask.id.desc())).all()
            return [self._to_read_schema(task) for task in tasks]

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

    def _to_read_schema(self, task: GradingTask) -> GradingTaskRead:
        return GradingTaskRead(
            id=task.id,
            task_name=task.task_name,
            course_name=task.course_name,
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
