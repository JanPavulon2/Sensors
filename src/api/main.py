"""
FastAPI Application Factory

EXPLANATION:
This file creates and configures the FastAPI app. Think of it as the "bootstrapper"
that assembles all the pieces:
- Routes (zone, animation, color endpoints)
- Middleware (error handlers, auth, logging)
- Exception handlers
- Dependency injection setup

The app factory pattern allows:
1. Easy testing (create app with test dependencies)
2. Configuration per environment (dev, test, prod)
3. Reusability (same factory in main_asyncio.py and tests)

FastAPI automatically:
- Creates OpenAPI (Swagger) docs at /docs
- Creates ReDoc at /redoc
- Validates request/response schemas against OpenAPI
- Generates client SDK documentation
"""
import sys
if hasattr(sys.stdout, 'reconfigure') and sys.stdout.encoding != 'UTF-8':
    sys.stdout.reconfigure(encoding='utf-8')
    
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional

from api.routes import zones, logger as logger_routes, system
from api.middleware.error_handler import register_exception_handlers
from api.websocket import websocket_logs_endpoint
from utils.logger import get_logger
from models.enums import LogCategory

log = get_logger().for_category(LogCategory.SYSTEM)


def create_app(
    title: str = "Diuna LED System",
    description: str = "REST API for programmable LED control",
    version: str = "1.0.0",
    docs_enabled: bool = True,
    cors_origins: list[str] = None
) -> FastAPI:
    """
    Create and configure FastAPI application.

    This is a factory function that assembles the complete API app.
    Called from main_asyncio.py to create the API server.

    Args:
        title: API title (shown in docs)
        description: API description
        version: API version
        docs_enabled: Enable /docs and /redoc (disable in production if desired)
        cors_origins: CORS allowed origins (default: all)

    Returns:
        Configured FastAPI application ready to run
    """

    # Create FastAPI app
    app = FastAPI(
        title=title,
        description=description,
        version=version,
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None
    )

    log.info(f"Creating FastAPI app: {title} v{version}")

    # =========================================================================
    # CORS Configuration
    # =========================================================================
    # CORS (Cross-Origin Resource Sharing) allows browsers to make requests
    # from different origins (domains). Without this, browser requests from
    # http://localhost:3000 to http://localhost:8000 would be blocked.

    if cors_origins is None:
        # Default: Allow frontend on localhost + typical dev URLs
        cors_origins = [
            "http://localhost:3000",      # React dev server (default)
            "http://localhost:5173",      # Vite dev server (alternative)
            "http://localhost",           # localhost without port
            "http://127.0.0.1:3000",      # 127.0.0.1 variant
            "http://127.0.0.1:5173",
            # Add production domain here later: "https://app.diuna.io"
        ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    log.debug(f"CORS enabled for origins: {cors_origins}")

    # =========================================================================
    # Exception Handlers
    # =========================================================================
    # Register handlers for different error types.
    # These convert exceptions to properly formatted JSON responses.

    register_exception_handlers(app)

    log.debug("Exception handlers registered")

    # =========================================================================
    # Routes
    # =========================================================================
    # Include all endpoint routers.
    # Each router has its own prefix (e.g., /zones) and is composed
    # into the main app under /api/v1.

    app.include_router(
        zones.router,
        prefix="/api/v1"
    )

    app.include_router(
        logger_routes.router,
        prefix="/api/v1"
    )

    app.include_router(
        system.router,
        prefix="/api/v1"
    )

    log.debug("Routes registered: zones (/api/v1/zones), logger (/api/v1/logger), system (/api/v1/system)")

    # =========================================================================
    # Health Check Endpoint
    # =========================================================================

    @app.get(
        "/api/health",
        tags=["System"],
        summary="Health check",
        description="Check if API is running and responding"
    )
    async def health_check():
        """Simple health check endpoint for monitoring"""
        return {
            "status": "healthy",
            "service": "diuna-led-api",
            "version": version
        }

    log.debug("Health check endpoint registered at /api/health")

    # =========================================================================
    # Root Redirect
    # =========================================================================

    @app.get("/", include_in_schema=False)
    async def root():
        """Redirect root to documentation"""
        return JSONResponse(
            {
                "message": "Diuna LED System API",
                "docs": "/docs",
                "health": "/api/health"
            }
        )

    # =========================================================================
    # WebSocket Endpoints
    # =========================================================================

    @app.websocket("/ws/logs")
    async def websocket_logs(websocket):
        """WebSocket endpoint for real-time log streaming"""
        try:
            log.debug("WebSocket connection attempt on /ws/logs")
            await websocket_logs_endpoint(websocket)
        except Exception as e:
            log.error(f"WebSocket handler error: {type(e).__name__}: {e}", exc_info=True)
            try:
                await websocket.close(code=1011, reason="Internal server error")
            except Exception:
                pass

    log.debug("WebSocket endpoint registered at /ws/logs")

    # =========================================================================
    # Startup/Shutdown Hooks
    # =========================================================================

    @app.on_event("startup")
    async def startup_event():
        """Called when FastAPI server starts"""
        log.info("FastAPI app starting up")
        # Note: LogBroadcaster is initialized in main_asyncio.py's run_api_server()
        # This startup hook is kept for documentation and future enhancements

    @app.on_event("shutdown")
    async def shutdown_event():
        """Called when FastAPI server shuts down"""
        log.info("FastAPI app shutting down")
        # Note: LogBroadcaster cleanup is handled by main_asyncio.py
        # This shutdown hook is kept for documentation and future enhancements

    log.info(f"FastAPI app created successfully: {title}")

    return app


# ============================================================================
# NOTE: This module is imported by main_asyncio.py
# ============================================================================
#
# Entry point is: python -m src.main_asyncio
#
# This module provides the create_app() factory function used to bootstrap
# the FastAPI application. It's kept separate for clean separation of concerns:
# - api/main.py: FastAPI app configuration
# - main_asyncio.py: Async runtime + API server integration
