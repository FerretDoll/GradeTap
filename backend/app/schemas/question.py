from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.models.question import DifficultyLevel, QuestionType


class QuestionRubricBase(BaseModel):
    dimension_name: str = Field(..., min_length=1, max_length=255)
    dimension_description: str = Field(default="")
    max_score: float = Field(..., gt=0)
    scoring_criteria: str = Field(..., min_length=1)
    deduction_criteria: str = Field(..., min_length=1)
    evidence_requirement: str = Field(..., min_length=1)
    sort_order: int = Field(default=0, ge=0)


class QuestionRubricCreate(QuestionRubricBase):
    question_id: int


class QuestionRubricUpdate(BaseModel):
    dimension_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    dimension_description: Optional[str] = None
    max_score: Optional[float] = Field(default=None, gt=0)
    scoring_criteria: Optional[str] = Field(default=None, min_length=1)
    deduction_criteria: Optional[str] = Field(default=None, min_length=1)
    evidence_requirement: Optional[str] = Field(default=None, min_length=1)
    sort_order: Optional[int] = Field(default=None, ge=0)


class QuestionRubricRead(QuestionRubricBase):
    id: int
    question_id: int
    created_at: datetime
    updated_at: datetime


class QuestionBase(BaseModel):
    question_number: str = Field(..., min_length=1, max_length=64)
    content: str = Field(..., min_length=1)
    question_type: QuestionType = QuestionType.OTHER
    knowledge_points: list[str] = Field(default_factory=list)
    difficulty: DifficultyLevel = DifficultyLevel.UNKNOWN
    expected_answer_type: str = Field(default="")
    total_score: float = Field(..., gt=0)
    sort_order: int = Field(default=0, ge=0)


class QuestionCreate(QuestionBase):
    task_id: int
    rubrics: list[QuestionRubricBase] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_rubric_total_score(self) -> "QuestionCreate":
        if not self.rubrics:
            return self
        rubric_total = sum(rubric.max_score for rubric in self.rubrics)
        if abs(rubric_total - self.total_score) > 0.001:
            raise ValueError("Rubric dimension scores must sum to question total_score.")
        return self


class QuestionUpdate(BaseModel):
    question_number: Optional[str] = Field(default=None, min_length=1, max_length=64)
    content: Optional[str] = Field(default=None, min_length=1)
    question_type: Optional[QuestionType] = None
    knowledge_points: Optional[list[str]] = None
    difficulty: Optional[DifficultyLevel] = None
    expected_answer_type: Optional[str] = None
    total_score: Optional[float] = Field(default=None, gt=0)
    sort_order: Optional[int] = Field(default=None, ge=0)
    rubrics: Optional[list[QuestionRubricBase]] = None

    @model_validator(mode="after")
    def validate_rubric_total_score(self) -> "QuestionUpdate":
        if self.rubrics is None or self.total_score is None:
            return self
        rubric_total = sum(rubric.max_score for rubric in self.rubrics)
        if abs(rubric_total - self.total_score) > 0.001:
            raise ValueError("Rubric dimension scores must sum to question total_score.")
        return self


class QuestionRead(QuestionBase):
    id: int
    task_id: int
    rubrics: list[QuestionRubricRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class TaskQuestionsUpdate(BaseModel):
    questions: list[QuestionUpdate]
    rubric_confirmed: bool = False
