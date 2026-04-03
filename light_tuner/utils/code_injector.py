"""
代码参数注入工具模块
提供字典转Python字符串、代码中参数字典替换等功能，支持动态修改代码中的参数配置
"""
import ast
from typing import Dict, Any
from light_tuner.utils.logger import logger


def convert_dict_to_python_str(parameters: Dict[Any, Any]) -> str:
    """
    将字典转换为合法的Python字典字符串
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

    if not code_content:
        logger.error("代码参数注入失败：原始代码内容为空")
        raise ValueError("code_content 不能为空字符串")

    if not target_dict_name:
        logger.error("代码参数注入失败：目标字典变量名不能为空")
        raise ValueError("target_dict_name 不能为空字符串")

    if not isinstance(new_parameter_dict, dict):
        logger.error(f"代码参数注入失败：新参数字典必须是字典类型，当前类型: {type(new_parameter_dict)}")
        raise TypeError(f"代码参数注入失败：新参数字典必须是字典类型，当前类型: {type(new_parameter_dict)}")

    try:
        tree=ast.parse(code_content)
        replaced = False
        new_dict_node=ast.parse(convert_dict_to_python_str(new_parameter_dict)).body[0].value

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == target_dict_name:
                        # 执行替换：将旧的右值替换为新生成的节点
                        node.value = new_dict_node
                        replaced = True

        if not replaced:
            logger.warning(f"未在代码中找到可替换的字典变量 '{target_dict_name}'")
            return code_content

        # 6. 将修改后的树还原为代码字符串
        return ast.unparse(tree)

    except SyntaxError as se:
        logger.error(f"代码注入失败，源码存在语法错误: {se}")
        return code_content
    except Exception as e:
        logger.error(f"AST 处理过程中发生异常: {e}")
        return code_content
