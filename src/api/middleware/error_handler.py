"""
Error handling middleware for API

EXPLANATION OF EXCEPTION HANDLERS:
FastAPI lets us define custom handlers for specific exception types.
When an exception is raised anywhere in the request, FastAPI catches it
and calls the appropriate handler to return a formatted error response.

This file defines handlers for common error scenarios:
- Validation errors (bad request format)
- Generic errors (unexpected problems)
- Custom domain errors (zone not found, etc.)
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from datetime import datetime
import uuid
from typing import Optional

from api.schemas.error import ErrorResponse, ErrorDetail, ValidationErrorResponse
from utils.logger import get_logger
from models.enums import LogCategory
import json

log = get_logger().for_category(LogCategory.API)


class DomainError(Exception):
    """Base class for domain-specific errors"""
    def __init__(
        self,
        code: str,
        message: str,
        details: Optional[dict] = None,
        status_code: int = 400
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        self.status_code = status_code
        super().__init__(message)


class ZoneNotFoundError(DomainError):
    """Zone ID doesn't exist"""
    def __init__(self, zone_id: str):
        super().__init__(
            code="ZONE_NOT_FOUND",
            message=f"Zone '{zone_id}' not found",
            details={"zone_id": zone_id},
            status_code=404
        )


class AnimationNotFoundError(DomainError):
    """Animation ID doesn't exist"""
    def __init__(self, animation_id: str):
        super().__init__(
            code="ANIMATION_NOT_FOUND",
            message=f"Animation '{animation_id}' not found",
            details={"animation_id": animation_id},
            status_code=404
        )


class InvalidColorModeError(DomainError):
    """Color mode is not supported"""
    def __init__(self, mode: str, valid_modes: list):
        super().__init__(
            code="INVALID_COLOR_MODE",
            message=f"Color mode '{mode}' is not supported",
            details={
                "mode": mode,
                "valid_modes": valid_modes
            },
            status_code=422
        )


class HardwareError(DomainError):
    """Hardware unavailable or error"""
    def __init__(self, message: str):
        super().__init__(
            code="HARDWARE_ERROR",
            message=message,
            status_code=503
        )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with FastAPI app"""

    # Handle validation errors (bad request format)
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle Pydantic validation errors (bad JSON structure)"""
        request_id = str(uuid.uuid4())

        log.warn(
            f"Validation error ({request_id}): {exc.errors().count} errors",
            extra={"request_id": request_id}
        )

        # Convert Pydantic errors to readable format
        validation_errors = []
        for error in exc.errors():
            field = ".".join(str(x) for x in error["loc"][1:])  # Skip "body"
            validation_errors.append({
                "field": field,
                "message": error["msg"],
                "type": error["type"]
            })

        response = ValidationErrorResponse(
            error=ErrorDetail(
                code="VALIDATION_ERROR",
                message="Request validation failed",
                details={"error_count": exc.errors().count},
                timestamp=datetime.utcnow()
            ),
            validation_errors=validation_errors,
            request_id=request_id
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=json.loads(response.model_dump_json())
        )

    # Handle domain-specific errors (our custom exceptions)
    @app.exception_handler(DomainError)
    async def domain_exception_handler(request: Request, exc: DomainError):
        """Handle domain-specific business logic errors"""
        request_id = str(uuid.uuid4())

        log.warn(
            f"Domain error ({request_id}): {exc.code} - {exc.message}",
            extra={"request_id": request_id}
        )

        response = ErrorResponse(
            error=ErrorDetail(
                code=exc.code,
                message=exc.message,
                details=exc.details,
                timestamp=datetime.utcnow()
            ),
            request_id=request_id
        )

        return JSONResponse(
            status_code=exc.status_code,
            content=json.loads(response.model_dump_json())
        )

    # Handle unexpected errors (server errors)
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected errors"""
        request_id = str(uuid.uuid4())

        log.error(
            f"Unexpected error ({request_id}): {type(exc).__name__}: {str(exc)}",
            extra={
                "request_id": request_id,
                "exception_type": type(exc).__name__,
                "traceback": True
            }
        )

        response = ErrorResponse(
            error=ErrorDetail(
                code="INTERNAL_SERVER_ERROR",
                message="An unexpected error occurred. Please try again.",
                details={"request_id": request_id},
                timestamp=datetime.utcnow()
            ),
            request_id=request_id
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=json.loads(response.model_dump_json())
        )
