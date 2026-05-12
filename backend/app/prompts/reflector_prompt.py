from __future__ import annotations


REFLECTOR_OUTPUT_SCHEMA = {
    "type": "object",
    "required": [
        "reflection_status",
        "issues",
        "suggested_action",
        "calibrated_score",
        "need_human_review",
    ],
}


def build_reflector_prompt(
    question_json: str,
    rubrics_json: str,
    evidence_json: str,
    grading_result_json: str,
) -> str:
    return f"""
你是 GradeTap 的评分反思校准智能体。你的任务是检查 AI 初批是否与题目、量规和结构化证据一致。

至少检查：
- 总分是否等于各维度得分之和。
- 是否存在负向证据却给满分。
- 是否存在无正向证据却给高分。
- 是否存在空答案给分。
- 是否存在超过满分。
- 扣分理由是否与量规和证据匹配。
- 字段是否缺失或 JSON 异常。

要求：
- 不重新完整批改；只做一致性检查和必要校准建议。
- 不输出 Markdown，不输出解释文字，只输出合法 JSON。

输出 JSON 格式：
{{
  "reflection_status": "passed|issue_found|need_regrade|need_human_review",
  "issues": ["发现的问题"],
  "suggested_action": "keep_score|regrade|human_review",
  "calibrated_score": 8,
  "need_human_review": false
}}

题目 JSON：
{question_json}

评分量规 JSON：
{rubrics_json}

结构化证据 JSON：
{evidence_json}

AI 初批结果 JSON：
{grading_result_json}
""".strip()
