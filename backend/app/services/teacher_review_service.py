from __future__ import annotations

from app.models.grading import ReviewStatus
from app.schemas.grading import GradingResultRead, TeacherRevisionCreate


class TeacherReviewService:
    def create_revision(
        self,
        task_id: int,
        grading_result: GradingResultRead,
        final_score: float,
        final_comment: str = "",
        revision_reason: str = "",
        teacher_id: int | None = None,
    ) -> TeacherRevisionCreate:
        review_status = (
            ReviewStatus.TEACHER_CONFIRMED
            if final_score == grading_result.score and not revision_reason
            else ReviewStatus.TEACHER_MODIFIED
        )
        return TeacherRevisionCreate(
            task_id=task_id,
            grading_result_id=grading_result.id,
            teacher_id=teacher_id,
            final_score=final_score,
            final_comment=final_comment,
            revision_reason=revision_reason,
            review_status=review_status,
        )


teacher_review_service = TeacherReviewService()
