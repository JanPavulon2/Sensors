from datetime import datetime
from typing import Optional
from models.enums import LogLevel, LogCategory


# === ANSI COLORS ===
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'


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
    """Structured logger with compact, colored terminal output."""

    def __init__(self, min_level: LogLevel = LogLevel.INFO, use_colors: bool = True):
        self.min_level = min_level
        self.use_colors = use_colors
        self._level_priority = {
            LogLevel.DEBUG: 0,
            LogLevel.INFO: 1,
            LogLevel.WARN: 2,
            LogLevel.ERROR: 3,
        }

    def _should_log(self, level: LogLevel) -> bool:
        return self._level_priority[level] >= self._level_priority[self.min_level]

    def _color(self, text: str, color: str) -> str:
        return f"{color}{text}{Colors.RESET}" if self.use_colors else text

    def _fmt_time(self) -> str:
        return datetime.now().strftime('[%H:%M:%S]')

    def _fmt_category(self, category: LogCategory) -> str:
        color = CATEGORY_COLORS.get(category, Colors.WHITE)
        return self._color(category.name.ljust(9), color)

    def _fmt_level_symbol(self, level: LogLevel) -> str:
        symbol = LEVEL_SYMBOLS.get(level, '·')
        return self._color(symbol, LEVEL_COLORS.get(level, Colors.WHITE))

    def log(
        self,
        category: LogCategory,
        message: str,
        level: LogLevel = LogLevel.INFO,
        details: Optional[list] = None,
        **kwargs
    ):
        """Main logging entry point."""
        if not self._should_log(level):
            return

        timestamp = self._fmt_time()
        cat = self._fmt_category(category)
        sym = self._fmt_level_symbol(level)
        msg = self._color(message, LEVEL_COLORS.get(level, Colors.WHITE))
        print(f"{timestamp} {cat} {sym} {msg}")

        all_details = list(details or [])
        for k, v in kwargs.items():
            all_details.append(f"{k}: {v}")

        if all_details:
            indent = " " * 11
            for i, d in enumerate(all_details):
                tree = "└─" if i == len(all_details) - 1 else "├─"
                print(f"{indent}{self._color(tree, Colors.DIM)} {d}")

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

    def log(self, message: str, level: LogLevel = LogLevel.INFO, category: Optional[LogCategory] = None, **kw):
        """Allows overriding category if necessary."""
        self._base.log(category or self._category, message, level, **kw)

    # Shortcut methods
    def debug(self, message: str, **kw): self.log(message, LogLevel.DEBUG, **kw)
    def info(self, message: str, **kw): self.log(message, LogLevel.INFO, **kw)
    def warn(self, message: str, **kw): self.log(message, LogLevel.WARN, **kw)
    def error(self, message: str, **kw): self.log(message, LogLevel.ERROR, **kw)

    def with_category(self, category: LogCategory) -> 'BoundLogger':
        """Create another bound logger from this one."""
        return BoundLogger(self._base, category)


# === Global instance helpers ===
_logger = Logger()

def get_logger() -> Logger:
    return _logger

def configure_logger(min_level: LogLevel = LogLevel.INFO, use_colors: bool = True):
    global _logger
    _logger = Logger(min_level=min_level, use_colors=use_colors)