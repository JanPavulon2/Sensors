"""
Diuna LED System - API Layer

Provides REST and WebSocket interfaces to the core LED control system.
All API endpoints are facades over the existing Phase 6 architecture.

Structure:
- routes/     : Endpoint handlers
- models/     : Request/response DTOs
- schemas/    : Pydantic schemas
- middleware/ : Auth, error handling, logging
- websocket/  : Real-time communication (future)
"""

from api.main import create_app

__all__ = ["create_app"]
