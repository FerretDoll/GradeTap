from __future__ import annotations


ANSWER_EXTRACTOR_OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["answers"],
    "properties": {
        "answers": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["question_number", "answer_text", "extraction_status", "confidence"],
            },
        },
    },
}


def build_answer_extractor_prompt(questions_json: str, student_submission_text: str) -> str:
    return f"""
你是 GradeTap 的学生答案抽取智能体。你的任务是根据题目列表，从学生作业中按题抽取答案。

要求：
- 只抽取答案，不评分，不评价。
- 优先按题号、标题和题干线索匹配。
- 每题输出 matched、missing、ambiguous、manual_check 或 extract_error。
- 找不到答案时 answer_text 使用空字符串，不要编造。
- 不输出 Markdown，不输出解释文字，只输出合法 JSON。

输出 JSON 格式：
{{
  "answers": [
    {{
      "question_number": "1",
      "answer_text": "学生该题答案",
      "extraction_status": "matched|missing|ambiguous|manual_check|extract_error",
      "confidence": 0.9
    }}
  ]
}}

题目 JSON：
{questions_json}

学生作业全文：
{student_submission_text}
""".strip()
