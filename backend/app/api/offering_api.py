from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.db.models import Account
from app.db.session import get_db
from app.services.access import active_user
from app.services.offering_service import create_offering, list_offerings

router = APIRouter()


class OfferingRead(BaseModel):
    id: int
    course_id: int
    class_group_id: int
    term: str
    course_name: str
    class_name: str
    teaching_role: str
    allowed_actions: list[str]


class OfferingCreate(BaseModel):
    term: str = Field(min_length=1, max_length=64, pattern=r"\S")
    course_id: int | None = Field(None, gt=0)
    class_group_id: int | None = Field(None, gt=0)
    course_name: str | None = Field(None, max_length=255, pattern=r"\S")
    class_name: str | None = Field(None, max_length=255, pattern=r"\S")

    @model_validator(mode="after")
    def validate_targets(self):
        for identifier, name in [(self.course_id, self.course_name), (self.class_group_id, self.class_name)]:
            if (identifier is None) == (name is None):
                raise ValueError("请选择已有记录或填写新名称")
        return self


@router.get("/offerings", response_model=list[OfferingRead])
def offerings(user: Account = Depends(active_user), db: Session = Depends(get_db)):
    return list_offerings(db, user.id)


@router.post("/offerings", response_model=OfferingRead, status_code=201)
def create(body: OfferingCreate, user: Account = Depends(active_user), db: Session = Depends(get_db)):
    return create_offering(db, user.id, body)
