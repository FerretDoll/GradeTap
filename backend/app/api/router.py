from fastapi import APIRouter, Depends

from app.api import auth_api, class_api, course_api, offering_api, settings_api, task_api
from app.services.access import admin, csrf_guard, workspace_access

api_router = APIRouter(dependencies=[Depends(csrf_guard)])
api_router.include_router(auth_api.router, tags=["accounts"])
api_router.include_router(offering_api.router, tags=["offerings"])
for prefix, router in [("tasks", task_api.router), ("courses", course_api.router), ("classes", class_api.router)]:
    api_router.include_router(router, prefix=f"/{prefix}", tags=[prefix], dependencies=[Depends(workspace_access)])
api_router.include_router(settings_api.router, prefix="/settings", tags=["settings"], dependencies=[Depends(admin)])
