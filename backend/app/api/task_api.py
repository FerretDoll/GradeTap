from __future__ import annotations

from typing import Union

from urllib.parse import quote

from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status
from fastapi.responses import StreamingResponse

from app.models.file import FileRole
from app.schemas.file import TaskFileUploadResponse, UploadedFileRead
from app.schemas.grading import (
    GradeByQuestionRequest,
    GradeByQuestionResponse,
    GradeByQuestionStudentStartResponse,
    GradingResultRead,
    TeacherReviewUpdate,
    TeacherRevisionRead,
)
from app.schemas.plagiarism import (
    PlagiarismCheckRead,
    PlagiarismRunResponse,
    PlagiarismStudentDetailRead,
    PlagiarismStudentsResponse,
)
from app.schemas.question import QuestionRead
from app.schemas.answer import (
    AnswerExtractionSnapshot,
    AnswerExtractionStartResponse,
    AnswerExtractionStudentStartResponse,
    StudentAnswerRead,
    StudentPrepareResponse,
)
from app.schemas.evidence import (
    EvidenceExtractionSnapshot,
    EvidenceExtractionStudentStartResponse,
)
from app.schemas.export import ExportResultsRequest
from app.schemas.task import GradingTaskCreate, GradingTaskRead
from app.services.file_parse_service import file_parse_service
from app.services.file_service import file_service
from app.services.grading_service import grading_service
from app.services.answer_extractor_service import answer_extractor_service
from app.services.evidence_extractor_service import evidence_extractor_service
from app.services.progress_event_service import progress_event_service
from app.services.plagiarism_check_service import plagiarism_check_service
from app.services.question_analyzer_service import question_analyzer_service
from app.services.student_prepare_service import student_prepare_service
from app.services.task_service import task_service
from app.services.teacher_review_service import teacher_review_service
from app.utils.excel_export import export_grades_to_excel

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


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int) -> Response:
    task_service.delete_task(task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{task_id}/files", response_model=list[UploadedFileRead])
def list_task_files(task_id: int) -> list[UploadedFileRead]:
    return file_service.list_task_files(task_id)


@router.post("/{task_id}/files", response_model=TaskFileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_task_file(
    task_id: int,
    file_role: FileRole,
    file: UploadFile = File(...),
) -> TaskFileUploadResponse:
    return await file_service.upload_task_file(task_id, file_role, file)


@router.delete("/{task_id}/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task_file(task_id: int, file_id: int) -> Response:
    file_service.delete_task_file(task_id, file_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{task_id}/parse-files")
def parse_files(task_id: int) -> dict:
    return file_parse_service.parse_task_files(task_id)


@router.post("/{task_id}/analyze-questions")
def analyze_questions(task_id: int) -> dict:
    task_service.ensure_task_exists(task_id)
    return question_analyzer_service.analyze_task_questions(task_id)


@router.get("/{task_id}/questions", response_model=list[QuestionRead])
def list_task_questions(task_id: int) -> list[QuestionRead]:
    return question_analyzer_service.list_task_questions(task_id)


@router.get("/{task_id}/events")
def stream_task_events(task_id: int) -> StreamingResponse:
    task_service.ensure_task_exists(task_id)
    return StreamingResponse(
        progress_event_service.stream(f"task:{task_id}"),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{task_id}/build-rubrics")
def build_rubrics(task_id: int) -> dict[str, Union[str, int]]:
    task_service.ensure_task_exists(task_id)
    return {"task_id": task_id, "status": "queued", "stage": "build_rubrics"}


@router.post("/{task_id}/prepare-students", response_model=StudentPrepareResponse)
def prepare_students(task_id: int) -> StudentPrepareResponse:
    task_service.ensure_task_exists(task_id)
    return student_prepare_service.prepare_students(task_id)


@router.post("/{task_id}/plagiarism-check", response_model=PlagiarismRunResponse)
def run_plagiarism_check(task_id: int) -> PlagiarismRunResponse:
    task_service.ensure_task_exists(task_id)
    return plagiarism_check_service.run_check(task_id)


@router.get("/{task_id}/plagiarism-checks/latest", response_model=PlagiarismCheckRead | None)
def get_latest_plagiarism_check(task_id: int) -> PlagiarismCheckRead | None:
    task_service.ensure_task_exists(task_id)
    return plagiarism_check_service.get_latest_check(task_id)


@router.get("/{task_id}/plagiarism-students", response_model=PlagiarismStudentsResponse)
def list_plagiarism_students(task_id: int) -> PlagiarismStudentsResponse:
    task_service.ensure_task_exists(task_id)
    return plagiarism_check_service.list_student_summaries(task_id)


@router.get("/{task_id}/plagiarism-students/{student_submission_id}", response_model=PlagiarismStudentDetailRead)
def get_plagiarism_student_detail(task_id: int, student_submission_id: int) -> PlagiarismStudentDetailRead:
    task_service.ensure_task_exists(task_id)
    return plagiarism_check_service.get_student_detail(task_id, student_submission_id)


@router.get("/{task_id}/extract-answers", response_model=AnswerExtractionSnapshot)
def get_answer_extraction(task_id: int) -> AnswerExtractionSnapshot:
    task_service.ensure_task_exists(task_id)
    return answer_extractor_service.get_snapshot(task_id)


@router.post("/{task_id}/extract-answers", response_model=AnswerExtractionStartResponse)
def extract_answers(task_id: int, max_workers: int = 3, force: bool = False) -> AnswerExtractionStartResponse:
    task_service.ensure_task_exists(task_id)
    return answer_extractor_service.start_extract_answers(task_id, max_workers=max_workers, force=force)


@router.post(
    "/{task_id}/extract-answers/{submission_id}",
    response_model=AnswerExtractionStudentStartResponse,
)
def extract_answers_for_submission(task_id: int, submission_id: int) -> AnswerExtractionStudentStartResponse:
    task_service.ensure_task_exists(task_id)
    return answer_extractor_service.start_extract_answers_for_submission(task_id, submission_id)


@router.post("/{task_id}/student-answers/{answer_id}/confirm", response_model=StudentAnswerRead)
def confirm_student_answer(task_id: int, answer_id: int) -> StudentAnswerRead:
    task_service.ensure_task_exists(task_id)
    return answer_extractor_service.confirm_student_answer(task_id, answer_id)


@router.get("/{task_id}/extract-evidence", response_model=EvidenceExtractionSnapshot)
def get_evidence_extraction(task_id: int) -> EvidenceExtractionSnapshot:
    task_service.ensure_task_exists(task_id)
    return evidence_extractor_service.get_snapshot(task_id)


@router.post("/{task_id}/extract-evidence")
def extract_evidence(
    task_id: int,
    max_workers: int = 3,
    force: bool = False,
) -> dict[str, Union[str, int, bool]]:
    task_service.ensure_task_exists(task_id)
    return evidence_extractor_service.start_extract_evidence(
        task_id,
        max_workers=max_workers,
        force=force,
    )


@router.post(
    "/{task_id}/extract-evidence/{submission_id}",
    response_model=EvidenceExtractionStudentStartResponse,
)
def extract_evidence_for_submission(
    task_id: int,
    submission_id: int,
) -> EvidenceExtractionStudentStartResponse:
    task_service.ensure_task_exists(task_id)
    return evidence_extractor_service.start_extract_evidence_for_submission(task_id, submission_id)


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
    saved_results = grading_service.save_grading_results(task_id, grading_results)
    return GradeByQuestionResponse(
        task_id=task_id,
        question_id=payload.question.id,
        grading_results=saved_results,
    )


@router.get("/{task_id}/grade-by-question")
def get_grading_progress(task_id: int) -> dict:
    task_service.ensure_task_exists(task_id)
    return grading_service.get_grading_snapshot(task_id)


@router.post("/{task_id}/grade-by-question/start")
def start_grade_by_question(
    task_id: int,
    max_workers: int = 2,
    force: bool = False,
) -> dict[str, Union[str, int, bool]]:
    task_service.ensure_task_exists(task_id)
    return grading_service.start_grade_task(
        task_id=task_id,
        max_workers=max_workers,
        force=force,
    )


@router.post(
    "/{task_id}/grade-by-question/{submission_id}",
    response_model=GradeByQuestionStudentStartResponse,
)
def start_grade_by_question_for_submission(
    task_id: int,
    submission_id: int,
) -> GradeByQuestionStudentStartResponse:
    task_service.ensure_task_exists(task_id)
    return grading_service.start_grade_task_for_submission(task_id, submission_id)


@router.get("/{task_id}/grading-results", response_model=list[GradingResultRead])
def list_grading_results(task_id: int) -> list[GradingResultRead]:
    task_service.ensure_task_exists(task_id)
    return grading_service.list_grading_results(task_id)


@router.get("/{task_id}/teacher-revisions", response_model=list[TeacherRevisionRead])
def list_teacher_revisions(task_id: int) -> list[TeacherRevisionRead]:
    task_service.ensure_task_exists(task_id)
    return teacher_review_service.list_revisions(task_id)


@router.put("/{task_id}/grading-results/{result_id}/review", response_model=TeacherRevisionRead)
def review_grading_result(
    task_id: int,
    result_id: int,
    payload: TeacherReviewUpdate,
) -> TeacherRevisionRead:
    task_service.ensure_task_exists(task_id)
    try:
        return teacher_review_service.save_review(
            task_id=task_id,
            grading_result_id=result_id,
            final_score=payload.final_score,
            final_comment=payload.final_comment,
            revision_reason=payload.revision_reason,
            review_status=payload.review_status,
            teacher_id=payload.teacher_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{task_id}/reflect-grading")
def reflect_grading(task_id: int) -> dict[str, Union[str, int]]:
    task_service.ensure_task_exists(task_id)
    return {"task_id": task_id, "status": "queued", "stage": "reflect_grading"}


@router.post("/{task_id}/route-review")
def route_review(task_id: int) -> dict[str, Union[str, int]]:
    task_service.ensure_task_exists(task_id)
    return {"task_id": task_id, "status": "queued", "stage": "route_review"}


@router.post("/{task_id}/export-results")
def export_results(task_id: int, payload: ExportResultsRequest | None = None) -> Response:
    task_service.ensure_task_exists(task_id)
    try:
        content = export_grades_to_excel(task_id, payload.teacher_revisions if payload else [])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    filename = f"gradetap-task-{task_id}-results.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
        },
    )
