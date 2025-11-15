"""
Structured logging system for LED Control Station

Provides compact, readable logging with color coding and consistent formatting.
Max 3-4 lines per action for readability on terminal.
"""

from enum import Enum, auto
from typing import Optional, Any
from datetime import datetime
from functools import partial
from models.enums import LogLevel, LogCategory


# ANSI color codes for terminal output
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


# Category colors (for visual grouping)
CATEGORY_COLORS = {
    LogCategory.CONFIG: Colors.CYAN,
    LogCategory.HARDWARE: Colors.BRIGHT_BLUE,
    LogCategory.STATE: Colors.BRIGHT_CYAN,
    LogCategory.COLOR: Colors.BRIGHT_MAGENTA,
    LogCategory.ANIMATION: Colors.BRIGHT_YELLOW,
    LogCategory.ZONE: Colors.BRIGHT_GREEN,
    LogCategory.SYSTEM: Colors.BRIGHT_WHITE,
    LogCategory.TRANSITION: Colors.MAGENTA,
}

# Level symbols
LEVEL_SYMBOLS = {
    LogLevel.DEBUG: '·',
    LogLevel.INFO: '✓',
    LogLevel.WARN: '⚠',
    LogLevel.ERROR: '✗',
}

# Level colors
LEVEL_COLORS = {
    LogLevel.DEBUG: Colors.DIM,
    LogLevel.INFO: Colors.GREEN,
    LogLevel.WARN: Colors.YELLOW,
    LogLevel.ERROR: Colors.RED,
}


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
        self.level_priority = {
            LogLevel.DEBUG: 0,
            LogLevel.INFO: 1,
            LogLevel.WARN: 2,
            LogLevel.ERROR: 3,
        }
        
    def _should_log(self, level: LogLevel) -> bool:
        """Check if message should be logged based on level"""
        return self.level_priority[level] >= self.level_priority[self.min_level]

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
        name = category.name
        color = CATEGORY_COLORS.get(category, Colors.WHITE)
        return self._colorize(name.ljust(9), color)  # Pad to 9 chars for alignment

    def _format_level_symbol(self, level: LogLevel) -> str:
        """Format level symbol with color"""
        symbol = LEVEL_SYMBOLS.get(level, '·')
        color = LEVEL_COLORS.get(level, Colors.WHITE)
        return self._colorize(symbol, color)

    def log(
        self,
        category: LogCategory,
        message: str,
        level: LogLevel = LogLevel.INFO,
        details: Optional[list] = None,
        **kwargs
    ):
        """
        Log a structured message

        Args:
            category: Log category (HARDWARE, STATE, etc.)
            message: Main message text
            level: Log level (DEBUG, INFO, WARN, ERROR)
            details: List of detail strings to show below message
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
        """
        if not self._should_log(level):
            return

        # Build main line
        timestamp = self._format_timestamp()
        category_str = self._format_category(category)
        symbol = self._format_level_symbol(level)

        # Colorize message based on level
        msg_color = LEVEL_COLORS.get(level, Colors.WHITE)
        message_str = self._colorize(message, msg_color)

        # Print main line
        print(f"{timestamp} {category_str} {symbol} {message_str}")

        # Build details from kwargs
        detail_lines = details or []

        # Add kwargs as details
        for key, value in kwargs.items():
            detail_lines.append(f"{key}: {value}")

        # Print details with tree structure
        if detail_lines:
            indent = " " * 11  # Align with category column
            for i, detail in enumerate(detail_lines):
                # Last item gets different tree character
                tree_char = "└─" if i == len(detail_lines) - 1 else "├─"
                detail_color = Colors.DIM if self.use_colors else ""
                print(f"{indent}{self._colorize(tree_char, detail_color)} {detail}")

    # Convenience methods for each category

    def config(self, message: str, level: LogLevel = LogLevel.INFO, **kwargs):
        """Log hardware event (GPIO, encoders, buttons, LEDs)"""
        self.log(LogCategory.CONFIG, message, level, **kwargs)

    def hardware(self, message: str, level: LogLevel = LogLevel.INFO, **kwargs):
        """Log hardware event (GPIO, encoders, buttons, LEDs)"""
        self.log(LogCategory.HARDWARE, message, level, **kwargs)

    def state(self, message: str, level: LogLevel = LogLevel.INFO, **kwargs):
        """Log state change (mode switches, edit mode toggle)"""
        self.log(LogCategory.STATE, message, level, **kwargs)

    def color(self, message: str, level: LogLevel = LogLevel.INFO, **kwargs):
        """Log color event (adjustments, mode changes)"""
        self.log(LogCategory.COLOR, message, level, **kwargs)

    def animation(self, message: str, level: LogLevel = LogLevel.INFO, **kwargs):
        """Log animation event (start/stop, parameter changes)"""
        self.log(LogCategory.ANIMATION, message, level, **kwargs)

    def zone(self, message: str, level: LogLevel = LogLevel.INFO, **kwargs):
        """Log zone event (selection, operations)"""
        self.log(LogCategory.ZONE, message, level, **kwargs)

    def system(self, message: str, level: LogLevel = LogLevel.INFO, **kwargs):
        """Log system event (startup, shutdown, errors)"""
        self.log(LogCategory.SYSTEM, message, level, **kwargs)

    def error(self, category: LogCategory, message: str, exception: Optional[Exception] = None):
        """Log error with optional exception"""
        kwargs = {}
        if exception:
            kwargs["error"] = str(exception)
            kwargs["type"] = type(exception).__name__
        self.log(category, message, LogLevel.ERROR, **kwargs)
    
    def warning(self, category: LogCategory, message: str, **kwargs):
        """Log warning """
        self.log(category, message, LogLevel.WARN, **kwargs)
    
    def warn(self, category: LogCategory, message: str, **kwargs):
        """Log warning """
        self.log(category, message, LogLevel.WARN, **kwargs)

    def info(self, log_category: LogCategory, message: str, **kwargs):
        """Log info """
        self.log(log_category, message, LogLevel.INFO, **kwargs)

    def debug(self, log_category: LogCategory, message: str, **kwargs):
        """Log debug """
        self.log(log_category, message, LogLevel.DEBUG, **kwargs)

# Global logger instance (can be reconfigured)
_logger = Logger()


def get_logger() -> Logger:
    """Get global logger instance"""
    return _logger


# def configure_logger(min_level: LogLevel = LogLevel.INFO, use_colors: bool = True):
#     """
#     Reconfigure global logger

#     Args:
#         min_level: Minimum log level to display
#         use_colors: Enable ANSI color codes
#     """
#     global _logger
#     _logger = Logger(min_level=min_level, use_colors=use_colors)

class CategoryLogger:
    """Logger bound to a specific category with level methods"""
    def __init__(self, category: LogCategory):
        self.category = category
        self._base = get_logger()

    def __call__(self, message: str, level: LogLevel = LogLevel.INFO, **kwargs):
        """Allow using as function: log("msg", level=LogLevel.INFO)"""
        self._base.log(self.category, message, level, **kwargs)

    def log(self, message: str, level: LogLevel = LogLevel.INFO, **kwargs):
        self._base.log(self.category, message, level, **kwargs)

    def info(self, message: str, **kwargs):
        self._base.log(self.category, message, LogLevel.INFO, **kwargs)

    def warn(self, message: str, **kwargs):
        self._base.log(self.category, message, LogLevel.WARN, **kwargs)

    def error(self, message: str, **kwargs):
        self._base.log(self.category, message, LogLevel.ERROR, **kwargs)

    def debug(self, message: str, **kwargs):
        self._base.log(self.category, message, LogLevel.DEBUG, **kwargs)

def get_category_logger(category: LogCategory):
    """Return a CategoryLogger bound to a specific category"""
    return CategoryLogger(category)