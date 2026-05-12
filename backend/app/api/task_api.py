from __future__ import annotations

from typing import Union

from fastapi import APIRouter, HTTPException, status

from app.schemas.grading import GradeByQuestionRequest, GradeByQuestionResponse
from app.schemas.task import GradingTaskCreate, GradingTaskRead
from app.services.grading_service import grading_service
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
def parse_files(task_id: int) -> dict[str, Union[str, int]]:
    task_service.ensure_task_exists(task_id)
    return {"task_id": task_id, "status": "queued", "stage": "parse_files"}


@router.post("/{task_id}/analyze-questions")
def analyze_questions(task_id: int) -> dict[str, Union[str, int]]:
    task_service.ensure_task_exists(task_id)
    return {"task_id": task_id, "status": "queued", "stage": "analyze_questions"}


@router.post("/{task_id}/build-rubrics")
def build_rubrics(task_id: int) -> dict[str, Union[str, int]]:
    task_service.ensure_task_exists(task_id)
    return {"task_id": task_id, "status": "queued", "stage": "build_rubrics"}


@router.post("/{task_id}/prepare-students")
def prepare_students(task_id: int) -> dict[str, Union[str, int]]:
    task_service.ensure_task_exists(task_id)
    return {"task_id": task_id, "status": "queued", "stage": "prepare_students"}


@router.post("/{task_id}/extract-answers")
def extract_answers(task_id: int) -> dict[str, Union[str, int]]:
    task_service.ensure_task_exists(task_id)
    return {"task_id": task_id, "status": "queued", "stage": "extract_answers"}


@router.post("/{task_id}/extract-evidence")
def extract_evidence(task_id: int) -> dict[str, Union[str, int]]:
    task_service.ensure_task_exists(task_id)
    return {"task_id": task_id, "status": "queued", "stage": "extract_evidence"}


@router.post("/{task_id}/grade-by-question", response_model=GradeByQuestionResponse)
def grade_by_question(task_id: int, payload: GradeByQuestionRequest) -> GradeByQuestionResponse:
    task_service.ensure_task_exists(task_id)
    try:
        grading_results = grading_service.grade_by_question(
            task_id=task_id,
            question=payload.question,
            rubrics=payload.rubrics,
            student_answers=payload.student_answers,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return GradeByQuestionResponse(
        task_id=task_id,
        question_id=payload.question.id,
        grading_results=grading_results,
    )


@router.post("/{task_id}/reflect-grading")
def reflect_grading(task_id: int) -> dict[str, Union[str, int]]:
    task_service.ensure_task_exists(task_id)
    return {"task_id": task_id, "status": "queued", "stage": "reflect_grading"}


@router.post("/{task_id}/route-review")
def route_review(task_id: int) -> dict[str, Union[str, int]]:
    task_service.ensure_task_exists(task_id)
    return {"task_id": task_id, "status": "queued", "stage": "route_review"}


@router.post("/{task_id}/export-results")
def export_results(task_id: int) -> dict[str, Union[str, int]]:
    task_service.ensure_task_exists(task_id)
    return {"task_id": task_id, "status": "queued", "stage": "export_results"}
