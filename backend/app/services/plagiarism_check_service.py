from __future__ import annotations

import difflib
from dataclasses import dataclass
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import delete, desc, or_, select

from app.db.models import (
    PlagiarismCheck,
    PlagiarismMatch,
    Question,
    StudentAnswer,
    StudentPlagiarismSummary,
    StudentSubmission,
)
from app.db.session import Base, SessionLocal, engine
from app.models.plagiarism import PlagiarismCheckStatus, PlagiarismRiskLevel
from app.schemas.plagiarism import (
    PlagiarismCheckRead,
    PlagiarismMatchedSegment,
    PlagiarismRunResponse,
    PlagiarismStudentDetailRead,
    PlagiarismStudentMatchRead,
    PlagiarismStudentSummaryRead,
    PlagiarismStudentsResponse,
)


@dataclass(frozen=True)
class NormalizedText:
    text: str
    index_map: list[int]


class PlagiarismCheckService:
    min_similarity = 0.2
    min_segment_chars = 32
    snippet_context_chars = 40

    def run_check(self, task_id: int) -> PlagiarismRunResponse:
        self._ensure_schema()
        with SessionLocal() as db:
            submissions = db.scalars(
                select(StudentSubmission)
                .where(StudentSubmission.task_id == task_id)
                .order_by(StudentSubmission.id),
            ).all()
            if not submissions:
                raise HTTPException(status_code=400, detail="请先完成学生解析，再运行查重测试")

            self._clear_task_results(db, task_id)
            check = PlagiarismCheck(
                task_id=task_id,
                status=PlagiarismCheckStatus.RUNNING,
                threshold=self.min_similarity,
                raw_config={
                    "scope": "question_answers",
                    "min_similarity": self.min_similarity,
                    "min_segment_chars": self.min_segment_chars,
                    "overall_similarity": "weighted_by_question_score",
                    "effects": "independent_test_only",
                },
            )
            db.add(check)
            db.flush()

            try:
                questions = db.scalars(
                    select(Question)
                    .where(Question.task_id == task_id)
                    .order_by(Question.sort_order, Question.id),
                ).all()
                if not questions:
                    raise HTTPException(status_code=400, detail="请先完成题目分析，再运行作业查重")
                answers = db.scalars(
                    select(StudentAnswer).where(StudentAnswer.task_id == task_id),
                ).all()
                answers_by_submission_question = {
                    (answer.student_submission_id, answer.question_id): answer
                    for answer in answers
                }
                if not answers_by_submission_question:
                    raise HTTPException(status_code=400, detail="请先完成答案抽取，再运行作业查重")

                pair_results: list[PlagiarismMatch] = []
                for left_index, left in enumerate(submissions):
                    for right in submissions[left_index + 1 :]:
                        result = self._compare_pair(
                            left,
                            right,
                            questions,
                            answers_by_submission_question,
                        )
                        if result["similarity_score"] < self.min_similarity:
                            continue
                        pair_results.append(
                            PlagiarismMatch(
                                task_id=task_id,
                                check_id=check.id,
                                student_a_submission_id=left.id,
                                student_b_submission_id=right.id,
                                similarity_score=result["similarity_score"],
                                risk_level=result["risk_level"],
                                matched_segments=result["matched_segments"],
                                evidence_summary=result["evidence_summary"],
                                raw_result=result["raw_result"],
                            ),
                        )
                db.add_all(pair_results)
                db.flush()

                summaries = self._build_summaries(task_id, check.id, submissions, pair_results)
                db.add_all(summaries)
                check.status = PlagiarismCheckStatus.COMPLETED
                check.finished_at = datetime.utcnow()
                db.commit()
                db.refresh(check)
            except Exception as exc:
                check.status = PlagiarismCheckStatus.FAILED
                check.error_message = str(exc)
                check.finished_at = datetime.utcnow()
                db.commit()
                raise

            return PlagiarismRunResponse(
                task_id=task_id,
                check=self._check_to_schema(check),
                total_students=len(submissions),
                match_count=len(pair_results),
            )

    def get_latest_check(self, task_id: int) -> PlagiarismCheckRead | None:
        self._ensure_schema()
        with SessionLocal() as db:
            check = self._latest_check(db, task_id)
            return self._check_to_schema(check) if check else None

    def list_student_summaries(self, task_id: int) -> PlagiarismStudentsResponse:
        self._ensure_schema()
        with SessionLocal() as db:
            check = self._latest_check(db, task_id)
            if check is None:
                return PlagiarismStudentsResponse(task_id=task_id, check=None, students=[])

            summaries = db.scalars(
                select(StudentPlagiarismSummary)
                .where(StudentPlagiarismSummary.task_id == task_id, StudentPlagiarismSummary.check_id == check.id)
                .order_by(desc(StudentPlagiarismSummary.max_similarity_score), StudentPlagiarismSummary.student_name),
            ).all()
            return PlagiarismStudentsResponse(
                task_id=task_id,
                check=self._check_to_schema(check),
                students=[self._summary_to_schema(summary, []) for summary in summaries],
            )

    def get_student_detail(self, task_id: int, student_submission_id: int) -> PlagiarismStudentDetailRead:
        self._ensure_schema()
        with SessionLocal() as db:
            check = self._latest_check(db, task_id)
            if check is None:
                raise HTTPException(status_code=404, detail="暂无查重结果")

            summary = db.scalars(
                select(StudentPlagiarismSummary).where(
                    StudentPlagiarismSummary.task_id == task_id,
                    StudentPlagiarismSummary.check_id == check.id,
                    StudentPlagiarismSummary.student_submission_id == student_submission_id,
                ),
            ).first()
            if summary is None:
                raise HTTPException(status_code=404, detail="未找到该学生的查重结果")

            matches = db.scalars(
                select(PlagiarismMatch)
                .where(
                    PlagiarismMatch.task_id == task_id,
                    PlagiarismMatch.check_id == check.id,
                    or_(
                        PlagiarismMatch.student_a_submission_id == student_submission_id,
                        PlagiarismMatch.student_b_submission_id == student_submission_id,
                    ),
                )
                .order_by(desc(PlagiarismMatch.similarity_score)),
            ).all()
            submission_ids = {
                item.student_a_submission_id
                for item in matches
            } | {
                item.student_b_submission_id
                for item in matches
            }
            submissions = {}
            if submission_ids:
                submissions = {
                    submission.id: submission
                    for submission in db.scalars(
                        select(StudentSubmission).where(StudentSubmission.id.in_(submission_ids)),
                    ).all()
                }
            return PlagiarismStudentDetailRead(
                **self._summary_to_schema(
                    summary,
                    [self._match_to_schema(match, student_submission_id, submissions) for match in matches],
                ).model_dump(),
                check=self._check_to_schema(check),
            )

    def clear_task_results(self, task_id: int) -> None:
        self._ensure_schema()
        with SessionLocal() as db:
            self._clear_task_results(db, task_id)
            db.commit()

    def _ensure_schema(self) -> None:
        Base.metadata.create_all(
            bind=engine,
            tables=[
                PlagiarismCheck.__table__,
                StudentPlagiarismSummary.__table__,
                PlagiarismMatch.__table__,
            ],
        )

    def _clear_task_results(self, db, task_id: int) -> None:
        db.execute(delete(PlagiarismMatch).where(PlagiarismMatch.task_id == task_id))
        db.execute(delete(StudentPlagiarismSummary).where(StudentPlagiarismSummary.task_id == task_id))
        db.execute(delete(PlagiarismCheck).where(PlagiarismCheck.task_id == task_id))

    def _latest_check(self, db, task_id: int) -> PlagiarismCheck | None:
        return db.scalars(
            select(PlagiarismCheck)
            .where(PlagiarismCheck.task_id == task_id)
            .order_by(desc(PlagiarismCheck.id)),
        ).first()

    def _normalize(self, value: str) -> NormalizedText:
        chars: list[str] = []
        index_map: list[int] = []
        for index, char in enumerate(value or ""):
            lowered = char.lower()
            if lowered.isspace() or lowered == "_":
                continue
            chars.append(lowered)
            index_map.append(index)
        return NormalizedText("".join(chars), index_map)

    def _compare_pair(
        self,
        left: StudentSubmission,
        right: StudentSubmission,
        questions: list[Question],
        answers_by_submission_question: dict[tuple[int, int], StudentAnswer],
    ) -> dict:
        weighted_similarity = 0.0
        total_weight = 0.0
        comparable_questions = 0
        segments: list[dict] = []
        question_results: list[dict] = []

        for question in questions:
            left_answer = answers_by_submission_question.get((left.id, question.id))
            right_answer = answers_by_submission_question.get((right.id, question.id))
            left_text = left_answer.answer_text if left_answer else ""
            right_text = right_answer.answer_text if right_answer else ""
            if not left_text.strip() and not right_text.strip():
                continue

            weight = max(float(question.total_score or 0), 1.0)
            question_result = self._compare_question_answer(question, left_text, right_text)
            weighted_similarity += question_result["similarity_score"] * weight
            total_weight += weight
            comparable_questions += 1
            question_results.append(
                {
                    "question_id": question.id,
                    "question_number": question.question_number,
                    "question_similarity": question_result["similarity_score"],
                    "weight": weight,
                },
            )
            segments.extend(question_result["matched_segments"])

        if total_weight <= 0:
            return self._empty_result()

        similarity = round(weighted_similarity / total_weight, 4)
        risk_level = self._risk_level(similarity)
        return {
            "similarity_score": similarity,
            "risk_level": risk_level,
            "matched_segments": segments,
            "evidence_summary": f"发现 {len(segments)} 个重复片段，按题加权相似度 {round(similarity * 100)}%",
            "raw_result": {
                "left_submission_id": left.id,
                "right_submission_id": right.id,
                "scope": "question_answers",
                "comparable_questions": comparable_questions,
                "question_results": question_results,
            },
        }

    def _compare_question_answer(self, question: Question, left_text: str, right_text: str) -> dict:
        left_norm = self._normalize(left_text)
        right_norm = self._normalize(right_text)
        if not left_norm.text or not right_norm.text:
            return {
                "similarity_score": 0,
                "matched_segments": [],
            }

        matcher = difflib.SequenceMatcher(None, left_norm.text, right_norm.text, autojunk=False)
        blocks = [
            block
            for block in matcher.get_matching_blocks()
            if block.size >= self.min_segment_chars
        ]
        common_chars = sum(block.size for block in blocks)
        similarity = round((2 * common_chars) / (len(left_norm.text) + len(right_norm.text)), 4)
        return {
            "similarity_score": similarity,
            "matched_segments": self._build_segments(
                left_text,
                right_text,
                left_norm,
                right_norm,
                blocks,
                question,
                similarity,
            ),
        }

    def _empty_result(self) -> dict:
        return {
            "similarity_score": 0,
            "risk_level": PlagiarismRiskLevel.NONE,
            "matched_segments": [],
            "evidence_summary": "可比对文本为空",
            "raw_result": {},
        }

    def _build_segments(
        self,
        left_content: str,
        right_content: str,
        left_norm: NormalizedText,
        right_norm: NormalizedText,
        blocks,
        question: Question,
        question_similarity: float,
    ) -> list[dict]:
        segments: list[dict] = []
        for index, block in enumerate(blocks[:12], start=1):
            left_start = left_norm.index_map[block.a]
            left_end = left_norm.index_map[block.a + block.size - 1] + 1
            right_start = right_norm.index_map[block.b]
            right_end = right_norm.index_map[block.b + block.size - 1] + 1
            left_snippet = self._snippet(left_content, left_start, left_end)
            right_snippet = self._snippet(right_content, right_start, right_end)
            segments.append(
                {
                    "segment_id": f"seg_{index:03d}",
                    "question_id": question.id,
                    "question_number": question.question_number,
                    "question_content": question.content,
                    "question_similarity": question_similarity,
                    "student_a_text": left_snippet,
                    "student_b_text": right_snippet,
                    "student_a_answer_text": left_content,
                    "student_b_answer_text": right_content,
                    "similarity": self._snippet_similarity(left_snippet, right_snippet),
                    "student_a_start": left_start,
                    "student_a_end": left_end,
                    "student_b_start": right_start,
                    "student_b_end": right_end,
                },
            )
        return segments

    def _snippet(self, content: str, start: int, end: int) -> str:
        prefix = max(0, start - self.snippet_context_chars)
        suffix = min(len(content), end + self.snippet_context_chars)
        return content[prefix:suffix].strip()

    def _snippet_similarity(self, left: str, right: str) -> float:
        left_norm = self._normalize(left).text
        right_norm = self._normalize(right).text
        if not left_norm or not right_norm:
            return 0
        return round(difflib.SequenceMatcher(None, left_norm, right_norm, autojunk=False).ratio(), 4)

    def _risk_level(self, similarity: float) -> PlagiarismRiskLevel:
        if similarity >= 0.7:
            return PlagiarismRiskLevel.HIGH
        if similarity >= 0.45:
            return PlagiarismRiskLevel.MEDIUM
        if similarity >= self.min_similarity:
            return PlagiarismRiskLevel.LOW
        return PlagiarismRiskLevel.NONE

    def _build_summaries(
        self,
        task_id: int,
        check_id: int,
        submissions: list[StudentSubmission],
        matches: list[PlagiarismMatch],
    ) -> list[StudentPlagiarismSummary]:
        summaries: list[StudentPlagiarismSummary] = []
        for submission in submissions:
            related = [
                match
                for match in matches
                if submission.id in {match.student_a_submission_id, match.student_b_submission_id}
            ]
            top_match = max(related, key=lambda item: item.similarity_score, default=None)
            summaries.append(
                StudentPlagiarismSummary(
                    task_id=task_id,
                    check_id=check_id,
                    student_submission_id=submission.id,
                    student_no=submission.student_no,
                    student_name=submission.student_name,
                    max_similarity_score=top_match.similarity_score if top_match else 0,
                    similar_students_count=len(related),
                    risk_level=top_match.risk_level if top_match else PlagiarismRiskLevel.NONE,
                    top_match_submission_id=self._other_submission_id(top_match, submission.id) if top_match else None,
                ),
            )
        return summaries

    def _other_submission_id(self, match: PlagiarismMatch, submission_id: int) -> int:
        if match.student_a_submission_id == submission_id:
            return match.student_b_submission_id
        return match.student_a_submission_id

    def _check_to_schema(self, check: PlagiarismCheck) -> PlagiarismCheckRead:
        return PlagiarismCheckRead(
            id=check.id,
            task_id=check.task_id,
            status=check.status,
            algorithm=check.algorithm,
            threshold=check.threshold,
            error_message=check.error_message,
            finished_at=check.finished_at,
            created_at=check.created_at,
            updated_at=check.updated_at,
        )

    def _summary_to_schema(
        self,
        summary: StudentPlagiarismSummary,
        matches: list[PlagiarismStudentMatchRead],
    ) -> PlagiarismStudentSummaryRead:
        return PlagiarismStudentSummaryRead(
            student_submission_id=summary.student_submission_id,
            student_no=summary.student_no,
            student_name=summary.student_name,
            max_similarity_score=summary.max_similarity_score,
            similar_students_count=summary.similar_students_count,
            risk_level=summary.risk_level,
            top_match_submission_id=summary.top_match_submission_id,
            matches=matches,
        )

    def _match_to_schema(
        self,
        match: PlagiarismMatch,
        current_submission_id: int,
        submissions: dict[int, StudentSubmission],
    ) -> PlagiarismStudentMatchRead:
        other_id = self._other_submission_id(match, current_submission_id)
        other = submissions.get(other_id)
        return PlagiarismStudentMatchRead(
            match_id=match.id,
            student_submission_id=other_id,
            student_no=other.student_no if other else "",
            student_name=other.student_name if other else "未知学生",
            similarity_score=match.similarity_score,
            risk_level=match.risk_level,
            matched_segments=self._orient_segments(match.matched_segments or [], current_submission_id, match),
            evidence_summary=match.evidence_summary,
        )

    def _orient_segments(
        self,
        segments: list[dict],
        current_submission_id: int,
        match: PlagiarismMatch,
    ) -> list[PlagiarismMatchedSegment]:
        current_is_a = match.student_a_submission_id == current_submission_id
        oriented = []
        for segment in segments:
            if current_is_a:
                oriented.append(
                    PlagiarismMatchedSegment(
                        segment_id=segment.get("segment_id", ""),
                        question_id=segment.get("question_id"),
                        question_number=segment.get("question_number", ""),
                        question_content=segment.get("question_content", ""),
                        question_similarity=segment.get("question_similarity", 0),
                        similarity=segment.get("similarity", 1),
                        student_text=segment.get("student_a_text", ""),
                        matched_student_text=segment.get("student_b_text", ""),
                        student_answer_text=segment.get("student_a_answer_text", ""),
                        matched_student_answer_text=segment.get("student_b_answer_text", ""),
                        student_start=segment.get("student_a_start", 0),
                        student_end=segment.get("student_a_end", 0),
                        matched_student_start=segment.get("student_b_start", 0),
                        matched_student_end=segment.get("student_b_end", 0),
                    ),
                )
            else:
                oriented.append(
                    PlagiarismMatchedSegment(
                        segment_id=segment.get("segment_id", ""),
                        question_id=segment.get("question_id"),
                        question_number=segment.get("question_number", ""),
                        question_content=segment.get("question_content", ""),
                        question_similarity=segment.get("question_similarity", 0),
                        similarity=segment.get("similarity", 1),
                        student_text=segment.get("student_b_text", ""),
                        matched_student_text=segment.get("student_a_text", ""),
                        student_answer_text=segment.get("student_b_answer_text", ""),
                        matched_student_answer_text=segment.get("student_a_answer_text", ""),
                        student_start=segment.get("student_b_start", 0),
                        student_end=segment.get("student_b_end", 0),
                        matched_student_start=segment.get("student_a_start", 0),
                        matched_student_end=segment.get("student_a_end", 0),
                    ),
                )
        return oriented


plagiarism_check_service = PlagiarismCheckService()
