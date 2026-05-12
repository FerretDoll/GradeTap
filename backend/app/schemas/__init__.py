"""Pydantic schemas."""

from app.schemas.answer import (
    StudentAnswerCreate,
    StudentAnswerRead,
    StudentSubmissionCreate,
    StudentSubmissionRead,
)
from app.schemas.class_group import ClassGroupCreate, ClassGroupRead, ClassGroupUpdate
from app.schemas.course import CourseCreate, CourseRead, CourseUpdate
from app.schemas.evidence import (
    AnswerEvidenceBatchRead,
    AnswerEvidenceCreate,
    AnswerEvidenceRead,
    RubricEvidenceBase,
)
from app.schemas.file import UploadedFileCreate, UploadedFileRead
from app.schemas.grading import (
    DimensionScore,
    EvidenceForGrading,
    GradeByQuestionRequest,
    GradeByQuestionResponse,
    GradingReflectionCreate,
    GradingReflectionRead,
    GradingResultCreate,
    GradingResultRead,
    StudentAnswerForGrading,
    TeacherRevisionCreate,
    TeacherRevisionRead,
)
from app.schemas.question import (
    QuestionCreate,
    QuestionRead,
    QuestionRubricCreate,
    QuestionRubricRead,
    QuestionRubricUpdate,
    QuestionUpdate,
    TaskQuestionsUpdate,
)
from app.schemas.task import GradingTaskCreate, GradingTaskRead

__all__ = [
    "AnswerEvidenceBatchRead",
    "AnswerEvidenceCreate",
    "AnswerEvidenceRead",
    "ClassGroupCreate",
    "ClassGroupRead",
    "ClassGroupUpdate",
    "CourseCreate",
    "CourseRead",
    "CourseUpdate",
    "DimensionScore",
    "EvidenceForGrading",
    "GradeByQuestionRequest",
    "GradeByQuestionResponse",
    "GradingReflectionCreate",
    "GradingReflectionRead",
    "GradingResultCreate",
    "GradingResultRead",
    "GradingTaskCreate",
    "GradingTaskRead",
    "QuestionCreate",
    "QuestionRead",
    "QuestionRubricCreate",
    "QuestionRubricRead",
    "QuestionRubricUpdate",
    "QuestionUpdate",
    "RubricEvidenceBase",
    "StudentAnswerForGrading",
    "StudentAnswerCreate",
    "StudentAnswerRead",
    "StudentSubmissionCreate",
    "StudentSubmissionRead",
    "TaskQuestionsUpdate",
    "TeacherRevisionCreate",
    "TeacherRevisionRead",
    "UploadedFileCreate",
    "UploadedFileRead",
]
