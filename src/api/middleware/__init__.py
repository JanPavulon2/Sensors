"""
API Middleware - Request/response processing

Middleware in FastAPI runs before and after each request.
Think of it like a filter that every request passes through.

Order matters: Middleware registered first runs first for requests,
but runs last for responses (like a stack).
"""
