"""
Experiment Management Module
Defines the Experiment class to manage a complete model hyperparameter optimization experiment.
Supports Grid Search and Random Search modes with multi-process concurrency control.
"""
import datetime
import os
from pathlib import Path
from typing import Dict, Literal, List, Optional
import multiprocessing

# Local module imports
from .param_generator import generate_grid_search_params, generate_random_search_params
from .test import Test
from light_tuner.storage.sqlite_manager import SQLiteManager
from light_tuner.utils.config import DEFAULT_MAX_WORKERS
from light_tuner.utils.file_operations import read_file
from light_tuner.utils.logger import logger

# Multi-processing support for Windows systems
multiprocessing.freeze_support()


class Experiment:

    def __init__(
            self,
            name: str,
            hparams_space: Dict,
            search_mode: Literal["grid", "random"],
            user_code_path: str,
            user_params_dict_name: str,
            random_search_sample_num: Optional[int] = None,
            max_workers: int = DEFAULT_MAX_WORKERS
    ) -> None:
        """
        Initialize an Experiment instance.

        Args:
            name: Name of the experiment.
            hparams_space: Hyperparameter search space dictionary.
            search_mode: Search mode, supports "grid" or "random".
            user_code_path: File path to the user's training code (relative or absolute).
            user_params_dict_name: The variable name of the parameter dictionary to be replaced in user code.
            random_search_sample_num: Number of hyperparameter combinations to generate in random search mode.
            max_workers: Maximum number of concurrent worker processes.

        Raises:
            ValueError: If an unsupported search mode is provided.
            FileNotFoundError: If the user code file path does not exist.
        """

        run_dir = Path(os.path.abspath(user_code_path)).parent
        self.db_path = str(run_dir / "light_tuner.db")
        os.environ["LIGHT_TUNER_DB_PATH"] = self.db_path
        self.db_manager = SQLiteManager(self.db_path)

        # Basic experiment configuration
        self.name = name
        self.hparams_space = hparams_space
        self.search_mode = search_mode
        self.random_search_sample_num = random_search_sample_num
        self.user_code_path = user_code_path
        self.user_params_dict_name = user_params_dict_name
        self.max_workers = max_workers

        # List of running processes
        self.running_processes = []

        # Validate search mode
        if self.search_mode not in ["grid", "random"]:
            error_msg = f"Unsupported search mode: {search_mode}"
            logger.error(f"[Experiment {self.name}] Initialization failed: {error_msg}")
            raise ValueError(error_msg)

        # Validate random search sample count (only required for "random" mode)
        if self.search_mode == "random":
            if (
                    self.random_search_sample_num is None
                    or not isinstance(self.random_search_sample_num, int)
                    or self.random_search_sample_num <= 0
            ):
                error_msg = f"In random search mode, random_search_sample_num must be a positive integer (current: {random_search_sample_num})"
                logger.error(f"[Experiment {self.name}] Initialization failed: {error_msg}")
                raise ValueError(error_msg)
        else:
            self.random_search_sample_num = None

        self.db_manager.insert_experiment(
            name=self.name,
            search_mode=self.search_mode,
            random_search_sample_num=self.random_search_sample_num,
            user_code_path=self.user_code_path,
            user_params_dict_name=self.user_params_dict_name,
            hparams_space=str(self.hparams_space),
            start_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            end_time=None,
            status="running"
        )

        # Pre-generate hyperparameter configs and test instances
        try:
            self.hparams_configs = self._generate_hyperparameter_configs()
            logger.info(f"[Experiment {self.name}] Generated {len(self.hparams_configs)} hyperparameter configurations")
        except Exception as e:
            logger.error(f"[Experiment {self.name}] Initialization failed: Error generating hparams - {str(e)}",
                         exc_info=True)
            raise

        try:
            self.test_instances = self._create_test_instances()
            logger.info(f"[Experiment {self.name}] Created {len(self.test_instances)} test instances")
        except Exception as e:
            logger.error(f"[Experiment {self.name}] Initialization failed: Error creating test instances - {str(e)}",
                         exc_info=True)
            raise

        logger.info(f"[Experiment {self.name}] Initializing configuration")
        logger.info(f"{'=' * 60}")
        logger.info(f"Search Mode       : {self.search_mode}")
        logger.info(f"Hparams Space     : {self.hparams_space}")
        if self.search_mode == "random":
            logger.info(f"Random Samples    : {self.random_search_sample_num}")
        logger.info(f"User Code Path    : {self.user_code_path}")
        logger.info(f"Target Param Dict : {self.user_params_dict_name}")
        logger.info(f"{'=' * 60}\n")

        logger.info(f"[Experiment {self.name}] Initialization complete ✅\n")

    def _generate_hyperparameter_configs(self) -> List[Dict]:
        """
        Private method: Generate all hyperparameter combinations based on the search mode.

        Returns:
            List[Dict]: A list of hyperparameter configuration dictionaries.

        Raises:
            ValueError: If the specified search mode is not supported.
        """
        if self.search_mode == "grid":
            configs = generate_grid_search_params(self.hparams_space)
        elif self.search_mode == "random":
            configs = generate_random_search_params(
                hparams_space=self.hparams_space,
                num_samples=self.random_search_sample_num
            )
        else:
            raise ValueError(f"Unsupported search mode: {self.search_mode}")

        logger.debug(f"[Experiment {self.name}] Hyperparameter config details: {configs}")
        return configs

    def _create_test_instances(self) -> List[Test]:
        """
        Private method: Create a list of Test instances based on generated configs.

        Reads the user code and initializes a Test instance for each hyperparameter configuration
        for subsequent multi-process execution.

        Returns:
            List[Test]: A list of Test class instances.

        Raises:
            FileNotFoundError: If the user code file is not found.
            IOError: If reading the user code file fails.
        """
        # Read user training code
        logger.debug(f"[Experiment {self.name}] Reading user code file: {self.user_code_path}")
        try:
            user_code_content = read_file(self.user_code_path)
            if not user_code_content:
                raise IOError("File content is empty")
            logger.debug(f"[Experiment {self.name}] User code file size: {len(user_code_content)} bytes")
        except FileNotFoundError:
            logger.error(f"[Experiment {self.name}] User code file not found: {self.user_code_path}")
            raise
        except IOError as e:
            logger.error(f"[Experiment {self.name}] Failed to read user code: {str(e)}", exc_info=True)
            raise

        # Create Test instances for each config
        test_instances = []
        for config_id, hparams_config in enumerate(self.hparams_configs):
            console_test_id = config_id + 1
            # Insert test record into DB
            db_test_id = self.db_manager.insert_test(
                experiment_id=self.db_manager.select_experiments(self.name)[0]["id"],
                hparams=str(hparams_config),
                start_time=None,
                end_time=None,
                status="paused"
            )
            # Instantiate Test object
            test_instance = Test(
                id=db_test_id,
                console_id=console_test_id,
                hparams=hparams_config,
                user_params_dict_name=self.user_params_dict_name,
                user_code=user_code_content
            )
            test_instances.append(test_instance)

            logger.debug(f"[Experiment {self.name}] Created Test Instance ID={config_id + 1} | Config={hparams_config}")

        return test_instances

    def start_all_tests(self) -> None:
        """
        Starts all test instances, ensuring concurrent processes do not exceed self.max_workers.

        Core Logic:
        1. Iteratively start test processes, waiting if the worker limit is reached.
        2. Periodically check the status of running processes and reclaim finished resources.
        3. After all processes are triggered, wait for the remaining ones to complete.
        """
        logger.info(f"[Experiment {self.name}] Starting execution of all tests")
        logger.info(f"{'=' * 60}")
        logger.info(f"Total Tests       : {len(self.test_instances)}")
        logger.info(f"Max Concurrency   : {self.max_workers}")
        logger.info(f"{'=' * 60}\n")

        try:
            # Iterate through all instances with concurrency control
            for idx, test_instance in enumerate(self.test_instances, 1):
                # Wait until the number of running processes is below the limit
                while len(self.running_processes) >= self.max_workers:
                    # Check running processes and reclaim completed ones
                    for running_test in list(self.running_processes):
                        if not running_test.is_alive():
                            running_test.join()  # Reclaim process resources
                            self.running_processes.remove(running_test)
                            self.db_manager.update_test_by_id(
                                id=running_test.id,
                                end_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                                status="finished"
                            )
                            logger.info(
                                f"[Experiment {self.name}] Reclaimed finished process | Test ID={getattr(running_test, 'id', 'Unknown')}")

                    logger.debug(
                        f"[Experiment {self.name}] Waiting for process slot | Current: {len(self.running_processes)}/{self.max_workers}")

                # Start new test process and add to running list
                try:
                    test_instance.start()
                    self.db_manager.update_test_by_id(
                        id=test_instance.id,
                        start_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                        status="running"
                    )
                    self.running_processes.append(test_instance)
                    logger.info(
                        f"[Experiment {self.name}] Launched test {idx}/{len(self.test_instances)} | Console ID={test_instance.console_id}")
                except Exception as e:
                    logger.error(
                        f"[Experiment {self.name}] Failed to start test {idx} | Console ID={test_instance.console_id} | Error: {str(e)}",
                        exc_info=True)

            # Wait for all remaining processes to finish
            logger.info(
                f"\n[Experiment {self.name}] All tests launched. Waiting for {len(self.running_processes)} processes to complete...")
            for idx, remaining_test in enumerate(self.running_processes, 1):
                if remaining_test.is_alive():
                    logger.debug(
                        f"[Experiment {self.name}] Waiting for process {idx} | ID={getattr(remaining_test, 'id', 'Unknown')}")
                    remaining_test.join()
                self.db_manager.update_test_by_id(
                    id=remaining_test.id,
                    end_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                    status="finished"
                )
                logger.info(f"[Experiment {self.name}] Process {idx} finished and resource reclaimed")

            # Clear process tracking list
            self.running_processes.clear()

            self.db_manager.update_experiment_by_name(
                name=self.name,
                end_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                status="finished"
            )

            logger.info(f"[Experiment {self.name}] All tests executed successfully ✅")

        except Exception as e:

            logger.error(f"[Experiment {self.name}] error during execution: {e}", exc_info=True)
            self.db_manager.update_experiment_by_name(
                name=self.name,
                end_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                status="failed"
            )
            for p in self.running_processes:
                if p.is_alive():
                    p.terminate()
            logger.warning(f"[Experiment {self.name}] Emergency cleanup performed. Experiment marked as FAILED.")

        finally:

            self.db_manager.close()
