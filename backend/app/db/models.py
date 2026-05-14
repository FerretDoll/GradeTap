from __future__ import annotations

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.answer import AnswerExtractionStatus
from app.models.file import FileRole
from app.models.grading import GradingStatus, ReflectionStatus, ReviewPriority, ReviewStatus, SuggestedAction
from app.models.question import DifficultyLevel, QuestionType
from app.models.task import GradingTaskStatus


def enum_values(enum_cls: type) -> list[str]:
    return [item.value for item in enum_cls]


class TimestampMixin:
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Course(TimestampMixin, Base):
    __tablename__ = "course"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    assignment_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    assignments: Mapped[list["CourseAssignment"]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
    )


class CourseAssignment(TimestampMixin, Base):
    __tablename__ = "course_assignment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("course.id"), nullable=False)
    assignment_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    total_score: Mapped[float] = mapped_column(Float, default=100, nullable=False)
    questions_payload: Mapped[list | None] = mapped_column(JSON, nullable=True)
    rubrics_payload: Mapped[list | None] = mapped_column(JSON, nullable=True)
    rubric_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rubric_confirmed_at: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)

    course: Mapped[Course] = relationship(back_populates="assignments")
    files: Mapped[list["CourseAssignmentFile"]] = relationship(
        back_populates="assignment",
        cascade="all, delete-orphan",
    )
    questions: Mapped[list["CourseAssignmentQuestion"]] = relationship(
        back_populates="assignment",
        cascade="all, delete-orphan",
    )


class CourseAssignmentFile(TimestampMixin, Base):
    __tablename__ = "course_assignment_file"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("course_assignment.id"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_role: Mapped[FileRole] = mapped_column(Enum(FileRole, values_callable=enum_values), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), default="", nullable=False)
    parsed_text: Mapped[str] = mapped_column(Text, default="", nullable=False)

    assignment: Mapped[CourseAssignment] = relationship(back_populates="files")


class CourseAssignmentQuestion(TimestampMixin, Base):
    __tablename__ = "course_assignment_question"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("course_assignment.id"), nullable=False)
    question_number: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[QuestionType] = mapped_column(Enum(QuestionType, values_callable=enum_values), nullable=False)
    knowledge_points: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    difficulty: Mapped[DifficultyLevel] = mapped_column(Enum(DifficultyLevel, values_callable=enum_values), nullable=False)
    expected_answer_type: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    total_score: Mapped[float] = mapped_column(Float, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    assignment: Mapped[CourseAssignment] = relationship(back_populates="questions")
    rubrics: Mapped[list["CourseAssignmentQuestionRubric"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
    )


class CourseAssignmentQuestionRubric(TimestampMixin, Base):
    __tablename__ = "course_assignment_question_rubric"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assignment_question_id: Mapped[int] = mapped_column(ForeignKey("course_assignment_question.id"), nullable=False)
    dimension_name: Mapped[str] = mapped_column(String(255), nullable=False)
    dimension_description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    max_score: Mapped[float] = mapped_column(Float, nullable=False)
    scoring_criteria: Mapped[str] = mapped_column(Text, nullable=False)
    deduction_criteria: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_requirement: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    question: Mapped[CourseAssignmentQuestion] = relationship(back_populates="rubrics")


class ClassGroup(TimestampMixin, Base):
    __tablename__ = "class"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    class_name: Mapped[str] = mapped_column(String(255), nullable=False)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    student_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    students: Mapped[list["ClassStudent"]] = relationship(
        back_populates="class_group",
        cascade="all, delete-orphan",
    )


class ClassStudent(TimestampMixin, Base):
    __tablename__ = "class_student"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    class_group_id: Mapped[int] = mapped_column(ForeignKey("class.id"), nullable=False)
    student_name: Mapped[str] = mapped_column(String(255), nullable=False)
    student_no: Mapped[str] = mapped_column(String(64), default="", nullable=False)

    class_group: Mapped[ClassGroup] = relationship(back_populates="students")


class SystemSetting(TimestampMixin, Base):
    __tablename__ = "system_setting"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    setting_key: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    setting_value: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)


class GradingTask(TimestampMixin, Base):
    __tablename__ = "grading_task"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_name: Mapped[str] = mapped_column(String(255), nullable=False)
    course_name: Mapped[str] = mapped_column(String(255), nullable=False)
    class_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[GradingTaskStatus] = mapped_column(
        Enum(GradingTaskStatus, values_callable=enum_values),
        default=GradingTaskStatus.CREATED,
        nullable=False,
    )
    grading_instruction: Mapped[str] = mapped_column(Text, default="", nullable=False)

    files: Mapped[list["UploadedFile"]] = relationship(back_populates="task")
    questions: Mapped[list["Question"]] = relationship(back_populates="task")
    submissions: Mapped[list["StudentSubmission"]] = relationship(back_populates="task")


class UploadedFile(TimestampMixin, Base):
    __tablename__ = "uploaded_file"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("grading_task.id"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_role: Mapped[FileRole] = mapped_column(Enum(FileRole, values_callable=enum_values), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), default="", nullable=False)
    parsed_text: Mapped[str] = mapped_column(Text, default="", nullable=False)

    task: Mapped[GradingTask] = relationship(back_populates="files")


class Question(TimestampMixin, Base):
    __tablename__ = "question"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("grading_task.id"), nullable=False)
    question_number: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[QuestionType] = mapped_column(Enum(QuestionType, values_callable=enum_values), nullable=False)
    knowledge_points: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    difficulty: Mapped[DifficultyLevel] = mapped_column(Enum(DifficultyLevel, values_callable=enum_values), nullable=False)
    expected_answer_type: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    total_score: Mapped[float] = mapped_column(Float, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    task: Mapped[GradingTask] = relationship(back_populates="questions")
    rubrics: Mapped[list["QuestionRubric"]] = relationship(back_populates="question")


class QuestionRubric(TimestampMixin, Base):
    __tablename__ = "question_rubric"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("question.id"), nullable=False)
    dimension_name: Mapped[str] = mapped_column(String(255), nullable=False)
    dimension_description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    max_score: Mapped[float] = mapped_column(Float, nullable=False)
    scoring_criteria: Mapped[str] = mapped_column(Text, nullable=False)
    deduction_criteria: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_requirement: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    question: Mapped[Question] = relationship(back_populates="rubrics")


class StudentSubmission(TimestampMixin, Base):
    __tablename__ = "student_submission"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("grading_task.id"), nullable=False)
    source_file_id: Mapped[int | None] = mapped_column(ForeignKey("uploaded_file.id"), nullable=True)
    student_no: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    student_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)

    task: Mapped[GradingTask] = relationship(back_populates="submissions")


class StudentAnswer(TimestampMixin, Base):
    __tablename__ = "student_answer"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("grading_task.id"), nullable=False)
    question_id: Mapped[int] = mapped_column(ForeignKey("question.id"), nullable=False)
    student_submission_id: Mapped[int] = mapped_column(ForeignKey("student_submission.id"), nullable=False)
    answer_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    extraction_status: Mapped[AnswerExtractionStatus] = mapped_column(
        Enum(AnswerExtractionStatus, values_callable=enum_values),
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(Float, default=1, nullable=False)
    raw_llm_output: Mapped[str | None] = mapped_column(Text, nullable=True)


class AnswerEvidence(TimestampMixin, Base):
    __tablename__ = "answer_evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("grading_task.id"), nullable=False)
    question_id: Mapped[int] = mapped_column(ForeignKey("question.id"), nullable=False)
    student_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    student_answer_id: Mapped[int] = mapped_column(ForeignKey("student_answer.id"), nullable=False)
    rubric_id: Mapped[int] = mapped_column(ForeignKey("question_rubric.id"), nullable=False)
    positive_evidence: Mapped[list | None] = mapped_column(JSON, nullable=True)
    negative_evidence: Mapped[list | None] = mapped_column(JSON, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    raw_llm_output: Mapped[dict | str | None] = mapped_column(JSON, nullable=True)


class AnswerGroup(TimestampMixin, Base):
    __tablename__ = "answer_group"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("grading_task.id"), nullable=False)
    question_id: Mapped[int] = mapped_column(ForeignKey("question.id"), nullable=False)
    group_key: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)


class AnswerGroupMember(TimestampMixin, Base):
    __tablename__ = "answer_group_member"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    answer_group_id: Mapped[int] = mapped_column(ForeignKey("answer_group.id"), nullable=False)
    student_answer_id: Mapped[int] = mapped_column(ForeignKey("student_answer.id"), nullable=False)


class GradingResult(TimestampMixin, Base):
    __tablename__ = "grading_result"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("grading_task.id"), nullable=False)
    question_id: Mapped[int] = mapped_column(ForeignKey("question.id"), nullable=False)
    student_answer_id: Mapped[int] = mapped_column(ForeignKey("student_answer.id"), nullable=False)
    student_submission_id: Mapped[int] = mapped_column(ForeignKey("student_submission.id"), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    final_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    dimension_scores: Mapped[list | None] = mapped_column(JSON, nullable=True)
    grading_status: Mapped[GradingStatus] = mapped_column(Enum(GradingStatus, values_callable=enum_values), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    ai_comment: Mapped[str] = mapped_column(Text, default="", nullable=False)
    final_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    review_priority: Mapped[ReviewPriority] = mapped_column(Enum(ReviewPriority, values_callable=enum_values), nullable=False)
    review_status: Mapped[ReviewStatus] = mapped_column(Enum(ReviewStatus, values_callable=enum_values), nullable=False)
    raw_llm_output: Mapped[dict | str | None] = mapped_column(JSON, nullable=True)


class GradingDeduction(TimestampMixin, Base):
    __tablename__ = "grading_deduction"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    grading_result_id: Mapped[int] = mapped_column(ForeignKey("grading_result.id"), nullable=False)
    rubric_id: Mapped[int | None] = mapped_column(ForeignKey("question_rubric.id"), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    points: Mapped[float] = mapped_column(Float, nullable=False)


class GradingReflection(TimestampMixin, Base):
    __tablename__ = "grading_reflection"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("grading_task.id"), nullable=False)
    grading_result_id: Mapped[int] = mapped_column(ForeignKey("grading_result.id"), nullable=False)
    reflection_status: Mapped[ReflectionStatus] = mapped_column(Enum(ReflectionStatus, values_callable=enum_values), nullable=False)
    issues: Mapped[list | None] = mapped_column(JSON, nullable=True)
    suggested_action: Mapped[SuggestedAction] = mapped_column(Enum(SuggestedAction, values_callable=enum_values), nullable=False)
    calibrated_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    need_human_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    raw_llm_output: Mapped[dict | str | None] = mapped_column(JSON, nullable=True)


class TeacherRevision(TimestampMixin, Base):
    __tablename__ = "teacher_revision"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("grading_task.id"), nullable=False)
    grading_result_id: Mapped[int] = mapped_column(ForeignKey("grading_result.id"), nullable=False)
    teacher_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    previous_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    previous_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_score: Mapped[float] = mapped_column(Float, nullable=False)
    final_comment: Mapped[str] = mapped_column(Text, default="", nullable=False)
    revision_reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    review_status: Mapped[ReviewStatus] = mapped_column(Enum(ReviewStatus, values_callable=enum_values), nullable=False)


class AdaptiveGradingRule(TimestampMixin, Base):
    __tablename__ = "adaptive_grading_rule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("grading_task.id"), nullable=True)
    question_id: Mapped[int | None] = mapped_column(ForeignKey("question.id"), nullable=True)
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False)
    rule_content: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AuditLog(TimestampMixin, Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("grading_task.id"), nullable=True)
    actor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    target_type: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detail: Mapped[dict | str | None] = mapped_column(JSON, nullable=True)
