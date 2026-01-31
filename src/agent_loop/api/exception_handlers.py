"""API exception handlers.

Translates domain exceptions to RFC 9457 Problem Details responses.
Uses http.HTTPStatus for semantic status codes per project standards.

Sources:
    - RFC 9457: https://www.rfc-editor.org/rfc/rfc9457
    - FastAPI Exception Handling: https://fastapi.tiangolo.com/tutorial/handling-errors/
"""

from http import HTTPStatus
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from agent_loop.domain.exceptions import (
    AgentLoopError,
    AuthenticationError,
    ExecutionError,
    InvalidInputError,
    ProviderError,
)


class ProblemDetail(BaseModel):
    """RFC 9457 Problem Details response schema."""

    type: str = "about:blank"
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None


class ValidationProblemDetail(ProblemDetail):
    """RFC 9457 with validation errors extension."""

    errors: list[dict[str, Any]] | None = None


def _create_problem_response(
    status: HTTPStatus,
    title: str,
    detail: str | None = None,
    instance: str | None = None,
) -> JSONResponse:
    """Create RFC 9457 compliant error response."""
    problem = ProblemDetail(
        type=f"https://httpstatuses.io/{status.value}",
        title=title,
        status=status.value,
        detail=detail,
        instance=instance,
    )
    return JSONResponse(
        status_code=status.value,
        content=problem.model_dump(exclude_none=True),
        media_type="application/problem+json",
    )


def _sanitize_error_value(value: Any) -> Any:
    """Convert non-JSON-serializable values to strings."""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, dict):
        return {k: _sanitize_error_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_error_value(item) for item in value]
    return value


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle Pydantic validation errors → 422.

    FastAPI guarantees exc is RequestValidationError via add_exception_handler.
    """
    validation_exc = cast(RequestValidationError, exc)
    sanitized_errors = [_sanitize_error_value(e) for e in validation_exc.errors()]
    problem = ValidationProblemDetail(
        type="https://httpstatuses.io/422",
        title="Validation Error",
        status=HTTPStatus.UNPROCESSABLE_ENTITY.value,
        detail="Request validation failed",
        instance=str(request.url.path),
        errors=sanitized_errors,
    )
    return JSONResponse(
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY.value,
        content=problem.model_dump(exclude_none=True),
        media_type="application/problem+json",
    )


async def domain_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all domain exceptions with appropriate HTTP status.

    FastAPI guarantees exc is AgentLoopError (or subtype) via add_exception_handler.
    Status codes are determined by exception type registration order.
    """
    domain_exc = cast(AgentLoopError, exc)
    return _create_problem_response(
        status=_get_status_for_exception(domain_exc),
        title=type(domain_exc).__name__.replace("Error", " Error"),
        detail=domain_exc.message,
        instance=str(request.url.path),
    )


def _get_status_for_exception(exc: AgentLoopError) -> HTTPStatus:
    """Map exception type to HTTP status using class identity."""
    status_map: dict[type[AgentLoopError], HTTPStatus] = {
        InvalidInputError: HTTPStatus.BAD_REQUEST,
        AuthenticationError: HTTPStatus.UNAUTHORIZED,
        ProviderError: HTTPStatus.BAD_GATEWAY,
        ExecutionError: HTTPStatus.INTERNAL_SERVER_ERROR,
    }
    return status_map.get(type(exc), HTTPStatus.INTERNAL_SERVER_ERROR)


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle any unhandled exception → 500 with RFC 9457 format.

    Catches exceptions not handled by domain handlers (e.g., OpenAI errors).
    """
    return _create_problem_response(
        status=HTTPStatus.INTERNAL_SERVER_ERROR,
        title="Internal Server Error",
        detail=str(exc),
        instance=str(request.url.path),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the FastAPI app."""
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    # Register specific types first (FastAPI matches most specific)
    app.add_exception_handler(InvalidInputError, domain_error_handler)
    app.add_exception_handler(AuthenticationError, domain_error_handler)
    app.add_exception_handler(ProviderError, domain_error_handler)
    app.add_exception_handler(ExecutionError, domain_error_handler)
    # Base class catches any other AgentLoopError subtypes
    app.add_exception_handler(AgentLoopError, domain_error_handler)
    # Catch-all for unhandled exceptions (e.g., OpenAI, network errors)
    app.add_exception_handler(Exception, unhandled_error_handler)
