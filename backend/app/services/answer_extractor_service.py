from __future__ import annotations

import json
from typing import Any

from app.prompts.answer_extractor_prompt import (
    ANSWER_EXTRACTOR_OUTPUT_SCHEMA,
    build_answer_extractor_prompt,
)
from app.schemas.answer import StudentAnswerCreate
from app.schemas.question import QuestionRead
from app.services.llm_service import LLMService, llm_service


class AnswerExtractorService:
    def __init__(self, llm: LLMService = llm_service) -> None:
        self._llm = llm

    def extract_answers(
        self,
        task_id: int,
        student_submission_id: int,
        questions: list[QuestionRead],
        student_submission_text: str,
    ) -> list[StudentAnswerCreate]:
        prompt = build_answer_extractor_prompt(
            questions_json=json.dumps(
                [question.model_dump(mode="json") for question in questions],
                ensure_ascii=False,
            ),
            student_submission_text=student_submission_text,
        )
        payload = self._llm.chat_json(prompt, schema=ANSWER_EXTRACTOR_OUTPUT_SCHEMA)
        question_by_number = {question.question_number: question for question in questions}
        answers: list[StudentAnswerCreate] = []
        for item in payload.get("answers", []):
            question = question_by_number.get(item.get("question_number"))
            if question is None:
                continue
            answers.append(
                StudentAnswerCreate(
                    task_id=task_id,
                    question_id=question.id,
                    student_submission_id=student_submission_id,
                    answer_text=item.get("answer_text", ""),
                    extraction_status=item.get("extraction_status", "manual_check"),
                    confidence=item.get("confidence", 0),
                    raw_llm_output=json.dumps(item, ensure_ascii=False),
                )
            )
        return answers


answer_extractor_service = AnswerExtractorService()
