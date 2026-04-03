"""
Context Management Module
Handles process-level global state, such as test identifiers, to ensure 
thread-safe access across different execution contexts.
"""
import multiprocessing
from typing import Optional

# Inter-process/thread lock for safe state modification
_lock = multiprocessing.Lock()

# Primary key ID of the Test table in the SQLite database for the current process.
# Used to pass the test_id to the log_metrics function automatically.
_test_id = None

# The execution sequence number of the test within the experiment.
# Used for identified console printing in log_metrics.
_console_test_id = None


def set_test_id(test_id: int) -> None:
    """Sets the current process-level test ID."""
    with _lock:
        global _test_id
        _test_id = test_id


def get_test_id() -> Optional[int]:
    """Retrieves the current test ID."""
    with _lock:
        if _test_id:
            return _test_id


def clear_test_id() -> None:
    """Resets the current test ID to None."""
    with _lock:
        global _test_id
        _test_id = None


def set_console_test_id(console_test_id: int) -> None:
    """Sets the display/console ID for the current test."""
    with _lock:
        global _console_test_id
        _console_test_id = console_test_id


def get_console_test_id() -> Optional[int]:
    """Retrieves the display/console ID."""
    with _lock:
        if _console_test_id:
            return _console_test_id


def clear_console_test_id() -> None:
    """Resets the display/console ID to None."""
    with _lock:
        global _console_test_id
        _console_test_id = None