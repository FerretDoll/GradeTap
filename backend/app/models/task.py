from enum import Enum


class GradingTaskStatus(str, Enum):
    CREATED = "created"
    FILES_UPLOADED = "files_uploaded"
    PARSED = "parsed"
    SCORE_GENERATED = "score_generated"
    SCORE_CONFIRMED = "score_confirmed"
    STUDENTS_PREPARED = "students_prepared"
    ANSWERS_EXTRACTED = "answers_extracted"
    ANSWERS_GROUPED = "answers_grouped"
    GRADING = "grading"
    GRADED = "graded"
    REVIEWING = "reviewing"
    REVIEWED = "reviewed"
    SUMMARY_GENERATED = "summary_generated"
    FAILED = "failed"
