"""
API Dependencies - Service container access for FastAPI endpoints

This module provides a centralized way for API endpoints to access Phase 6 services
(ZoneService, ColorManager, etc.) without requiring direct coupling to the LED controller.

Pattern:
1. main_asyncio.py creates ServiceContainer during initialization
2. main_asyncio.py calls set_service_container() after creation
3. API endpoints use get_service_container() dependency via Depends()

Example:
    @app.get("/api/v1/zones")
    async def list_zones(services: ServiceContainer = Depends(get_service_container)):
        return services.zone_service.get_all()
"""

from typing import Optional
from fastapi import HTTPException, status
from services.service_container import ServiceContainer


# Global service container (set by main_asyncio.py during initialization)
_service_container: Optional[ServiceContainer] = None


def set_service_container(services: ServiceContainer) -> None:
    """
    Store the service container for API access.

    Called by main_asyncio.py after creating ServiceContainer.

    Args:
        services: The ServiceContainer with all Phase 6 services
    """
    global _service_container
    _service_container = services


async def get_service_container() -> ServiceContainer:
    """
    FastAPI dependency for accessing service container.

    Usage:
        @app.get("/api/v1/zones")
        async def list_zones(services: ServiceContainer = Depends(get_service_container)):
            ...

    Returns:
        ServiceContainer with all Phase 6 services

    Raises:
        HTTPException: 503 Service Unavailable if services not initialized
    """
    if _service_container is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service container not initialized. LED controller may still be starting."
        )
    return _service_container
