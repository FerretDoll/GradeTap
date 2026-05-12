from __future__ import annotations

from fastapi import APIRouter, File, Response, UploadFile, status

from app.schemas.class_group import (
    ClassGroupCreate,
    ClassGroupRead,
    ClassGroupUpdate,
    ClassStudentCreate,
    ClassStudentRead,
    ClassStudentUpdate,
    StudentImportResult,
)
from app.services.class_group_service import class_group_service

router = APIRouter()


@router.post("", response_model=ClassGroupRead, status_code=status.HTTP_201_CREATED)
def create_class_group(payload: ClassGroupCreate) -> ClassGroupRead:
    return class_group_service.create_class_group(payload)


@router.get("", response_model=list[ClassGroupRead])
def list_class_groups() -> list[ClassGroupRead]:
    return class_group_service.list_class_groups()


@router.get("/{class_group_id}/students", response_model=list[ClassStudentRead])
def list_students(class_group_id: int) -> list[ClassStudentRead]:
    return class_group_service.list_students(class_group_id)


@router.post("/{class_group_id}/students", response_model=ClassStudentRead, status_code=status.HTTP_201_CREATED)
def create_student(class_group_id: int, payload: ClassStudentCreate) -> ClassStudentRead:
    return class_group_service.create_student(class_group_id, payload)


@router.post("/{class_group_id}/students/import", response_model=StudentImportResult)
async def import_students(class_group_id: int, file: UploadFile = File(...)) -> StudentImportResult:
    return await class_group_service.import_students_from_excel(class_group_id, file)


@router.put("/{class_group_id}/students/{student_id}", response_model=ClassStudentRead)
def update_student(
    class_group_id: int,
    student_id: int,
    payload: ClassStudentUpdate,
) -> ClassStudentRead:
    return class_group_service.update_student(class_group_id, student_id, payload)


@router.delete("/{class_group_id}/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(class_group_id: int, student_id: int) -> Response:
    class_group_service.delete_student(class_group_id, student_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{class_group_id}", response_model=ClassGroupRead)
def update_class_group(class_group_id: int, payload: ClassGroupUpdate) -> ClassGroupRead:
    return class_group_service.update_class_group(class_group_id, payload)


@router.delete("/{class_group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_class_group(class_group_id: int) -> Response:
    class_group_service.delete_class_group(class_group_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
