from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


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
