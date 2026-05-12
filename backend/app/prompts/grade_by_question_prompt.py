from __future__ import annotations


GRADE_BY_QUESTION_OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["grading_results"],
    "properties": {
        "grading_results": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "student_answer_id",
                    "student_submission_id",
                    "score",
                    "dimension_scores",
                    "grading_status",
                    "confidence",
                    "ai_comment",
                ],
            },
        },
    },
}


def build_grade_by_question_prompt(
    question_json: str,
    rubrics_json: str,
    student_answers_with_evidence_json: str,
) -> str:
    return f"""
你是 GradeTap 的按题评分智能体。现在只批改同一道题下的一批学生答案。

要求：
- 必须主要依据 structured_evidence 评分，不要直接从学生原文黑盒给分。
- 每个评分维度都必须给出分数和理由。
- 维度得分不得超过维度满分；总分必须等于各维度得分之和。
- 证据不足时不能随意给高分，应降低 confidence 并说明原因。
- 同一道题所有学生必须使用同一套评分量规。
- 不输出 Markdown，不输出解释文字，只输出合法 JSON。

输出 JSON 格式：
{{
  "grading_results": [
    {{
      "student_answer_id": 1,
      "student_submission_id": 1,
      "score": 8,
      "dimension_scores": [
        {{
          "rubric_id": 1,
          "dimension_name": "概念理解",
          "max_score": 5,
          "score": 4,
          "reason": "基于证据的评分理由",
          "evidence_ids": [1]
        }}
      ],
      "grading_status": "correct|partial|incorrect|missing|need_review|extract_error|evidence_error",
      "confidence": 0.86,
      "ai_comment": "给学生的简短评语",
      "review_required": false,
      "review_priority": "low|medium|high|urgent"
    }}
  ]
}}

题目 JSON：
{question_json}

评分量规 JSON：
{rubrics_json}

学生答案和结构化证据 JSON：
{student_answers_with_evidence_json}
""".strip()
