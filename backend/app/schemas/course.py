from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.file import FileRole


class CourseBase(BaseModel):
    course_name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="")


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    course_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None


class CourseRead(CourseBase):
    id: int
    assignment_count: int = 0
    created_at: datetime
    updated_at: datetime


class CourseAssignmentBase(BaseModel):
    assignment_name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="")
    total_score: float = Field(default=100, ge=0)


class CourseAssignmentCreate(CourseAssignmentBase):
    pass


class CourseAssignmentUpdate(BaseModel):
    assignment_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    total_score: Optional[float] = Field(default=None, ge=0)


class CourseAssignmentRead(CourseAssignmentBase):
    id: int
    course_id: int
    file_count: int = 0
    created_at: datetime
    updated_at: datetime


class CourseAssignmentFileRead(BaseModel):
    id: int
    assignment_id: int
    file_name: str
    file_role: FileRole
    content_type: str = ""
    storage_path: str = ""
    parsed_text: str = ""
    created_at: datetime
    updated_at: datetime
