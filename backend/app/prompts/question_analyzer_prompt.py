from __future__ import annotations


QUESTION_ANALYZER_OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["questions"],
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "question_number",
                    "content",
                    "question_type",
                    "knowledge_points",
                    "difficulty",
                    "expected_answer_type",
                    "total_score",
                    "sort_order",
                ],
            },
        },
    },
}


def build_question_analyzer_prompt(
    requirement_text: str,
    reference_answer_text: str = "",
    grading_instruction: str = "",
) -> str:
    return f"""
你是 GradeTap 的题目分析智能体。你的任务是只分析题目结构，不批改学生答案。

要求：
- 识别每道题的题号、题干、题型、知识点、难度、期望答案类型和排序。
- 如果原文有明确分值，使用原文分值；如果没有明确分值，按总分 100 分合理分配。
- 所有题目 total_score 之和必须等于 100。
- 不输出 Markdown，不输出解释文字，只输出合法 JSON。

输出 JSON 格式：
{{
  "questions": [
    {{
      "question_number": "1",
      "content": "题干原文",
      "question_type": "single_choice|multiple_choice|true_false|fill_blank|short_answer|essay|calculation|code|sql|other",
      "knowledge_points": ["知识点"],
      "difficulty": "easy|medium|hard|unknown",
      "expected_answer_type": "期望答案类型",
      "total_score": 10,
      "sort_order": 1
    }}
  ]
}}

作业要求：
{requirement_text}

参考答案：
{reference_answer_text}

教师补充说明：
{grading_instruction}
""".strip()
