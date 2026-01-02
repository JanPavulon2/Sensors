from datetime import datetime
from typing import Optional, TYPE_CHECKING
import traceback
import sys
from models.enums import LogLevel, LogCategory

if TYPE_CHECKING:
    from services.log_broadcaster import LogBroadcaster

# === ANSI COLORS ===
class Colors:
    """ANSI escape codes for colored terminal output"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Foreground colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bright foreground colors
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'

    # Extended 256-color palette (for unique category colors)
    ORANGE = '\033[38;5;208m'           # Orange
    LIGHT_PURPLE = '\033[38;5;141m'     # Light purple
    LIGHT_GRAY = '\033[38;5;245m'       # Light gray
    DARK_CYAN = '\033[38;5;30m'         # Dark cyan
    PINK = '\033[38;5;219m'             # Pink


CATEGORY_COLORS = {
    LogCategory.CONFIG: Colors.CYAN,
    LogCategory.HARDWARE: Colors.BRIGHT_BLUE,
    LogCategory.STATE: Colors.BRIGHT_CYAN,
    LogCategory.COLOR: Colors.BRIGHT_MAGENTA,
    LogCategory.ANIMATION: Colors.BRIGHT_YELLOW,
    LogCategory.ZONE: Colors.BRIGHT_GREEN,
    LogCategory.SYSTEM: Colors.BRIGHT_WHITE,
    LogCategory.TRANSITION: Colors.MAGENTA,
    LogCategory.EVENT: Colors.BRIGHT_MAGENTA,
    LogCategory.RENDER_ENGINE: Colors.MAGENTA,
    LogCategory.SHUTDOWN: Colors.DARK_CYAN,       # Shutdown operations (normal lifecycle event)
    LogCategory.LIFECYCLE: Colors.ORANGE,         # Important lifecycle events
    LogCategory.TASK: Colors.LIGHT_PURPLE,        # Task tracking and management
    LogCategory.API: Colors.PINK,                 # API operations
    LogCategory.WEBSOCKET: Colors.LIGHT_GRAY,     # WebSocket connections
    LogCategory.GENERAL: Colors.WHITE,            # Fallback for general category
}

LEVEL_SYMBOLS = {
    LogLevel.DEBUG: '·',
    LogLevel.INFO: '✓',
    LogLevel.WARN: '⚠',
    LogLevel.ERROR: '✗',
}

LEVEL_COLORS = {
    LogLevel.DEBUG: Colors.DIM,
    LogLevel.INFO: Colors.GREEN,
    LogLevel.WARN: Colors.YELLOW,
    LogLevel.ERROR: Colors.RED,
}


# === CORE LOGGER ===
class Logger:
    """
    Structured logger with compact output format

    Format:
    [HH:MM:SS] CATEGORY · Message
               └─ Detail 1
               └─ Detail 2

    Example:
    [14:23:45] COLOR ✓ Adjusted hue
               └─ Zone: lamp, HUE: 120° → 150° (green)
    """

    def __init__(self, min_level: LogLevel = LogLevel.INFO, use_colors: bool = True):
        """
        Initialize logger

        Args:
            min_level: Minimum log level to display
            use_colors: Enable ANSI color codes (disable for file output)
        """
        self.min_level = min_level
        self.use_colors = use_colors
        self._level_priority = {
            LogLevel.DEBUG: 0,
            LogLevel.INFO: 1,
            LogLevel.WARN: 2,
            LogLevel.ERROR: 3,
        }
        self._broadcaster: Optional['LogBroadcaster'] = None

    def _should_log(self, level: LogLevel) -> bool:
        """Check if message should be logged based on level"""
        return self._level_priority[level] >= self._level_priority[self.min_level]

    def _colorize(self, text: str, color: str) -> str:
        """Apply color to text if colors enabled"""
        if not self.use_colors:
            return text
        return f"{color}{text}{Colors.RESET}"

    def _format_timestamp(self) -> str:
        """Format current time as [HH:MM:SS]"""
        return datetime.now().strftime('[%H:%M:%S]')

    def _format_category(self, category: LogCategory) -> str:
        """Format category name with color"""
        color = CATEGORY_COLORS.get(category, Colors.WHITE)
        return self._colorize(category.name.ljust(9), color)

    def _format_level_symbol(self, level: LogLevel) -> str:
        """Format level symbol with color"""
        symbol = LEVEL_SYMBOLS.get(level, '·')
        return self._colorize(symbol, LEVEL_COLORS.get(level, Colors.WHITE))

    def set_broadcaster(self, broadcaster: 'LogBroadcaster') -> None:
        """
        Set the log broadcaster for WebSocket streaming.

        Args:
            broadcaster: LogBroadcaster instance for streaming logs
        """
        self._broadcaster = broadcaster

    def _format_traceback(self) -> str:
        """
        Format the current exception traceback for logging.

        Returns:
            Formatted traceback string with visual separation
        """
        exc_type, exc_value, exc_tb = sys.exc_info()
        if exc_type is None:
            return ""

        # Get full traceback as list of strings
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_tb)
        tb_text = ''.join(tb_lines).rstrip()

        # Add visual separation and indentation
        indent = " " * 11
        separator = self._colorize("┈" * 60, Colors.DIM)

        formatted_lines = [
            f"{indent}{separator}",
            f"{indent}{self._colorize('TRACEBACK:', Colors.RED)}"
        ]

        # Add each line of traceback with indentation
        for line in tb_text.split('\n'):
            formatted_lines.append(f"{indent}{line}")

        formatted_lines.append(f"{indent}{separator}")

        return '\n'.join(formatted_lines)

    def log(
        self,
        category: LogCategory,
        message: str,
        level: LogLevel = LogLevel.INFO,
        details: Optional[list] = None,
        exc_info: bool = False,
        **kwargs
    ):
        """
        Log a structured message

        Args:
            category: Log category (HARDWARE, STATE, etc.)
            message: Main message text
            level: Log level (DEBUG, INFO, WARN, ERROR)
            details: List of detail strings to show below message
            exc_info: If True, print full exception traceback (requires active exception)
            **kwargs: Additional key-value pairs to show as details

        Example:
            logger.log(
                LogCategory.COLOR,
                "Adjusted hue",
                zone="lamp",
                hue_from=120,
                hue_to=150
            )

            Output:
            [14:23:45] COLOR ✓ Adjusted hue
                       └─ zone: lamp
                       └─ hue: 120° → 150°

            With exc_info=True:
            [14:23:45] ERROR ✗ Handler failed
                       └─ handler: on_rotate
                       ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
                       TRACEBACK:
                       Traceback (most recent call last):
                         File "...", line X, in ...
                       Exception: error message
                       ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
        """
        if not self._should_log(level):
            return

        # Build main line
        timestamp = self._format_timestamp()
        timestamp_str = timestamp[1:-1]  # Remove brackets for ISO format
        cat = self._format_category(category)
        sym = self._format_level_symbol(level)
        msg = self._colorize(message, LEVEL_COLORS.get(level, Colors.WHITE))

        # Print main line
        try:
            print(f"{timestamp} {cat} {sym} {msg}")
        except UnicodeEncodeError:
            safe_sym = sym.encode("ascii", "replace").decode()
            safe_msg = msg.encode("ascii", "replace").decode()
            print(f"{timestamp} {cat} {safe_sym} {safe_msg}")

        # Add kwargs as details
        all_details = list(details or [])
        for k, v in kwargs.items():
            all_details.append(f"{k}: {v}")

        # Print details with tree structure
        if all_details:
            indent = " " * 11
            for i, d in enumerate(all_details):
                # Last item gets different tree character (unless traceback follows)
                is_last = i == len(all_details) - 1 and not exc_info
                tree = "└─" if is_last else "├─"
                try:
                    print(f"{indent}{self._colorize(tree, Colors.DIM)} {d}")
                except UnicodeEncodeError:
                    safe_tree = tree.encode("ascii", "replace").decode()
                    print(f"{indent}{self._colorize(safe_tree, Colors.DIM)} {d}")

        # Print exception traceback if requested
        if exc_info:
            traceback_str = self._format_traceback()
            if traceback_str:
                print(traceback_str)

        # Broadcast to WebSocket clients if broadcaster is set
        if self._broadcaster:
            # Use ISO 8601 format for WebSocket, include details in message
            full_message = message
            if all_details:
                full_message = f"{message} ({', '.join(all_details)})"

            self._broadcaster.log(
                timestamp=datetime.now().isoformat(),
                level=level.name,
                category=category.name,
                message=full_message
            )

    # === Level helpers (backward-compatible) ===
    def debug(self, category: LogCategory, message: str, **kw): self.log(category, message, LogLevel.DEBUG, **kw)
    def info(self, category: LogCategory, message: str, **kw): self.log(category, message, LogLevel.INFO, **kw)
    def warn(self, category: LogCategory, message: str, **kw): self.log(category, message, LogLevel.WARN, **kw)
    def error(self, category: LogCategory, message: str, **kw): self.log(category, message, LogLevel.ERROR, **kw)

    # === Contextual logger creation ===
    def for_category(self, category: LogCategory) -> 'BoundLogger':
        """Return a contextual logger bound to a specific category."""
        return BoundLogger(self, category)


class BoundLogger:
    """Logger bound to a default category, with ability to override if needed."""

    def __init__(self, base: Logger, category: LogCategory):
        self._base = base
        self._category = category

    def log(
        self,
        message: str,
        level: LogLevel = LogLevel.INFO,
        category: Optional[LogCategory] = None,
        details: Optional[list] = None,
        exc_info: bool = False,
        **kw
    ):
        """
        Log a message with optional exception traceback.

        Args:
            message: Main message text
            level: Log level (DEBUG, INFO, WARN, ERROR)
            category: Override default category if needed
            details: List of detail strings
            exc_info: If True, print full exception traceback
            **kw: Additional key-value pairs as details
        """
        self._base.log(category or self._category, message, level, details, exc_info, **kw)

    # Shortcut methods
    def debug(self, message: str, **kw): self.log(message, LogLevel.DEBUG, **kw)
    def info(self, message: str, **kw): self.log(message, LogLevel.INFO, **kw)
    def warn(self, message: str, **kw): self.log(message, LogLevel.WARN, **kw)
    def error(self, message: str, exc_info: bool = False, **kw):
        """
        Log an error message with optional exception traceback.

        Args:
            message: Error message
            exc_info: If True, print full exception traceback (default: False)
            **kw: Additional key-value pairs as details
        """
        self.log(message, LogLevel.ERROR, exc_info=exc_info, **kw)

    def with_category(self, category: LogCategory) -> 'BoundLogger':
        """Create another bound logger from this one."""
        return BoundLogger(self._base, category)


# === Global instance helpers ===
_logger = Logger()

def get_logger() -> Logger:
    return _logger

def get_category_logger(category: LogCategory) -> BoundLogger:
    """Compatibility function: returns a logger bound to a specific category"""
    return _logger.for_category(category)

def configure_logger(min_level: LogLevel = LogLevel.INFO, use_colors: bool = True):
    """
    Configure the logger singleton (modify in-place, don't create new instance).

    This respects the singleton pattern - updates properties on the existing instance
    rather than replacing it. This ensures any broadcasters or references remain valid.
    """
    global _logger
    # Modify existing logger instead of creating new one (preserves singleton + broadcaster)
    _logger.min_level = min_level
    _logger.use_colors = use_colors