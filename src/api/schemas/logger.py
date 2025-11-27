"""
Pydantic schemas for logger API endpoints.

This module defines request/response models for:
- Log level enumeration
- Log category enumeration
- WebSocket log message format
"""

from pydantic import BaseModel, Field
from typing import List


class LogLevelResponse(BaseModel):
    """Response containing available log levels."""
    levels: List[str] = Field(
        ...,
        description="List of available log level names (DEBUG, INFO, WARN, ERROR)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "levels": ["DEBUG", "INFO", "WARN", "ERROR"]
            }
        }


class LogCategoryResponse(BaseModel):
    """Response containing available log categories."""
    categories: List[str] = Field(
        ...,
        description="List of available log category names"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "categories": [
                    "CONFIG", "HARDWARE", "STATE", "COLOR", "ANIMATION",
                    "ZONE", "SYSTEM", "TRANSITION", "EVENT", "RENDER_ENGINE",
                    "GENERAL", "API"
                ]
            }
        }


class LogMessage(BaseModel):
    """WebSocket log message format."""
    timestamp: str = Field(
        ...,
        description="ISO 8601 timestamp of log entry"
    )
    level: str = Field(
        ...,
        description="Log level (DEBUG, INFO, WARN, ERROR)"
    )
    category: str = Field(
        ...,
        description="Log category (e.g., ZONE, COLOR, RENDER_ENGINE)"
    )
    message: str = Field(
        ...,
        description="Log message text"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2025-11-27T14:30:45.123456",
                "level": "INFO",
                "category": "ZONE",
                "message": "Zone FLOOR selected"
            }
        }
