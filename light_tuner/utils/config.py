"""
Project Configuration Constants Module
Stores global configuration parameters and logging settings.
"""
import logging

# Whether to print metrics to the console during test execution
CONSOLE_PRINT_METRICS = True

# Default maximum number of concurrent worker processes
DEFAULT_MAX_WORKERS = 1

# Logging Configuration
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s | %(process)d | %(module)s | %(levelname)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ANSI Color Codes for terminal logging output
COLOR_CODES = {
    logging.DEBUG: "\033[0;37m",    # Gray (DEBUG)
    logging.INFO: "\033[0;32m",     # Green (INFO)
    logging.WARNING: "\033[0;33m",  # Yellow (WARNING)
    logging.ERROR: "\033[0;31m",    # Red (ERROR)
    logging.CRITICAL: "\033[1;31m"  # Bright Red (CRITICAL)
}