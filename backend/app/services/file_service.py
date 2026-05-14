from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy import select

from app.core.config import settings
from app.db.models import GradingTask, UploadedFile
from app.db.session import SessionLocal
from app.models.file import FileRole
from app.models.task import GradingTaskStatus
from app.schemas.file import UploadedFileRead
from app.services.file_parse_service import parse_document_text


SINGLE_FILE_ROLES = {FileRole.REQUIREMENT, FileRole.REFERENCE_ANSWER}


class FileService:
    async def upload_task_file(self, task_id: int, file_role: FileRole, file: UploadFile) -> UploadedFileRead:
        if not file.filename:
            raise HTTPException(status_code=400, detail="File name is required")

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
            self._delete_storage_file(uploaded_file.storage_path)
            db.delete(uploaded_file)
            db.commit()

    def _parse_text(self, path: Path) -> str:
        try:
            return parse_document_text(path)
        except ValueError:
            return ""
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
