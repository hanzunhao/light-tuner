"""
代码参数注入工具模块
提供字典转Python字符串、代码中参数字典替换等功能，支持动态修改代码中的参数配置
"""
import re
from typing import Dict, Any
from light_tuner.utils.logger import logger


def convert_dict_to_python_str(parameters: Dict[Any, Any]) -> str:
    """
    将字典转换为合法的Python字典字符串

    基于repr()实现，确保输出的字符串可以直接作为Python代码执行，
    支持常见数据类型（字符串、数字、布尔值、None等）的正确转换。

    Args:
        parameters: 需要转换的字典对象

    Returns:
        str: 可直接执行的Python字典字符串

    Raises:
        TypeError: 当输入不是字典类型时抛出
    """
    # 输入类型校验
    if not isinstance(parameters, dict):
        error_msg = f"字典转换失败：输入必须是字典类型，当前类型: {type(parameters)}"
        logger.error(error_msg)
        raise TypeError(error_msg)

    return repr(parameters)


def replace_parameter_dict_in_code(
        code_content: str,
        target_dict_name: str,
        new_parameter_dict: Dict[Any, Any]
) -> str:
    """
    在Python代码字符串中替换指定名称的字典变量定义

    支持匹配多种字典定义格式（单行/多行、不同空格缩进、带注释等），
    将原有字典定义替换为新的参数字典，适用于动态注入参数配置的场景。

    Args:
        code_content: 原始Python代码字符串
        target_dict_name: 要替换的字典变量名（如"params"）
        new_parameter_dict: 新的参数字典

    Returns:
        str: 替换后的代码字符串
    """

    # 前置校验：核心参数不能为空
    if not code_content:
        logger.error("代码参数注入失败：原始代码内容为空")
        raise ValueError("code_content 不能为空字符串")

    if not target_dict_name:
        logger.error("代码参数注入失败：目标字典变量名不能为空")
        raise ValueError("target_dict_name 不能为空字符串")

    if not isinstance(new_parameter_dict, dict):
        logger.error(f"代码参数注入失败：新参数字典必须是字典类型，当前类型: {type(new_parameter_dict)}")
        raise TypeError(f"代码参数注入失败：新参数字典必须是字典类型，当前类型: {type(new_parameter_dict)}")

    # 生成新的字典赋值代码
    new_dict_code = f"{target_dict_name} = {convert_dict_to_python_str(new_parameter_dict)}"

    # 正则表达式
    pattern = re.compile(
        rf"{re.escape(target_dict_name)}\s*=\s*"
        r"\{\s*"
        r'(?:".+?":\s*.+?,?\s*)*'
        r"\}",
        re.VERBOSE | re.DOTALL | re.MULTILINE  # 多行、点匹配换行、允许正则注释
    )

    # 执行替换（如果未匹配到则返回原代码）
    modified_code = pattern.sub(new_dict_code, code_content)

    if modified_code == code_content:
        logger.warning(f"未在代码中找到可替换的字典变量 '{target_dict_name}'")

    return modified_code
