from enum import Enum


class FileRole(str, Enum):
    REQUIREMENT = "requirement"
    REFERENCE_ANSWER = "reference_answer"
    STUDENT_SUBMISSION = "student_submission"
    REPORT = "report"
