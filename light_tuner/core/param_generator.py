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
    Random Search - Generates a specified number of unique hyperparameter combinations
    by sampling from the full grid.

    This method ensures uniqueness by first generating the entire search space (Cartesian product)
    and then performing a random sample without replacement. This is more robust than
    naive random selection when num_samples is close to the total grid size.

    Args:
        hparams_space: A dictionary where keys are hyperparameter names and values are
                       either lists of candidates or (min, max, step) tuples.
        num_samples: The target number of random combinations to generate.

    Returns:
        List[Dict[str, Any]]: A list of unique, randomly sampled hyperparameter configurations.
    """
    # 1. Reuse Grid Search logic to generate all theoretical combinations
    # This ensures consistency in parameter normalization and Cartesian product generation.
    all_possible_combinations = generate_grid_search_params(hparams_space)
    grid_total = len(all_possible_combinations)

    # 2. Safety check: Cap num_samples at the maximum possible combinations
    # This prevents the sampler from requesting more items than exist in the population.
    original_num = num_samples
    num_samples = max(1, min(num_samples, grid_total))

    if original_num != num_samples:
        logger.info(
            f"Corrected random search sample size: {original_num} → {num_samples} "
            f"(Total possible combinations: {grid_total})"
        )

    # 3. Perform random sampling without replacement to ensure 100% uniqueness
    # random.sample is efficient for this purpose as it picks unique elements from a population.
    sampled_combinations = random.sample(all_possible_combinations, num_samples)

    return sampled_combinations
