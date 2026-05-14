from fastapi import APIRouter

from app.api import class_api, course_api, settings_api, task_api

api_router = APIRouter()
api_router.include_router(task_api.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(course_api.router, prefix="/courses", tags=["courses"])
api_router.include_router(class_api.router, prefix="/classes", tags=["classes"])
api_router.include_router(settings_api.router, prefix="/settings", tags=["settings"])
