from __future__ import annotations

import json

from app.prompts.evidence_extractor_prompt import (
    EVIDENCE_EXTRACTOR_OUTPUT_SCHEMA,
    build_evidence_extractor_prompt,
)
from app.schemas.answer import StudentAnswerRead
from app.schemas.evidence import AnswerEvidenceCreate
from app.schemas.question import QuestionRead, QuestionRubricRead
from app.services.llm_service import LLMService, llm_service


class EvidenceExtractorService:
    def __init__(self, llm: LLMService = llm_service) -> None:
        self._llm = llm

    def extract_evidence(
        self,
        task_id: int,
        question: QuestionRead,
        student_answer: StudentAnswerRead,
        rubrics: list[QuestionRubricRead],
        student_id: int | None = None,
    ) -> list[AnswerEvidenceCreate]:
        prompt = build_evidence_extractor_prompt(
            question_json=question.model_dump_json(),
            rubrics_json=json.dumps(
                [rubric.model_dump(mode="json") for rubric in rubrics],
                ensure_ascii=False,
            ),
            answer_text=student_answer.answer_text,
        )
        payload = self._llm.chat_json(prompt, schema=EVIDENCE_EXTRACTOR_OUTPUT_SCHEMA)
        return [
            AnswerEvidenceCreate(
                task_id=task_id,
                question_id=question.id,
                student_id=student_id,
                student_answer_id=student_answer.id,
                rubric_id=item.get("rubric_id"),
                positive_evidence=item.get("positive_evidence", []),
                negative_evidence=item.get("negative_evidence", []),
                confidence=item.get("confidence", 0),
                raw_llm_output=item,
            )
            for item in payload.get("evidence_items", [])
        ]


evidence_extractor_service = EvidenceExtractorService()
