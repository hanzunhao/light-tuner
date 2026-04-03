"""
Test Execution Module
Defines the Test class (inheriting from multiprocessing.Process), responsible for executing
model training code with a specific hyperparameter configuration.
Core Flow: Parameter Injection → Temporary File Creation → Code Execution → Cleanup.
"""
import multiprocessing
import runpy
import traceback
from typing import Dict, Optional

# Local module imports
from light_tuner.utils.code_injector import replace_parameter_dict_in_code
from light_tuner.utils.file_operations import delete_file, create_temp_py_file
from light_tuner.utils.logger import logger
from light_tuner.utils.context import set_test_id, clear_test_id, set_console_test_id, clear_console_test_id


class Test(multiprocessing.Process):
    """
    Execution process class for a single hyperparameter test.

    Inherits from multiprocessing.Process to execute model training code in an isolated
    process. It automatically handles parameter injection, temporary file management,
    code execution, and resource cleanup to ensure process safety.

    Attributes:
        id: Unique test identifier corresponding to the database primary key.
        console_id: A unique identifier used for console logging during an experiment run.
        hparams: Dictionary of hyperparameters used for this specific test.
        user_params_dict_name: The name of the parameter dictionary variable to be replaced in user code.
        user_code: The raw text content of the user's training code.
    """

    def __init__(
            self,
            id: int,
            console_id: int,
            hparams: Dict,
            user_params_dict_name: str,
            user_code: str
    ) -> None:
        """
        Initialize the test process instance.

        Args:
            id: Unique test identifier (DB primary key).
            console_id: Identifier for console output.
            hparams: Hyperparameter combination dictionary for this test.
            user_params_dict_name: The variable name of the dict to replace in the user's script.
            user_code: Text content of the training script.
        """
        super().__init__()

        # Basic configuration attributes
        self.id = id
        self.console_id = console_id
        self.hparams = hparams
        self.user_params_dict_name = user_params_dict_name
        self.user_code = user_code

        logger.info(f"[Test-{self.console_id}] Initialization complete | Hparams: {self.hparams}")

    def run(self) -> None:
        """
        Core execution logic of the process (called automatically on .start()).

        Execution Flow:
        1. Inject hyperparameters into the user code.
        2. Create a temporary Python file to save the injected code.
        3. Execute the training code within the temporary file.
        4. Ensure the temporary file is deleted regardless of success or failure.
        """
        temp_file_path: Optional[str] = None
        logger.info(f"[Test-{self.console_id}] Execution started | PID: {self.pid}")

        try:
            # Set context IDs for logging and database tracking within this process
            set_test_id(self.id)
            set_console_test_id(self.console_id)

            # Step 1: Inject hyperparameters into user code
            injected_code = replace_parameter_dict_in_code(
                code_content=self.user_code,
                target_dict_name=self.user_params_dict_name,
                new_parameter_dict=self.hparams
            )

            # Step 2: Create temporary Python file
            temp_file_path = create_temp_py_file(injected_code)
            if not temp_file_path:
                raise RuntimeError(f"Test[{self.console_id}]: Failed to create temporary file.")
            logger.info(f"[Test-{self.console_id}] Temporary file created | Path: {temp_file_path}")

            # Step 3: Run the injected user code
            logger.info(f"[Test-{self.console_id}] Launching training script ✨")
            runpy.run_path(path_name=temp_file_path, run_name="__main__")
            logger.info(f"[Test-{self.console_id}] Training script finished successfully ✅")

        except Exception as e:
            error_detail = traceback.format_exc()
            logger.error(f"[Test-{self.console_id}] Execution failed ❌ | Error: {str(e)}")
            logger.debug(f"[Test-{self.console_id}] Error Stacktrace:\n{error_detail}")

        finally:
            # Clear context and perform cleanup
            clear_test_id()
            clear_console_test_id()

            # Step 4: Ensure temporary file is removed to avoid disk clutter
            if temp_file_path:
                delete_file(temp_file_path)
                logger.info(f"[Test-{self.console_id}] Temporary file cleaned up | Path: {temp_file_path}")