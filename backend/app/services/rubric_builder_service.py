from __future__ import annotations

import json

from app.prompts.rubric_builder_prompt import (
    RUBRIC_BUILDER_OUTPUT_SCHEMA,
    build_rubric_builder_prompt,
)
from app.schemas.question import QuestionCreate, QuestionRubricBase
from app.services.llm_service import LLMService, llm_service


class RubricBuilderService:
    def __init__(self, llm: LLMService = llm_service) -> None:
        self._llm = llm

    def build_rubrics(
        self,
        questions: list[QuestionCreate],
        reference_answer_text: str = "",
        grading_instruction: str = "",
    ) -> list[QuestionCreate]:
        prompt = build_rubric_builder_prompt(
            questions_json=json.dumps([question.model_dump() for question in questions], ensure_ascii=False),
            reference_answer_text=reference_answer_text,
            grading_instruction=grading_instruction,
        )
        payload = self._llm.chat_json(prompt, schema=RUBRIC_BUILDER_OUTPUT_SCHEMA)
        rubric_map = {
            item.get("question_number"): [
                QuestionRubricBase(**rubric) for rubric in item.get("rubrics", [])
            ]
            for item in payload.get("questions", [])
        }
        return [
            question.model_copy(update={"rubrics": rubric_map.get(question.question_number, [])})
            for question in questions
        ]


rubric_builder_service = RubricBuilderService()
