from datetime import datetime

from pydantic import BaseModel, Field

from app.models.file import FileRole


class UploadedFileBase(BaseModel):
    file_name: str = Field(..., min_length=1, max_length=255)
    file_role: FileRole
    content_type: str = Field(default="")
    storage_path: str = Field(default="")
    parsed_text: str = Field(default="")


class UploadedFileCreate(UploadedFileBase):
    task_id: int


class UploadedFileRead(UploadedFileBase):
    id: int
    task_id: int
    created_at: datetime
    updated_at: datetime
