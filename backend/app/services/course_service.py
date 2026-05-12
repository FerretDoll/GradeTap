from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select

from app.db.models import Course
from app.db.session import SessionLocal
from app.schemas.course import CourseCreate, CourseRead, CourseUpdate


class CourseService:
    def create_course(self, payload: CourseCreate) -> CourseRead:
        with SessionLocal() as db:
            course = Course(
                course_name=payload.course_name,
                description=payload.description,
                assignment_count=0,
            )
            db.add(course)
            db.commit()
            db.refresh(course)
            return self._to_read_schema(course)

    def list_courses(self) -> list[CourseRead]:
        with SessionLocal() as db:
            courses = db.scalars(select(Course).order_by(Course.id.desc())).all()
            return [self._to_read_schema(course) for course in courses]

    def get_course(self, course_id: int) -> Optional[CourseRead]:
        with SessionLocal() as db:
            course = db.get(Course, course_id)
            if course is None:
                return None
            return self._to_read_schema(course)

    def update_course(self, course_id: int, payload: CourseUpdate) -> CourseRead:
        with SessionLocal() as db:
            course = db.get(Course, course_id)
            if course is None:
                raise HTTPException(status_code=404, detail="Course not found")
            update_data = payload.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(course, key, value)
            db.commit()
            db.refresh(course)
            return self._to_read_schema(course)

    def delete_course(self, course_id: int) -> None:
        with SessionLocal() as db:
            course = db.get(Course, course_id)
            if course is None:
                raise HTTPException(status_code=404, detail="Course not found")
            db.delete(course)
            db.commit()

    def _to_read_schema(self, course: Course) -> CourseRead:
        return CourseRead(
            id=course.id,
            course_name=course.course_name,
            description=course.description,
            assignment_count=course.assignment_count,
            created_at=self._ensure_datetime(course.created_at),
            updated_at=self._ensure_datetime(course.updated_at),
        )

    def _ensure_datetime(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


course_service = CourseService()
