from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import delete, select

from app.db.models import (
    AnswerEvidence,
    GradingDeduction,
    GradingReflection,
    GradingResult,
    GradingTask,
    Question,
    QuestionRubric,
    StudentAnswer,
    StudentSubmission,
    TeacherRevision,
)
from app.db.session import SessionLocal
from app.models.answer import AnswerExtractionStatus
from app.models.task import GradingTaskStatus
from app.prompts.evidence_extractor_prompt import (
    EVIDENCE_EXTRACTOR_OUTPUT_SCHEMA,
    build_evidence_extractor_prompt,
)
from app.schemas.answer import StudentAnswerRead
from app.schemas.evidence import (
    AnswerEvidenceCreate,
    AnswerEvidenceRead,
    EvidenceExtractionQuestionRead,
    EvidenceExtractionSnapshot,
    EvidenceExtractionStudentStartResponse,
    StudentEvidenceExtractionProgress,
)
from app.schemas.question import QuestionRead, QuestionRubricRead
from app.services.llm_service import LLMService, llm_service
from app.services.progress_event_service import progress_event_service


class EvidenceExtractorService:
    def __init__(self, llm: LLMService = llm_service) -> None:
        self._llm = llm
        self._running_task_ids: set[int] = set()
        self._running_submission_keys: set[tuple[int, int]] = set()
        self._running_lock = threading.Lock()

    def extract_evidence(
        self,
        task_id: int,
        question: QuestionRead,
        student_answer: StudentAnswerRead,
        rubrics: list[QuestionRubricRead],
        student_id: int | None = None,
    ) -> list[AnswerEvidenceCreate]:
        prompt = build_evidence_extractor_prompt(
            question_json=question.model_dump_json(),
            rubrics_json=json.dumps(
                [rubric.model_dump(mode="json") for rubric in rubrics],
                ensure_ascii=False,
            ),
            answer_text=student_answer.answer_text,
        )
        payload = self._llm.chat_json(prompt, schema=EVIDENCE_EXTRACTOR_OUTPUT_SCHEMA)
        return [
            AnswerEvidenceCreate(
                task_id=task_id,
                question_id=question.id,
                student_id=student_id,
                student_answer_id=student_answer.id,
                rubric_id=item.get("rubric_id"),
                positive_evidence=item.get("positive_evidence", []),
                negative_evidence=item.get("negative_evidence", []),
                confidence=item.get("confidence", 0),
                raw_llm_output=item,
            )
            for item in payload.get("evidence_items", [])
        ]

    def get_snapshot(self, task_id: int) -> EvidenceExtractionSnapshot:
        with SessionLocal() as db:
            task = db.get(GradingTask, task_id)
            if task is None:
                raise HTTPException(status_code=404, detail="Task not found")

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
            eligible_submission_ids = self._eligible_submission_ids(db, task_id, answers)
            answers = [
                answer
                for answer in answers
                if answer.student_submission_id in eligible_submission_ids
            ]
            evidence_items = db.scalars(
                select(AnswerEvidence)
                .where(AnswerEvidence.task_id == task_id)
                .order_by(AnswerEvidence.student_answer_id, AnswerEvidence.rubric_id),
            ).all()

            evidence_by_answer: dict[int, list[AnswerEvidenceRead]] = {}
            for item in evidence_items:
                evidence_by_answer.setdefault(item.student_answer_id, []).append(self._to_evidence_read(item))

            extraction_started = self._evidence_extraction_started(task, evidence_items)

            questions_by_submission: dict[int, list[EvidenceExtractionQuestionRead]] = {}
            completed_answers = 0
            for answer in answers:
                answer_evidence = evidence_by_answer.get(answer.id, [])
                question_read = EvidenceExtractionQuestionRead(
                    question_id=answer.question_id,
                    student_answer_id=answer.id,
                    answer_text=answer.answer_text,
                    extraction_status=answer.extraction_status.value,
                    answer_confidence=answer.confidence,
                    evidence_items=answer_evidence,
                )
                if extraction_started and self._question_evidence_complete(question_read):
                    completed_answers += 1
                questions_by_submission.setdefault(answer.student_submission_id, []).append(question_read)

            students: list[StudentEvidenceExtractionProgress] = []
            for submission in submissions:
                questions = questions_by_submission.get(submission.id, [])
                if extraction_started:
                    completed_questions = len(
                        [
                            question
                            for question in questions
                            if self._question_evidence_complete(question)
                        ],
                    )
                    if questions and completed_questions >= len(questions):
                        status = "done"
                    elif completed_questions > 0:
                        status = "processing"
                    else:
                        status = "pending"
                else:
                    completed_questions = 0
                    status = "pending"
                students.append(
                    StudentEvidenceExtractionProgress(
                        submission_id=submission.id,
                        student_name=submission.student_name,
                        student_no=submission.student_no,
                        status=status,
                        questions=questions,
                    ),
                )

            return EvidenceExtractionSnapshot(
                task_id=task_id,
                status=task.status.value,
                evidence_extraction_started=extraction_started,
                total_answers=len(answers),
                completed_answers=completed_answers,
                students=students,
            )

    def start_extract_evidence(
        self,
        task_id: int,
        max_workers: int = 3,
        force: bool = False,
    ) -> dict[str, int | str | bool]:
        max_workers = max(1, min(max_workers, 5))
        with self._running_lock:
            if task_id in self._running_task_ids:
                raise HTTPException(status_code=409, detail="证据提取正在进行中，请稍候")
            self._running_task_ids.add(task_id)

        snapshot = self.get_snapshot(task_id)
        if snapshot.total_answers <= 0:
            with self._running_lock:
                self._running_task_ids.discard(task_id)
            raise HTTPException(status_code=400, detail="请先完成答案抽取，再提取评分证据")

        thread = threading.Thread(
            target=self._run_extract_evidence_job,
            args=(task_id, max_workers, force),
            daemon=True,
        )
        thread.start()
        return {
            "task_id": task_id,
            "status": "queued",
            "stage": "extract_evidence",
            "force": force,
            "max_workers": max_workers,
            "total_answers": snapshot.total_answers,
            "completed_answers": snapshot.completed_answers,
        }

    def start_extract_evidence_for_submission(
        self,
        task_id: int,
        submission_id: int,
    ) -> EvidenceExtractionStudentStartResponse:
        submission_key = (task_id, submission_id)
        with self._running_lock:
            if task_id in self._running_task_ids:
                raise HTTPException(status_code=409, detail="批量证据提取正在进行中，请稍候")
            if submission_key in self._running_submission_keys:
                raise HTTPException(status_code=409, detail="该学生证据正在提取中，请稍候")
            self._running_submission_keys.add(submission_key)

        try:
            snapshot = self.get_snapshot(task_id)
            if snapshot.total_answers <= 0:
                raise HTTPException(status_code=400, detail="请先完成答案抽取，再提取评分证据")
            submission = next(
                (student for student in snapshot.students if student.submission_id == submission_id),
                None,
            )
            if submission is None:
                raise HTTPException(status_code=404, detail="未找到该学生的作业提交记录")
            answer_count = len(
                [
                    question
                    for question in submission.questions
                    if not self._question_skips_evidence(question)
                ],
            )
            if answer_count <= 0:
                raise HTTPException(status_code=400, detail="该学生没有可提取证据的答案")
        except Exception:
            with self._running_lock:
                self._running_submission_keys.discard(submission_key)
            raise

        thread = threading.Thread(
            target=self._run_extract_one_submission_evidence_job,
            args=(task_id, submission_id),
            daemon=True,
        )
        thread.start()
        return EvidenceExtractionStudentStartResponse(
            task_id=task_id,
            submission_id=submission_id,
            total_answers=answer_count,
        )

    def _run_extract_evidence_job(self, task_id: int, max_workers: int, force: bool) -> None:
        progress_channel = f"task:{task_id}"
        try:
            with SessionLocal() as db:
                answers = db.scalars(
                    select(StudentAnswer)
                    .where(StudentAnswer.task_id == task_id)
                    .order_by(StudentAnswer.student_submission_id, StudentAnswer.question_id),
                ).all()
                eligible_submission_ids = self._eligible_submission_ids(db, task_id, answers)
                answers = [
                    answer
                    for answer in answers
                    if answer.student_submission_id in eligible_submission_ids
                ]
                if force:
                    self._clear_after_evidence_extraction(db, task_id)
                answers_to_process = self._answers_needing_evidence(db, task_id, answers, force=force)
                answers_by_submission: dict[int, list[int]] = {
                    submission_id: []
                    for submission_id in eligible_submission_ids
                }
                for answer in answers_to_process:
                    answers_by_submission.setdefault(answer.student_submission_id, []).append(answer.id)
                task = db.get(GradingTask, task_id)
                if task is not None:
                    task.status = GradingTaskStatus.ANSWERS_EXTRACTED
                db.commit()

            self._publish(
                progress_channel,
                "stage_started",
                {
                    "stage": "extract_evidence",
                    "total_answers": len(answers),
                    "pending_answers": sum(len(answer_ids) for answer_ids in answers_by_submission.values()),
                    "completed_answers": 0,
                    "max_workers": max_workers,
                    "force": force,
                },
            )

            completed_answers = 0
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [
                    executor.submit(
                        self._extract_submission_answers,
                        task_id,
                        submission_id,
                        answer_ids,
                        progress_channel,
                    )
                    for submission_id, answer_ids in answers_by_submission.items()
                ]
                for future in as_completed(futures):
                    processed_count = 0
                    try:
                        processed_count = future.result()
                    except Exception:
                        pass
                    completed_answers += processed_count
                    self._publish(
                        progress_channel,
                        "answer_progress",
                        {
                            "stage": "extract_evidence",
                            "completed_answers": completed_answers,
                            "total_answers": len(answers),
                        },
                    )

            with SessionLocal() as db:
                task = db.get(GradingTask, task_id)
                if task is not None:
                    task.status = GradingTaskStatus.EVIDENCE_EXTRACTED
                    db.commit()
            self._publish(
                progress_channel,
                "stage_done",
                {
                    "stage": "extract_evidence",
                    "answer_count": len(answers),
                },
            )
        except Exception as exc:
            self._publish(
                progress_channel,
                "stage_failed",
                {
                    "stage": "extract_evidence",
                    "message": str(exc),
                },
            )
        finally:
            with self._running_lock:
                self._running_task_ids.discard(task_id)

    def _run_extract_one_submission_evidence_job(self, task_id: int, submission_id: int) -> None:
        submission_key = (task_id, submission_id)
        progress_channel = f"task:{task_id}"
        student_name = ""
        student_no = ""
        answer_ids: list[int] = []
        try:
            with SessionLocal() as db:
                submission = db.get(StudentSubmission, submission_id)
                if submission is None or submission.task_id != task_id:
                    return
                student_name = submission.student_name
                student_no = submission.student_no or ""
                answers = db.scalars(
                    select(StudentAnswer)
                    .where(
                        StudentAnswer.task_id == task_id,
                        StudentAnswer.student_submission_id == submission_id,
                    )
                    .order_by(StudentAnswer.question_id),
                ).all()
                all_answers = db.scalars(
                    select(StudentAnswer).where(StudentAnswer.task_id == task_id),
                ).all()
                if submission_id not in self._eligible_submission_ids(db, task_id, all_answers):
                    return
                self._clear_after_evidence_extraction_for_submission(db, task_id, submission_id)
                db.commit()
                answer_ids = [answer.id for answer in answers if not self._should_skip_evidence(answer)]

            if not answer_ids:
                return

            self._publish(
                progress_channel,
                "student_started",
                {
                    "stage": "extract_evidence",
                    "submission_id": submission_id,
                    "student_name": student_name,
                    "student_no": student_no,
                    "total_answers": len(answer_ids),
                    "completed_answers": 0,
                },
            )
            self._extract_submission_answers(task_id, submission_id, answer_ids, progress_channel)
            self._publish(
                progress_channel,
                "student_done",
                {
                    "stage": "extract_evidence",
                    "submission_id": submission_id,
                    "student_name": student_name,
                    "student_no": student_no,
                    "total_answers": len(answer_ids),
                    "completed_answers": len(answer_ids),
                },
            )
        except Exception as exc:
            self._publish(
                progress_channel,
                "student_failed",
                {
                    "stage": "extract_evidence",
                    "submission_id": submission_id,
                    "student_name": student_name,
                    "student_no": student_no,
                    "total_answers": len(answer_ids),
                    "completed_answers": 0,
                    "message": str(exc),
                },
            )
        finally:
            with self._running_lock:
                self._running_submission_keys.discard(submission_key)

    def _extract_submission_answers(
        self,
        task_id: int,
        submission_id: int,
        answer_ids: list[int],
        progress_channel: str,
    ) -> int:
        processed_count = 0
        for answer_id in answer_ids:
            self._extract_one_answer(task_id, answer_id, progress_channel)
            processed_count += 1
        processed_count += self._publish_skipped_answers_for_submission(
            task_id,
            submission_id,
            progress_channel,
            exclude_answer_ids=set(answer_ids),
        )
        return processed_count

    def _publish_skipped_answers_for_submission(
        self,
        task_id: int,
        submission_id: int,
        progress_channel: str,
        exclude_answer_ids: set[int],
    ) -> int:
        published = 0
        with SessionLocal() as db:
            answers = db.scalars(
                select(StudentAnswer)
                .where(
                    StudentAnswer.task_id == task_id,
                    StudentAnswer.student_submission_id == submission_id,
                )
                .order_by(StudentAnswer.question_id),
            ).all()
            for answer in answers:
                if answer.id in exclude_answer_ids or not self._should_skip_evidence(answer):
                    continue
                self._publish(
                    progress_channel,
                    "answer_done",
                    {
                        "stage": "extract_evidence",
                        "student_answer_id": answer.id,
                        "submission_id": submission_id,
                        "question_id": answer.question_id,
                        "evidence_count": 0,
                        "skipped": True,
                    },
                )
                published += 1
        return published

    def _extract_one_answer(self, task_id: int, answer_id: int, progress_channel: str) -> int | None:
        with SessionLocal() as db:
            answer = db.get(StudentAnswer, answer_id)
            if answer is None:
                return None
            if self._should_skip_evidence(answer):
                return answer.student_submission_id
            question = db.get(Question, answer.question_id)
            if question is None:
                return answer.student_submission_id
            rubrics = db.scalars(
                select(QuestionRubric)
                .where(QuestionRubric.question_id == question.id)
                .order_by(QuestionRubric.sort_order, QuestionRubric.id),
            ).all()
            if not rubrics:
                return answer.student_submission_id
            submission = db.get(StudentSubmission, answer.student_submission_id)
            question_schema = self._to_question_read(question, rubrics)
            answer_schema = self._to_answer_read(answer)
            student_name = submission.student_name if submission else ""
            student_no = submission.student_no if submission else ""
            submission_id = answer.student_submission_id

        self._publish(
            progress_channel,
            "answer_started",
            {
                "stage": "extract_evidence",
                "student_answer_id": answer_id,
                "submission_id": answer_schema.student_submission_id,
                "question_id": question_schema.id,
                "student_name": student_name,
                "student_no": student_no,
            },
        )
        try:
            evidence_items = self.extract_evidence(
                task_id=task_id,
                question=question_schema,
                student_answer=answer_schema,
                rubrics=question_schema.rubrics,
                student_id=None,
            )
            normalized_items = self._normalize_evidence_items(
                task_id=task_id,
                question=question_schema,
                answer=answer_schema,
                evidence_items=evidence_items,
            )
            with SessionLocal() as db:
                db.execute(delete(AnswerEvidence).where(AnswerEvidence.student_answer_id == answer_id))
                db.add_all(
                    [
                        AnswerEvidence(
                            task_id=item.task_id,
                            question_id=item.question_id,
                            student_id=item.student_id,
                            student_answer_id=item.student_answer_id,
                            rubric_id=item.rubric_id,
                            positive_evidence=item.positive_evidence,
                            negative_evidence=item.negative_evidence,
                            confidence=item.confidence,
                            raw_llm_output=item.raw_llm_output,
                        )
                        for item in normalized_items
                    ],
                )
                db.commit()
            self._publish(
                progress_channel,
                "answer_done",
                {
                    "stage": "extract_evidence",
                    "student_answer_id": answer_id,
                    "submission_id": answer_schema.student_submission_id,
                    "question_id": question_schema.id,
                    "evidence_count": len(normalized_items),
                },
            )
            return submission_id
        except (RuntimeError, ValueError, ValidationError) as exc:
            fallback_items = [
                AnswerEvidenceCreate(
                    task_id=task_id,
                    question_id=question_schema.id,
                    student_id=None,
                    student_answer_id=answer_schema.id,
                    rubric_id=rubric.id,
                    positive_evidence=[],
                    negative_evidence=[],
                    confidence=0,
                    raw_llm_output=str(exc),
                )
                for rubric in question_schema.rubrics
            ]
            with SessionLocal() as db:
                db.execute(delete(AnswerEvidence).where(AnswerEvidence.student_answer_id == answer_id))
                db.add_all(
                    [
                        AnswerEvidence(
                            task_id=item.task_id,
                            question_id=item.question_id,
                            student_id=item.student_id,
                            student_answer_id=item.student_answer_id,
                            rubric_id=item.rubric_id,
                            positive_evidence=item.positive_evidence,
                            negative_evidence=item.negative_evidence,
                            confidence=item.confidence,
                            raw_llm_output=item.raw_llm_output,
                        )
                        for item in fallback_items
                    ],
                )
                db.commit()
            self._publish(
                progress_channel,
                "answer_failed",
                {
                    "stage": "extract_evidence",
                    "student_answer_id": answer_id,
                    "submission_id": answer_schema.student_submission_id,
                    "question_id": question_schema.id,
                    "message": str(exc),
                },
            )
            return submission_id

    def _answers_needing_evidence(self, db, task_id: int, answers: list[StudentAnswer], force: bool) -> list[StudentAnswer]:
        answers = [answer for answer in answers if not self._should_skip_evidence(answer)]
        if force:
            return answers
        evidence_counts = {
            answer_id: count
            for answer_id, count in db.execute(
                select(AnswerEvidence.student_answer_id, AnswerEvidence.id)
                .where(AnswerEvidence.task_id == task_id),
            ).all()
        }
        return [answer for answer in answers if answer.id not in evidence_counts]

    def _should_skip_evidence(self, answer: StudentAnswer) -> bool:
        return answer.extraction_status == AnswerExtractionStatus.MISSING or not answer.answer_text.strip()

    def _evidence_extraction_started(self, task: GradingTask, evidence_items: list[AnswerEvidence]) -> bool:
        if evidence_items:
            return True
        return task.status in {
            GradingTaskStatus.EVIDENCE_EXTRACTED,
            GradingTaskStatus.GRADING,
            GradingTaskStatus.GRADED,
            GradingTaskStatus.REFLECTING,
            GradingTaskStatus.REFLECTED,
            GradingTaskStatus.REVIEW_ROUTED,
            GradingTaskStatus.WAITING_TEACHER_REVIEW,
            GradingTaskStatus.TEACHER_REVIEWED,
            GradingTaskStatus.EXPORTED,
            GradingTaskStatus.SUMMARY_GENERATED,
        }

    def _question_skips_evidence(self, question: EvidenceExtractionQuestionRead) -> bool:
        return question.extraction_status == AnswerExtractionStatus.MISSING.value or not question.answer_text.strip()

    def _question_evidence_complete(self, question: EvidenceExtractionQuestionRead) -> bool:
        if question.evidence_items:
            return True
        return self._question_skips_evidence(question)

    def _eligible_submission_ids(self, db, task_id: int, answers: list[StudentAnswer]) -> set[int]:
        question_count = db.scalar(
            select(Question.id).where(Question.task_id == task_id).limit(1),
        )
        if question_count is None:
            return set()
        total_questions = len({
            question_id
            for question_id, in db.execute(select(Question.id).where(Question.task_id == task_id)).all()
        })
        answers_by_submission: dict[int, list[StudentAnswer]] = {}
        for answer in answers:
            answers_by_submission.setdefault(answer.student_submission_id, []).append(answer)
        return {
            submission_id
            for submission_id, submission_answers in answers_by_submission.items()
            if len(submission_answers) >= total_questions
        }

    def _clear_after_evidence_extraction(self, db, task_id: int) -> None:
        result_ids = select(GradingResult.id).where(GradingResult.task_id == task_id)
        db.execute(delete(GradingDeduction).where(GradingDeduction.grading_result_id.in_(result_ids)))
        db.execute(delete(GradingReflection).where(GradingReflection.grading_result_id.in_(result_ids)))
        db.execute(delete(TeacherRevision).where(TeacherRevision.grading_result_id.in_(result_ids)))
        db.execute(delete(GradingResult).where(GradingResult.task_id == task_id))
        db.execute(delete(AnswerEvidence).where(AnswerEvidence.task_id == task_id))

    def _clear_after_evidence_extraction_for_submission(self, db, task_id: int, submission_id: int) -> None:
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

    def _normalize_evidence_items(
        self,
        task_id: int,
        question: QuestionRead,
        answer: StudentAnswerRead,
        evidence_items: list[AnswerEvidenceCreate],
    ) -> list[AnswerEvidenceCreate]:
        items_by_rubric = {
            item.rubric_id: item
            for item in evidence_items
            if item.rubric_id in {rubric.id for rubric in question.rubrics}
        }
        return [
            items_by_rubric.get(rubric.id)
            or AnswerEvidenceCreate(
                task_id=task_id,
                question_id=question.id,
                student_id=None,
                student_answer_id=answer.id,
                rubric_id=rubric.id,
                positive_evidence=[],
                negative_evidence=[],
                confidence=0,
                raw_llm_output={"missing_rubric_evidence": True},
            )
            for rubric in question.rubrics
        ]

    def _to_evidence_read(self, item: AnswerEvidence) -> AnswerEvidenceRead:
        return AnswerEvidenceRead(
            id=item.id,
            task_id=item.task_id,
            question_id=item.question_id,
            student_id=item.student_id,
            student_answer_id=item.student_answer_id,
            rubric_id=item.rubric_id,
            positive_evidence=item.positive_evidence or [],
            negative_evidence=item.negative_evidence or [],
            confidence=item.confidence,
            raw_llm_output=item.raw_llm_output,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    def _to_answer_read(self, answer: StudentAnswer) -> StudentAnswerRead:
        return StudentAnswerRead(
            id=answer.id,
            task_id=answer.task_id,
            question_id=answer.question_id,
            student_submission_id=answer.student_submission_id,
            answer_text=answer.answer_text,
            extraction_status=answer.extraction_status,
            confidence=answer.confidence,
            raw_llm_output=answer.raw_llm_output,
            created_at=answer.created_at,
            updated_at=answer.updated_at,
        )

    def _to_question_read(self, question: Question, rubrics: list[QuestionRubric]) -> QuestionRead:
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
            rubrics=[self._to_rubric_read(rubric) for rubric in rubrics],
            created_at=question.created_at,
            updated_at=question.updated_at,
        )

    def _to_rubric_read(self, rubric: QuestionRubric) -> QuestionRubricRead:
        return QuestionRubricRead(
            id=rubric.id,
            question_id=rubric.question_id,
            dimension_name=rubric.dimension_name,
            dimension_description=rubric.dimension_description,
            max_score=rubric.max_score,
            scoring_criteria=rubric.scoring_criteria,
            deduction_criteria=rubric.deduction_criteria,
            evidence_requirement=rubric.evidence_requirement,
            sort_order=rubric.sort_order,
            created_at=rubric.created_at,
            updated_at=rubric.updated_at,
        )

    def _publish(self, channel: str, event: str, data: dict[str, Any]) -> None:
        progress_event_service.publish(channel, event, data)


evidence_extractor_service = EvidenceExtractorService()
