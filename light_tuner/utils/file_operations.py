"""
File Operations Utility Module
Provides common file manipulation functions such as creating temporary Python files,
reading file contents, and secure file deletion.
"""
import os
import tempfile
from typing import Optional, Union
from light_tuner.utils.logger import logger


def create_temp_py_file(content: str) -> Optional[str]:
    """
    Creates a temporary Python file and writes the specified content to it.

    Creates a temporary file with a .py extension. The file is NOT automatically
    deleted by the OS; it must be manually cleaned up using delete_file().
    This is specifically designed for generating executable Python scripts
    on the fly.

    Args:
        content: The string content to be written into the temporary file.

    Returns:
        Optional[str]: The absolute path to the temporary file if successful;
                      None if content is empty or creation fails.

    Raises:
        IOError: If writing to the file fails.
    """
    if not content:
        logger.warning("Failed to create temporary file: Content is empty.")
        return None

    try:
        # Inject multi-processing support at the top of the user script
        # This is critical for compatibility across different Operating Systems.
        freeze_support_code = (
            "import multiprocessing\n"
            "multiprocessing.freeze_support()\n"
        )

        # Merge injected boilerplate with the actual user code
        final_content = freeze_support_code + content

        # Create a persistent temporary file (delete=False)
        with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.py',
                delete=False,
                encoding='utf-8'
        ) as temp_file:
            temp_file.write(final_content)
            temp_file_path = temp_file.name

        return os.path.abspath(temp_file_path)
    except IOError as e:
        logger.error(f"Failed to create temporary file: {str(e)}", exc_info=True)
        return None


def read_file(file_path: str) -> Optional[str]:
    """
    Reads the content of a file using UTF-8 encoding.

    Safely reads a text file with comprehensive error handling to prevent
    crashes due to missing files or permission issues.

    Args:
        file_path: Path to the file (relative or absolute).

    Returns:
        Optional[str]: File content string if successful; None otherwise.

    Raises:
        PermissionError: If the process lacks read permissions.
        UnicodeDecodeError: If the file is not valid UTF-8.
    """
    if not file_path:
        logger.warning("Failed to read file: Path is empty.")
        return None

    normalized_path = os.path.abspath(file_path)

    if not os.path.exists(file_path):
        logger.warning(f"Failed to read file: File does not exist - {normalized_path}")
        return None

    if not os.path.isfile(file_path):
        logger.warning(f"Failed to read file: Path is not a file - {normalized_path}")
        return None

    try:
        with open(file_path, "r", encoding="utf-8") as file_handler:
            file_content = file_handler.read()
        return file_content
    except PermissionError:
        logger.error(f"Failed to read file: Permission denied - {normalized_path}")
        return None
    except UnicodeDecodeError:
        logger.error(f"Failed to read file: Not UTF-8 encoded - {file_path}", exc_info=True)
        return None
    except IOError as e:
        logger.error(f"Failed to read file: IO Error - {file_path} | {str(e)}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Failed to read file: Unexpected error - {normalized_path} | {str(e)}", exc_info=True)
        return None


def delete_file(file_path: Union[str, None]) -> None:
    """
    Safely deletes a file at the specified path.

    Includes pre-validation and exception handling to ensure deletion attempts
    do not crash the program. Supports None values.

    Args:
        file_path: Path to the file to be deleted (can be None).
    """
    if not file_path:
        return

    normalized_path = os.path.abspath(file_path)

    if not os.path.exists(normalized_path) or not os.path.isfile(normalized_path):
        return

    try:
        os.remove(file_path)
    except PermissionError:
        logger.error(f"Failed to delete file: Permission denied - {normalized_path}")
    except IOError as e:
        logger.error(f"Failed to delete file: IO Error - {normalized_path} | {str(e)}", exc_info=True)
    except Exception as e:
        logger.error(f"Failed to delete file: Unexpected error - {normalized_path} | {str(e)}", exc_info=True)