from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

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


class StudentFileMatchRead(BaseModel):
    student_id: int
    student_name: str
    student_no: str = ""
    match_status: Literal["matched", "missing", "ambiguous"]
    matched_file_id: Optional[int] = None
    matched_file_name: str = ""
    confidence: float = Field(default=0, ge=0, le=1)
    reason: str = ""
    candidate_files: list[str] = Field(default_factory=list)
    submission_id: Optional[int] = None


class StudentPrepareResponse(BaseModel):
    task_id: int
    status: str
    stage: str = "prepare_students"
    matched_count: int
    total_students: int
    missing_count: int
    ambiguous_count: int
    matches: list[StudentFileMatchRead]


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
