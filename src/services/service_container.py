"""Service Container - Dependency injection container for all core services"""

from dataclasses import dataclass
from managers.config_manager import ConfigManager
from services.zone_service import ZoneService
from services.animation_service import AnimationService
from services.application_state_service import ApplicationStateService
from services.event_bus import EventBus
from engine.frame_manager import FrameManager
from managers.color_manager import ColorManager


@dataclass
class ServiceContainer:
    """
    Centralized dependency injection container for all core services and managers.

    This container aggregates all domain services, infrastructure services, and
    application managers needed by controllers and API endpoints. Eliminates the
    need for controllers to know about parent objects or reach into LEDController internals.

    Services included:
    - zone_service: Zone operations and state management
    - animation_service: Animation operations and state management
    - app_state_service: Application-level state and mode management
    - frame_manager: Centralized rendering system with priority queues
    - event_bus: Pub-sub event routing for decoupling components

    Managers included:
    - color_manager: Color preset lookup and management

    Usage:
        # Create container during app startup
        services = ServiceContainer(
            zone_service=zone_service,
            animation_service=animation_service,
            app_state_service=app_state_service,
            frame_manager=frame_manager,
            event_bus=event_bus,
            color_manager=color_manager,
            config_manager=config_manager
        )

        # Pass to controllers
        controller = StaticModeController(services=services)
        controller2 = PowerToggleController(
            services=services,
            animation_engine=animation_engine,
            static_mode_controller=static_mode_controller
        )

        # API endpoints can use services directly
        @app.get("/api/zones")
        async def get_zones(services: ServiceContainer):
            return services.zone_service.get_all()
    """

    zone_service: ZoneService
    animation_service: AnimationService
    app_state_service: ApplicationStateService
    frame_manager: FrameManager
    event_bus: EventBus
    color_manager: ColorManager
    config_manager: ConfigManager
