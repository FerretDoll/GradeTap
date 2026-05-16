from __future__ import annotations

import re

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import delete, or_, select

from app.db.models import (
    AdaptiveGradingRule,
    AnswerEvidence,
    AnswerGroup,
    AnswerGroupMember,
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
from app.models.file import FileRole
from app.models.task import GradingTaskStatus
from app.prompts.question_analyzer_prompt import (
    QUESTION_ANALYZER_OUTPUT_SCHEMA,
    build_question_analyzer_prompt,
)
from app.schemas.question import QuestionCreate, QuestionRead
from app.services.llm_service import LLMService, llm_service
from app.services.progress_event_service import progress_event_service


class QuestionAnalyzerService:
    def __init__(self, llm: LLMService = llm_service) -> None:
        self._llm = llm

    def analyze_questions(
        self,
        task_id: int,
        requirement_text: str,
        reference_answer_text: str = "",
        grading_instruction: str = "",
        progress_channel: str | None = None,
    ) -> list[QuestionCreate]:
        prompt = build_question_analyzer_prompt(
            requirement_text=requirement_text,
            reference_answer_text=reference_answer_text,
            grading_instruction=grading_instruction,
        )
        if progress_channel:
            payload = self._llm.chat_json_stream(
                prompt,
                schema=QUESTION_ANALYZER_OUTPUT_SCHEMA,
                on_delta=self._build_delta_handler(progress_channel, "analyze_questions"),
            )
        else:
            payload = self._llm.chat_json(prompt, schema=QUESTION_ANALYZER_OUTPUT_SCHEMA)
        questions = payload.get("questions", [])
        return [QuestionCreate(task_id=task_id, **item) for item in questions]

    def analyze_task_questions(self, task_id: int) -> dict:
        with SessionLocal() as db:
            task = db.get(GradingTask, task_id)
            if task is None:
                raise HTTPException(status_code=404, detail="Task not found")

            files = db.scalars(
                select(UploadedFile)
                .where(UploadedFile.task_id == task_id)
                .order_by(UploadedFile.file_role, UploadedFile.id),
            ).all()
            requirement_text = self._combined_parsed_text(files, FileRole.REQUIREMENT)
            reference_answer_text = self._combined_parsed_text(files, FileRole.REFERENCE_ANSWER)
            if not requirement_text.strip():
                raise HTTPException(status_code=400, detail="请先解析作业要求文件，再进行题目分析")

            progress_channel = f"task:{task_id}"
            self._publish(progress_channel, "stage_started", {"stage": "analyze_questions"})
            try:
                question_payloads = self.analyze_questions(
                    task_id=task_id,
                    requirement_text=requirement_text,
                    reference_answer_text=reference_answer_text,
                    grading_instruction=task.grading_instruction,
                    progress_channel=progress_channel,
                )
            except ValidationError as exc:
                self._publish(progress_channel, "stage_failed", {"stage": "analyze_questions", "message": str(exc)})
                raise HTTPException(status_code=502, detail=f"题目分析字段不完整或不合法：{exc}") from exc
            except ValueError as exc:
                self._publish(progress_channel, "stage_failed", {"stage": "analyze_questions", "message": str(exc)})
                raise HTTPException(status_code=502, detail=f"题目分析结果不是合法 JSON：{exc}") from exc
            except RuntimeError as exc:
                self._publish(progress_channel, "stage_failed", {"stage": "analyze_questions", "message": str(exc)})
                raise HTTPException(status_code=502, detail=str(exc)) from exc

            if not question_payloads:
                self._publish(progress_channel, "stage_failed", {"stage": "analyze_questions", "message": "题目分析未返回任何题目"})
                raise HTTPException(status_code=502, detail="题目分析未返回任何题目")

            self._clear_after_question_analysis(db, task_id)

            questions = [
                Question(
                    task_id=question.task_id,
                    question_number=question.question_number,
                    content=question.content,
                    question_type=question.question_type,
                    knowledge_points=question.knowledge_points,
                    difficulty=question.difficulty,
                    expected_answer_type=question.expected_answer_type,
                    total_score=question.total_score,
                    sort_order=question.sort_order,
                )
                for question in question_payloads
            ]
            db.add_all(questions)
            task.status = GradingTaskStatus.QUESTIONS_ANALYZED
            db.commit()

            for question in questions:
                db.refresh(question)

            result = {
                "task_id": task_id,
                "status": task.status.value,
                "stage": "analyze_questions",
                "question_count": len(questions),
                "questions": [self._to_read_schema(question).model_dump(mode="json") for question in questions],
            }
            self._publish(
                progress_channel,
                "stage_done",
                {"stage": "analyze_questions", "question_count": len(questions)},
            )
            return result

    def list_task_questions(self, task_id: int) -> list[QuestionRead]:
        with SessionLocal() as db:
            task = db.get(GradingTask, task_id)
            if task is None:
                raise HTTPException(status_code=404, detail="Task not found")
            questions = db.scalars(
                select(Question)
                .where(Question.task_id == task_id)
                .order_by(Question.sort_order, Question.id),
            ).all()
            return [self._to_read_schema(question) for question in questions]

    def _combined_parsed_text(self, files: list[UploadedFile], file_role: FileRole) -> str:
        return "\n\n".join(
            uploaded_file.parsed_text
            for uploaded_file in files
            if uploaded_file.file_role == file_role and uploaded_file.parsed_text.strip()
        )

    def _to_read_schema(self, question: Question) -> QuestionRead:
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

    def _build_delta_handler(self, channel: str | None, stage: str):
        if not channel:
            return None
        buffer = ""
        seen_question_numbers: set[str] = set()
        ordered_question_numbers: list[str] = []

        def on_delta(text: str) -> None:
            nonlocal buffer
            buffer += text
            current_numbers = re.findall(r'"question_number"\s*:\s*"([^"]+)"', buffer)
            new_numbers = [number for number in current_numbers if number not in seen_question_numbers]
            if not new_numbers:
                return
            seen_question_numbers.update(new_numbers)
            ordered_question_numbers.extend(new_numbers)
            self._publish(
                channel,
                "llm_progress",
                {
                    "stage": stage,
                    "recognized_count": len(ordered_question_numbers),
                    "question_numbers": ordered_question_numbers,
                },
            )

        return on_delta

    def _publish(self, channel: str | None, event: str, data: dict) -> None:
        if channel:
            progress_event_service.publish(channel, event, data)

    def _clear_after_question_analysis(self, db, task_id: int) -> None:
        question_ids = select(Question.id).where(Question.task_id == task_id)
        grading_result_ids = select(GradingResult.id).where(GradingResult.task_id == task_id)
        answer_group_ids = select(AnswerGroup.id).where(AnswerGroup.task_id == task_id)

        db.execute(
            delete(GradingDeduction).where(
                GradingDeduction.grading_result_id.in_(grading_result_ids),
            ),
        )
        db.execute(
            delete(GradingReflection).where(
                or_(
                    GradingReflection.grading_result_id.in_(grading_result_ids),
                    GradingReflection.task_id == task_id,
                ),
            ),
        )
        db.execute(
            delete(TeacherRevision).where(
                or_(
                    TeacherRevision.grading_result_id.in_(grading_result_ids),
                    TeacherRevision.task_id == task_id,
                ),
            ),
        )
        db.execute(delete(GradingResult).where(GradingResult.task_id == task_id))
        db.execute(delete(AnswerEvidence).where(AnswerEvidence.task_id == task_id))
        db.execute(delete(AnswerGroupMember).where(AnswerGroupMember.answer_group_id.in_(answer_group_ids)))
        db.execute(delete(AnswerGroup).where(AnswerGroup.task_id == task_id))
        db.execute(delete(StudentAnswer).where(StudentAnswer.task_id == task_id))
        db.execute(delete(StudentSubmission).where(StudentSubmission.task_id == task_id))
        db.execute(
            delete(AdaptiveGradingRule).where(
                or_(
                    AdaptiveGradingRule.task_id == task_id,
                    AdaptiveGradingRule.question_id.in_(question_ids),
                ),
            ),
        )
        db.execute(delete(QuestionRubric).where(QuestionRubric.question_id.in_(question_ids)))
        db.execute(delete(Question).where(Question.task_id == task_id))


question_analyzer_service = QuestionAnalyzerService()
