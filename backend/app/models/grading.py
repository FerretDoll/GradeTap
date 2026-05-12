from enum import Enum


class GradingStatus(str, Enum):
    CORRECT = "correct"
    PARTIAL = "partial"
    INCORRECT = "incorrect"
    MISSING = "missing"
    NEED_REVIEW = "need_review"
    EXTRACT_ERROR = "extract_error"
    EVIDENCE_ERROR = "evidence_error"


class ReviewStatus(str, Enum):
    AI_GENERATED = "ai_generated"
    TEACHER_CONFIRMED = "teacher_confirmed"
    TEACHER_MODIFIED = "teacher_modified"
    SYSTEM_REGRADED = "system_regraded"


class ReviewPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class ReflectionStatus(str, Enum):
    PASSED = "passed"
    ISSUE_FOUND = "issue_found"
    NEED_REGRADE = "need_regrade"
    NEED_HUMAN_REVIEW = "need_human_review"


class SuggestedAction(str, Enum):
    KEEP_SCORE = "keep_score"
    REGRADE = "regrade"
    HUMAN_REVIEW = "human_review"
