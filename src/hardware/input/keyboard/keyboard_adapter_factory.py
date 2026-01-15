from services.event_bus import EventBus
from utils.logger import get_logger, LogCategory
from runtime.runtime_info import RuntimeInfo
from .keyboard_adapter_interface import IKeyboardAdapter

log = get_logger().for_category(LogCategory.HARDWARE)

def create_keyboard_adapter(event_bus: EventBus) -> IKeyboardAdapter:
    """
    Keyboard adapter factory.

    Priority:
    1. Evdev (Linux physical keyboard)
    2. Stdin (Unix terminal)
    3. Dummy (Windows or fallback - no keyboard)
    """

    # Try evdev first (Linux physical keyboard)
    if RuntimeInfo.has_evdev():
        try:
            from .evdev_keyboard_adapter import EvdevKeyboardAdapter
            adapter = EvdevKeyboardAdapter(event_bus)
            log.info("Using evdev keyboard adapter")
            return adapter
        except Exception as e:
            log.info(
                "Evdev not available, falling back",
                reason=str(e)
            )

    # Try stdin (Unix terminal - requires termios)
    if RuntimeInfo.has_module("termios"):
        try:
            from .stdin_keyboard_adapter import StdinKeyboardAdapter
            log.info("Using stdin keyboard adapter")
            return StdinKeyboardAdapter(event_bus)
        except Exception as e:
            log.info(
                "Stdin keyboard not available, falling back to dummy",
                reason=str(e)
            )

    # Fallback to dummy (Windows or any platform without keyboard support)
    log.info("Using dummy keyboard adapter (no keyboard input)")
    from .dummy_keyboard_adapter import DummyKeyboardAdapter
    return DummyKeyboardAdapter(event_bus)
    