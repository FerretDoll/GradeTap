from __future__ import annotations

import json

from app.prompts.reflector_prompt import REFLECTOR_OUTPUT_SCHEMA, build_reflector_prompt
from app.schemas.grading import GradingReflectionCreate, GradingResultRead
from app.schemas.question import QuestionRead, QuestionRubricRead
from app.services.llm_service import LLMService, llm_service


class ReflectorService:
    def __init__(self, llm: LLMService = llm_service) -> None:
        self._llm = llm

    def reflect_grading(
        self,
        task_id: int,
        question: QuestionRead,
        rubrics: list[QuestionRubricRead],
        evidence_items: list[dict],
        grading_result: GradingResultRead,
    ) -> GradingReflectionCreate:
        prompt = build_reflector_prompt(
            question_json=question.model_dump_json(),
            rubrics_json=json.dumps(
                [rubric.model_dump(mode="json") for rubric in rubrics],
                ensure_ascii=False,
            ),
            evidence_json=json.dumps(evidence_items, ensure_ascii=False),
            grading_result_json=grading_result.model_dump_json(),
        )
        payload = self._llm.chat_json(prompt, schema=REFLECTOR_OUTPUT_SCHEMA)
        return GradingReflectionCreate(
            task_id=task_id,
            grading_result_id=grading_result.id,
            raw_llm_output=payload,
            **payload,
        )


reflector_service = ReflectorService()
