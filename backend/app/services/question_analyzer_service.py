from __future__ import annotations

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import delete, select

from app.db.models import GradingTask, Question, QuestionRubric, UploadedFile
from app.db.session import SessionLocal
from app.models.file import FileRole
from app.models.task import GradingTaskStatus
from app.prompts.question_analyzer_prompt import (
    QUESTION_ANALYZER_OUTPUT_SCHEMA,
    build_question_analyzer_prompt,
)
from app.schemas.question import QuestionCreate, QuestionRead
from app.services.llm_service import LLMService, llm_service


class QuestionAnalyzerService:
    def __init__(self, llm: LLMService = llm_service) -> None:
        self._llm = llm

    def analyze_questions(
        self,
        task_id: int,
        requirement_text: str,
        reference_answer_text: str = "",
        grading_instruction: str = "",
    ) -> list[QuestionCreate]:
        prompt = build_question_analyzer_prompt(
            requirement_text=requirement_text,
            reference_answer_text=reference_answer_text,
            grading_instruction=grading_instruction,
        )
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

            try:
                question_payloads = self.analyze_questions(
                    task_id=task_id,
                    requirement_text=requirement_text,
                    reference_answer_text=reference_answer_text,
                    grading_instruction=task.grading_instruction,
                )
            except ValidationError as exc:
                raise HTTPException(status_code=502, detail=f"题目分析字段不完整或不合法：{exc}") from exc
            except ValueError as exc:
                raise HTTPException(status_code=502, detail=f"题目分析结果不是合法 JSON：{exc}") from exc
            except RuntimeError as exc:
                raise HTTPException(status_code=502, detail=str(exc)) from exc

            if not question_payloads:
                raise HTTPException(status_code=502, detail="题目分析未返回任何题目")

            db.execute(
                delete(QuestionRubric).where(
                    QuestionRubric.question_id.in_(
                        select(Question.id).where(Question.task_id == task_id),
                    ),
                ),
            )
            db.execute(delete(Question).where(Question.task_id == task_id))

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

            return {
                "task_id": task_id,
                "status": task.status.value,
                "stage": "analyze_questions",
                "question_count": len(questions),
                "questions": [self._to_read_schema(question).model_dump(mode="json") for question in questions],
            }

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


question_analyzer_service = QuestionAnalyzerService()
