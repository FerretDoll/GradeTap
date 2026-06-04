from __future__ import annotations

import copy
import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from fastapi import HTTPException
from sqlalchemy import delete, select

from app.db.models import (
    AnswerEvidence,
    GradingCache,
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
from app.db.session import SessionLocal, engine
from app.models.answer import AnswerExtractionStatus
from app.models.grading import GradingStatus, ReviewPriority, ReviewStatus
from app.models.task import GradingTaskStatus
from app.prompts.grade_by_question_prompt import (
    GRADE_BY_QUESTION_OUTPUT_SCHEMA,
    build_grade_by_question_prompt,
)
from app.schemas.grading import (
    GradeByQuestionStudentStartResponse,
    GradingResultCreate,
    GradingResultRead,
    StudentAnswerForGrading,
)
from app.schemas.grading import EvidenceForGrading
from app.schemas.question import QuestionRead, QuestionRubricRead
from app.services.llm_service import LLMService, llm_service
from app.services.progress_event_service import progress_event_service


class GradingService:
    _GRADING_STARTED_STATUSES = frozenset({
        GradingTaskStatus.GRADING,
        GradingTaskStatus.GRADED,
        GradingTaskStatus.REFLECTING,
        GradingTaskStatus.REFLECTED,
        GradingTaskStatus.REVIEW_ROUTED,
        GradingTaskStatus.WAITING_TEACHER_REVIEW,
        GradingTaskStatus.TEACHER_REVIEWED,
        GradingTaskStatus.EXPORTED,
        GradingTaskStatus.SUMMARY_GENERATED,
    })

    def __init__(self, llm: LLMService = llm_service) -> None:
        self._llm = llm
        self._running_task_ids: set[int] = set()
        self._running_submission_keys: set[tuple[int, int]] = set()
        self._running_lock = threading.Lock()

    def grade_by_question(
        self,
        task_id: int,
        question: QuestionRead,
        rubrics: list[QuestionRubricRead],
        student_answers: list[StudentAnswerForGrading],
    ) -> list[GradingResultCreate]:
        student_answers = [
            answer
            for answer in student_answers
            if self._answer_should_use_ai(answer)
        ]
        if not student_answers:
            return []
        self._validate_evidence_coverage(rubrics, student_answers)
        cache_context = self._build_cache_context(question, rubrics)
        answers_by_cache_key = self._group_answers_by_cache_key(student_answers, cache_context)
        cached_payloads = self._load_cached_payloads(answers_by_cache_key.keys())

        results_by_answer_id: dict[int, GradingResultCreate] = {}
        uncached_representatives: list[StudentAnswerForGrading] = []
        representative_cache_keys: dict[int, str] = {}
        for cache_key, answers in answers_by_cache_key.items():
            cached_payload = cached_payloads.get(cache_key)
            if cached_payload is not None:
                for answer in answers:
                    results_by_answer_id[answer.student_answer_id] = self._clone_cached_result(
                        task_id=task_id,
                        question_id=question.id,
                        answer=answer,
                        cache_key=cache_key,
                        payload=cached_payload,
                    )
                continue

            representative = answers[0]
            uncached_representatives.append(representative)
            representative_cache_keys[representative.student_answer_id] = cache_key

        generated_by_representative_id: dict[int, GradingResultCreate] = {}
        if uncached_representatives:
            grading_input = self._build_grading_input(uncached_representatives)
            prompt = build_grade_by_question_prompt(
                question_json=question.model_dump_json(),
                rubrics_json=json.dumps(
                    [rubric.model_dump(mode="json") for rubric in rubrics],
                    ensure_ascii=False,
                ),
                student_answers_with_evidence_json=json.dumps(grading_input, ensure_ascii=False),
            )
            payload = self._llm.chat_json(prompt, schema=GRADE_BY_QUESTION_OUTPUT_SCHEMA)
            for item in payload.get("grading_results", []):
                result = GradingResultCreate(
                    task_id=task_id,
                    question_id=question.id,
                    raw_llm_output=item,
                    **item,
                )
                generated_by_representative_id[result.student_answer_id] = result

            cache_rows: list[dict] = []
            for representative in uncached_representatives:
                result = generated_by_representative_id.get(representative.student_answer_id)
                if result is None:
                    continue
                cache_key = representative_cache_keys[representative.student_answer_id]
                cache_rows.append(
                    self._build_cache_row(
                        cache_key=cache_key,
                        cache_context=cache_context,
                        answer=representative,
                        result=result,
                    )
                )
                for answer in answers_by_cache_key[cache_key]:
                    results_by_answer_id[answer.student_answer_id] = self._clone_cached_result(
                        task_id=task_id,
                        question_id=question.id,
                        answer=answer,
                        cache_key=cache_key,
                        payload=self._build_cache_payload(result),
                    )
            self._save_cached_payloads(cache_rows)

        return [
            results_by_answer_id[answer.student_answer_id]
            for answer in student_answers
            if answer.student_answer_id in results_by_answer_id
        ]

    def save_grading_results(
        self,
        task_id: int,
        grading_results: list[GradingResultCreate],
        update_task_status: bool = True,
    ) -> list[GradingResultRead]:
        if not grading_results:
            return []

        answer_ids = [result.student_answer_id for result in grading_results]
        with SessionLocal() as db:
            existing_results = db.scalars(
                select(GradingResult).where(
                    GradingResult.task_id == task_id,
                    GradingResult.student_answer_id.in_(answer_ids),
                ),
            ).all()
            existing_by_answer_id = {
                result.student_answer_id: result
                for result in existing_results
            }
            existing_ids = [result.id for result in existing_results]
            if existing_ids:
                db.execute(delete(GradingDeduction).where(GradingDeduction.grading_result_id.in_(existing_ids)))
                db.execute(delete(GradingReflection).where(GradingReflection.grading_result_id.in_(existing_ids)))
                db.execute(delete(TeacherRevision).where(TeacherRevision.grading_result_id.in_(existing_ids)))

            saved_results: list[GradingResult] = []
            for result in grading_results:
                values = result.model_dump(mode="json")
                values["dimension_scores"] = [
                    item.model_dump(mode="json")
                    for item in result.dimension_scores
                ]
                grading_result = existing_by_answer_id.get(result.student_answer_id)
                if grading_result is None:
                    grading_result = GradingResult(**values)
                    db.add(grading_result)
                else:
                    for key, value in values.items():
                        setattr(grading_result, key, value)
                saved_results.append(grading_result)

            if update_task_status:
                task = db.get(GradingTask, task_id)
                if task is not None:
                    task.status = GradingTaskStatus.GRADED

            db.commit()
            return [self._to_grading_result_read(result) for result in saved_results]

    def start_grade_task(
        self,
        task_id: int,
        max_workers: int = 2,
        force: bool = False,
    ) -> dict[str, int | str | bool]:
        max_workers = max(1, min(max_workers, 5))
        with self._running_lock:
            if task_id in self._running_task_ids:
                raise HTTPException(status_code=409, detail="AI 评分正在进行中，请稍后")
            self._running_task_ids.add(task_id)

        try:
            snapshot = self.get_grading_snapshot(task_id)
            if snapshot["total_answers"] <= 0:
                raise HTTPException(status_code=400, detail="请先完成答案抽取和证据提取，再启动 AI 评分")
        except Exception:
            with self._running_lock:
                self._running_task_ids.discard(task_id)
            raise

        thread = threading.Thread(
            target=self._run_grade_task_job,
            args=(task_id, max_workers, force),
            daemon=True,
        )
        thread.start()
        return {
            "task_id": task_id,
            "status": "queued",
            "stage": "grade_by_question",
            "force": force,
            "max_workers": max_workers,
            "total_answers": snapshot["total_answers"],
            "completed_answers": 0 if force else snapshot["completed_answers"],
        }

    def start_grade_task_for_submission(
        self,
        task_id: int,
        submission_id: int,
    ) -> GradeByQuestionStudentStartResponse:
        submission_key = (task_id, submission_id)
        with self._running_lock:
            if task_id in self._running_task_ids:
                raise HTTPException(status_code=409, detail="批量 AI 评分正在进行中，请稍候")
            if submission_key in self._running_submission_keys:
                raise HTTPException(status_code=409, detail="该学生正在 AI 评分中，请稍候")
            self._running_submission_keys.add(submission_key)

        try:
            snapshot = self.get_grading_snapshot(task_id)
            if snapshot["total_answers"] <= 0:
                raise HTTPException(status_code=400, detail="请先完成答案抽取和证据提取，再启动 AI 评分")
            with SessionLocal() as db:
                submission = db.get(StudentSubmission, submission_id)
                if submission is None or submission.task_id != task_id:
                    raise HTTPException(status_code=404, detail="未找到该学生的作业提交记录")
                question_count = self._gradable_question_count_for_submission(db, task_id, submission_id)
            if question_count <= 0:
                raise HTTPException(status_code=400, detail="该学生没有可评分的答案")
        except Exception:
            with self._running_lock:
                self._running_submission_keys.discard(submission_key)
            raise

        thread = threading.Thread(
            target=self._run_grade_one_submission_job,
            args=(task_id, submission_id),
            daemon=True,
        )
        thread.start()
        return GradeByQuestionStudentStartResponse(
            task_id=task_id,
            submission_id=submission_id,
            total_questions=question_count,
        )

    def get_grading_snapshot(self, task_id: int) -> dict[str, int | str]:
        with SessionLocal() as db:
            task = db.get(GradingTask, task_id)
            if task is None:
                raise HTTPException(status_code=404, detail="Task not found")
            ready_answer_ids = self._ready_answer_ids(db, task_id)
            completed_answer_ids = {
                answer_id
                for answer_id, in db.execute(
                    select(GradingResult.student_answer_id).where(
                        GradingResult.task_id == task_id,
                        GradingResult.student_answer_id.in_(ready_answer_ids or [-1]),
                    ),
                ).all()
            }
            return {
                "task_id": task_id,
                "status": task.status.value,
                "stage": "grade_by_question",
                "total_answers": len(ready_answer_ids),
                "completed_answers": len(completed_answer_ids),
            }

    def list_grading_results(self, task_id: int) -> list[GradingResultRead]:
        with SessionLocal() as db:
            task = db.get(GradingTask, task_id)
            if task is not None and task.status in self._GRADING_STARTED_STATUSES:
                self._ensure_missing_answer_results(db, task_id)
            db.commit()
            results = db.scalars(
                select(GradingResult)
                .where(GradingResult.task_id == task_id)
                .order_by(GradingResult.student_submission_id, GradingResult.question_id),
            ).all()
            return [self._to_grading_result_read(result) for result in results]

    def _run_grade_task_job(self, task_id: int, max_workers: int, force: bool) -> None:
        progress_channel = f"task:{task_id}"
        try:
            with SessionLocal() as db:
                task = db.get(GradingTask, task_id)
                if task is None:
                    return
                if force:
                    self._clear_after_grading(db, task_id)
                task.status = GradingTaskStatus.GRADING
                question_ids = [
                    question_id
                    for question_id, in db.execute(
                        select(Question.id)
                        .where(Question.task_id == task_id)
                        .order_by(Question.sort_order, Question.id),
                    ).all()
                ]
                total_answers = len(self._ready_answer_ids(db, task_id))
                completed_answers = 0 if force else self._completed_ready_answer_count(db, task_id)
                db.commit()

            self._publish(
                progress_channel,
                "stage_started",
                {
                    "stage": "grade_by_question",
                    "total_questions": len(question_ids),
                    "total_answers": total_answers,
                    "completed_answers": completed_answers,
                    "max_workers": max_workers,
                    "force": force,
                },
            )

            processed_answers = 0
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [
                    executor.submit(self._grade_one_question, task_id, question_id, force, progress_channel)
                    for question_id in question_ids
                ]
                for future in as_completed(futures):
                    try:
                        processed_answers += future.result()
                    except Exception as exc:
                        self._publish(
                            progress_channel,
                            "question_failed",
                            {
                                "stage": "grade_by_question",
                                "message": str(exc),
                            },
                        )
                    current_completed = min(total_answers, processed_answers if force else completed_answers + processed_answers)
                    self._publish(
                        progress_channel,
                        "question_progress",
                        {
                            "stage": "grade_by_question",
                            "completed_answers": current_completed,
                            "total_answers": total_answers,
                        },
                    )

            with SessionLocal() as db:
                self._ensure_missing_answer_results(db, task_id)
                task = db.get(GradingTask, task_id)
                if task is not None:
                    task.status = GradingTaskStatus.GRADED
                    db.commit()
            self._publish(
                progress_channel,
                "stage_done",
                {
                    "stage": "grade_by_question",
                    "answer_count": total_answers,
                },
            )
        except Exception as exc:
            with SessionLocal() as db:
                task = db.get(GradingTask, task_id)
                if task is not None:
                    task.status = GradingTaskStatus.FAILED
                    db.commit()
            self._publish(
                progress_channel,
                "stage_failed",
                {
                    "stage": "grade_by_question",
                    "message": str(exc),
                },
            )
        finally:
            with self._running_lock:
                self._running_task_ids.discard(task_id)

    def _run_grade_one_submission_job(self, task_id: int, submission_id: int) -> None:
        submission_key = (task_id, submission_id)
        progress_channel = f"task:{task_id}"
        student_name = ""
        student_no = ""
        question_ids: list[int] = []
        try:
            with SessionLocal() as db:
                submission = db.get(StudentSubmission, submission_id)
                if submission is None or submission.task_id != task_id:
                    return
                student_name = submission.student_name
                student_no = submission.student_no or ""
                self._clear_after_grading_for_submission(db, task_id, submission_id)
                question_ids = [
                    question_id
                    for question_id, in db.execute(
                        select(Question.id)
                        .where(Question.task_id == task_id)
                        .order_by(Question.sort_order, Question.id),
                    ).all()
                ]
                gradable_question_ids = [
                    question_id
                    for question_id in question_ids
                    if self._has_gradable_answers_for_submission(db, task_id, question_id, submission_id)
                ]
                db.commit()

            if not gradable_question_ids:
                return

            self._publish(
                progress_channel,
                "student_started",
                {
                    "stage": "grade_by_question",
                    "submission_id": submission_id,
                    "student_name": student_name,
                    "student_no": student_no,
                    "total_questions": len(gradable_question_ids),
                    "completed_questions": 0,
                },
            )
            completed_questions = 0
            for question_id in gradable_question_ids:
                self._grade_one_question(
                    task_id,
                    question_id,
                    force=True,
                    progress_channel=progress_channel,
                    submission_id=submission_id,
                )
                completed_questions += 1
                self._publish(
                    progress_channel,
                    "student_question_progress",
                    {
                        "stage": "grade_by_question",
                        "submission_id": submission_id,
                        "question_id": question_id,
                        "total_questions": len(gradable_question_ids),
                        "completed_questions": completed_questions,
                    },
                )
            with SessionLocal() as db:
                self._ensure_missing_answer_results_for_submission(db, task_id, submission_id)
                db.commit()
            self._publish(
                progress_channel,
                "student_done",
                {
                    "stage": "grade_by_question",
                    "submission_id": submission_id,
                    "student_name": student_name,
                    "student_no": student_no,
                    "total_questions": len(question_ids),
                    "completed_questions": len(question_ids),
                },
            )
        except Exception as exc:
            self._publish(
                progress_channel,
                "student_failed",
                {
                    "stage": "grade_by_question",
                    "submission_id": submission_id,
                    "student_name": student_name,
                    "student_no": student_no,
                    "total_questions": len(question_ids),
                    "completed_questions": 0,
                    "message": str(exc),
                },
            )
        finally:
            with self._running_lock:
                self._running_submission_keys.discard(submission_key)

    def _grade_one_question(
        self,
        task_id: int,
        question_id: int,
        force: bool,
        progress_channel: str,
        submission_id: int | None = None,
    ) -> int:
        with SessionLocal() as db:
            question = db.get(Question, question_id)
            if question is None:
                return 0
            rubrics = db.scalars(
                select(QuestionRubric)
                .where(QuestionRubric.question_id == question_id)
                .order_by(QuestionRubric.sort_order, QuestionRubric.id),
            ).all()
            if not rubrics:
                return 0
            answers = self._ready_answers_for_question(
                db,
                task_id,
                question_id,
                rubrics,
                force,
                submission_id=submission_id,
            )
            if not answers:
                return 0
            question_schema = self._to_question_read(question, rubrics)
            rubric_schemas = [self._to_rubric_read(rubric) for rubric in rubrics]
            answer_schemas = [
                self._to_student_answer_for_grading(answer, self._answer_evidence_for_grading(db, answer), db.get(StudentSubmission, answer.student_submission_id))
                for answer in answers
            ]

        self._publish(
            progress_channel,
            "question_started",
            {
                "stage": "grade_by_question",
                "question_id": question_id,
                "answer_count": len(answer_schemas),
            },
        )
        grading_results = self.grade_by_question(
            task_id=task_id,
            question=question_schema,
            rubrics=rubric_schemas,
            student_answers=answer_schemas,
        )
        self.save_grading_results(task_id, grading_results, update_task_status=False)
        self._publish(
            progress_channel,
            "question_done",
            {
                "stage": "grade_by_question",
                "question_id": question_id,
                "answer_count": len(grading_results),
            },
        )
        return len(grading_results)

    def _has_gradable_answers_for_submission(
        self,
        db,
        task_id: int,
        question_id: int,
        submission_id: int,
    ) -> bool:
        rubrics = db.scalars(
            select(QuestionRubric)
            .where(QuestionRubric.question_id == question_id)
            .order_by(QuestionRubric.sort_order, QuestionRubric.id),
        ).all()
        if not rubrics:
            return False
        return bool(
            self._ready_answers_for_question(
                db,
                task_id,
                question_id,
                rubrics,
                force=True,
                submission_id=submission_id,
            ),
        )

    def _gradable_question_count_for_submission(self, db, task_id: int, submission_id: int) -> int:
        question_ids = [
            question_id
            for question_id, in db.execute(
                select(Question.id)
                .where(Question.task_id == task_id)
                .order_by(Question.sort_order, Question.id),
            ).all()
        ]
        return sum(
            1
            for question_id in question_ids
            if self._has_gradable_answers_for_submission(db, task_id, question_id, submission_id)
        )

    def _ready_answers_for_question(
        self,
        db,
        task_id: int,
        question_id: int,
        rubrics: list[QuestionRubric],
        force: bool,
        submission_id: int | None = None,
    ) -> list[StudentAnswer]:
        query = (
            select(StudentAnswer)
            .where(StudentAnswer.task_id == task_id)
            .where(StudentAnswer.question_id == question_id)
        )
        if submission_id is not None:
            query = query.where(StudentAnswer.student_submission_id == submission_id)
        answers = db.scalars(query.order_by(StudentAnswer.student_submission_id, StudentAnswer.id)).all()
        existing_result_answer_ids = set()
        if not force:
            existing_result_answer_ids = {
                answer_id
                for answer_id, in db.execute(
                    select(GradingResult.student_answer_id).where(
                        GradingResult.task_id == task_id,
                        GradingResult.question_id == question_id,
                    ),
                ).all()
            }
        rubric_ids = {rubric.id for rubric in rubrics}
        ready_answers = []
        for answer in answers:
            if answer.id in existing_result_answer_ids:
                continue
            if not self._answer_should_use_ai(self._to_minimal_answer_for_check(answer)):
                continue
            evidence_rubric_ids = {
                rubric_id
                for rubric_id, in db.execute(
                    select(AnswerEvidence.rubric_id).where(AnswerEvidence.student_answer_id == answer.id),
                ).all()
            }
            if rubric_ids - evidence_rubric_ids:
                continue
            ready_answers.append(answer)
        return ready_answers

    def _ready_answer_ids(self, db, task_id: int) -> list[int]:
        questions = db.scalars(select(Question).where(Question.task_id == task_id)).all()
        rubric_ids_by_question_id = {
            question.id: {
                rubric_id
                for rubric_id, in db.execute(
                    select(QuestionRubric.id).where(QuestionRubric.question_id == question.id),
                ).all()
            }
            for question in questions
        }
        answers = db.scalars(
            select(StudentAnswer)
            .where(StudentAnswer.task_id == task_id)
            .order_by(StudentAnswer.student_submission_id, StudentAnswer.question_id),
        ).all()
        ready_ids = []
        for answer in answers:
            if not answer.answer_text.strip():
                continue
            rubric_ids = rubric_ids_by_question_id.get(answer.question_id, set())
            if not rubric_ids:
                continue
            evidence_rubric_ids = {
                rubric_id
                for rubric_id, in db.execute(
                    select(AnswerEvidence.rubric_id).where(AnswerEvidence.student_answer_id == answer.id),
                ).all()
            }
            if not (rubric_ids - evidence_rubric_ids):
                ready_ids.append(answer.id)
        return ready_ids

    def _completed_ready_answer_count(self, db, task_id: int) -> int:
        ready_answer_ids = self._ready_answer_ids(db, task_id)
        if not ready_answer_ids:
            return 0
        return len(
            {
                answer_id
                for answer_id, in db.execute(
                    select(GradingResult.student_answer_id).where(
                        GradingResult.task_id == task_id,
                        GradingResult.student_answer_id.in_(ready_answer_ids),
                    ),
                ).all()
            },
        )

    def _clear_after_grading(self, db, task_id: int) -> None:
        result_ids = select(GradingResult.id).where(GradingResult.task_id == task_id)
        db.execute(delete(GradingDeduction).where(GradingDeduction.grading_result_id.in_(result_ids)))
        db.execute(delete(GradingReflection).where(GradingReflection.grading_result_id.in_(result_ids)))
        db.execute(delete(TeacherRevision).where(TeacherRevision.grading_result_id.in_(result_ids)))
        db.execute(delete(GradingResult).where(GradingResult.task_id == task_id))

    def _clear_after_grading_for_submission(self, db, task_id: int, submission_id: int) -> None:
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

    def _answer_evidence_for_grading(self, db, answer: StudentAnswer) -> list[AnswerEvidence]:
        return db.scalars(
            select(AnswerEvidence)
            .where(AnswerEvidence.student_answer_id == answer.id)
            .order_by(AnswerEvidence.rubric_id, AnswerEvidence.id),
        ).all()

    def _to_minimal_answer_for_check(self, answer: StudentAnswer) -> StudentAnswerForGrading:
        return StudentAnswerForGrading(
            student_answer_id=answer.id,
            student_submission_id=answer.student_submission_id,
            answer_text=answer.answer_text,
        )

    def _to_student_answer_for_grading(
        self,
        answer: StudentAnswer,
        evidence_items: list[AnswerEvidence],
        submission: StudentSubmission | None,
    ) -> StudentAnswerForGrading:
        return StudentAnswerForGrading(
            student_answer_id=answer.id,
            student_submission_id=answer.student_submission_id,
            student_no=submission.student_no if submission else "",
            student_name=submission.student_name if submission else "",
            answer_text=answer.answer_text,
            answer_confidence=answer.confidence,
            structured_evidence=[
                EvidenceForGrading(
                    id=evidence.id,
                    rubric_id=evidence.rubric_id,
                    positive_evidence=evidence.positive_evidence or [],
                    negative_evidence=evidence.negative_evidence or [],
                    confidence=evidence.confidence,
                )
                for evidence in evidence_items
            ],
        )

    def _answer_should_use_ai(self, answer: StudentAnswerForGrading) -> bool:
        return bool(str(answer.answer_text or "").strip())

    def _ensure_missing_answer_results(self, db, task_id: int) -> None:
        missing_answers = db.scalars(
            select(StudentAnswer)
            .where(StudentAnswer.task_id == task_id)
            .where(
                (StudentAnswer.extraction_status == AnswerExtractionStatus.MISSING)
                | (StudentAnswer.answer_text == "")
            )
            .order_by(StudentAnswer.student_submission_id, StudentAnswer.question_id),
        ).all()
        self._upsert_missing_answer_results(db, task_id, missing_answers)

    def _ensure_missing_answer_results_for_submission(self, db, task_id: int, submission_id: int) -> None:
        missing_answers = db.scalars(
            select(StudentAnswer)
            .where(StudentAnswer.task_id == task_id)
            .where(StudentAnswer.student_submission_id == submission_id)
            .where(
                (StudentAnswer.extraction_status == AnswerExtractionStatus.MISSING)
                | (StudentAnswer.answer_text == "")
            )
            .order_by(StudentAnswer.question_id),
        ).all()
        self._upsert_missing_answer_results(db, task_id, missing_answers)

    def _upsert_missing_answer_results(self, db, task_id: int, missing_answers: list[StudentAnswer]) -> None:
        if not missing_answers:
            return

        answer_ids = [answer.id for answer in missing_answers]
        existing_results = db.scalars(
            select(GradingResult).where(
                GradingResult.task_id == task_id,
                GradingResult.student_answer_id.in_(answer_ids),
            ),
        ).all()
        existing_by_answer_id = {
            result.student_answer_id: result
            for result in existing_results
        }
        for answer in missing_answers:
            result = existing_by_answer_id.get(answer.id)
            values = {
                "task_id": task_id,
                "question_id": answer.question_id,
                "student_answer_id": answer.id,
                "student_submission_id": answer.student_submission_id,
                "score": 0,
                "final_score": None,
                "dimension_scores": [],
                "grading_status": GradingStatus.MISSING,
                "confidence": 1,
                "ai_comment": "缺答，记 0 分。",
                "final_comment": None,
                "review_required": False,
                "review_priority": ReviewPriority.LOW,
                "review_status": ReviewStatus.AI_GENERATED,
                "raw_llm_output": {"source": "system_missing_answer"},
            }
            if result is None:
                db.add(GradingResult(**values))
            else:
                for key, value in values.items():
                    setattr(result, key, value)

    def _validate_evidence_coverage(
        self,
        rubrics: list[QuestionRubricRead],
        student_answers: list[StudentAnswerForGrading],
    ) -> None:
        rubric_ids = {rubric.id for rubric in rubrics}
        if not rubric_ids:
            raise ValueError("grade_by_question requires at least one rubric dimension.")
        if not student_answers:
            raise ValueError("grade_by_question requires at least one student answer.")

        for answer in student_answers:
            evidence_rubric_ids = {item.rubric_id for item in answer.structured_evidence}
            missing_rubric_ids = rubric_ids - evidence_rubric_ids
            if missing_rubric_ids:
                missing = ", ".join(str(rubric_id) for rubric_id in sorted(missing_rubric_ids))
                raise ValueError(
                    "student_answer_id "
                    f"{answer.student_answer_id} is missing structured evidence for rubric_id(s): {missing}"
                )

    def _build_grading_input(self, student_answers: list[StudentAnswerForGrading]) -> list[dict]:
        return [
            {
                "student_answer_id": answer.student_answer_id,
                "student_submission_id": answer.student_submission_id,
                "student_id": answer.student_id,
                "student_no": answer.student_no,
                "student_name": answer.student_name,
                "answer_text": answer.answer_text,
                "answer_confidence": answer.answer_confidence,
                "structured_evidence": [
                    {
                        "evidence_id": evidence.id,
                        "rubric_id": evidence.rubric_id,
                        "positive_evidence": evidence.positive_evidence,
                        "negative_evidence": evidence.negative_evidence,
                        "confidence": evidence.confidence,
                    }
                    for evidence in answer.structured_evidence
                ],
            }
            for answer in student_answers
        ]

    def _build_cache_context(
        self,
        question: QuestionRead,
        rubrics: list[QuestionRubricRead],
    ) -> dict[str, str]:
        question_payload = {
            "question_number": question.question_number,
            "content": question.content,
            "question_type": question.question_type.value,
            "knowledge_points": question.knowledge_points,
            "difficulty": question.difficulty.value,
            "expected_answer_type": question.expected_answer_type,
            "total_score": question.total_score,
        }
        rubric_payload = [
            {
                "dimension_name": rubric.dimension_name,
                "dimension_description": rubric.dimension_description,
                "max_score": rubric.max_score,
                "scoring_criteria": rubric.scoring_criteria,
                "deduction_criteria": rubric.deduction_criteria,
                "evidence_requirement": rubric.evidence_requirement,
                "sort_order": rubric.sort_order,
            }
            for rubric in sorted(rubrics, key=lambda item: item.sort_order)
        ]
        return {
            "question_fingerprint": self._hash_json(question_payload),
            "rubric_fingerprint": self._hash_json(rubric_payload),
        }

    def _group_answers_by_cache_key(
        self,
        student_answers: list[StudentAnswerForGrading],
        cache_context: dict[str, str],
    ) -> dict[str, list[StudentAnswerForGrading]]:
        grouped: dict[str, list[StudentAnswerForGrading]] = {}
        for answer in student_answers:
            cache_key = self._build_cache_key(answer.answer_text, cache_context)
            grouped.setdefault(cache_key, []).append(answer)
        return grouped

    def _build_cache_key(self, answer_text: str, cache_context: dict[str, str]) -> str:
        payload = {
            "kind": "grade_by_question",
            "version": 1,
            "question_fingerprint": cache_context["question_fingerprint"],
            "rubric_fingerprint": cache_context["rubric_fingerprint"],
            "answer_hash": self._hash_text(answer_text),
        }
        return self._hash_json(payload)

    def _load_cached_payloads(self, cache_keys) -> dict[str, dict]:
        cache_keys = list(cache_keys)
        if not cache_keys:
            return {}
        self._ensure_cache_schema()
        with SessionLocal() as db:
            rows = db.scalars(
                select(GradingCache).where(GradingCache.cache_key.in_(cache_keys)),
            ).all()
            return {
                row.cache_key: row.result_payload
                for row in rows
                if isinstance(row.result_payload, dict)
            }

    def _save_cached_payloads(self, cache_rows: list[dict]) -> None:
        if not cache_rows:
            return
        self._ensure_cache_schema()
        with SessionLocal() as db:
            existing_rows = db.scalars(
                select(GradingCache).where(
                    GradingCache.cache_key.in_([row["cache_key"] for row in cache_rows]),
                ),
            ).all()
            existing_by_key = {row.cache_key: row for row in existing_rows}
            for row in cache_rows:
                existing = existing_by_key.get(row["cache_key"])
                if existing is None:
                    db.add(GradingCache(**row))
                    continue
                for key, value in row.items():
                    setattr(existing, key, value)
            db.commit()

    def _build_cache_row(
        self,
        cache_key: str,
        cache_context: dict[str, str],
        answer: StudentAnswerForGrading,
        result: GradingResultCreate,
    ) -> dict:
        return {
            "cache_key": cache_key,
            "question_fingerprint": cache_context["question_fingerprint"],
            "rubric_fingerprint": cache_context["rubric_fingerprint"],
            "answer_hash": self._hash_text(answer.answer_text),
            "answer_text": answer.answer_text,
            "result_payload": self._build_cache_payload(result),
        }

    def _build_cache_payload(self, result: GradingResultCreate) -> dict:
        payload = result.model_dump(mode="json")
        for key in ("task_id", "question_id", "student_answer_id", "student_submission_id"):
            payload.pop(key, None)
        for dimension in payload.get("dimension_scores", []):
            dimension["evidence_ids"] = []
        return payload

    def _clone_cached_result(
        self,
        task_id: int,
        question_id: int,
        answer: StudentAnswerForGrading,
        cache_key: str,
        payload: dict,
    ) -> GradingResultCreate:
        values = copy.deepcopy(payload)
        values["task_id"] = task_id
        values["question_id"] = question_id
        values["student_answer_id"] = answer.student_answer_id
        values["student_submission_id"] = answer.student_submission_id
        values["dimension_scores"] = self._remap_dimension_evidence_ids(
            values.get("dimension_scores") or [],
            answer,
        )
        values["raw_llm_output"] = {
            "source": "grading_cache",
            "cache_key": cache_key,
            "cached_raw_llm_output": values.get("raw_llm_output"),
        }
        return GradingResultCreate(**values)

    def _remap_dimension_evidence_ids(
        self,
        dimension_scores: list[dict],
        answer: StudentAnswerForGrading,
    ) -> list[dict]:
        evidence_ids_by_rubric_id = {
            evidence.rubric_id: [evidence.id] if evidence.id is not None else []
            for evidence in answer.structured_evidence
        }
        remapped = []
        for dimension in dimension_scores:
            item = copy.deepcopy(dimension)
            item["evidence_ids"] = evidence_ids_by_rubric_id.get(item.get("rubric_id"), [])
            remapped.append(item)
        return remapped

    def _hash_text(self, value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _hash_json(self, value) -> str:
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return self._hash_text(encoded)

    def _ensure_cache_schema(self) -> None:
        GradingCache.__table__.create(bind=engine, checkfirst=True)

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

    def _to_grading_result_read(self, result: GradingResult) -> GradingResultRead:
        return GradingResultRead(
            id=result.id,
            task_id=result.task_id,
            question_id=result.question_id,
            student_answer_id=result.student_answer_id,
            student_submission_id=result.student_submission_id,
            score=result.score,
            final_score=result.final_score,
            dimension_scores=result.dimension_scores or [],
            grading_status=result.grading_status,
            confidence=result.confidence,
            ai_comment=result.ai_comment,
            final_comment=result.final_comment,
            review_required=result.review_required,
            review_priority=result.review_priority,
            review_status=result.review_status,
            raw_llm_output=result.raw_llm_output,
            created_at=result.created_at,
            updated_at=result.updated_at,
        )

    def _publish(self, channel: str, event: str, data: dict[str, Any]) -> None:
        progress_event_service.publish(channel, event, data)


grading_service = GradingService()
