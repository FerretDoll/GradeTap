from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import re
import threading
from typing import Any

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import delete, select

from app.db.models import (
    AnswerEvidence,
    ClassStudent,
    Course,
    CourseAssignment,
    CourseAssignmentQuestion,
    CourseAssignmentQuestionRubric,
    GradingDeduction,
    GradingReflection,
    GradingResult,
    GradingTask,
    Question,
    QuestionRubric,
    StudentAnswer,
    StudentSubmission,
    TeacherRevision,
    UploadedFile,
)
from app.db.session import SessionLocal
from app.models.answer import AnswerExtractionStatus
from app.models.file import FileRole
from app.models.task import GradingTaskStatus
from app.prompts.answer_extractor_prompt import (
    ANSWER_EXTRACTOR_OUTPUT_SCHEMA,
    build_answer_extractor_prompt,
)
from app.schemas.answer import (
    AnswerExtractionSnapshot,
    AnswerExtractionStartResponse,
    AnswerExtractionStudentStartResponse,
    StudentAnswerCreate,
    StudentAnswerExtractionProgress,
    StudentAnswerRead,
)
from app.schemas.question import QuestionRead
from app.services.llm_service import LLMService, llm_service
from app.services.progress_event_service import progress_event_service
from app.services.student_prepare_service import student_prepare_service


class AnswerExtractorService:
    def __init__(self, llm: LLMService = llm_service) -> None:
        self._llm = llm
        self._running_task_ids: set[int] = set()
        self._running_submission_keys: set[tuple[int, int]] = set()
        self._running_lock = threading.Lock()

    def extract_answers(
        self,
        task_id: int,
        student_submission_id: int,
        questions: list[QuestionRead],
        student_submission_text: str,
        progress_channel: str | None = None,
        student_name: str = "",
        student_no: str = "",
    ) -> list[StudentAnswerCreate]:
        prompt = build_answer_extractor_prompt(
            questions_json=json.dumps(
                [question.model_dump(mode="json") for question in questions],
                ensure_ascii=False,
            ),
            student_submission_text=student_submission_text,
        )
        if progress_channel:
            payload = self._llm.chat_json_stream(
                prompt,
                schema=ANSWER_EXTRACTOR_OUTPUT_SCHEMA,
                on_delta=self._build_delta_handler(
                    channel=progress_channel,
                    task_id=task_id,
                    submission_id=student_submission_id,
                    student_name=student_name,
                    student_no=student_no,
                    total_questions=len(questions),
                ),
            )
        else:
            payload = self._llm.chat_json(prompt, schema=ANSWER_EXTRACTOR_OUTPUT_SCHEMA)
        question_by_number = {question.question_number: question for question in questions}
        answers: list[StudentAnswerCreate] = []
        for item in payload.get("answers", []):
            question = question_by_number.get(item.get("question_number"))
            if question is None:
                continue
            answer_text, extraction_status, confidence = self._normalize_extraction_item(question, item)
            answers.append(
                StudentAnswerCreate(
                    task_id=task_id,
                    question_id=question.id,
                    student_submission_id=student_submission_id,
                    answer_text=answer_text,
                    extraction_status=extraction_status,
                    confidence=confidence,
                    raw_llm_output=json.dumps(item, ensure_ascii=False),
                )
            )
        return answers

    def _clean_extracted_answer_text(self, answer_text: str) -> str:
        cleaned = str(answer_text or "").strip()
        cleaned = re.sub(r"\s*LIMIT\s+0\s*,\s*1000\s*;?\s*$", "", cleaned, flags=re.IGNORECASE)
        return cleaned.strip()

    def _coalesce_review_status(self, status: AnswerExtractionStatus) -> AnswerExtractionStatus:
        if status == AnswerExtractionStatus.MANUAL_CHECK:
            return AnswerExtractionStatus.AMBIGUOUS
        return status

    def _normalize_extraction_item(
        self,
        question: QuestionRead,
        item: dict[str, Any],
    ) -> tuple[str, AnswerExtractionStatus, float]:
        answer_text = self._clean_extracted_answer_text(item.get("answer_text", ""))
        try:
            extraction_status = AnswerExtractionStatus(str(item.get("extraction_status", "ambiguous")))
        except ValueError:
            extraction_status = AnswerExtractionStatus.AMBIGUOUS
        extraction_status = self._coalesce_review_status(extraction_status)
        confidence = float(item.get("confidence", 0) or 0)

        if self._looks_incomplete_sql_answer(question, answer_text):
            if extraction_status == AnswerExtractionStatus.MATCHED:
                extraction_status = AnswerExtractionStatus.AMBIGUOUS
            confidence = min(confidence, 0.75)

        return answer_text, extraction_status, confidence

    def _looks_incomplete_sql_answer(self, question: QuestionRead, answer_text: str) -> bool:
        if not answer_text.strip():
            return False

        question_type = getattr(question.question_type, "value", question.question_type)
        expected_answer_type = str(question.expected_answer_type or "").lower()
        if question_type not in {"sql", "code"} and "sql" not in expected_answer_type and "code" not in expected_answer_type:
            return False

        content = str(question.content or "")
        numbered_steps = len(re.findall(r"(?:^|\s)\d+[、.)]", content))
        multi_step_markers = len(
            re.findall(
                r"步骤|定义变量|SELECT\.\.\.INTO|SELECT\s*\.\.\.\s*INTO|存入|计算|拼接|格式化输出",
                content,
                flags=re.IGNORECASE,
            ),
        )
        if numbered_steps < 2 and multi_step_markers < 2:
            return False

        statements = [part.strip() for part in re.split(r";\s*", answer_text) if part.strip()]
        if len(statements) > 1:
            return False

        mentions_set = bool(re.search(r"\bSET\b|定义变量|@pkg_id|@cust_id|@discount", content, flags=re.IGNORECASE))
        mentions_into = bool(re.search(r"INTO|存入", content, flags=re.IGNORECASE))
        answer_has_set = bool(re.search(r"\bSET\b", answer_text, flags=re.IGNORECASE))
        answer_has_into = bool(re.search(r"\bINTO\b", answer_text, flags=re.IGNORECASE))

        if mentions_set and not answer_has_set:
            return True
        if mentions_into and not answer_has_into:
            return True
        if numbered_steps >= 2 and len(statements) <= 1:
            return True
        return False

    def start_extract_answers(
        self,
        task_id: int,
        max_workers: int = 3,
        force: bool = False,
    ) -> AnswerExtractionStartResponse:
        max_workers = max(1, min(max_workers, 5))
        with self._running_lock:
            if task_id in self._running_task_ids:
                raise HTTPException(status_code=409, detail="答案抽取正在进行中，请稍候")
            self._running_task_ids.add(task_id)

        try:
            snapshot = self.get_snapshot(task_id)
            if snapshot.total_questions <= 0:
                raise HTTPException(status_code=400, detail="请先在作业管理中完成题目分析，或确认当前课程下已有带题目的作业")
            if snapshot.total_students <= 0:
                raise HTTPException(status_code=400, detail="前一步没有匹配成功的学生作业，请先完成学生解析")
        except Exception:
            with self._running_lock:
                self._running_task_ids.discard(task_id)
            raise

        thread = threading.Thread(
            target=self._run_extract_answers_job,
            args=(task_id, max_workers, force),
            daemon=True,
        )
        thread.start()
        return AnswerExtractionStartResponse(
            task_id=task_id,
            total_questions=snapshot.total_questions,
            total_students=snapshot.total_students,
            max_workers=max_workers,
        )

    def start_extract_answers_for_submission(
        self,
        task_id: int,
        submission_id: int,
    ) -> AnswerExtractionStudentStartResponse:
        submission_key = (task_id, submission_id)
        with self._running_lock:
            if task_id in self._running_task_ids:
                raise HTTPException(status_code=409, detail="批量答案抽取正在进行中，请稍候")
            if submission_key in self._running_submission_keys:
                raise HTTPException(status_code=409, detail="该学生答案正在抽取中，请稍候")
            self._running_submission_keys.add(submission_key)

        try:
            snapshot = self.get_snapshot(task_id)
            if snapshot.total_questions <= 0:
                raise HTTPException(status_code=400, detail="请先在作业管理中完成题目分析，或确认当前课程下已有带题目的作业")
            submission = next(
                (student for student in snapshot.students if student.submission_id == submission_id),
                None,
            )
            if submission is None:
                raise HTTPException(status_code=404, detail="未找到该学生的作业提交记录")
        except Exception:
            with self._running_lock:
                self._running_submission_keys.discard(submission_key)
            raise

        thread = threading.Thread(
            target=self._run_extract_one_submission_job,
            args=(task_id, submission_id),
            daemon=True,
        )
        thread.start()
        return AnswerExtractionStudentStartResponse(
            task_id=task_id,
            submission_id=submission_id,
            total_questions=snapshot.total_questions,
        )

    def get_snapshot(self, task_id: int) -> AnswerExtractionSnapshot:
        with SessionLocal() as db:
            task = db.get(GradingTask, task_id)
            if task is None:
                raise HTTPException(status_code=404, detail="Task not found")
            self._ensure_task_questions(db, task)
            self._ensure_task_submissions(db, task)
            db.commit()

            questions = db.scalars(
                select(Question)
                .where(Question.task_id == task_id)
                .order_by(Question.sort_order, Question.id),
            ).all()
            submissions = db.scalars(
                select(StudentSubmission)
                .where(StudentSubmission.task_id == task_id)
                .order_by(StudentSubmission.id),
            ).all()
            answers = db.scalars(
                select(StudentAnswer)
                .where(StudentAnswer.task_id == task_id)
                .order_by(StudentAnswer.student_submission_id, StudentAnswer.question_id),
            ).all()
            files = {
                uploaded_file.id: uploaded_file
                for uploaded_file in db.scalars(
                    select(UploadedFile).where(UploadedFile.task_id == task_id),
                ).all()
            }

            answers_by_submission: dict[int, list[StudentAnswerRead]] = {}
            for answer in answers:
                answers_by_submission.setdefault(answer.student_submission_id, []).append(
                    self._to_answer_read(answer),
                )

            total_questions = len(questions)
            students: list[StudentAnswerExtractionProgress] = []
            for submission in submissions:
                student_answers = answers_by_submission.get(submission.id, [])
                completed_questions = len(
                    [
                        answer
                        for answer in student_answers
                        if answer.extraction_status != AnswerExtractionStatus.EXTRACT_ERROR
                    ],
                )
                if total_questions and completed_questions >= total_questions:
                    status = "done"
                elif completed_questions > 0:
                    status = "processing"
                else:
                    status = "pending"
                source_file = files.get(submission.source_file_id or 0)
                students.append(
                    StudentAnswerExtractionProgress(
                        submission_id=submission.id,
                        student_name=submission.student_name,
                        student_no=submission.student_no,
                        source_file_id=submission.source_file_id,
                        source_file_name=source_file.file_name if source_file else "",
                        content=submission.content,
                        total_questions=total_questions,
                        completed_questions=min(completed_questions, total_questions),
                        status=status,
                        answers=student_answers,
                    ),
                )

            completed_students = len([student for student in students if student.status == "done"])
            return AnswerExtractionSnapshot(
                task_id=task_id,
                status=task.status.value,
                total_questions=total_questions,
                total_students=len(students),
                completed_students=completed_students,
                students=students,
            )

    def _run_extract_answers_job(self, task_id: int, max_workers: int, force: bool) -> None:
        progress_channel = f"task:{task_id}"
        try:
            with SessionLocal() as db:
                task = db.get(GradingTask, task_id)
                if task is None:
                    return
                self._ensure_task_questions(db, task)
                self._ensure_task_submissions(db, task)
                db.commit()
                questions = [
                    self._to_question_read(question)
                    for question in db.scalars(
                        select(Question)
                        .where(Question.task_id == task_id)
                        .order_by(Question.sort_order, Question.id),
                    ).all()
                ]
                submissions = db.scalars(
                    select(StudentSubmission)
                    .where(StudentSubmission.task_id == task_id)
                    .order_by(StudentSubmission.id),
                ).all()
                if force:
                    self._clear_after_answer_extraction(db, task_id)
                    submissions_to_process = submissions
                else:
                    submissions_to_process = self._submissions_needing_extraction(db, task_id, submissions, len(questions))
                db.commit()

            self._publish(
                progress_channel,
                "stage_started",
                {
                    "stage": "extract_answers",
                    "total_students": len(submissions_to_process),
                    "total_questions": len(questions),
                    "max_workers": max_workers,
                    "force": force,
                },
            )
            completed_students = 0
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [
                    executor.submit(
                        self._extract_one_submission,
                        task_id,
                        submission.id,
                        submission.student_name,
                        submission.student_no,
                        submission.content,
                        questions,
                        progress_channel,
                    )
                    for submission in submissions_to_process
                ]
                for future in as_completed(futures):
                    completed_students += 1
                    try:
                        future.result()
                    except Exception:
                        pass
                    self._publish(
                        progress_channel,
                        "student_batch_progress",
                        {
                            "stage": "extract_answers",
                            "completed_students": completed_students,
                            "total_students": len(submissions_to_process),
                        },
                    )

            with SessionLocal() as db:
                task = db.get(GradingTask, task_id)
                if task is not None:
                    task.status = GradingTaskStatus.ANSWERS_EXTRACTED
                    db.commit()
            self._publish(
                progress_channel,
                "stage_done",
                {
                    "stage": "extract_answers",
                    "student_count": len(submissions_to_process),
                    "question_count": len(questions),
                },
            )
        finally:
            with self._running_lock:
                self._running_task_ids.discard(task_id)

    def _run_extract_one_submission_job(self, task_id: int, submission_id: int) -> None:
        submission_key = (task_id, submission_id)
        progress_channel = f"task:{task_id}"
        try:
            with SessionLocal() as db:
                task = db.get(GradingTask, task_id)
                if task is None:
                    return
                submission = db.get(StudentSubmission, submission_id)
                if submission is None or submission.task_id != task_id:
                    return
                self._ensure_task_questions(db, task)
                questions = [
                    self._to_question_read(question)
                    for question in db.scalars(
                        select(Question)
                        .where(Question.task_id == task_id)
                        .order_by(Question.sort_order, Question.id),
                    ).all()
                ]
                if not questions:
                    return
                self._clear_after_answer_extraction_for_submission(db, task_id, submission_id)
                db.commit()

            self._extract_one_submission(
                task_id,
                submission.id,
                submission.student_name,
                submission.student_no,
                submission.content,
                questions,
                progress_channel,
            )
        finally:
            with self._running_lock:
                self._running_submission_keys.discard(submission_key)

    def _extract_one_submission(
        self,
        task_id: int,
        submission_id: int,
        student_name: str,
        student_no: str,
        content: str,
        questions: list[QuestionRead],
        progress_channel: str,
    ) -> None:
        self._publish(
            progress_channel,
            "student_started",
            {
                "stage": "extract_answers",
                "submission_id": submission_id,
                "student_name": student_name,
                "student_no": student_no,
                "total_questions": len(questions),
                "completed_questions": 0,
            },
        )
        try:
            answers = self.extract_answers(
                task_id=task_id,
                student_submission_id=submission_id,
                questions=questions,
                student_submission_text=content,
                progress_channel=progress_channel,
                student_name=student_name,
                student_no=student_no,
            )
            with SessionLocal() as db:
                db.execute(
                    delete(StudentAnswer).where(
                        StudentAnswer.task_id == task_id,
                        StudentAnswer.student_submission_id == submission_id,
                    ),
                )
                db.add_all(
                    [
                        StudentAnswer(
                            task_id=answer.task_id,
                            question_id=answer.question_id,
                            student_submission_id=answer.student_submission_id,
                            answer_text=answer.answer_text,
                            extraction_status=answer.extraction_status,
                            confidence=answer.confidence,
                            raw_llm_output=answer.raw_llm_output,
                        )
                        for answer in answers
                    ],
                )
                db.commit()
            self._publish(
                progress_channel,
                "student_done",
                {
                    "stage": "extract_answers",
                    "submission_id": submission_id,
                    "student_name": student_name,
                    "student_no": student_no,
                    "total_questions": len(questions),
                    "completed_questions": len(answers),
                },
            )
        except (RuntimeError, ValueError, ValidationError) as exc:
            with SessionLocal() as db:
                db.add_all(
                    [
                        StudentAnswer(
                            task_id=task_id,
                            question_id=question.id,
                            student_submission_id=submission_id,
                            answer_text="",
                            extraction_status=AnswerExtractionStatus.EXTRACT_ERROR,
                            confidence=0,
                            raw_llm_output=str(exc),
                        )
                        for question in questions
                    ],
                )
                db.commit()
            self._publish(
                progress_channel,
                "student_failed",
                {
                    "stage": "extract_answers",
                    "submission_id": submission_id,
                    "student_name": student_name,
                    "student_no": student_no,
                    "total_questions": len(questions),
                    "completed_questions": 0,
                    "message": str(exc),
                },
            )

    def _build_delta_handler(
        self,
        channel: str,
        task_id: int,
        submission_id: int,
        student_name: str,
        student_no: str,
        total_questions: int,
    ):
        buffer = ""
        seen_question_numbers: set[str] = set()

        def on_delta(text: str) -> None:
            nonlocal buffer
            buffer += text
            current_numbers = re.findall(r'"question_number"\s*:\s*"([^"]+)"', buffer)
            new_numbers = [number for number in current_numbers if number not in seen_question_numbers]
            if not new_numbers:
                return
            seen_question_numbers.update(new_numbers)
            self._publish(
                channel,
                "student_question_progress",
                {
                    "stage": "extract_answers",
                    "task_id": task_id,
                    "submission_id": submission_id,
                    "student_name": student_name,
                    "student_no": student_no,
                    "total_questions": total_questions,
                    "completed_questions": min(len(seen_question_numbers), total_questions),
                    "question_numbers": list(seen_question_numbers),
                },
            )

        return on_delta

    def _clear_after_answer_extraction(self, db, task_id: int) -> None:
        result_ids = select(GradingResult.id).where(GradingResult.task_id == task_id)
        db.execute(delete(GradingDeduction).where(GradingDeduction.grading_result_id.in_(result_ids)))
        db.execute(delete(GradingReflection).where(GradingReflection.grading_result_id.in_(result_ids)))
        db.execute(delete(TeacherRevision).where(TeacherRevision.grading_result_id.in_(result_ids)))
        db.execute(delete(GradingResult).where(GradingResult.task_id == task_id))
        db.execute(delete(AnswerEvidence).where(AnswerEvidence.task_id == task_id))
        db.execute(delete(StudentAnswer).where(StudentAnswer.task_id == task_id))

    def _clear_after_answer_extraction_for_submission(self, db, task_id: int, submission_id: int) -> None:
        answer_ids = select(StudentAnswer.id).where(
            StudentAnswer.task_id == task_id,
            StudentAnswer.student_submission_id == submission_id,
        )
        result_ids = select(GradingResult.id).where(
            GradingResult.task_id == task_id,
            GradingResult.student_submission_id == submission_id,
        )
        db.execute(delete(GradingDeduction).where(GradingDeduction.grading_result_id.in_(result_ids)))
        db.execute(delete(GradingReflection).where(GradingReflection.grading_result_id.in_(result_ids)))
        db.execute(delete(TeacherRevision).where(TeacherRevision.grading_result_id.in_(result_ids)))
        db.execute(
            delete(GradingResult).where(
                GradingResult.task_id == task_id,
                GradingResult.student_submission_id == submission_id,
            ),
        )
        db.execute(delete(AnswerEvidence).where(AnswerEvidence.student_answer_id.in_(answer_ids)))
        db.execute(
            delete(StudentAnswer).where(
                StudentAnswer.task_id == task_id,
                StudentAnswer.student_submission_id == submission_id,
            ),
        )

    def _ensure_task_submissions(self, db, task: GradingTask) -> None:
        class_group = student_prepare_service._find_task_class_group(db, task)
        if class_group is None:
            return

        students = db.scalars(
            select(ClassStudent)
            .where(ClassStudent.class_group_id == class_group.id)
            .order_by(ClassStudent.id),
        ).all()
        files = db.scalars(
            select(UploadedFile)
            .where(
                UploadedFile.task_id == task.id,
                UploadedFile.file_role == FileRole.STUDENT_SUBMISSION,
            )
            .order_by(UploadedFile.id),
        ).all()
        if not students or not files:
            return

        files_by_id = {file.id: file for file in files}
        existing_submissions = db.scalars(
            select(StudentSubmission).where(StudentSubmission.task_id == task.id),
        ).all()
        existing_file_ids = {
            submission.source_file_id
            for submission in existing_submissions
            if submission.source_file_id is not None
        }
        existing_student_keys = {
            self._student_submission_key(submission.student_no, submission.student_name)
            for submission in existing_submissions
        }
        existing_by_student_key = {
            self._student_submission_key(submission.student_no, submission.student_name): submission
            for submission in existing_submissions
        }

        for student in students:
            student_key = self._student_submission_key(student.student_no, student.student_name)
            existing_submission = existing_by_student_key.get(student_key)
            if existing_submission is not None:
                current_file = files_by_id.get(existing_submission.source_file_id or 0)
                if current_file is not None:
                    if existing_submission.content != current_file.parsed_text:
                        existing_submission.content = current_file.parsed_text
                    continue

                candidates = [
                    candidate
                    for candidate in student_prepare_service._match_student_files(student, files)
                    if candidate.file.id not in existing_file_ids
                ]
                if student_prepare_service._match_status(candidates) != "matched":
                    continue

                top_candidate = candidates[0]
                self._clear_after_answer_extraction_for_submission(db, task.id, existing_submission.id)
                existing_submission.source_file_id = top_candidate.file.id
                existing_submission.content = top_candidate.file.parsed_text
                existing_file_ids.add(top_candidate.file.id)
                continue

            candidates = [
                candidate
                for candidate in student_prepare_service._match_student_files(student, files)
                if candidate.file.id not in existing_file_ids
            ]
            if student_prepare_service._match_status(candidates) != "matched":
                continue
            top_candidate = candidates[0]
            db.add(
                StudentSubmission(
                    task_id=task.id,
                    source_file_id=top_candidate.file.id,
                    student_no=student.student_no,
                    student_name=student.student_name,
                    content=top_candidate.file.parsed_text,
                ),
            )
            existing_file_ids.add(top_candidate.file.id)
            existing_student_keys.add(student_key)

    def _student_submission_key(self, student_no: str, student_name: str) -> str:
        if student_no:
            return f"no:{student_no.strip().lower()}"
        return f"name:{student_name.strip().lower()}"

    def _submissions_needing_extraction(
        self,
        db,
        task_id: int,
        submissions: list[StudentSubmission],
        question_count: int,
    ) -> list[StudentSubmission]:
        if question_count <= 0:
            return submissions
        answers = db.scalars(select(StudentAnswer).where(StudentAnswer.task_id == task_id)).all()
        answers_by_submission: dict[int, list[StudentAnswer]] = {}
        for answer in answers:
            answers_by_submission.setdefault(answer.student_submission_id, []).append(answer)
        return [
            submission
            for submission in submissions
            if self._submission_needs_extraction(answers_by_submission.get(submission.id, []), question_count)
        ]

    def _submission_needs_extraction(self, answers: list[StudentAnswer], question_count: int) -> bool:
        if len(answers) < question_count:
            return True
        return any(answer.extraction_status == AnswerExtractionStatus.EXTRACT_ERROR for answer in answers)

    def _ensure_task_questions(self, db, task: GradingTask) -> None:
        existing_question = db.scalars(
            select(Question.id).where(Question.task_id == task.id).limit(1),
        ).first()
        if existing_question is not None:
            return

        assignment_name = task.assignment_name or task.task_name
        assignments = db.scalars(
            select(CourseAssignment)
            .join(Course, Course.id == CourseAssignment.course_id)
            .where(Course.course_name == task.course_name)
            .order_by(
                CourseAssignment.rubric_confirmed.desc(),
                (CourseAssignment.assignment_name == assignment_name).desc(),
                CourseAssignment.id.desc(),
            ),
        ).all()
        if not assignments:
            assignments = db.scalars(
                select(CourseAssignment)
                .where(CourseAssignment.assignment_name == assignment_name)
                .order_by(CourseAssignment.rubric_confirmed.desc(), CourseAssignment.id.desc()),
            ).all()

        assignment_questions = []
        for assignment in assignments:
            candidate_questions = db.scalars(
                select(CourseAssignmentQuestion)
                .where(CourseAssignmentQuestion.assignment_id == assignment.id)
                .order_by(CourseAssignmentQuestion.sort_order, CourseAssignmentQuestion.id),
            ).all()
            if candidate_questions:
                assignment_questions = candidate_questions
                break
        if not assignment_questions:
            return

        for assignment_question in assignment_questions:
            question = Question(
                task_id=task.id,
                question_number=assignment_question.question_number,
                content=assignment_question.content,
                question_type=assignment_question.question_type,
                knowledge_points=assignment_question.knowledge_points,
                difficulty=assignment_question.difficulty,
                expected_answer_type=assignment_question.expected_answer_type,
                total_score=assignment_question.total_score,
                sort_order=assignment_question.sort_order,
            )
            db.add(question)
            db.flush()
            assignment_rubrics = db.scalars(
                select(CourseAssignmentQuestionRubric)
                .where(CourseAssignmentQuestionRubric.assignment_question_id == assignment_question.id)
                .order_by(CourseAssignmentQuestionRubric.sort_order, CourseAssignmentQuestionRubric.id),
            ).all()
            db.add_all(
                [
                    QuestionRubric(
                        question_id=question.id,
                        dimension_name=rubric.dimension_name,
                        dimension_description=rubric.dimension_description,
                        max_score=rubric.max_score,
                        scoring_criteria=rubric.scoring_criteria,
                        deduction_criteria=rubric.deduction_criteria,
                        evidence_requirement=rubric.evidence_requirement,
                        sort_order=rubric.sort_order,
                    )
                    for rubric in assignment_rubrics
                ],
            )

    def confirm_student_answer(self, task_id: int, answer_id: int) -> StudentAnswerRead:
        with SessionLocal() as db:
            answer = db.get(StudentAnswer, answer_id)
            if answer is None or answer.task_id != task_id:
                raise HTTPException(status_code=404, detail="Student answer not found")
            if answer.extraction_status not in {
                AnswerExtractionStatus.AMBIGUOUS,
                AnswerExtractionStatus.MANUAL_CHECK,
            }:
                raise HTTPException(status_code=400, detail="当前答案状态无需确认")
            answer.extraction_status = AnswerExtractionStatus.MATCHED
            answer.confidence = max(float(answer.confidence or 0), 0.9)
            db.commit()
            db.refresh(answer)
            return self._to_answer_read(answer)

    def _to_answer_read(self, answer: StudentAnswer) -> StudentAnswerRead:
        return StudentAnswerRead(
            id=answer.id,
            task_id=answer.task_id,
            question_id=answer.question_id,
            student_submission_id=answer.student_submission_id,
            answer_text=answer.answer_text,
            extraction_status=self._coalesce_review_status(answer.extraction_status),
            confidence=answer.confidence,
            raw_llm_output=answer.raw_llm_output,
            created_at=answer.created_at,
            updated_at=answer.updated_at,
        )

    def _to_question_read(self, question: Question) -> QuestionRead:
        return QuestionRead(
            id=question.id,
            task_id=question.task_id,
            question_number=question.question_number,
            content=question.content,
            question_type=question.question_type,
            knowledge_points=question.knowledge_points or [],
            difficulty=question.difficulty,
            expected_answer_type=question.expected_answer_type,
            total_score=question.total_score,
            sort_order=question.sort_order,
            rubrics=[],
            created_at=question.created_at,
            updated_at=question.updated_at,
        )

    def _publish(self, channel: str, event: str, data: dict[str, Any]) -> None:
        progress_event_service.publish(channel, event, data)


answer_extractor_service = AnswerExtractorService()
