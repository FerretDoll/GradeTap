from __future__ import annotations

from app.models.grading import ReviewPriority
from app.schemas.grading import GradingReflectionRead, GradingResultRead


class ReviewRouterService:
    def route_review(
        self,
        grading_result: GradingResultRead,
        reflection: GradingReflectionRead | None = None,
        answer_confidence: float = 1,
        evidence_confidence: float = 1,
    ) -> dict:
        reasons: list[str] = []
        priority = ReviewPriority.LOW

        if answer_confidence < 0.8:
            reasons.append("answer_confidence_below_threshold")
            priority = ReviewPriority.MEDIUM
        if evidence_confidence < 0.8:
            reasons.append("evidence_confidence_below_threshold")
            priority = ReviewPriority.HIGH
        if grading_result.confidence < 0.8:
            reasons.append("grading_confidence_below_threshold")
            priority = ReviewPriority.HIGH
        if reflection and reflection.need_human_review:
            reasons.append("reflector_requires_human_review")
            priority = ReviewPriority.URGENT

        return {
            "review_required": bool(reasons),
            "review_priority": priority,
            "review_reasons": reasons,
        }


review_router_service = ReviewRouterService()
