from __future__ import annotations


EVIDENCE_EXTRACTOR_OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["evidence_items"],
    "properties": {
        "evidence_items": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["rubric_id", "positive_evidence", "negative_evidence", "confidence"],
            },
        },
    },
}


def build_evidence_extractor_prompt(question_json: str, rubrics_json: str, answer_text: str) -> str:
    return f"""
你是 GradeTap 的评分证据提取智能体。你的任务是根据题目和评分量规，从学生答案中提取证据。

要求：
- 只提取证据，不给分，不判断最终对错。
- 对每个评分维度输出正向证据、负向证据和置信度。
- 找不到证据时使用空数组，不要编造。
- 证据必须来自学生答案原文或对原文的极短归纳。
- 不输出 Markdown，不输出解释文字，只输出合法 JSON。

输出 JSON 格式：
{{
  "evidence_items": [
    {{
      "rubric_id": 1,
      "positive_evidence": ["支持得分的证据"],
      "negative_evidence": ["支持扣分的证据"],
      "confidence": 0.85
    }}
  ]
}}

题目 JSON：
{question_json}

评分量规 JSON：
{rubrics_json}

学生答案：
{answer_text}
""".strip()
