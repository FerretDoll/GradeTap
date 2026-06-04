from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy import delete, or_, select

from app.core.config import settings
from app.db.models import (
    AnswerEvidence,
    AnswerGroupMember,
    GradingDeduction,
    GradingReflection,
    GradingResult,
    GradingTask,
    PlagiarismMatch,
    StudentAnswer,
    StudentPlagiarismSummary,
    StudentSubmission,
    TeacherRevision,
    UploadedFile,
)
from app.db.session import SessionLocal
from app.models.file import FileRole
from app.models.task import GradingTaskStatus
from app.schemas.file import TaskFileUploadResponse, UploadedFileRead
from app.services.file_parse_service import parse_document_text
from app.utils.zip_submission_parser import extract_student_submissions_from_zip


SINGLE_FILE_ROLES = {FileRole.REQUIREMENT, FileRole.REFERENCE_ANSWER}


class FileService:
    async def upload_task_file(self, task_id: int, file_role: FileRole, file: UploadFile) -> TaskFileUploadResponse:
        if not file.filename:
            raise HTTPException(status_code=400, detail="File name is required")

        suffix = Path(file.filename).suffix.lower()
        if file_role == FileRole.STUDENT_SUBMISSION and suffix == ".zip":
            return await self._upload_student_submission_zip(task_id, file)

        uploaded_file = await self._upload_single_task_file(task_id, file_role, file)
        return TaskFileUploadResponse(
            files=[uploaded_file],
            extracted_from_zip=False,
            source_file_name=file.filename,
            message=f"{file.filename} 已上传",
        )

    async def _upload_single_task_file(self, task_id: int, file_role: FileRole, file: UploadFile) -> UploadedFileRead:
        with SessionLocal() as db:
            task = db.get(GradingTask, task_id)
            if task is None:
                raise HTTPException(status_code=404, detail="Task not found")

            task_dir = Path(settings.local_storage_root).expanduser().resolve() / "tasks" / str(task_id)
            task_dir.mkdir(parents=True, exist_ok=True)

            stored_name = f"{file_role.value}-{uuid4().hex}{Path(file.filename).suffix.lower()}"
            storage_path = task_dir / stored_name

            with storage_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            parsed_text = self._parse_text(storage_path)

            if file_role in SINGLE_FILE_ROLES:
                existing_files = db.scalars(
                    select(UploadedFile).where(
                        UploadedFile.task_id == task_id,
                        UploadedFile.file_role == file_role,
                    ),
                ).all()
                for existing_file in existing_files:
                    self._delete_storage_file(existing_file.storage_path)
                    db.delete(existing_file)

            uploaded_file = UploadedFile(
                task_id=task_id,
                file_name=file.filename,
                file_role=file_role,
                content_type=file.content_type or "",
                storage_path=str(storage_path),
                parsed_text=parsed_text,
            )
            db.add(uploaded_file)
            if task.status == GradingTaskStatus.CREATED:
                task.status = GradingTaskStatus.FILES_UPLOADED
            db.commit()
            db.refresh(uploaded_file)
            return self._to_read_schema(uploaded_file)

    async def _upload_student_submission_zip(self, task_id: int, file: UploadFile) -> TaskFileUploadResponse:
        with SessionLocal() as db:
            task = db.get(GradingTask, task_id)
            if task is None:
                raise HTTPException(status_code=404, detail="Task not found")

            task_dir = Path(settings.local_storage_root).expanduser().resolve() / "tasks" / str(task_id)
            task_dir.mkdir(parents=True, exist_ok=True)

            zip_path = task_dir / f"student_submission-archive-{uuid4().hex}.zip"
            with zip_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            try:
                extracted_submissions = extract_student_submissions_from_zip(zip_path, task_dir)
            except ValueError as exc:
                self._delete_storage_file(str(zip_path))
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            finally:
                self._delete_storage_file(str(zip_path))

            uploaded_files: list[UploadedFileRead] = []
            for submission in extracted_submissions:
                display_name = submission.folder_name
                if submission.source_files:
                    display_name = f"{submission.folder_name}/{submission.source_files[0]}"
                stored_name = f"student_submission-{uuid4().hex}.txt"
                storage_path = task_dir / stored_name
                storage_path.write_text(submission.parsed_text, encoding="utf-8")

                uploaded_file = UploadedFile(
                    task_id=task_id,
                    file_name=display_name,
                    file_role=FileRole.STUDENT_SUBMISSION,
                    content_type="text/plain",
                    storage_path=str(storage_path),
                    parsed_text=submission.parsed_text,
                )
                db.add(uploaded_file)
                db.flush()
                uploaded_files.append(self._to_read_schema(uploaded_file))

            if task.status == GradingTaskStatus.CREATED:
                task.status = GradingTaskStatus.FILES_UPLOADED
            db.commit()

            return TaskFileUploadResponse(
                files=uploaded_files,
                extracted_from_zip=True,
                source_file_name=file.filename or "",
                message=f"已从 {file.filename} 解压并导入 {len(uploaded_files)} 份学生作业",
            )

    def list_task_files(self, task_id: int) -> list[UploadedFileRead]:
        with SessionLocal() as db:
            if db.get(GradingTask, task_id) is None:
                raise HTTPException(status_code=404, detail="Task not found")
            files = db.scalars(
                select(UploadedFile)
                .where(UploadedFile.task_id == task_id)
                .order_by(UploadedFile.file_role, UploadedFile.id.desc()),
            ).all()
            return [self._to_read_schema(file) for file in files]

    def delete_task_file(self, task_id: int, file_id: int) -> None:
        with SessionLocal() as db:
            uploaded_file = db.get(UploadedFile, file_id)
            if uploaded_file is None or uploaded_file.task_id != task_id:
                raise HTTPException(status_code=404, detail="File not found")
            storage_path = uploaded_file.storage_path
            if uploaded_file.file_role == FileRole.STUDENT_SUBMISSION:
                self._delete_student_submissions_for_file(db, task_id, file_id)
            db.delete(uploaded_file)
            db.commit()
            self._delete_storage_file(storage_path)

    def _delete_student_submissions_for_file(self, db, task_id: int, file_id: int) -> None:
        submission_ids = db.scalars(
            select(StudentSubmission.id).where(
                StudentSubmission.task_id == task_id,
                StudentSubmission.source_file_id == file_id,
            ),
        ).all()
        if not submission_ids:
            return

        answer_ids = db.scalars(
            select(StudentAnswer.id).where(
                StudentAnswer.task_id == task_id,
                StudentAnswer.student_submission_id.in_(submission_ids),
            ),
        ).all()
        result_ids = db.scalars(
            select(GradingResult.id).where(
                GradingResult.task_id == task_id,
                GradingResult.student_submission_id.in_(submission_ids),
            ),
        ).all()

        db.execute(delete(GradingDeduction).where(GradingDeduction.grading_result_id.in_(result_ids)))
        db.execute(delete(GradingReflection).where(GradingReflection.grading_result_id.in_(result_ids)))
        db.execute(delete(TeacherRevision).where(TeacherRevision.grading_result_id.in_(result_ids)))
        db.execute(delete(GradingResult).where(GradingResult.id.in_(result_ids)))
        db.execute(delete(AnswerEvidence).where(AnswerEvidence.student_answer_id.in_(answer_ids)))
        db.execute(delete(AnswerGroupMember).where(AnswerGroupMember.student_answer_id.in_(answer_ids)))
        db.execute(delete(StudentAnswer).where(StudentAnswer.id.in_(answer_ids)))
        db.execute(
            delete(PlagiarismMatch).where(
                PlagiarismMatch.task_id == task_id,
                or_(
                    PlagiarismMatch.student_a_submission_id.in_(submission_ids),
                    PlagiarismMatch.student_b_submission_id.in_(submission_ids),
                ),
            ),
        )
        db.execute(
            delete(StudentPlagiarismSummary).where(
                StudentPlagiarismSummary.task_id == task_id,
                or_(
                    StudentPlagiarismSummary.student_submission_id.in_(submission_ids),
                    StudentPlagiarismSummary.top_match_submission_id.in_(submission_ids),
                ),
            ),
        )
        db.execute(delete(StudentSubmission).where(StudentSubmission.id.in_(submission_ids)))

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

    def _to_read_schema(self, uploaded_file: UploadedFile) -> UploadedFileRead:
        return UploadedFileRead(
            id=uploaded_file.id,
            task_id=uploaded_file.task_id,
            file_name=uploaded_file.file_name,
            file_role=uploaded_file.file_role,
            content_type=uploaded_file.content_type,
            storage_path=uploaded_file.storage_path,
            parsed_text=uploaded_file.parsed_text,
            created_at=self._ensure_datetime(uploaded_file.created_at),
            updated_at=self._ensure_datetime(uploaded_file.updated_at),
        )

    def _ensure_datetime(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


file_service = FileService()
