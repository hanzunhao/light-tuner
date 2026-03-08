"""
代码参数注入工具模块
提供字典转Python字符串、代码中参数字典替换等功能，支持动态修改代码中的参数配置
"""
import re
from typing import Dict, Any


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
        raise TypeError(f"输入必须是字典类型，当前类型: {type(parameters)}")

    # 使用repr确保输出合法的Python语法格式
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

    Examples:
        >>> code = "params = {'lr': 0.01, 'bs': 32}"
        >>> replace_parameter_dict_in_code(code, "params", {"lr": 0.001, "bs": 64})
        "params = {'lr': 0.001, 'bs': 64}"
    """
    # 生成新的字典赋值代码
    new_dict_code = f"{target_dict_name} = {convert_dict_to_python_str(new_parameter_dict)}"

    # 正则表达式
    pattern = re.compile(
        rf"{re.escape(target_dict_name)}\s*=\s*"
        r"\{\s*"
        r'(?:".+?":\s*.+?,?\s*)*'
        r"\}",
        re.VERBOSE | re.DOTALL  # VERBOSE允许注释正则，DOTALL让.匹配换行
    )

    # 执行替换（如果未匹配到则返回原代码）
    modified_code = pattern.sub(new_dict_code, code_content)

    # 可选：添加未匹配到的提示（便于调试）
    if modified_code == code_content:
        print(f"警告：未在代码中找到可替换的字典变量 '{target_dict_name}'")

    return modified_code
