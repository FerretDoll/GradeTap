from __future__ import annotations

import re
from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.db.models import (
    AnswerEvidence,
    AnswerGroup,
    AnswerGroupMember,
    ClassGroup,
    ClassStudent,
    GradingDeduction,
    GradingReflection,
    GradingResult,
    GradingTask,
    PlagiarismCheck,
    PlagiarismMatch,
    StudentAnswer,
    StudentPlagiarismSummary,
    StudentSubmission,
    TeacherRevision,
    UploadedFile,
)
from app.db.session import SessionLocal
from app.models.file import FileRole
from app.models.task import GradingTaskStatus
from app.schemas.answer import StudentFileMatchRead, StudentPrepareResponse


@dataclass(frozen=True)
class FileCandidate:
    file: UploadedFile
    confidence: float
    reason: str


class StudentPrepareService:
    def prepare_students(self, task_id: int) -> StudentPrepareResponse:
        with SessionLocal() as db:
            task = db.get(GradingTask, task_id)
            if task is None:
                raise HTTPException(status_code=404, detail="Task not found")

            class_group = self._find_task_class_group(db, task)
            if class_group is None:
                raise HTTPException(status_code=400, detail=f"未找到任务班级：{task.class_name}")

            students = db.scalars(
                select(ClassStudent)
                .where(ClassStudent.class_group_id == class_group.id)
                .order_by(ClassStudent.id),
            ).all()
            if not students:
                raise HTTPException(status_code=400, detail="该班级暂无学生，请先维护学生名单")

            files = db.scalars(
                select(UploadedFile)
                .where(
                    UploadedFile.task_id == task_id,
                    UploadedFile.file_role == FileRole.STUDENT_SUBMISSION,
                )
                .order_by(UploadedFile.id),
            ).all()
            if not files:
                raise HTTPException(status_code=400, detail="请先上传学生作业文件")

            self._clear_after_student_prepare(db, task_id)

            matches: list[StudentFileMatchRead] = []
            for student in students:
                candidates = self._match_student_files(student, files)
                top_candidate = candidates[0] if candidates else None
                status = self._match_status(candidates)
                submission_id = None
                if status == "matched" and top_candidate is not None:
                    submission = StudentSubmission(
                        task_id=task_id,
                        source_file_id=top_candidate.file.id,
                        student_no=student.student_no,
                        student_name=student.student_name,
                        content=top_candidate.file.parsed_text,
                    )
                    db.add(submission)
                    db.flush()
                    submission_id = submission.id

                matches.append(
                    StudentFileMatchRead(
                        student_id=student.id,
                        student_name=student.student_name,
                        student_no=student.student_no,
                        match_status=status,
                        matched_file_id=top_candidate.file.id if top_candidate else None,
                        matched_file_name=top_candidate.file.file_name if top_candidate else "",
                        confidence=top_candidate.confidence if top_candidate else 0,
                        reason=top_candidate.reason if top_candidate else "未在文件名或解析文本中找到学生姓名/学号",
                        candidate_files=[candidate.file.file_name for candidate in candidates[:3]],
                        submission_id=submission_id,
                    ),
                )

            task.status = GradingTaskStatus.STUDENTS_PREPARED
            db.commit()

            matched_count = sum(1 for item in matches if item.match_status == "matched")
            ambiguous_count = sum(1 for item in matches if item.match_status == "ambiguous")
            missing_count = len(matches) - matched_count - ambiguous_count
            return StudentPrepareResponse(
                task_id=task_id,
                status=task.status.value,
                matched_count=matched_count,
                total_students=len(matches),
                missing_count=missing_count,
                ambiguous_count=ambiguous_count,
                matches=matches,
            )

    def _find_task_class_group(self, db: Session, task: GradingTask) -> ClassGroup | None:
        return db.scalars(
            select(ClassGroup)
            .where(ClassGroup.class_name == task.class_name)
            .order_by(ClassGroup.id.desc()),
        ).first()

    def _match_student_files(self, student: ClassStudent, files: list[UploadedFile]) -> list[FileCandidate]:
        candidates = [candidate for file in files if (candidate := self._score_file(student, file))]
        return sorted(candidates, key=lambda item: item.confidence, reverse=True)

    def _score_file(self, student: ClassStudent, file: UploadedFile) -> FileCandidate | None:
        filename_text = self._normalize_text(file.file_name)
        full_text = self._normalize_text(f"{file.file_name}\n{file.parsed_text}")
        student_name = self._normalize_text(student.student_name)
        student_no = self._normalize_text(student.student_no)

        confidence = 0.0
        reasons: list[str] = []
        if student_no:
            if student_no in filename_text:
                confidence = max(confidence, 0.96)
                reasons.append("文件名包含学号")
            elif student_no in full_text:
                confidence = max(confidence, 0.9)
                reasons.append("文件内容包含学号")
        if student_name:
            if student_name in filename_text:
                confidence = max(confidence, 0.88)
                reasons.append("文件名包含姓名")
            elif student_name in full_text:
                confidence = max(confidence, 0.78)
                reasons.append("文件内容包含姓名")

        if student_no and student_name and student_no in full_text and student_name in full_text:
            confidence = max(confidence, 0.98)
            if "姓名与学号均匹配" not in reasons:
                reasons.append("姓名与学号均匹配")

        if confidence < 0.75:
            return None
        return FileCandidate(file=file, confidence=round(confidence, 2), reason="、".join(reasons))

    def _match_status(self, candidates: list[FileCandidate]) -> str:
        if not candidates:
            return "missing"
        if len(candidates) == 1:
            return "matched"
        if candidates[0].confidence - candidates[1].confidence < 0.08:
            return "ambiguous"
        return "matched"

    def _normalize_text(self, value: str | None) -> str:
        return re.sub(r"\s+", "", value or "").lower()

    def _clear_after_student_prepare(self, db: Session, task_id: int) -> None:
        result_ids = select(GradingResult.id).where(GradingResult.task_id == task_id)
        db.execute(delete(GradingDeduction).where(GradingDeduction.grading_result_id.in_(result_ids)))
        db.execute(
            delete(GradingReflection).where(
                or_(
                    GradingReflection.grading_result_id.in_(result_ids),
                    GradingReflection.task_id == task_id,
                ),
            ),
        )
        db.execute(
            delete(TeacherRevision).where(
                or_(
                    TeacherRevision.grading_result_id.in_(result_ids),
                    TeacherRevision.task_id == task_id,
                ),
            ),
        )
        db.execute(delete(GradingResult).where(GradingResult.task_id == task_id))
        db.execute(delete(AnswerEvidence).where(AnswerEvidence.task_id == task_id))

        group_ids = select(AnswerGroup.id).where(AnswerGroup.task_id == task_id)
        db.execute(delete(AnswerGroupMember).where(AnswerGroupMember.answer_group_id.in_(group_ids)))
        db.execute(delete(AnswerGroup).where(AnswerGroup.task_id == task_id))
        db.execute(delete(StudentAnswer).where(StudentAnswer.task_id == task_id))
        db.execute(delete(PlagiarismMatch).where(PlagiarismMatch.task_id == task_id))
        db.execute(delete(StudentPlagiarismSummary).where(StudentPlagiarismSummary.task_id == task_id))
        db.execute(delete(PlagiarismCheck).where(PlagiarismCheck.task_id == task_id))
        db.execute(delete(StudentSubmission).where(StudentSubmission.task_id == task_id))


student_prepare_service = StudentPrepareService()
