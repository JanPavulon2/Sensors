from typing import Protocol
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.EVENT)

class IKeyboardAdapter(Protocol):
    """
    Keyboard input abstraction.

    Implementations:
    - publish KeyboardKeyPressEvent to EventBus
    - block until cancelled
    """

    async def run(self) -> None:
        ...