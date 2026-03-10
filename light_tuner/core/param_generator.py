"""
超参数生成器模块
提供网格搜索和随机搜索两种超参数组合生成方式
"""
import random
from typing import Dict, List, Any
from light_tuner.utils.logger import logger


# todo: 增加判断,若随即搜索时传入的采样数甚至大于网格搜索结果数，采样数赋值为网格搜索结果数

def generate_grid_search_params(hparams_space: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
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
    # 提取超参数名称列表和对应的候选值列表
    param_names = list(hparams_space.keys())
    param_values = list(hparams_space.values())

    # 初始化组合列表，起始为包含空列表的列表
    param_combinations = [[]]

    # 遍历每个参数的候选值，生成笛卡尔积
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
    random_combinations = []

    # 生成指定数量的随机超参数组合
    for _ in range(num_samples):
        single_combination = {}

        # 遍历每个超参数，生成对应的值
        for param_name, param_config in hparams_space.items():
            # 处理离散型超参数
            if isinstance(param_config, list):
                single_combination[param_name] = random.choice(param_config)

            # 处理连续型超参数（min, max, step）
            elif isinstance(param_config, tuple) and len(param_config) == 3:
                min_val, max_val, step_val = param_config
                candidates = []
                current_val = min_val

                # 生成步长间隔的候选值（处理浮点精度问题）
                while current_val <= max_val + 1e-8:
                    # 保留6位小数避免浮点精度问题
                    candidates.append(round(current_val, 6))
                    current_val += step_val

                # 检查候选值是否为空
                if not candidates:
                    logger.warning(f"连续参数{param_name}无有效取值 - min={min_val}, max={max_val}, step={step_val}")
                    continue

                # 从候选值中随机选择
                single_combination[param_name] = random.choice(candidates)

            # 不支持的参数类型
            else:
                logger.error(f"不支持的参数类型 - {param_name}={param_config}（类型: {type(param_config)}）")
                raise

        random_combinations.append(single_combination)

    return random_combinations
