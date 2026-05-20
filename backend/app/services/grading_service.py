from __future__ import annotations

import json

from sqlalchemy import delete, select

from app.db.models import GradingDeduction, GradingReflection, GradingResult, GradingTask, StudentAnswer, TeacherRevision
from app.db.session import SessionLocal
from app.models.answer import AnswerExtractionStatus
from app.models.grading import GradingStatus, ReviewPriority, ReviewStatus
from app.models.task import GradingTaskStatus
from app.prompts.grade_by_question_prompt import (
    GRADE_BY_QUESTION_OUTPUT_SCHEMA,
    build_grade_by_question_prompt,
)
from app.schemas.grading import GradingResultCreate, GradingResultRead, StudentAnswerForGrading
from app.schemas.question import QuestionRead, QuestionRubricRead
from app.services.llm_service import LLMService, llm_service


class GradingService:
    def __init__(self, llm: LLMService = llm_service) -> None:
        self._llm = llm

    def grade_by_question(
        self,
        task_id: int,
        question: QuestionRead,
        rubrics: list[QuestionRubricRead],
        student_answers: list[StudentAnswerForGrading],
    ) -> list[GradingResultCreate]:
        student_answers = [
            answer
            for answer in student_answers
            if self._answer_should_use_ai(answer)
        ]
        if not student_answers:
            return []
        self._validate_evidence_coverage(rubrics, student_answers)
        grading_input = self._build_grading_input(student_answers)
        prompt = build_grade_by_question_prompt(
            question_json=question.model_dump_json(),
            rubrics_json=json.dumps(
                [rubric.model_dump(mode="json") for rubric in rubrics],
                ensure_ascii=False,
            ),
            student_answers_with_evidence_json=json.dumps(grading_input, ensure_ascii=False),
        )
        payload = self._llm.chat_json(prompt, schema=GRADE_BY_QUESTION_OUTPUT_SCHEMA)
        return [
            GradingResultCreate(
                task_id=task_id,
                question_id=question.id,
                raw_llm_output=item,
                **item,
            )
            for item in payload.get("grading_results", [])
        ]

    def save_grading_results(
        self,
        task_id: int,
        grading_results: list[GradingResultCreate],
    ) -> list[GradingResultRead]:
        if not grading_results:
            return []

        answer_ids = [result.student_answer_id for result in grading_results]
        with SessionLocal() as db:
            existing_results = db.scalars(
                select(GradingResult).where(
                    GradingResult.task_id == task_id,
                    GradingResult.student_answer_id.in_(answer_ids),
                ),
            ).all()
            existing_by_answer_id = {
                result.student_answer_id: result
                for result in existing_results
            }
            existing_ids = [result.id for result in existing_results]
            if existing_ids:
                db.execute(delete(GradingDeduction).where(GradingDeduction.grading_result_id.in_(existing_ids)))
                db.execute(delete(GradingReflection).where(GradingReflection.grading_result_id.in_(existing_ids)))
                db.execute(delete(TeacherRevision).where(TeacherRevision.grading_result_id.in_(existing_ids)))

            saved_results: list[GradingResult] = []
            for result in grading_results:
                values = result.model_dump(mode="json")
                values["dimension_scores"] = [
                    item.model_dump(mode="json")
                    for item in result.dimension_scores
                ]
                grading_result = existing_by_answer_id.get(result.student_answer_id)
                if grading_result is None:
                    grading_result = GradingResult(**values)
                    db.add(grading_result)
                else:
                    for key, value in values.items():
                        setattr(grading_result, key, value)
                saved_results.append(grading_result)

            task = db.get(GradingTask, task_id)
            if task is not None:
                task.status = GradingTaskStatus.GRADED

            db.commit()
            return [self._to_grading_result_read(result) for result in saved_results]

    def list_grading_results(self, task_id: int) -> list[GradingResultRead]:
        with SessionLocal() as db:
            self._ensure_missing_answer_results(db, task_id)
            db.commit()
            results = db.scalars(
                select(GradingResult)
                .where(GradingResult.task_id == task_id)
                .order_by(GradingResult.student_submission_id, GradingResult.question_id),
            ).all()
            return [self._to_grading_result_read(result) for result in results]

    def _answer_should_use_ai(self, answer: StudentAnswerForGrading) -> bool:
        return bool(str(answer.answer_text or "").strip())

    def _ensure_missing_answer_results(self, db, task_id: int) -> None:
        missing_answers = db.scalars(
            select(StudentAnswer)
            .where(StudentAnswer.task_id == task_id)
            .where(
                (StudentAnswer.extraction_status == AnswerExtractionStatus.MISSING)
                | (StudentAnswer.answer_text == "")
            )
            .order_by(StudentAnswer.student_submission_id, StudentAnswer.question_id),
        ).all()
        if not missing_answers:
            return

        answer_ids = [answer.id for answer in missing_answers]
        existing_results = db.scalars(
            select(GradingResult).where(
                GradingResult.task_id == task_id,
                GradingResult.student_answer_id.in_(answer_ids),
            ),
        ).all()
        existing_by_answer_id = {
            result.student_answer_id: result
            for result in existing_results
        }
        for answer in missing_answers:
            result = existing_by_answer_id.get(answer.id)
            values = {
                "task_id": task_id,
                "question_id": answer.question_id,
                "student_answer_id": answer.id,
                "student_submission_id": answer.student_submission_id,
                "score": 0,
                "final_score": None,
                "dimension_scores": [],
                "grading_status": GradingStatus.MISSING,
                "confidence": 1,
                "ai_comment": "缺答，记 0 分。",
                "final_comment": None,
                "review_required": False,
                "review_priority": ReviewPriority.LOW,
                "review_status": ReviewStatus.AI_GENERATED,
                "raw_llm_output": {"source": "system_missing_answer"},
            }
            if result is None:
                db.add(GradingResult(**values))
            else:
                for key, value in values.items():
                    setattr(result, key, value)

    def _validate_evidence_coverage(
        self,
        rubrics: list[QuestionRubricRead],
        student_answers: list[StudentAnswerForGrading],
    ) -> None:
        rubric_ids = {rubric.id for rubric in rubrics}
        if not rubric_ids:
            raise ValueError("grade_by_question requires at least one rubric dimension.")
        if not student_answers:
            raise ValueError("grade_by_question requires at least one student answer.")

        for answer in student_answers:
            evidence_rubric_ids = {item.rubric_id for item in answer.structured_evidence}
            missing_rubric_ids = rubric_ids - evidence_rubric_ids
            if missing_rubric_ids:
                missing = ", ".join(str(rubric_id) for rubric_id in sorted(missing_rubric_ids))
                raise ValueError(
                    "student_answer_id "
                    f"{answer.student_answer_id} is missing structured evidence for rubric_id(s): {missing}"
                )

    def _build_grading_input(self, student_answers: list[StudentAnswerForGrading]) -> list[dict]:
        return [
            {
                "student_answer_id": answer.student_answer_id,
                "student_submission_id": answer.student_submission_id,
                "student_id": answer.student_id,
                "student_no": answer.student_no,
                "student_name": answer.student_name,
                "answer_text": answer.answer_text,
                "answer_confidence": answer.answer_confidence,
                "structured_evidence": [
                    {
                        "evidence_id": evidence.id,
                        "rubric_id": evidence.rubric_id,
                        "positive_evidence": evidence.positive_evidence,
                        "negative_evidence": evidence.negative_evidence,
                        "confidence": evidence.confidence,
                    }
                    for evidence in answer.structured_evidence
                ],
            }
            for answer in student_answers
        ]

    def _to_grading_result_read(self, result: GradingResult) -> GradingResultRead:
        return GradingResultRead(
            id=result.id,
            task_id=result.task_id,
            question_id=result.question_id,
            student_answer_id=result.student_answer_id,
            student_submission_id=result.student_submission_id,
            score=result.score,
            final_score=result.final_score,
            dimension_scores=result.dimension_scores or [],
            grading_status=result.grading_status,
            confidence=result.confidence,
            ai_comment=result.ai_comment,
            final_comment=result.final_comment,
            review_required=result.review_required,
            review_priority=result.review_priority,
            review_status=result.review_status,
            raw_llm_output=result.raw_llm_output,
            created_at=result.created_at,
            updated_at=result.updated_at,
        )


grading_service = GradingService()
