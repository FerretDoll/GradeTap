from datetime import datetime, timezone

from fastapi import HTTPException

from app.models.task import GradingTaskStatus
from app.schemas.task import GradingTaskCreate, GradingTaskRead


class TaskService:
    def __init__(self) -> None:
        self._tasks: dict[int, GradingTaskRead] = {}
        self._next_id = 1

    def create_task(self, payload: GradingTaskCreate) -> GradingTaskRead:
        now = datetime.now(timezone.utc)
        task = GradingTaskRead(
            id=self._next_id,
            task_name=payload.task_name,
            course_name=payload.course_name,
            class_name=payload.class_name,
            status=GradingTaskStatus.CREATED,
            grading_instruction=payload.grading_instruction,
            created_at=now,
            updated_at=now,
        )
        self._tasks[task.id] = task
        self._next_id += 1
        return task

    def list_tasks(self) -> list[GradingTaskRead]:
        return sorted(self._tasks.values(), key=lambda task: task.id, reverse=True)

    def get_task(self, task_id: int) -> GradingTaskRead | None:
        return self._tasks.get(task_id)

    def ensure_task_exists(self, task_id: int) -> GradingTaskRead:
        task = self.get_task(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return task


task_service = TaskService()
