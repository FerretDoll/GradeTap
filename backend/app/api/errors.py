from uuid import uuid4

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.orm.exc import StaleDataError
from starlette.exceptions import HTTPException


def install_errors(app):
    def response(status, detail):
        body = dict(detail, request_id=uuid4().hex)
        return JSONResponse(body, status_code=status, headers={"X-Request-ID": body["request_id"]})

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        detail = exc.detail
        if not isinstance(detail, dict):
            code = {400: "invalid_request", 404: "not_found", 409: "conflict"}.get(exc.status_code, "request_failed")
            detail = {"code": code, "message": str(detail)}
        return response(exc.status_code, detail)

    @app.exception_handler(RequestValidationError)
    async def invalid(request: Request, exc: RequestValidationError):
        return response(422, {"code": "validation_error", "message": "请求字段有误，请检查填写内容"})

    @app.exception_handler(StaleDataError)
    async def stale(request: Request, exc: StaleDataError):
        return response(409, {"code": "version_conflict", "message": "记录已更新，请刷新"})

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception):
        return response(500, {"code": "internal_error", "message": "服务暂时不可用"})
