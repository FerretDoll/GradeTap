from __future__ import annotations

import json
import re
from collections.abc import Callable

from app.prompts.rubric_builder_prompt import (
    RUBRIC_BUILDER_OUTPUT_SCHEMA,
    build_rubric_builder_prompt,
)
from app.schemas.question import QuestionCreate, QuestionRubricBase
from app.services.llm_service import LLMService, llm_service
from app.services.progress_event_service import progress_event_service


class RubricBuilderService:
    def __init__(self, llm: LLMService = llm_service) -> None:
        self._llm = llm

    def build_rubrics(
        self,
        questions: list[QuestionCreate],
        reference_answer_text: str = "",
        grading_instruction: str = "",
        progress_channel: str | None = None,
    ) -> list[QuestionCreate]:
        prompt = build_rubric_builder_prompt(
            questions_json=json.dumps([question.model_dump() for question in questions], ensure_ascii=False),
            reference_answer_text=reference_answer_text,
            grading_instruction=grading_instruction,
        )
        if progress_channel:
            payload = self._llm.chat_json_stream(
                prompt,
                schema=RUBRIC_BUILDER_OUTPUT_SCHEMA,
                on_delta=self._build_delta_handler(progress_channel, "build_rubrics"),
            )
        else:
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

    def _build_delta_handler(self, channel: str | None, stage: str) -> Callable[[str], None] | None:
        if not channel:
            return None
        buffer = ""
        seen_question_numbers: set[str] = set()
        ordered_question_numbers: list[str] = []

        def on_delta(text: str) -> None:
            nonlocal buffer
            buffer += text
            current_numbers = re.findall(r'"question_number"\s*:\s*"([^"]+)"', buffer)
            new_numbers = [number for number in current_numbers if number not in seen_question_numbers]
            if not new_numbers:
                return
            seen_question_numbers.update(new_numbers)
            ordered_question_numbers.extend(new_numbers)
            progress_event_service.publish(
                channel,
                "llm_progress",
                {
                    "stage": stage,
                    "recognized_count": len(ordered_question_numbers),
                    "question_numbers": ordered_question_numbers,
                },
            )

        return on_delta


rubric_builder_service = RubricBuilderService()
