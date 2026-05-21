from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.grading import ReviewStatus


class ExportTeacherRevision(BaseModel):
    grading_result_id: int | None = None
    student_answer_id: int | None = None
    student_submission_id: int | None = None
    question_id: int | None = None
    final_score: float = Field(..., ge=0)
    final_comment: str = ""
    teacher_comment: str = ""
    revision_reason: str = ""
    review_status: ReviewStatus = ReviewStatus.TEACHER_MODIFIED


class ExportResultsRequest(BaseModel):
    teacher_revisions: list[ExportTeacherRevision] = Field(default_factory=list)
