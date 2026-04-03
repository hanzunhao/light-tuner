"""
Hyperparameter Generator Module
Provides two methods for generating hyperparameter combinations: Grid Search and Random Search.
"""
import random
from typing import Dict, List, Any, Union
from light_tuner.utils.logger import logger


def _normalize_hparam_config(param_name: str, param_config: Union[List[Any], tuple[float, float, float]]) -> List[Any]:
    """
    Normalizes hyperparameter configuration: Converts discrete/continuous parameters into a list of candidates.

    Args:
        param_name: Name of the hyperparameter (used for logging).
        param_config: Either a discrete list of values or a continuous range
                      represented as a (min, max, step) tuple.

    Returns:
        List[Any]: A normalized list of candidate values.
    """
    if isinstance(param_config, list):
        if not param_config:
            error_msg = f"Candidate list for discrete parameter '{param_name}' is empty."
            logger.error(error_msg)
            raise ValueError(error_msg)
        return param_config

    elif isinstance(param_config, tuple) and len(param_config) == 3:
        min_val, max_val, step_val = param_config
        if step_val <= 0:
            error_msg = f"Invalid step for continuous parameter '{param_name}': step={step_val} (must be > 0)."
            logger.error(error_msg)
            raise ValueError(error_msg)

        candidates = []
        current_val = min_val
        # Use a small epsilon (1e-8) to handle floating-point precision issues
        while current_val <= max_val + 1e-8:
            candidates.append(round(current_val, 6))
            current_val += step_val

        if not candidates:
            error_msg = f"No valid values for continuous parameter '{param_name}': min={min_val}, max={max_val}, step={step_val}."
            logger.error(error_msg)
            raise ValueError(error_msg)
        return candidates


def generate_grid_search_params(hparams_space: Dict[str, Union[List[Any], tuple[float, float, float]]]) -> List[Dict[str, Any]]:
    """
    Grid Search - Generates all possible combinations within the hyperparameter space.

    Iterates through all candidate values for each parameter to generate a Cartesian product.
    Best suited for exhaustive searches in small hyperparameter spaces.

    Args:
        hparams_space: A dictionary where keys are hyperparameter names and values are
                       candidate lists or (min, max, step) tuples.

    Returns:
        List[Dict[str, Any]]: A list of all hyperparameter combinations.
    """
    # Normalize all parameter configurations
    normalized_hparams = {}
    for param_name, param_config in hparams_space.items():
        normalized_hparams[param_name] = _normalize_hparam_config(param_name, param_config)

    # Extract names and corresponding candidate value lists
    param_names = list(normalized_hparams.keys())
    param_values = list(normalized_hparams.values())

    # Initialize combination list with an empty seed
    param_combinations = [[]]

    # Generate Cartesian product
    for values in param_values:
        temp_combinations = []
        for combination in param_combinations:
            for value in values:
                temp_combinations.append(combination + [value])
        param_combinations = temp_combinations

    # Convert combination lists into dictionaries
    return [dict(zip(param_names, combination)) for combination in param_combinations]


def generate_random_search_params(
        hparams_space: Dict[str, Union[List[Any], tuple[float, float, float]]],
        num_samples: int
) -> List[Dict[str, Any]]:
    """
    Random Search - Randomly generates a specified number of hyperparameter combinations.

    Supports two types of hyperparameters:
    1. Discrete: Passed as a list; one value is chosen at random.
    2. Continuous: Passed as a (min, max, step) tuple; values are sampled from generated steps.

    Args:
        hparams_space: A dictionary of hyperparameter spaces.
        num_samples: The number of random combinations to generate.

    Returns:
        List[Dict[str, Any]]: A list of randomly generated hyperparameter combinations.
    """
    # Normalize parameters and calculate total possible combinations (grid size)
    normalized_hparams = {}
    grid_total = 1
    for param_name, param_config in hparams_space.items():
        candidates = _normalize_hparam_config(param_name, param_config)
        normalized_hparams[param_name] = candidates
        grid_total *= len(candidates)

    # Sanity check for num_samples: Cap at grid_total and ensure at least 1
    original_num = num_samples
    num_samples = max(1, min(num_samples, grid_total))

    if original_num != num_samples:
        logger.info(f"Corrected random search sample size: {original_num} → {num_samples} (Total possible combinations: {grid_total})")

    random_combinations = []
    param_names = list(normalized_hparams.keys())

    # Generate unique random combinations
    for _ in range(num_samples):
        single_combination = {}
        for param_name in param_names:
            candidates = normalized_hparams[param_name]
            if not candidates:
                continue
            single_combination[param_name] = random.choice(candidates)
        random_combinations.append(single_combination)

    return random_combinations