"""
Logging Utility Module
Provides a globally unified logger with ANSI color support for terminal output.
Handles log formatting, level mapping, and prevents duplicate handlers.
"""
import logging
from light_tuner.utils.config import LOG_LEVEL, LOG_FORMAT, DATE_FORMAT, COLOR_CODES

# ANSI escape code to reset color formatting
RESET_CODE = "\033[0m"


# ===================== Custom Colored Formatter =====================
class ColoredFormatter(logging.Formatter):
    """
    Extends logging.Formatter to wrap the entire log line in ANSI color codes 
    based on the severity level.
    """

    def format(self, record):
        # 1. Retrieve the color code corresponding to the log level
        color_code = COLOR_CODES.get(record.levelno, RESET_CODE)

        # 2. Call parent method to generate the standard log string (time, pid, etc.)
        log_message = super().format(record)

        # 3. Wrap the final log string in the color code and reset it at the end
        return f"{color_code}{log_message}{RESET_CODE}"


def setup_logger(name: str = "light_tuner") -> logging.Logger:
    """
    Initializes a globally unique logger instance with colored output.

    Args:
        name: Unique identifier for the logger.

    Returns:
        A configured logging.Logger instance.
    """
    # Retrieve or create a logger instance
    logger = logging.getLogger(name)

    # Map string log levels from config to logging constants
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }

    # Set logging level (defaults to INFO if level is not found)
    logger.setLevel(level_map.get(LOG_LEVEL, logging.INFO))

    # Disable propagation to prevent duplicate logs appearing in parent loggers
    logger.propagate = False

    # Ensure handlers are only added once to prevent duplicate output in multi-module setups
    if not logger.handlers:
        # Create a stream handler for console output
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logger.level)

        # Apply the custom colored formatter using global config formats
        formatter = ColoredFormatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)
        console_handler.setFormatter(formatter)

        # Attach the handler to the logger
        logger.addHandler(console_handler)

    return logger


# Initialize a global logger instance for immediate use across the project
logger = setup_logger()