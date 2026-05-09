from fastapi import APIRouter

from app.api import task_api

api_router = APIRouter()
api_router.include_router(task_api.router, prefix="/tasks", tags=["tasks"])
