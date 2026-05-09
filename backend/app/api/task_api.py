from fastapi import APIRouter, HTTPException, status

from app.schemas.task import GradingTaskCreate, GradingTaskRead
from app.services.task_service import task_service

router = APIRouter()


@router.post("", response_model=GradingTaskRead, status_code=status.HTTP_201_CREATED)
def create_task(payload: GradingTaskCreate) -> GradingTaskRead:
    return task_service.create_task(payload)


@router.get("", response_model=list[GradingTaskRead])
def list_tasks() -> list[GradingTaskRead]:
    return task_service.list_tasks()


@router.get("/{task_id}", response_model=GradingTaskRead)
def get_task(task_id: int) -> GradingTaskRead:
    task = task_service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/{task_id}/parse-files")
def parse_files(task_id: int) -> dict[str, str | int]:
    task_service.ensure_task_exists(task_id)
    return {"task_id": task_id, "status": "queued", "stage": "parse_files"}


@router.post("/{task_id}/set-score")
def set_score(task_id: int) -> dict[str, str | int]:
    task_service.ensure_task_exists(task_id)
    return {"task_id": task_id, "status": "queued", "stage": "set_score"}


@router.post("/{task_id}/prepare-students")
def prepare_students(task_id: int) -> dict[str, str | int]:
    task_service.ensure_task_exists(task_id)
    return {"task_id": task_id, "status": "queued", "stage": "prepare_students"}


@router.post("/{task_id}/extract-answers")
def extract_answers(task_id: int) -> dict[str, str | int]:
    task_service.ensure_task_exists(task_id)
    return {"task_id": task_id, "status": "queued", "stage": "extract_answers"}


@router.post("/{task_id}/grade-by-question")
def grade_by_question(task_id: int) -> dict[str, str | int]:
    task_service.ensure_task_exists(task_id)
    return {"task_id": task_id, "status": "queued", "stage": "grade_by_question"}
