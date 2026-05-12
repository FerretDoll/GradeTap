from __future__ import annotations

import json

from app.prompts.grade_by_question_prompt import (
    GRADE_BY_QUESTION_OUTPUT_SCHEMA,
    build_grade_by_question_prompt,
)
from app.schemas.grading import GradingResultCreate, StudentAnswerForGrading
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


grading_service = GradingService()
