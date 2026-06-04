from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.plagiarism import PlagiarismCheckStatus, PlagiarismRiskLevel


class PlagiarismCheckRead(BaseModel):
    id: int
    task_id: int
    status: PlagiarismCheckStatus
    algorithm: str
    threshold: float
    error_message: str = ""
    finished_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class PlagiarismRunResponse(BaseModel):
    task_id: int
    check: PlagiarismCheckRead
    total_students: int
    match_count: int


class PlagiarismMatchedSegment(BaseModel):
    segment_id: str
    question_id: Optional[int] = None
    question_number: str = ""
    question_content: str = ""
    question_similarity: float = Field(default=0, ge=0, le=1)
    similarity: float = Field(default=1, ge=0, le=1)
    student_text: str = ""
    matched_student_text: str = ""
    student_answer_text: str = ""
    matched_student_answer_text: str = ""
    student_start: int = 0
    student_end: int = 0
    matched_student_start: int = 0
    matched_student_end: int = 0


class PlagiarismStudentMatchRead(BaseModel):
    match_id: int
    student_submission_id: int
    student_no: str = ""
    student_name: str
    similarity_score: float = Field(default=0, ge=0, le=1)
    risk_level: PlagiarismRiskLevel
    matched_segments: list[PlagiarismMatchedSegment] = Field(default_factory=list)
    evidence_summary: str = ""


class PlagiarismStudentSummaryRead(BaseModel):
    student_submission_id: int
    student_no: str = ""
    student_name: str
    max_similarity_score: float = Field(default=0, ge=0, le=1)
    similar_students_count: int = 0
    risk_level: PlagiarismRiskLevel = PlagiarismRiskLevel.NONE
    top_match_submission_id: Optional[int] = None
    matches: list[PlagiarismStudentMatchRead] = Field(default_factory=list)


class PlagiarismStudentDetailRead(PlagiarismStudentSummaryRead):
    check: Optional[PlagiarismCheckRead] = None


class PlagiarismStudentsResponse(BaseModel):
    task_id: int
    check: Optional[PlagiarismCheckRead] = None
    students: list[PlagiarismStudentSummaryRead] = Field(default_factory=list)
