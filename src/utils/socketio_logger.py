"""
Socket.IO Logging Adapter

Routes Socket.IO and python-engineio logs to Diuna's custom logger.
This bridges the gap between Socket.IO's standard logging and our custom logger.
"""

import logging
from utils.logger import get_logger, LogCategory

# Create a standard Python logger for Socket.IO
socketio_py_logger = logging.getLogger("socketio")
engineio_py_logger = logging.getLogger("engineio")

# Get our custom Diuna loggers
socketio_diuna_logger = get_logger().for_category(LogCategory.SOCKETIO)
engineio_diuna_logger = get_logger().for_category(LogCategory.SOCKETIO)


class SocketIOLogHandler(logging.Handler):
    """
    Custom logging handler that routes Socket.IO logs to Diuna logger.

    Maps Python logging levels to Diuna log methods.
    """

    def __init__(self, diuna_logger):
        super().__init__()
        self.diuna_logger = diuna_logger

    def emit(self, record: logging.LogRecord):
        """
        Emit a log record to the Diuna logger.

        Args:
            record: LogRecord from Socket.IO/engineio
        """
        try:
            # Skip very noisy messages
            msg = record.getMessage()

            # Filter out noise (connection keepalives, ping/pong)
            if any(skip in msg for skip in [
                'websocket.py',
                'ping pong',
                'Sending packet',
                'Received packet',
            ]):
                return

            # Map Python logging levels to Diuna log methods
            if record.levelno >= logging.ERROR:
                self.diuna_logger.error(f"[{record.name}] {msg}")
            elif record.levelno >= logging.WARNING:
                self.diuna_logger.warn(f"[{record.name}] {msg}")
            elif record.levelno >= logging.INFO:
                self.diuna_logger.info(f"[{record.name}] {msg}")
            else:
                self.diuna_logger.debug(f"[{record.name}] {msg}")
        except Exception as e:
            # Never crash the logging system
            try:
                self.diuna_logger.error(f"Error in SocketIOLogHandler: {e}")
            except:
                pass


def setup_socketio_logging():
    """
    Configure Socket.IO and engineio loggers to route to Diuna logger.

    Call this once during app startup.
    """
    # Remove any existing handlers
    socketio_py_logger.handlers.clear()
    engineio_py_logger.handlers.clear()

    # Add our custom handler
    socketio_handler = SocketIOLogHandler(socketio_diuna_logger)
    engineio_handler = SocketIOLogHandler(engineio_diuna_logger)

    socketio_py_logger.addHandler(socketio_handler)
    engineio_py_logger.addHandler(engineio_handler)

    # Set log level to DEBUG to capture all messages
    socketio_py_logger.setLevel(logging.DEBUG)
    engineio_py_logger.setLevel(logging.DEBUG)

    # Prevent propagation to root logger (avoid duplicate logs)
    socketio_py_logger.propagate = False
    engineio_py_logger.propagate = False
