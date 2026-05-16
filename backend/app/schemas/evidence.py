from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, Union

from pydantic import BaseModel, Field


class RubricEvidenceBase(BaseModel):
    rubric_id: int
    positive_evidence: list[str] = Field(default_factory=list)
    negative_evidence: list[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0, le=1)
    raw_llm_output: Optional[Union[dict[str, Any], str]] = None


class AnswerEvidenceCreate(RubricEvidenceBase):
    task_id: int
    question_id: int
    student_id: Optional[int] = None
    student_answer_id: int


class AnswerEvidenceRead(RubricEvidenceBase):
    id: int
    task_id: int
    question_id: int
    student_id: Optional[int]
    student_answer_id: int
    created_at: datetime
    updated_at: datetime


class AnswerEvidenceBatchRead(BaseModel):
    task_id: int
    question_id: int
    student_answer_id: int
    evidence_items: list[AnswerEvidenceRead] = Field(default_factory=list)


class EvidenceExtractionQuestionRead(BaseModel):
    question_id: int
    student_answer_id: int
    answer_text: str = ""
    extraction_status: str = ""
    answer_confidence: float = Field(default=0, ge=0, le=1)
    evidence_items: list[AnswerEvidenceRead] = Field(default_factory=list)


class StudentEvidenceExtractionProgress(BaseModel):
    submission_id: int
    student_name: str
    student_no: str = ""
    status: str = "pending"
    questions: list[EvidenceExtractionQuestionRead] = Field(default_factory=list)


class EvidenceExtractionSnapshot(BaseModel):
    task_id: int
    status: str
    stage: str = "extract_evidence"
    total_answers: int
    completed_answers: int
    students: list[StudentEvidenceExtractionProgress] = Field(default_factory=list)
