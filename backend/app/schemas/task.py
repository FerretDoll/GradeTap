from datetime import datetime

from pydantic import BaseModel, Field

from app.models.task import GradingTaskStatus


class GradingTaskCreate(BaseModel):
    task_name: str = Field(..., min_length=1, max_length=255)
    course_name: str = Field(..., min_length=1, max_length=255)
    class_name: str = Field(..., min_length=1, max_length=255)
    grading_instruction: str = Field(default="")


class GradingTaskRead(BaseModel):
    id: int
    task_name: str
    course_name: str
    class_name: str
    status: GradingTaskStatus
    grading_instruction: str
    created_at: datetime
    updated_at: datetime
