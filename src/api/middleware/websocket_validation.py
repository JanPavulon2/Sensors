"""
WebSocket Validation Middleware

Validates WebSocket handlers at app startup to catch missing type hints early.
This prevents HTTP 403 errors caused by missing type annotations on WebSocket parameters.

Key insight: FastAPI uses type hints for ASGI parameter injection and routing.
Missing type hints cause ASGI-level rejection (HTTP 403) BEFORE the handler body
executes, so no application-level logging occurs.

This validator catches such issues at startup time, failing fast with clear error messages.
"""

from fastapi import FastAPI
from pathlib import Path
import ast
from typing import List, Tuple


class WebSocketValidationError(Exception):
    """Raised when WebSocket handler validation fails."""
    pass


def validate_app_websockets(app: FastAPI) -> None:
    """
    Validate all WebSocket handlers in a FastAPI app at startup.

    Checks for:
    - Missing type hints on WebSocket parameters
    - Incorrect type hints (must be FastAPI.WebSocket)
    - Missing first parameter named 'websocket'

    Raises:
        WebSocketValidationError: If any WebSocket handler is invalid

    Example:
        app = create_app()
        validate_app_websockets(app)  # Raises if invalid
    """
    errors: List[str] = []

    # Inspect all routes in the app
    for route in app.routes:
        # Check for WebSocket routes
        if hasattr(route, "path") and hasattr(route, "endpoint"):
            # WebSocket routes have a different structure than HTTP routes
            if "websocket" in str(type(route)).lower() or hasattr(route, "receive"):
                endpoint = route.endpoint

                # Get the handler function
                if callable(endpoint):
                    # Check if function has type hints
                    annotations = getattr(endpoint, "__annotations__", {})

                    # First parameter should be named 'websocket'
                    param_names = endpoint.__code__.co_varnames[
                        : endpoint.__code__.co_argcount
                    ]

                    if not param_names:
                        errors.append(
                            f"WebSocket handler '{endpoint.__name__}' has no parameters. "
                            f"Expected: 'websocket: WebSocket'"
                        )
                        continue

                    first_param = param_names[0]
                    if first_param != "websocket":
                        errors.append(
                            f"WebSocket handler '{endpoint.__name__}' first parameter is '{first_param}'. "
                            f"Expected: 'websocket'"
                        )
                        continue

                    # Check for type hint
                    if "websocket" not in annotations:
                        errors.append(
                            f"WebSocket handler '{endpoint.__name__}' is missing type hint on "
                            f"'websocket' parameter. Must be: 'websocket: WebSocket'"
                        )
                        continue

                    # Verify type hint is WebSocket
                    type_hint = annotations.get("websocket")
                    if type_hint and hasattr(type_hint, "__name__"):
                        if type_hint.__name__ != "WebSocket":
                            errors.append(
                                f"WebSocket handler '{endpoint.__name__}' has incorrect type hint: "
                                f"'{type_hint.__name__}'. Must be 'WebSocket'"
                            )

    if errors:
        error_message = "❌ WebSocket Handler Validation Failed:\n\n"
        for i, error in enumerate(errors, 1):
            error_message += f"  {i}. {error}\n"
        error_message += (
            "\nSee: .claude/context/development/WEBSOCKET_DEBUGGING.md for details."
        )
        raise WebSocketValidationError(error_message)
