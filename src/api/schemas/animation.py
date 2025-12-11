"""
Animation schemas - Pydantic models for animation-related requests/responses
"""

from pydantic import BaseModel, Field
from typing import List


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
