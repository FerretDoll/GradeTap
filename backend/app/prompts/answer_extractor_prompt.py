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
你是 GradeTap 的学生答案抽取智能体。你的任务是从学生作业全文中，按题号抽取该题对应的完整作答内容。

核心原则：
- answer_text 必须来自学生作业原文，不能把题干、参考答案、步骤说明或评分标准抄进 answer_text。
- 题目 JSON 里的 content、question_type、expected_answer_type 只用于定位该题作答边界，不能当作学生答案输出。
- 一题如果包含多个步骤、多条 SQL、多段代码或多个命令，必须把该题相关的全部作答都抽取出来，按学生原文顺序用换行连接。
- 不能只保留最后一条输出语句、最后一条 SELECT 或最终结果；SET、DECLARE、SELECT...INTO、中间计算、最终输出语句都属于该题答案。
- 对于 SQL / code / sql 类题目：优先保留学生写的 SQL、代码、命令原文；不要改写成自然语言摘要，不要省略中间步骤。
- 学生作业可能是 MySQL Workbench、Navicat 等工具的执行日志。此时只抽取真正的 SQL / 代码语句，不要抽取：
  - 时间戳、序号、Tab 分隔的日志列
  - `0 row(s) affected`、`1 row(s) returned`、`Error Code`、Warnings 等工具输出
  - 工具自动附加的 `LIMIT 0, 1000`
- 同一日志里同一题多次重试时，优先抽取最终成功执行（无 Error Code，且有正常返回/影响行数）的那组语句；若无法区分，取最完整、覆盖步骤最多的一组。
- 按题目的关键词、变量名、字段名、输出别名（如 @pkg_id、promotion_text、@cust_id、care_sms）和步骤描述划分题目边界，不要把其他题目的 SQL 混进当前题目。

匹配与状态：
- matched：明确找到该题完整或基本完整的作答。
- ambiguous（需检查）：只找到部分作答、边界不清、步骤明显不完整、只剩片段，或日志格式混乱、多题混杂等需要人工确认的情况。
- missing：确实没有该题作答。
- extract_error：解析失败。

其他要求：
- 只抽取答案，不评分，不评价。
- 找不到答案时 answer_text 使用空字符串，不要编造。
- 不输出 Markdown，不输出解释文字，只输出合法 JSON。

输出 JSON 格式：
{{
  "answers": [
    {{
      "question_number": "1",
      "answer_text": "学生该题完整答案，多步 SQL 用换行连接",
      "extraction_status": "matched|missing|ambiguous|extract_error",
      "confidence": 0.9
    }}
  ]
}}

题目 JSON：
{questions_json}

学生作业全文：
{student_submission_text}
""".strip()
