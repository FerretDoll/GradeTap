from __future__ import annotations


RUBRIC_BUILDER_OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["questions"],
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["question_number", "rubrics"],
            },
        },
    },
}


def build_rubric_builder_prompt(
    questions_json: str,
    reference_answer_text: str = "",
    grading_instruction: str = "",
) -> str:
    return f"""
你是 GradeTap 的评分量规生成智能体。你的任务是为每道题生成可执行、可复核的评分量规。

要求：
- 每道题必须包含一个或多个评分维度。
- 每个评分维度必须包含维度名称、维度说明、维度分值、得分条件、扣分条件和证据要求。
- 每道题所有维度 max_score 之和必须等于该题 total_score。
- 证据要求要说明评分前需要从学生答案中找什么正向证据和负向证据。
- 不批改学生答案，不输出 Markdown，不输出解释文字，只输出合法 JSON。

输出 JSON 格式：
{{
  "questions": [
    {{
      "question_number": "1",
      "rubrics": [
        {{
          "dimension_name": "概念理解",
          "dimension_description": "考查学生是否理解核心概念",
          "max_score": 5,
          "scoring_criteria": "完整说明核心概念可得满分",
          "deduction_criteria": "概念混淆、遗漏关键点应扣分",
          "evidence_requirement": "需要找到学生对核心概念的准确表述",
          "sort_order": 1
        }}
      ]
    }}
  ]
}}

题目 JSON：
{questions_json}

参考答案：
{reference_answer_text}

教师补充说明：
{grading_instruction}
""".strip()
