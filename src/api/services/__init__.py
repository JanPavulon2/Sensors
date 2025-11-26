"""
API Service Layer

These services bridge between HTTP routes and the domain logic.
They handle:
- Converting requests to domain objects
- Calling domain logic (controllers, managers)
- Converting domain objects back to API responses
- Error handling

Think of it as a "facade pattern" - simplifies what the routes need to do.
"""
