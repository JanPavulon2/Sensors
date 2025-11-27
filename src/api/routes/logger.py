"""
Logger API routes for exposing log levels, categories, and WebSocket streaming.

Provides:
- GET /api/v1/logger/levels - List available log levels
- GET /api/v1/logger/categories - List available log categories
- WS /ws/logs - WebSocket endpoint for real-time log streaming
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from models.enums import LogLevel, LogCategory
from api.schemas.logger import LogLevelResponse, LogCategoryResponse
from services.log_broadcaster import get_broadcaster

router = APIRouter(
    prefix="/logger",
    tags=["Logger"],
)


@router.get("/levels", response_model=LogLevelResponse)
async def get_log_levels():
    """
    Get all available log levels.

    Returns:
        List of log level names (DEBUG, INFO, WARN, ERROR)
    """
    levels = [level.name for level in LogLevel]
    return LogLevelResponse(levels=levels)


@router.get("/categories", response_model=LogCategoryResponse)
async def get_log_categories():
    """
    Get all available log categories.

    Returns:
        List of log category names available in the application
    """
    categories = [category.name for category in LogCategory]
    return LogCategoryResponse(categories=categories)


@router.get("/recent")
async def get_recent_logs(limit: int = 100):
    """
    Get recently logged messages (fallback REST endpoint).

    This endpoint provides a REST alternative for retrieving recent logs
    when WebSocket is not available. Currently returns empty list as logs
    are streamed via WebSocket only. Can be enhanced to store log history
    if needed.

    Args:
        limit: Maximum number of recent logs to return (max 1000)

    Returns:
        List of recent log entries
    """
    # Limit to reasonable max
    limit = min(limit, 1000)
    # TODO: Implement log history storage in LogBroadcaster if needed
    return {"logs": []}

