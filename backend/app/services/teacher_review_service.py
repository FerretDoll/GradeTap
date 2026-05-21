from __future__ import annotations

from sqlalchemy import select

from app.db.models import GradingResult, GradingTask, TeacherRevision
from app.db.session import SessionLocal
from app.models.grading import ReviewStatus
from app.models.task import GradingTaskStatus
from app.schemas.grading import GradingResultRead, TeacherRevisionCreate, TeacherRevisionRead


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

    def list_revisions(self, task_id: int) -> list[TeacherRevisionRead]:
        with SessionLocal() as db:
            revisions = db.scalars(
                select(TeacherRevision)
                .where(TeacherRevision.task_id == task_id)
                .order_by(TeacherRevision.grading_result_id, TeacherRevision.id.desc()),
            ).all()
            latest_by_result_id: dict[int, TeacherRevision] = {}
            for revision in revisions:
                latest_by_result_id.setdefault(revision.grading_result_id, revision)
            return [
                self._to_read_schema(revision)
                for revision in latest_by_result_id.values()
            ]

    def save_review(
        self,
        task_id: int,
        grading_result_id: int,
        final_score: float,
        final_comment: str = "",
        revision_reason: str = "",
        review_status: ReviewStatus | None = None,
        teacher_id: int | None = None,
    ) -> TeacherRevisionRead:
        with SessionLocal() as db:
            result = db.get(GradingResult, grading_result_id)
            if result is None or result.task_id != task_id:
                raise ValueError("Grading result not found")

            resolved_review_status = (
                review_status
                or (
                    ReviewStatus.TEACHER_CONFIRMED
                    if final_score == result.score
                    else ReviewStatus.TEACHER_MODIFIED
                )
            )
            previous_score = result.final_score if result.final_score is not None else result.score
            previous_comment = result.final_comment if result.final_comment is not None else result.ai_comment
            revision = TeacherRevision(
                task_id=task_id,
                grading_result_id=result.id,
                teacher_id=teacher_id,
                previous_score=previous_score,
                previous_comment=previous_comment,
                final_score=final_score,
                final_comment=final_comment,
                revision_reason=revision_reason,
                review_status=resolved_review_status,
            )
            db.add(revision)

            result.final_score = final_score
            result.final_comment = final_comment
            result.review_status = resolved_review_status
            result.review_required = False

            task = db.get(GradingTask, task_id)
            if task is not None:
                task.status = GradingTaskStatus.TEACHER_REVIEWED

            db.commit()
            db.refresh(revision)
            return self._to_read_schema(revision)

    def _to_read_schema(self, revision: TeacherRevision) -> TeacherRevisionRead:
        return TeacherRevisionRead(
            id=revision.id,
            task_id=revision.task_id,
            grading_result_id=revision.grading_result_id,
            teacher_id=revision.teacher_id,
            previous_score=revision.previous_score,
            previous_comment=revision.previous_comment,
            final_score=revision.final_score,
            final_comment=revision.final_comment,
            revision_reason=revision.revision_reason,
            review_status=revision.review_status,
            created_at=revision.created_at,
        )


teacher_review_service = TeacherReviewService()
