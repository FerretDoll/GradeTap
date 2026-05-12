from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ClassGroupBase(BaseModel):
    class_name: str = Field(..., min_length=1, max_length=255)
    note: str = Field(default="")


class ClassGroupCreate(ClassGroupBase):
    pass


class ClassGroupUpdate(BaseModel):
    class_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    note: Optional[str] = None


class ClassGroupRead(ClassGroupBase):
    id: int
    student_count: int = 0
    created_at: datetime
    updated_at: datetime


class ClassStudentBase(BaseModel):
    student_name: str = Field(..., min_length=1, max_length=255)
    student_no: str = Field(default="", max_length=64)


class ClassStudentCreate(ClassStudentBase):
    pass


class ClassStudentUpdate(BaseModel):
    student_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    student_no: Optional[str] = Field(default=None, max_length=64)


class ClassStudentRead(ClassStudentBase):
    id: int
    class_group_id: int
    created_at: datetime
    updated_at: datetime


class StudentImportResult(BaseModel):
    imported_count: int
    skipped_count: int
    students: list[ClassStudentRead]
    errors: list[str] = Field(default_factory=list)
