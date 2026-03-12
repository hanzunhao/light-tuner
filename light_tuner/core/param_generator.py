"""
超参数生成器模块
提供网格搜索和随机搜索两种超参数组合生成方式
"""
import random
from typing import Dict, List, Any, Union
from light_tuner.utils.logger import logger


def _normalize_hparam_config(param_name: str, param_config: Union[List[Any], tuple[float, float, float]]) -> List[Any]:
    """
        通用参数格式归范化函数：将离散/连续参数转换为候选值列表

        Args:
            param_name: 超参数名称（用于日志输出）
            param_config: 离散型（列表）或连续型（min, max, step三元组）参数配置

        Returns:
            List[Any]: 归范化后的候选值列表
    """
    if isinstance(param_config, list):
        if not param_config:
            error_msg = f"离散参数{param_name}候选值列表为空，无有效取值"
            logger.error(error_msg)
            raise ValueError(error_msg)
        return param_config
    elif isinstance(param_config, tuple) and len(param_config) == 3:
        min_val, max_val, step_val = param_config
        if step_val <= 0:
            error_msg = f"连续参数{param_name}步长无效 - step={step_val}（步长必须大于0）"
            logger.error(error_msg)  # step≤0属于严重错误，用error级别日志
            raise ValueError(error_msg)
        candidates = []
        current_val = min_val
        while current_val <= max_val + 1e-8:
            candidates.append(round(current_val, 6))
            current_val += step_val
        if not candidates:
            error_msg = f"连续参数{param_name}无有效取值 - min={min_val}, max={max_val}, step={step_val}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        return candidates


def generate_grid_search_params(hparams_space: Dict[str, Union[List[Any], tuple[float, float, float]]]) -> List[
    Dict[str, Any]]:
    """
    网格搜索 - 生成超参数空间的所有可能组合

    遍历超参数空间中每个参数的所有候选值，生成笛卡尔积组合，
    适用于小范围超参数空间的穷尽搜索

    Args:
        hparams_space: 超参数空间字典
                       key: 超参数名称（字符串）
                       value: 该超参数的所有候选值列表

    Returns:
        List[Dict[str, Any]]: 所有超参数组合的列表，每个元素是一个超参数字典
    """
    # 归范化所有参数配置
    normalized_hparams = {}
    for param_name, param_config in hparams_space.items():
        normalized_hparams[param_name] = _normalize_hparam_config(param_name, param_config)

    # 提取超参数名称列表和对应的候选值列表
    param_names = list(normalized_hparams.keys())
    param_values = list(normalized_hparams.values())

    # 初始化组合列表
    param_combinations = [[]]

    # 遍历生成笛卡尔积
    for values in param_values:
        temp_combinations = []
        for combination in param_combinations:
            for value in values:
                temp_combinations.append(combination + [value])
        param_combinations = temp_combinations

    # 将组合列表转换为超参数字典列表并返回
    return [dict(zip(param_names, combination)) for combination in param_combinations]


def generate_random_search_params(
        hparams_space: Dict[str, List[Any] | tuple[float, float, float]],
        num_samples: int
) -> List[Dict[str, Any]]:
    """
    随机搜索 - 从超参数空间中随机生成指定数量的超参数组合

    支持两种类型的超参数：
    1. 离散型：以列表形式传入，随机选择其中一个值
    2. 连续型：以(min, max, step)元组形式传入，先生成步长间隔的候选值，再随机选择

    Args:
        hparams_space: 超参数空间字典
                       key: 超参数名称（字符串）
                       value: 离散型（列表）或连续型（三元组）超参数候选值
        num_samples: 需要生成的随机超参数组合数量

    Returns:
        List[Dict[str, Any]]: 随机生成的超参数组合列表
    """

    # 先归范化所有参数，计算网格搜索总组合数
    normalized_hparams = {}
    grid_total = 1
    for param_name, param_config in hparams_space.items():
        candidates = _normalize_hparam_config(param_name, param_config)
        normalized_hparams[param_name] = candidates
        grid_total *= len(candidates)

    # 修正采样数：若采样数大于网格总数则取网格总数，若采样数<=0则设为1
    original_num = num_samples
    num_samples = min(num_samples, grid_total)
    if original_num != num_samples:
        logger.info(f"随机搜索采样数修正：{original_num} → {num_samples}（网格搜索总组合数：{grid_total}）")
    
    # 生成随机组合
    random_combinations = []
    param_names = list(normalized_hparams.keys())

    # 生成指定数量的随机超参数组合
    for _ in range(num_samples):
        single_combination = {}
        for param_name in param_names:
            candidates = normalized_hparams[param_name]
            if not candidates:
                continue
            single_combination[param_name] = random.choice(candidates)
        random_combinations.append(single_combination)

    return random_combinations
