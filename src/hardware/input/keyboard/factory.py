import asyncio
from services.event_bus import EventBus
from utils.logger import get_logger, LogCategory
from runtime.runtime_info import RuntimeInfo
from .adapters.base import IKeyboardAdapter

log = get_logger().for_category(LogCategory.HARDWARE)

async def start_keyboard(event_bus: EventBus) -> None:
    """
    Start the first working keyboard adapter.

    Priority:
    1. Evdev (Linux physical keyboard)
    2. STDIN (SSH / terminal)
    3. Dummy (fallback)
    """

    adapters: list[IKeyboardAdapter] = []

    try:
        from .adapters.evdev import EvdevKeyboardAdapter
        adapters.append(EvdevKeyboardAdapter(event_bus))
    except Exception as e:
        log.info(
            "Evdev adapter not available",
            reason=str(e)
        )

    try:
        from .adapters.stdin import StdinKeyboardAdapter
        adapters.append(StdinKeyboardAdapter(event_bus))
    except Exception as e:
        log.info(
            "STDIN adapter not available",
            reason=str(e)
        )

    from .adapters.dummy import DummyKeyboardAdapter
    adapters.append(DummyKeyboardAdapter(event_bus))

    for adapter in adapters:
        try:
            log.info(
                "Starting keyboard adapter",
                adapter=adapter.__class__.__name__
            )
            await adapter.run()
            return

        except asyncio.CancelledError:
            raise

        except Exception as e:
            log.warn(
                "Keyboard adapter failed, falling back",
                adapter=adapter.__class__.__name__,
                reason=str(e)
            )

    log.error("No keyboard adapter could be started")
    raise RuntimeError("Keyboard input unavailable")    