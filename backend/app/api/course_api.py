from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.schemas.course import CourseCreate, CourseRead, CourseUpdate
from app.services.course_service import course_service

router = APIRouter()


@router.post("", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
def create_course(payload: CourseCreate) -> CourseRead:
    return course_service.create_course(payload)


@router.get("", response_model=list[CourseRead])
def list_courses() -> list[CourseRead]:
    return course_service.list_courses()


@router.put("/{course_id}", response_model=CourseRead)
def update_course(course_id: int, payload: CourseUpdate) -> CourseRead:
    return course_service.update_course(course_id, payload)


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(course_id: int) -> Response:
    course_service.delete_course(course_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
