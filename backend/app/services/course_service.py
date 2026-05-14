from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from pydantic import ValidationError
from sqlalchemy import delete, func, inspect, select, text

from app.core.config import settings
from app.db.models import (
    Course,
    CourseAssignment,
    CourseAssignmentFile,
    CourseAssignmentQuestion,
    CourseAssignmentQuestionRubric,
)
from app.db.session import Base, SessionLocal
from app.models.file import FileRole
from app.schemas.course import (
    CourseAssignmentCreate,
    CourseAssignmentFileRead,
    CourseAssignmentRead,
    CourseAssignmentUpdate,
    CourseAssignmentQuestionsUpdate,
    CourseCreate,
    CourseRead,
    CourseUpdate,
)
from app.schemas.question import QuestionCreate
from app.services.file_parse_service import parse_document_text
from app.services.question_analyzer_service import question_analyzer_service
from app.services.rubric_builder_service import rubric_builder_service


ASSIGNMENT_FILE_ROLES = {FileRole.REQUIREMENT, FileRole.REFERENCE_ANSWER}


class CourseService:
    def create_course(self, payload: CourseCreate) -> CourseRead:
        self._ensure_assignment_schema()
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
        self._ensure_assignment_schema()
        with SessionLocal() as db:
            courses = db.scalars(select(Course).order_by(Course.id.desc())).all()
            return [self._to_read_schema(course) for course in courses]

    def get_course(self, course_id: int) -> Optional[CourseRead]:
        self._ensure_assignment_schema()
        with SessionLocal() as db:
            course = db.get(Course, course_id)
            if course is None:
                return None
            return self._to_read_schema(course)

    def update_course(self, course_id: int, payload: CourseUpdate) -> CourseRead:
        self._ensure_assignment_schema()
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
        self._ensure_assignment_schema()
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
        self._ensure_assignment_schema()
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
            return self._to_assignment_read_schema(assignment, file_count=0, db=db)

    def list_assignments(self, course_id: int) -> list[CourseAssignmentRead]:
        self._ensure_assignment_schema()
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
                    db=db,
                )
                for assignment in assignments
            ]

    def update_assignment(
        self,
        course_id: int,
        assignment_id: int,
        payload: CourseAssignmentUpdate,
    ) -> CourseAssignmentRead:
        self._ensure_assignment_schema()
        with SessionLocal() as db:
            assignment = self._get_assignment(db, course_id, assignment_id)
            update_data = payload.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(assignment, key, value)
            db.commit()
            db.refresh(assignment)
            file_count = self._assignment_file_counts(db, [assignment.id]).get(assignment.id, 0)
            return self._to_assignment_read_schema(assignment, file_count=file_count, db=db)

    def delete_assignment(self, course_id: int, assignment_id: int) -> None:
        self._ensure_assignment_schema()
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
        self._ensure_assignment_schema()
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
        self._ensure_assignment_schema()
        with SessionLocal() as db:
            self._get_assignment(db, course_id, assignment_id)
            files = db.scalars(
                select(CourseAssignmentFile)
                .where(CourseAssignmentFile.assignment_id == assignment_id)
                .order_by(CourseAssignmentFile.file_role, CourseAssignmentFile.id.desc()),
            ).all()
            return [self._to_assignment_file_read_schema(file) for file in files]

    def delete_assignment_file(self, course_id: int, assignment_id: int, file_id: int) -> None:
        self._ensure_assignment_schema()
        with SessionLocal() as db:
            self._get_assignment(db, course_id, assignment_id)
            assignment_file = db.get(CourseAssignmentFile, file_id)
            if assignment_file is None or assignment_file.assignment_id != assignment_id:
                raise HTTPException(status_code=404, detail="File not found")
            self._delete_storage_file(assignment_file.storage_path)
            db.delete(assignment_file)
            db.commit()

    def parse_assignment_files(self, course_id: int, assignment_id: int) -> dict:
        self._ensure_assignment_schema()
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

    def analyze_assignment_questions(self, course_id: int, assignment_id: int) -> dict:
        self._ensure_assignment_schema()
        with SessionLocal() as db:
            assignment = self._get_assignment(db, course_id, assignment_id)
            files = self._assignment_files(db, assignment_id)
            requirement_text = self._combined_parsed_text(files, FileRole.REQUIREMENT)
            reference_answer_text = self._combined_parsed_text(files, FileRole.REFERENCE_ANSWER)
            if not requirement_text.strip():
                raise HTTPException(status_code=400, detail="请先解析作业文件，再进行题目分析")

            try:
                question_payloads = question_analyzer_service.analyze_questions(
                    task_id=0,
                    requirement_text=requirement_text,
                    reference_answer_text=reference_answer_text,
                    grading_instruction=assignment.description,
                )
            except ValidationError as exc:
                raise HTTPException(status_code=502, detail=f"题目分析字段不完整或不合法：{exc}") from exc
            except ValueError as exc:
                raise HTTPException(status_code=502, detail=f"题目分析结果不是合法 JSON：{exc}") from exc
            except RuntimeError as exc:
                raise HTTPException(status_code=502, detail=str(exc)) from exc

            questions = [question.model_dump(mode="json") for question in question_payloads]
            self._sync_assignment_question_records(db, assignment_id, questions)
            assignment.questions_payload = None
            assignment.rubrics_payload = None
            assignment.rubric_confirmed = False
            assignment.rubric_confirmed_at = None
            db.commit()
            db.refresh(assignment)
            return {
                "course_id": course_id,
                "assignment_id": assignment_id,
                "stage": "analyze_questions",
                "question_count": len(questions),
                "questions": self._assignment_questions_payload(db, assignment_id),
                "rubric_confirmed": assignment.rubric_confirmed,
            }

    def build_assignment_rubrics(self, course_id: int, assignment_id: int) -> dict:
        self._ensure_assignment_schema()
        with SessionLocal() as db:
            assignment = self._get_assignment(db, course_id, assignment_id)
            source_questions = self._assignment_questions_payload(db, assignment_id)
            if not source_questions:
                source_questions = assignment.questions_payload or []
            if not source_questions:
                raise HTTPException(status_code=400, detail="请先完成题目分析，再生成评分量规")
            files = self._assignment_files(db, assignment_id)
            reference_answer_text = self._combined_parsed_text(files, FileRole.REFERENCE_ANSWER)
            try:
                questions = [
                    QuestionCreate(
                        **{
                            **question,
                            "task_id": 0,
                            "rubrics": question.get("rubrics", []),
                        },
                    )
                    for question in source_questions
                ]
                rubric_questions = rubric_builder_service.build_rubrics(
                    questions=questions,
                    reference_answer_text=reference_answer_text,
                    grading_instruction=assignment.description,
                )
            except ValidationError as exc:
                raise HTTPException(status_code=502, detail=f"量规字段不完整或不合法：{exc}") from exc
            except ValueError as exc:
                raise HTTPException(status_code=502, detail=f"量规生成结果不是合法 JSON：{exc}") from exc
            except RuntimeError as exc:
                raise HTTPException(status_code=502, detail=str(exc)) from exc

            rubrics = [question.model_dump(mode="json") for question in rubric_questions]
            self._sync_assignment_question_records(db, assignment_id, rubrics)
            assignment.questions_payload = None
            assignment.rubrics_payload = None
            assignment.rubric_confirmed = False
            assignment.rubric_confirmed_at = None
            db.commit()
            db.refresh(assignment)
            return {
                "course_id": course_id,
                "assignment_id": assignment_id,
                "stage": "build_rubrics",
                "question_count": len(rubrics),
                "questions": self._assignment_questions_payload(db, assignment_id),
                "rubrics": self._assignment_questions_payload(db, assignment_id),
                "rubric_confirmed": assignment.rubric_confirmed,
            }

    def list_assignment_questions(self, course_id: int, assignment_id: int) -> dict:
        self._ensure_assignment_schema()
        with SessionLocal() as db:
            assignment = self._get_assignment(db, course_id, assignment_id)
            questions = self._assignment_questions_payload(db, assignment_id)
            if not questions:
                questions = assignment.rubrics_payload or assignment.questions_payload or []
            return {
                "course_id": course_id,
                "assignment_id": assignment_id,
                "questions": questions,
                "rubrics": questions if any(question.get("rubrics") for question in questions) else [],
                "rubric_confirmed": assignment.rubric_confirmed,
                "rubric_confirmed_at": self._ensure_optional_datetime(assignment.rubric_confirmed_at),
            }

    def confirm_assignment_rubrics(
        self,
        course_id: int,
        assignment_id: int,
        payload: CourseAssignmentQuestionsUpdate,
    ) -> dict:
        self._ensure_assignment_schema()
        with SessionLocal() as db:
            assignment = self._get_assignment(db, course_id, assignment_id)
            questions = payload.questions
            if not questions:
                raise HTTPException(status_code=400, detail="评分量规不能为空")
            for question in questions:
                if not question.get("rubrics"):
                    raise HTTPException(status_code=400, detail="每道题都必须包含评分量规")
            assignment.rubric_confirmed = payload.rubric_confirmed
            assignment.rubric_confirmed_at = datetime.now(timezone.utc) if payload.rubric_confirmed else None
            self._sync_assignment_question_records(db, assignment_id, questions)
            assignment.questions_payload = None
            assignment.rubrics_payload = None
            db.commit()
            db.refresh(assignment)
            saved_questions = self._assignment_questions_payload(db, assignment_id)
            return {
                "course_id": course_id,
                "assignment_id": assignment_id,
                "stage": "teacher_confirm_rubrics",
                "questions": saved_questions,
                "rubrics": saved_questions,
                "rubric_confirmed": assignment.rubric_confirmed,
                "rubric_confirmed_at": self._ensure_optional_datetime(assignment.rubric_confirmed_at),
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

    def _ensure_optional_datetime(self, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return self._ensure_datetime(value)

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

    def _assignment_files(self, db, assignment_id: int) -> list[CourseAssignmentFile]:
        return db.scalars(
            select(CourseAssignmentFile)
            .where(CourseAssignmentFile.assignment_id == assignment_id)
            .order_by(CourseAssignmentFile.file_role, CourseAssignmentFile.id),
        ).all()

    def _combined_parsed_text(self, files: list[CourseAssignmentFile], file_role: FileRole) -> str:
        return "\n\n".join(
            assignment_file.parsed_text
            for assignment_file in files
            if assignment_file.file_role == file_role and assignment_file.parsed_text.strip()
        )

    def _ensure_assignment_schema(self) -> None:
        table_name = CourseAssignment.__tablename__
        with SessionLocal() as db:
            Base.metadata.create_all(
                bind=db.bind,
                tables=[
                    CourseAssignmentQuestion.__table__,
                    CourseAssignmentQuestionRubric.__table__,
                ],
            )
            existing_columns = {column["name"] for column in inspect(db.bind).get_columns(table_name)}
            dialect = db.bind.dialect.name
            column_specs = {
                "questions_payload": "JSON NULL" if dialect == "mysql" else "TEXT NULL",
                "rubrics_payload": "JSON NULL" if dialect == "mysql" else "TEXT NULL",
                "rubric_confirmed": "BOOL NOT NULL DEFAULT 0" if dialect == "mysql" else "BOOLEAN NOT NULL DEFAULT 0",
                "rubric_confirmed_at": "DATETIME NULL",
            }
            for column_name, column_type in column_specs.items():
                if column_name not in existing_columns:
                    db.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))
            db.commit()

    def _clear_assignment_question_records(self, db, assignment_id: int) -> None:
        assignment_question_ids = select(CourseAssignmentQuestion.id).where(
            CourseAssignmentQuestion.assignment_id == assignment_id,
        )
        db.execute(
            delete(CourseAssignmentQuestionRubric).where(
                CourseAssignmentQuestionRubric.assignment_question_id.in_(assignment_question_ids),
            ),
        )
        db.execute(
            delete(CourseAssignmentQuestion).where(
                CourseAssignmentQuestion.assignment_id == assignment_id,
            ),
        )

    def _sync_assignment_question_records(self, db, assignment_id: int, questions: list[dict]) -> None:
        self._clear_assignment_question_records(db, assignment_id)
        for question_payload in questions:
            question = CourseAssignmentQuestion(
                assignment_id=assignment_id,
                question_number=str(question_payload.get("question_number") or ""),
                content=str(question_payload.get("content") or ""),
                question_type=question_payload.get("question_type") or "other",
                knowledge_points=question_payload.get("knowledge_points") or [],
                difficulty=question_payload.get("difficulty") or "unknown",
                expected_answer_type=str(question_payload.get("expected_answer_type") or ""),
                total_score=float(question_payload.get("total_score") or 0),
                sort_order=int(question_payload.get("sort_order") or 0),
            )
            db.add(question)
            db.flush()
            for rubric_payload in question_payload.get("rubrics") or []:
                db.add(
                    CourseAssignmentQuestionRubric(
                        assignment_question_id=question.id,
                        dimension_name=str(rubric_payload.get("dimension_name") or ""),
                        dimension_description=str(rubric_payload.get("dimension_description") or ""),
                        max_score=float(rubric_payload.get("max_score") or 0),
                        scoring_criteria=str(rubric_payload.get("scoring_criteria") or ""),
                        deduction_criteria=str(rubric_payload.get("deduction_criteria") or ""),
                        evidence_requirement=str(rubric_payload.get("evidence_requirement") or ""),
                        sort_order=int(rubric_payload.get("sort_order") or 0),
                    ),
                )

    def _assignment_questions_payload(self, db, assignment_id: int) -> list[dict]:
        questions = db.scalars(
            select(CourseAssignmentQuestion)
            .where(CourseAssignmentQuestion.assignment_id == assignment_id)
            .order_by(CourseAssignmentQuestion.sort_order, CourseAssignmentQuestion.id),
        ).all()
        if not questions:
            return []

        rubrics = db.scalars(
            select(CourseAssignmentQuestionRubric)
            .where(
                CourseAssignmentQuestionRubric.assignment_question_id.in_(
                    [question.id for question in questions],
                ),
            )
            .order_by(
                CourseAssignmentQuestionRubric.assignment_question_id,
                CourseAssignmentQuestionRubric.sort_order,
                CourseAssignmentQuestionRubric.id,
            ),
        ).all()
        rubric_map: dict[int, list[dict]] = {}
        for rubric in rubrics:
            rubric_map.setdefault(rubric.assignment_question_id, []).append(
                {
                    "dimension_name": rubric.dimension_name,
                    "dimension_description": rubric.dimension_description,
                    "max_score": rubric.max_score,
                    "scoring_criteria": rubric.scoring_criteria,
                    "deduction_criteria": rubric.deduction_criteria,
                    "evidence_requirement": rubric.evidence_requirement,
                    "sort_order": rubric.sort_order,
                },
            )

        return [
            {
                "question_number": question.question_number,
                "content": question.content,
                "question_type": question.question_type.value,
                "knowledge_points": question.knowledge_points or [],
                "difficulty": question.difficulty.value,
                "expected_answer_type": question.expected_answer_type,
                "total_score": question.total_score,
                "sort_order": question.sort_order,
                "rubrics": rubric_map.get(question.id, []),
            }
            for question in questions
        ]

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
        db=None,
    ) -> CourseAssignmentRead:
        questions = self._assignment_questions_payload(db, assignment.id) if db is not None else []
        if not questions:
            questions = assignment.rubrics_payload or assignment.questions_payload or []
        rubrics = questions if any(question.get("rubrics") for question in questions) else []
        return CourseAssignmentRead(
            id=assignment.id,
            course_id=assignment.course_id,
            assignment_name=assignment.assignment_name,
            description=assignment.description,
            total_score=assignment.total_score,
            file_count=file_count,
            questions=questions,
            rubrics=rubrics,
            rubric_confirmed=assignment.rubric_confirmed,
            rubric_confirmed_at=self._ensure_optional_datetime(assignment.rubric_confirmed_at),
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
