"""
Animation schemas - Pydantic models for animation-related requests/responses
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class AnimationResponse(BaseModel):
    """Complete animation definition"""
    id: str = Field(description="Animation ID (e.g., 'BREATHE')")
    display_name: str = Field(description="Display name (e.g., 'Breathe')")
    description: str = Field(description="Animation description")
    parameters: List[str] = Field(description="List of supported parameter IDs")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "BREATHE",
                "display_name": "Breathe",
                "description": "Smooth breathing effect",
                "parameters": ["ANIM_INTENSITY"]
            }
        }


class AnimationListResponse(BaseModel):
    """List of all animations"""
    animations: List[AnimationResponse]
    count: int = Field(description="Total number of animations")


class AnimationStartRequest(BaseModel):
    """Request to start animation on a zone"""
    animation_id: str = Field(
        description="Animation ID (e.g., 'BREATHE', 'SNAKE', 'COLOR_CYCLE')"
    )
    parameters: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional animation parameters (e.g., {'ANIM_INTENSITY': 50})"
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "animation_id": "BREATHE",
                    "description": "Start breathe animation with default parameters"
                },
                {
                    "animation_id": "BREATHE",
                    "parameters": {
                        "ANIM_INTENSITY": 75
                    },
                    "description": "Start breathe animation with custom intensity"
                }
            ]
        }


class AnimationStopRequest(BaseModel):
    """Request to stop animation on a zone"""
    # No fields needed - just indicates intent to stop
    class Config:
        json_schema_extra = {
            "example": {}
        }


class AnimationParameterUpdateRequest(BaseModel):
    """Request to update animation parameters while running"""
    parameters: Dict[str, Any] = Field(
        description="Animation parameters to update (e.g., {'ANIM_INTENSITY': 50})"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "parameters": {
                    "ANIM_INTENSITY": 75,
                    "ANIM_LENGTH": 5
                }
            }
        }
