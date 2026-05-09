import json
from typing import Any


class LLMService:
    """Central entry point for all model calls.

    Real provider integration belongs here so grading services do not call LLM
    APIs directly.
    """

    def chat_json(self, prompt: str, schema: dict[str, Any] | None = None) -> dict[str, Any]:
        raise NotImplementedError("Configure an LLM provider before calling chat_json.")

    def chat_text(self, prompt: str) -> str:
        raise NotImplementedError("Configure an LLM provider before calling chat_text.")

    def parse_json_response(self, raw_text: str) -> dict[str, Any]:
        return json.loads(raw_text)


llm_service = LLMService()
