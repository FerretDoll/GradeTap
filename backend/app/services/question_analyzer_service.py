from __future__ import annotations

from app.prompts.question_analyzer_prompt import (
    QUESTION_ANALYZER_OUTPUT_SCHEMA,
    build_question_analyzer_prompt,
)
from app.schemas.question import QuestionCreate
from app.services.llm_service import LLMService, llm_service


class QuestionAnalyzerService:
    def __init__(self, llm: LLMService = llm_service) -> None:
        self._llm = llm

    def analyze_questions(
        self,
        task_id: int,
        requirement_text: str,
        reference_answer_text: str = "",
        grading_instruction: str = "",
    ) -> list[QuestionCreate]:
        prompt = build_question_analyzer_prompt(
            requirement_text=requirement_text,
            reference_answer_text=reference_answer_text,
            grading_instruction=grading_instruction,
        )
        payload = self._llm.chat_json(prompt, schema=QUESTION_ANALYZER_OUTPUT_SCHEMA)
        questions = payload.get("questions", [])
        return [QuestionCreate(task_id=task_id, **item) for item in questions]


question_analyzer_service = QuestionAnalyzerService()
