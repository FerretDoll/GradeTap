from __future__ import annotations

import json
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.services.settings_service import settings_service


class LLMService:
    """Central entry point for all model calls.

    Real provider integration belongs here so grading services do not call LLM
    APIs directly.
    """

    def chat_json(
        self,
        prompt: str,
        schema: Optional[dict[str, Any]] = None,
        max_retries: int | None = None,
    ) -> dict[str, Any]:
        settings = self._get_runtime_settings()
        retries = max_retries or settings["max_retries"]
        schema_text = json.dumps(schema, ensure_ascii=False) if schema else ""
        json_prompt = prompt
        if schema_text:
            json_prompt = f"{prompt}\n\n输出必须匹配这个 JSON Schema：\n{schema_text}"

        last_error: Exception | None = None
        for _ in range(retries):
            raw_text = self._chat_completion(
                prompt=json_prompt,
                settings=settings,
                response_format={"type": "json_object"},
            )
            try:
                return self.parse_json_response(raw_text)
            except json.JSONDecodeError as exc:
                last_error = exc
                repair_prompt = self._build_json_repair_prompt(raw_text, schema_text)
                repaired_text = self._chat_completion(
                    prompt=repair_prompt,
                    settings=settings,
                    response_format={"type": "json_object"},
                )
                try:
                    return self.parse_json_response(repaired_text)
                except json.JSONDecodeError as repair_exc:
                    last_error = repair_exc
        raise ValueError("LLM did not return valid JSON") from last_error

    def chat_text(self, prompt: str, max_retries: int | None = None) -> str:
        settings = self._get_runtime_settings()
        retries = max_retries or settings["max_retries"]
        last_error: Exception | None = None
        for _ in range(retries):
            try:
                return self._chat_completion(prompt=prompt, settings=settings)
            except (HTTPError, URLError, TimeoutError, RuntimeError, ValueError) as exc:
                last_error = exc
        raise RuntimeError("LLM request failed") from last_error

    def parse_json_response(self, raw_text: str) -> dict[str, Any]:
        return json.loads(raw_text)

    def _get_runtime_settings(self) -> dict[str, Any]:
        settings = settings_service.get_llm_settings_dict(include_secret=True)
        if not settings["enabled"]:
            raise RuntimeError("LLM provider is disabled. Enable it in model settings first.")
        if not settings["api_key"]:
            raise RuntimeError("LLM API Key is missing. Configure it in model settings first.")
        if not settings["base_url"] or not settings["model"]:
            raise RuntimeError("LLM Base URL or model is missing.")
        return settings

    def _chat_completion(
        self,
        prompt: str,
        settings: dict[str, Any],
        response_format: dict[str, str] | None = None,
    ) -> str:
        url = f"{settings['base_url'].rstrip('/')}/chat/completions"
        payload: dict[str, Any] = {
            "model": settings["model"],
            "messages": [
                {
                    "role": "system",
                    "content": "你是 GradeTap 的后端模型调用层。请严格按业务提示输出。",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": settings["temperature"],
        }
        if response_format:
            payload["response_format"] = response_format

        request = Request(
            url=url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {settings['api_key']}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=120) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"LLM provider returned HTTP {exc.code}: {detail}") from exc

        choices = response_payload.get("choices") or []
        if not choices:
            raise ValueError("LLM provider returned no choices")
        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, list):
            content = "".join(str(item.get("text", "")) for item in content if isinstance(item, dict))
        if not content:
            raise ValueError("LLM provider returned empty content")
        return str(content).strip()

    def _build_json_repair_prompt(self, raw_text: str, schema_text: str = "") -> str:
        schema_instruction = f"\nJSON Schema：\n{schema_text}" if schema_text else ""
        return f"""
下面内容不是合法 JSON。请修复为合法 JSON，只输出 JSON，不输出 Markdown 或解释文字。{schema_instruction}

待修复内容：
{raw_text}
""".strip()


llm_service = LLMService()
