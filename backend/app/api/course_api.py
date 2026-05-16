from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status
from fastapi.responses import StreamingResponse

from app.models.file import FileRole
from app.schemas.course import (
    CourseAssignmentCreate,
    CourseAssignmentFileRead,
    CourseAssignmentQuestionsUpdate,
    CourseAssignmentRead,
    CourseAssignmentUpdate,
    CourseCreate,
    CourseRead,
    CourseUpdate,
)
from app.services.course_service import course_service
from app.services.progress_event_service import progress_event_service

router = APIRouter()


@router.post("", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
def create_course(payload: CourseCreate) -> CourseRead:
    return course_service.create_course(payload)


@router.get("", response_model=list[CourseRead])
def list_courses() -> list[CourseRead]:
    return course_service.list_courses()


@router.get("/{course_id}", response_model=CourseRead)
def get_course(course_id: int) -> CourseRead:
    course = course_service.get_course(course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@router.put("/{course_id}", response_model=CourseRead)
def update_course(course_id: int, payload: CourseUpdate) -> CourseRead:
    return course_service.update_course(course_id, payload)


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(course_id: int) -> Response:
    course_service.delete_course(course_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{course_id}/assignments",
    response_model=CourseAssignmentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_assignment(course_id: int, payload: CourseAssignmentCreate) -> CourseAssignmentRead:
    return course_service.create_assignment(course_id, payload)


@router.get("/{course_id}/assignments", response_model=list[CourseAssignmentRead])
def list_assignments(course_id: int) -> list[CourseAssignmentRead]:
    return course_service.list_assignments(course_id)


@router.put("/{course_id}/assignments/{assignment_id}", response_model=CourseAssignmentRead)
def update_assignment(
    course_id: int,
    assignment_id: int,
    payload: CourseAssignmentUpdate,
) -> CourseAssignmentRead:
    return course_service.update_assignment(course_id, assignment_id, payload)


@router.delete("/{course_id}/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(course_id: int, assignment_id: int) -> Response:
    course_service.delete_assignment(course_id, assignment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{course_id}/assignments/{assignment_id}/files",
    response_model=list[CourseAssignmentFileRead],
)
def list_assignment_files(course_id: int, assignment_id: int) -> list[CourseAssignmentFileRead]:
    return course_service.list_assignment_files(course_id, assignment_id)


@router.post(
    "/{course_id}/assignments/{assignment_id}/files",
    response_model=CourseAssignmentFileRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_assignment_file(
    course_id: int,
    assignment_id: int,
    file_role: FileRole,
    file: UploadFile = File(...),
) -> CourseAssignmentFileRead:
    return await course_service.upload_assignment_file(course_id, assignment_id, file_role, file)


@router.delete(
    "/{course_id}/assignments/{assignment_id}/files/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_assignment_file(course_id: int, assignment_id: int, file_id: int) -> Response:
    course_service.delete_assignment_file(course_id, assignment_id, file_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{course_id}/assignments/{assignment_id}/parse-files")
def parse_assignment_files(course_id: int, assignment_id: int) -> dict:
    return course_service.parse_assignment_files(course_id, assignment_id)


@router.post("/{course_id}/assignments/{assignment_id}/analyze-questions")
def analyze_assignment_questions(course_id: int, assignment_id: int) -> dict:
    return course_service.analyze_assignment_questions(course_id, assignment_id)


@router.post("/{course_id}/assignments/{assignment_id}/build-rubrics")
def build_assignment_rubrics(course_id: int, assignment_id: int) -> dict:
    return course_service.build_assignment_rubrics(course_id, assignment_id)


@router.get("/{course_id}/assignments/{assignment_id}/events")
def stream_assignment_events(course_id: int, assignment_id: int) -> StreamingResponse:
    return StreamingResponse(
        progress_event_service.stream(f"assignment:{course_id}:{assignment_id}"),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{course_id}/assignments/{assignment_id}/questions")
def list_assignment_questions(course_id: int, assignment_id: int) -> dict:
    return course_service.list_assignment_questions(course_id, assignment_id)


@router.put("/{course_id}/assignments/{assignment_id}/questions")
def confirm_assignment_rubrics(
    course_id: int,
    assignment_id: int,
    payload: CourseAssignmentQuestionsUpdate,
) -> dict:
    return course_service.confirm_assignment_rubrics(course_id, assignment_id, payload)
