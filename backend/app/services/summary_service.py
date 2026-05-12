from __future__ import annotations

import json

from app.prompts.summary_prompt import SUMMARY_OUTPUT_SCHEMA, build_summary_prompt
from app.services.llm_service import LLMService, llm_service


class SummaryService:
    def __init__(self, llm: LLMService = llm_service) -> None:
        self._llm = llm

    def generate_summary(self, final_results: list[dict]) -> dict:
        prompt = build_summary_prompt(
            final_results_json=json.dumps(final_results, ensure_ascii=False),
        )
        return self._llm.chat_json(prompt, schema=SUMMARY_OUTPUT_SCHEMA)


summary_service = SummaryService()
