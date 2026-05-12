PIPELINE_STAGES = [
    "parse_files",
    "analyze_questions",
    "build_rubrics",
    "wait_for_teacher_confirm_rubrics",
    "prepare_students",
    "extract_answers",
    "extract_evidence",
    "grade_by_question",
    "reflect_grading",
    "route_review",
    "wait_for_teacher_review",
    "export_results",
    "summary",
]


def describe_pipeline() -> list[str]:
    return PIPELINE_STAGES.copy()
