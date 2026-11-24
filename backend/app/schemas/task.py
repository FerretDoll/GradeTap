from datetime import datetime

from pydantic import BaseModel, Field

from app.models.task import GradingTaskStatus


class GradingTaskCreate(BaseModel):
    task_name: str = Field(..., min_length=1, max_length=255)
    offering_id: int = Field(gt=0)
    assignment_id: int | None = Field(None, gt=0)
    assignment_name: str = Field(default="", max_length=255)
    grading_instruction: str = Field(default="")


class GradingTaskRead(BaseModel):
    offering_id: int | None
    course_id: int | None
    class_group_id: int | None
    assignment_id: int | None
    submission_round: int
    is_archived: bool
    archived_at: datetime | None
    id: int
    task_name: str
    course_name: str
    assignment_name: str = ""
    class_name: str
    status: GradingTaskStatus
    grading_instruction: str
    created_at: datetime
    updated_at: datetime
