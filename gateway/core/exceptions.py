"""
Problem-Details error helpers (RFC 7807).

Add handlers to FastAPI via:

    from core.exceptions import add_exception_handlers
    add_exception_handlers(app)
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError


class ProblemDetail(BaseModel):
    type: str  # URI-like code e.g. "auth/invalid-credentials"
    title: str
    detail: str
    status: int
    instance: Optional[str] = None
    extras: Dict[str, Any] = {}


class AppException(Exception):
    """Domain errors raise this. Convert to ProblemDetail automatically."""

    def __init__(self, *, code: str, message: str, status_code: int):
        self.problem = ProblemDetail(
            type=code,
            title=code.split("/")[-1].replace("-", " ").title(),
            detail=message,
            status=status_code,
        )
        super().__init__(message)


def _problem_to_response(pb: ProblemDetail) -> JSONResponse:
    return JSONResponse(status_code=pb.status, content=pb.dict(exclude_none=True))


def add_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def _handle_app_exc(_: Request, exc: AppException):
        return _problem_to_response(exc.problem)

    @app.exception_handler(ValidationError)
    async def _handle_val(_: Request, exc: ValidationError):
        problem = ProblemDetail(
            type="validation/error",
            title="Validation Error",
            detail=str(exc),
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
        return _problem_to_response(problem)

    @app.exception_handler(Exception)
    async def _handle_uncaught(_: Request, exc: Exception):
        problem = ProblemDetail(
            type="internal/error",
            title="Internal Error",
            detail=str(exc),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
        return _problem_to_response(problem)
