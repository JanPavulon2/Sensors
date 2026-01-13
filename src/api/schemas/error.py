"""
Error schemas - Pydantic models for error responses

NOTE: Pydantic is a data validation library that converts raw JSON/dict data
into strongly-typed Python objects. It also auto-generates OpenAPI docs.

BaseModel is the parent class - subclass it and add typed fields. Pydantic
will automatically validate incoming data against these types.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class ErrorDetail(BaseModel):
    """Detailed error information"""
    code: str = Field(description="Machine-readable error code")
    message: str = Field(description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional context (field names, valid values, etc.)"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the error occurred"
    )


class ErrorResponse(BaseModel):
    """API error response - standardized format

    All API errors use this structure for consistency.
    Helps frontend handle errors predictably.
    """
    error: ErrorDetail = Field(description="Error information")
    request_id: Optional[str] = Field(None, description="Request ID for logging/debugging")

    class Config:
        json_schema_extra = {
            "example": {
                "error": {
                    "code": "INVALID_ZONE_ID",
                    "message": "Zone 'NONEXISTENT' not found",
                    "details": {
                        "field": "zone_id",
                        "value": "NONEXISTENT",
                        "valid_values": ["FLOOR", "LAMP", "LEFT", "RIGHT"]
                    },
                    "timestamp": "2025-11-26T10:30:00Z"
                },
                "request_id": "req-12345"
            }
        }


class ValidationErrorResponse(BaseModel):
    """Validation error - when request body is invalid"""
    error: ErrorDetail = Field(description="Error information")
    validation_errors: list[Dict[str, Any]] = Field(
        description="Per-field validation errors"
    )
    request_id: Optional[str] = Field(None, description="Request ID for logging/debugging")

    class Config:
        json_schema_extra = {
            "example": {
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": None,
                    "timestamp": "2025-11-26T10:30:00Z"
                },
                "validation_errors": [
                    {
                        "field": "color.rgb",
                        "message": "Value must be [r, g, b] with values 0-255"
                    }
                ],
                "request_id": "req-12345"
            }
        }
