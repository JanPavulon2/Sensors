"""
Authentication middleware for API

EXPLANATION:
In FastAPI, dependencies are a powerful feature for request handling.
They can:
1. Validate headers (like Authorization)
2. Extract data from requests
3. Check permissions
4. Share data across endpoints

This module creates a reusable dependency that validates API tokens.
Endpoints can use: current_user = Depends(get_current_user) to require auth.

JWT (JSON Web Tokens) is a standard way to represent user identity.
Format: "Bearer <token>" in Authorization header
Token contains: user_id, scopes, expiration, all signed with a secret

For now we use simple bearer tokens. Future: upgrade to JWT verification.
"""

from fastapi import Header, HTTPException, status, Depends
from typing import Optional, List
import uuid

# TODO: In Phase 8.2, add JWT verification
# from datetime import datetime, timedelta
# import jwt


class User:
    """Represents an authenticated user"""
    def __init__(
        self,
        user_id: str,
        scopes: Optional[List[str]] = None
    ):
        self.user_id = user_id
        self.scopes = scopes or ["default"]

    def has_scope(self, scope: str) -> bool:
        """Check if user has required scope"""
        return scope in self.scopes or "admin" in self.scopes


async def get_current_user(
    authorization: Optional[str] = Header(None)
) -> User:
    """
    FastAPI dependency that validates authentication.

    Extract user from Authorization header.
    Called automatically by endpoints that use: Depends(get_current_user)

    Args:
        authorization: "Bearer <token>" from request header

    Returns:
        User object if valid, raises exception if not

    Raises:
        HTTPException: 401 if missing/invalid token, 403 if insufficient permissions
    """

    # Check if Authorization header exists
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Parse "Bearer <token>" format
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]

    # TODO: Verify JWT token signature
    # try:
    #     payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    #     user_id = payload.get("sub")
    #     scopes = payload.get("scopes", [])
    # except jwt.ExpiredSignatureError:
    #     raise HTTPException(status_code=401, detail="Token expired")
    # except jwt.InvalidTokenError:
    #     raise HTTPException(status_code=401, detail="Invalid token")

    # For now: accept any bearer token and extract user_id (development only!)
    # In production, validate the JWT signature above
    user_id = token.split("-")[0] if "-" in token else token

    return User(user_id=user_id, scopes=["zones:read", "zones:write", "animations:read"])


def require_scope(required_scope: str):
    """
    FastAPI dependency factory for scope checking.

    Usage:
        @app.get("/admin-endpoint")
        async def admin_only(user: User = Depends(require_scope("admin"))):
            ...

    Args:
        required_scope: Scope name like "zones:write", "admin"

    Returns:
        Dependency function
    """
    async def check_scope(user: User = Depends(get_current_user)) -> User:
        if not user.has_scope(required_scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required scope: {required_scope}"
            )
        return user

    return check_scope


def create_test_token(user_id: str = "test-user", scopes: Optional[List[str]] = None) -> str:
    """
    Create a test token for development/testing.

    For production: Use JWT signing instead.

    Args:
        user_id: User identifier
        scopes: List of permission scopes

    Returns:
        Bearer token string
    """
    # For development: simple bearer token
    # Format: "user-id-<random>" for easy identification
    test_token = f"{user_id}-{uuid.uuid4().hex[:8]}"
    return test_token
