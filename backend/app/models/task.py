from enum import Enum


class GradingTaskStatus(str, Enum):
    CREATED = "created"
    FILES_UPLOADED = "files_uploaded"
    PARSED = "parsed"
    QUESTIONS_ANALYZED = "questions_analyzed"
    RUBRICS_GENERATED = "rubrics_generated"
    WAITING_RUBRIC_CONFIRM = "waiting_rubric_confirm"
    RUBRICS_CONFIRMED = "rubrics_confirmed"
    STUDENTS_PREPARED = "students_prepared"
    ANSWERS_EXTRACTED = "answers_extracted"
    EVIDENCE_EXTRACTED = "evidence_extracted"
    GRADING = "grading"
    GRADED = "graded"
    REFLECTING = "reflecting"
    REFLECTED = "reflected"
    REVIEW_ROUTED = "review_routed"
    WAITING_TEACHER_REVIEW = "waiting_teacher_review"
    TEACHER_REVIEWED = "teacher_reviewed"
    EXPORTED = "exported"
    SUMMARY_GENERATED = "summary_generated"
    FAILED = "failed"
