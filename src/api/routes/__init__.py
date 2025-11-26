"""
API Routes - HTTP endpoint handlers

Routes receive HTTP requests, validate them, call services,
and return HTTP responses.

Structure: Each domain area (zones, animations, colors) gets its own router.
Then they're all included in the main FastAPI app.
"""
