from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.answer import AnswerExtractionStatus


class StudentSubmissionBase(BaseModel):
    student_no: str = Field(default="", max_length=64)
    student_name: str = Field(..., min_length=1, max_length=255)
    content: str = Field(default="")
    source_file_id: Optional[int] = None


class StudentSubmissionCreate(StudentSubmissionBase):
    task_id: int


class StudentSubmissionRead(StudentSubmissionBase):
    id: int
    task_id: int
    created_at: datetime
    updated_at: datetime


class StudentAnswerBase(BaseModel):
    answer_text: str = Field(default="")
    extraction_status: AnswerExtractionStatus = AnswerExtractionStatus.MATCHED
    confidence: float = Field(default=1, ge=0, le=1)
    raw_llm_output: Optional[str] = None


class StudentAnswerCreate(StudentAnswerBase):
    task_id: int
    question_id: int
    student_submission_id: int


class StudentAnswerRead(StudentAnswerBase):
    id: int
    task_id: int
    question_id: int
    student_submission_id: int
    created_at: datetime
    updated_at: datetime
