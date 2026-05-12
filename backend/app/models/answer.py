from enum import Enum


class AnswerExtractionStatus(str, Enum):
    MATCHED = "matched"
    MISSING = "missing"
    AMBIGUOUS = "ambiguous"
    MANUAL_CHECK = "manual_check"
    EXTRACT_ERROR = "extract_error"
