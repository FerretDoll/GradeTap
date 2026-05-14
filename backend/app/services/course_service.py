from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy import func, select

from app.core.config import settings
from app.db.models import Course, CourseAssignment, CourseAssignmentFile
from app.db.session import SessionLocal
from app.models.file import FileRole
from app.schemas.course import (
    CourseAssignmentCreate,
    CourseAssignmentFileRead,
    CourseAssignmentRead,
    CourseAssignmentUpdate,
    CourseCreate,
    CourseRead,
    CourseUpdate,
)
from app.services.file_parse_service import parse_document_text


ASSIGNMENT_FILE_ROLES = {FileRole.REQUIREMENT, FileRole.REFERENCE_ANSWER}


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
            files = db.scalars(
                select(CourseAssignmentFile)
                .join(CourseAssignment)
                .where(CourseAssignment.course_id == course_id),
            ).all()
            for file in files:
                self._delete_storage_file(file.storage_path)
            db.delete(course)
            db.commit()

    def create_assignment(self, course_id: int, payload: CourseAssignmentCreate) -> CourseAssignmentRead:
        with SessionLocal() as db:
            course = db.get(Course, course_id)
            if course is None:
                raise HTTPException(status_code=404, detail="Course not found")
            assignment = CourseAssignment(
                course_id=course_id,
                assignment_name=payload.assignment_name,
                description=payload.description,
                total_score=payload.total_score,
            )
            db.add(assignment)
            db.flush()
            course.assignment_count = self._assignment_count(db, course_id)
            db.commit()
            db.refresh(assignment)
            return self._to_assignment_read_schema(assignment, file_count=0)

    def list_assignments(self, course_id: int) -> list[CourseAssignmentRead]:
        with SessionLocal() as db:
            course = db.get(Course, course_id)
            if course is None:
                raise HTTPException(status_code=404, detail="Course not found")
            assignments = db.scalars(
                select(CourseAssignment)
                .where(CourseAssignment.course_id == course_id)
                .order_by(CourseAssignment.id.desc()),
            ).all()
            file_counts = self._assignment_file_counts(db, [assignment.id for assignment in assignments])
            course.assignment_count = len(assignments)
            db.commit()
            return [
                self._to_assignment_read_schema(
                    assignment,
                    file_count=file_counts.get(assignment.id, 0),
                )
                for assignment in assignments
            ]

    def update_assignment(
        self,
        course_id: int,
        assignment_id: int,
        payload: CourseAssignmentUpdate,
    ) -> CourseAssignmentRead:
        with SessionLocal() as db:
            assignment = self._get_assignment(db, course_id, assignment_id)
            update_data = payload.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(assignment, key, value)
            db.commit()
            db.refresh(assignment)
            file_count = self._assignment_file_counts(db, [assignment.id]).get(assignment.id, 0)
            return self._to_assignment_read_schema(assignment, file_count=file_count)

    def delete_assignment(self, course_id: int, assignment_id: int) -> None:
        with SessionLocal() as db:
            assignment = self._get_assignment(db, course_id, assignment_id)
            files = db.scalars(
                select(CourseAssignmentFile).where(CourseAssignmentFile.assignment_id == assignment_id),
            ).all()
            for file in files:
                self._delete_storage_file(file.storage_path)
            db.delete(assignment)
            course = db.get(Course, course_id)
            if course is not None:
                db.flush()
                course.assignment_count = self._assignment_count(db, course_id)
            db.commit()

    async def upload_assignment_file(
        self,
        course_id: int,
        assignment_id: int,
        file_role: FileRole,
        file: UploadFile,
    ) -> CourseAssignmentFileRead:
        if file_role not in ASSIGNMENT_FILE_ROLES:
            raise HTTPException(status_code=400, detail="课程作业仅支持作业文件和参考答案文件")
        if not file.filename:
            raise HTTPException(status_code=400, detail="File name is required")

        with SessionLocal() as db:
            self._get_assignment(db, course_id, assignment_id)
            assignment_dir = (
                Path(settings.local_storage_root).expanduser().resolve()
                / "course_assignments"
                / str(course_id)
                / str(assignment_id)
            )
            assignment_dir.mkdir(parents=True, exist_ok=True)

            stored_name = f"{file_role.value}-{uuid4().hex}{Path(file.filename).suffix.lower()}"
            storage_path = assignment_dir / stored_name
            with storage_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            parsed_text = self._parse_text(storage_path)
            existing_files = db.scalars(
                select(CourseAssignmentFile).where(
                    CourseAssignmentFile.assignment_id == assignment_id,
                    CourseAssignmentFile.file_role == file_role,
                ),
            ).all()
            for existing_file in existing_files:
                self._delete_storage_file(existing_file.storage_path)
                db.delete(existing_file)

            assignment_file = CourseAssignmentFile(
                assignment_id=assignment_id,
                file_name=file.filename,
                file_role=file_role,
                content_type=file.content_type or "",
                storage_path=str(storage_path),
                parsed_text=parsed_text,
            )
            db.add(assignment_file)
            db.commit()
            db.refresh(assignment_file)
            return self._to_assignment_file_read_schema(assignment_file)

    def list_assignment_files(self, course_id: int, assignment_id: int) -> list[CourseAssignmentFileRead]:
        with SessionLocal() as db:
            self._get_assignment(db, course_id, assignment_id)
            files = db.scalars(
                select(CourseAssignmentFile)
                .where(CourseAssignmentFile.assignment_id == assignment_id)
                .order_by(CourseAssignmentFile.file_role, CourseAssignmentFile.id.desc()),
            ).all()
            return [self._to_assignment_file_read_schema(file) for file in files]

    def delete_assignment_file(self, course_id: int, assignment_id: int, file_id: int) -> None:
        with SessionLocal() as db:
            self._get_assignment(db, course_id, assignment_id)
            assignment_file = db.get(CourseAssignmentFile, file_id)
            if assignment_file is None or assignment_file.assignment_id != assignment_id:
                raise HTTPException(status_code=404, detail="File not found")
            self._delete_storage_file(assignment_file.storage_path)
            db.delete(assignment_file)
            db.commit()

    def parse_assignment_files(self, course_id: int, assignment_id: int) -> dict:
        with SessionLocal() as db:
            self._get_assignment(db, course_id, assignment_id)
            files = db.scalars(
                select(CourseAssignmentFile)
                .where(CourseAssignmentFile.assignment_id == assignment_id)
                .order_by(CourseAssignmentFile.file_role, CourseAssignmentFile.id),
            ).all()
            if not files:
                raise HTTPException(status_code=400, detail="No files uploaded for this assignment")

            parsed_files: list[dict] = []
            failed_files: list[dict] = []
            for assignment_file in files:
                try:
                    parsed_text = parse_document_text(Path(assignment_file.storage_path))
                    assignment_file.parsed_text = parsed_text
                    parsed_files.append(
                        {
                            "id": assignment_file.id,
                            "file_name": assignment_file.file_name,
                            "file_role": assignment_file.file_role.value,
                            "parsed_text_length": len(parsed_text),
                        },
                    )
                except ValueError as exc:
                    failed_files.append(
                        {
                            "id": assignment_file.id,
                            "file_name": assignment_file.file_name,
                            "file_role": assignment_file.file_role.value,
                            "error": str(exc),
                        },
                    )

            if not parsed_files:
                raise HTTPException(status_code=400, detail="No supported files could be parsed")

            db.commit()
            return {
                "course_id": course_id,
                "assignment_id": assignment_id,
                "stage": "parse_assignment_files",
                "parsed_count": len(parsed_files),
                "failed_count": len(failed_files),
                "parsed_files": parsed_files,
                "failed_files": failed_files,
            }

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

    def _get_assignment(self, db, course_id: int, assignment_id: int) -> CourseAssignment:
        assignment = db.get(CourseAssignment, assignment_id)
        if assignment is None or assignment.course_id != course_id:
            raise HTTPException(status_code=404, detail="Assignment not found")
        return assignment

    def _assignment_count(self, db, course_id: int) -> int:
        return int(
            db.scalar(
                select(func.count()).select_from(CourseAssignment).where(CourseAssignment.course_id == course_id),
            )
            or 0,
        )

    def _assignment_file_counts(self, db, assignment_ids: list[int]) -> dict[int, int]:
        if not assignment_ids:
            return {}
        rows = db.execute(
            select(CourseAssignmentFile.assignment_id, func.count(CourseAssignmentFile.id))
            .where(CourseAssignmentFile.assignment_id.in_(assignment_ids))
            .group_by(CourseAssignmentFile.assignment_id),
        ).all()
        return {int(assignment_id): int(count) for assignment_id, count in rows}

    def _parse_text(self, path: Path) -> str:
        try:
            return parse_document_text(path)
        except ValueError:
            return ""

    def _delete_storage_file(self, storage_path: str) -> None:
        if not storage_path:
            return
        try:
            Path(storage_path).unlink(missing_ok=True)
        except OSError:
            return

    def _to_assignment_read_schema(
        self,
        assignment: CourseAssignment,
        file_count: int = 0,
    ) -> CourseAssignmentRead:
        return CourseAssignmentRead(
            id=assignment.id,
            course_id=assignment.course_id,
            assignment_name=assignment.assignment_name,
            description=assignment.description,
            total_score=assignment.total_score,
            file_count=file_count,
            created_at=self._ensure_datetime(assignment.created_at),
            updated_at=self._ensure_datetime(assignment.updated_at),
        )

    def _to_assignment_file_read_schema(self, assignment_file: CourseAssignmentFile) -> CourseAssignmentFileRead:
        return CourseAssignmentFileRead(
            id=assignment_file.id,
            assignment_id=assignment_file.assignment_id,
            file_name=assignment_file.file_name,
            file_role=assignment_file.file_role,
            content_type=assignment_file.content_type,
            storage_path=assignment_file.storage_path,
            parsed_text=assignment_file.parsed_text,
            created_at=self._ensure_datetime(assignment_file.created_at),
            updated_at=self._ensure_datetime(assignment_file.updated_at),
        )


course_service = CourseService()
