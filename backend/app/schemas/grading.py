from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, Union

from pydantic import BaseModel, Field, model_validator

from app.models.grading import (
    GradingStatus,
    ReflectionStatus,
    ReviewPriority,
    ReviewStatus,
    SuggestedAction,
)


class DimensionScore(BaseModel):
    rubric_id: int
    dimension_name: str = Field(..., min_length=1, max_length=255)
    max_score: float = Field(..., gt=0)
    score: float = Field(..., ge=0)
    reason: str = Field(..., min_length=1)
    evidence_ids: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_score_not_over_max(self) -> "DimensionScore":
        if self.score > self.max_score:
            raise ValueError("Dimension score cannot exceed max_score.")
        return self


class GradingResultBase(BaseModel):
    score: float = Field(..., ge=0)
    final_score: Optional[float] = Field(default=None, ge=0)
    dimension_scores: list[DimensionScore] = Field(default_factory=list)
    grading_status: GradingStatus = GradingStatus.PARTIAL
    confidence: float = Field(..., ge=0, le=1)
    ai_comment: str = Field(default="")
    final_comment: Optional[str] = None
    review_required: bool = False
    review_priority: ReviewPriority = ReviewPriority.LOW
    review_status: ReviewStatus = ReviewStatus.AI_GENERATED
    raw_llm_output: Optional[Union[dict[str, Any], str]] = None

    @model_validator(mode="after")
    def validate_score_total(self) -> "GradingResultBase":
        if not self.dimension_scores:
            return self
        total = sum(item.score for item in self.dimension_scores)
        if abs(total - self.score) > 0.001:
            raise ValueError("score must equal the sum of dimension_scores.")
        return self


class GradingResultCreate(GradingResultBase):
    task_id: int
    question_id: int
    student_answer_id: int
    student_submission_id: int


class GradingResultRead(GradingResultBase):
    id: int
    task_id: int
    question_id: int
    student_answer_id: int
    student_submission_id: int
    created_at: datetime
    updated_at: datetime


class EvidenceForGrading(BaseModel):
    id: Optional[int] = None
    rubric_id: int
    positive_evidence: list[str] = Field(default_factory=list)
    negative_evidence: list[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0, le=1)


class StudentAnswerForGrading(BaseModel):
    student_answer_id: int
    student_submission_id: int
    student_id: Optional[int] = None
    student_no: str = ""
    student_name: str = ""
    answer_text: str = ""
    answer_confidence: float = Field(default=1, ge=0, le=1)
    structured_evidence: list[EvidenceForGrading] = Field(default_factory=list)


class GradeByQuestionRequest(BaseModel):
    question: "QuestionRead"
    rubrics: list["QuestionRubricRead"]
    student_answers: list[StudentAnswerForGrading]


class GradeByQuestionResponse(BaseModel):
    task_id: int
    question_id: int
    grading_results: list[GradingResultRead] = Field(default_factory=list)


class GradeByQuestionStudentStartResponse(BaseModel):
    task_id: int
    submission_id: int
    status: str = "queued"
    stage: str = "grade_by_question"
    total_questions: int


class GradingReflectionBase(BaseModel):
    reflection_status: ReflectionStatus
    issues: list[str] = Field(default_factory=list)
    suggested_action: SuggestedAction = SuggestedAction.KEEP_SCORE
    calibrated_score: Optional[float] = Field(default=None, ge=0)
    need_human_review: bool = False
    raw_llm_output: Optional[Union[dict[str, Any], str]] = None


class GradingReflectionCreate(GradingReflectionBase):
    task_id: int
    grading_result_id: int


class GradingReflectionRead(GradingReflectionBase):
    id: int
    task_id: int
    grading_result_id: int
    created_at: datetime
    updated_at: datetime


class TeacherRevisionBase(BaseModel):
    final_score: float = Field(..., ge=0)
    final_comment: str = Field(default="")
    revision_reason: str = Field(default="")
    review_status: ReviewStatus = ReviewStatus.TEACHER_MODIFIED


class TeacherRevisionCreate(TeacherRevisionBase):
    task_id: int
    grading_result_id: int
    teacher_id: Optional[int] = None


class TeacherRevisionRead(TeacherRevisionBase):
    id: int
    task_id: int
    grading_result_id: int
    teacher_id: Optional[int]
    previous_score: Optional[float] = None
    previous_comment: Optional[str] = None
    created_at: datetime


class TeacherReviewUpdate(BaseModel):
    final_score: float = Field(..., ge=0)
    final_comment: str = Field(default="")
    revision_reason: str = Field(default="")
    review_status: ReviewStatus | None = None
    teacher_id: Optional[int] = None


from app.schemas.question import QuestionRead, QuestionRubricRead  # noqa: E402

GradeByQuestionRequest.model_rebuild()
