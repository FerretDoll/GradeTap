PIPELINE_STAGES = [
    "parse_files",
    "set_score",
    "prepare_students",
    "extract_answers",
    "group_answers",
    "grade_by_question",
    "teacher_review",
    "summary",
]


def describe_pipeline() -> list[str]:
    return PIPELINE_STAGES.copy()
