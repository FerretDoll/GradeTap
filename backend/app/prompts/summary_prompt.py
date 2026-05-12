from __future__ import annotations


SUMMARY_OUTPUT_SCHEMA = {
    "type": "object",
    "required": [
        "class_average",
        "highest_score",
        "lowest_score",
        "question_summaries",
        "frequent_deductions",
        "key_knowledge_points",
        "students_to_watch",
    ],
}


def build_summary_prompt(final_results_json: str) -> str:
    return f"""
你是 GradeTap 的成绩汇总智能体。你的任务是基于最终成绩生成班级分析数据。

要求：
- 优先使用 final_score；没有 final_score 时再使用 AI score。
- 至少输出班级平均分、最高分、最低分、各题平均分、得分率、高频扣分点、重点讲解知识点、需要关注学生。
- 不输出 Markdown，不输出解释文字，只输出合法 JSON。

输出 JSON 格式：
{{
  "class_average": 82.5,
  "highest_score": 98,
  "lowest_score": 56,
  "question_summaries": [
    {{
      "question_number": "1",
      "average_score": 8.2,
      "score_rate": 0.82
    }}
  ],
  "frequent_deductions": ["高频扣分点"],
  "key_knowledge_points": ["需要重点讲解的知识点"],
  "students_to_watch": [
    {{
      "student_no": "001",
      "student_name": "学生姓名",
      "reason": "需要关注的原因"
    }}
  ]
}}

最终成绩与评分明细 JSON：
{final_results_json}
""".strip()
