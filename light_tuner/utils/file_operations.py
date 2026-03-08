"""
文件操作工具模块
提供临时Python文件创建、文件读取、文件删除等常用文件操作功能
"""
import os
import tempfile
from typing import Optional, Union


def create_temp_py_file(content: str) -> Optional[str]:
    """
    创建临时Python文件并写入指定内容

    创建一个后缀为.py的临时文件，写入指定字符串内容，文件不会自动删除，
    需调用delete_file手动清理。适用于需要临时生成Python脚本的场景。

    Args:
        content: 要写入临时文件的字符串内容

    Returns:
        Optional[str]: 成功创建则返回临时文件的绝对路径；
                      若输入内容为空或创建失败则返回None

    Raises:
        IOError: 当文件写入操作失败时抛出
    """
    # 空内容校验
    if not content:
        return None

    try:
        # 创建不自动删除的临时Python文件
        with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.py',
                delete=False,
                encoding='utf-8'
        ) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name

        return temp_file_path
    except IOError as e:
        print(f"创建临时Python文件失败: {str(e)}")
        return None


def read_file(file_path: str) -> Optional[str]:
    """
    读取指定路径的文件内容（UTF-8编码）

    安全读取文本文件内容，包含完善的异常处理，避免因文件不存在、权限不足等
    问题导致程序崩溃。

    Args:
        file_path: 要读取的文件路径（相对路径或绝对路径）

    Returns:
        Optional[str]: 成功读取则返回文件内容字符串；
                      若文件不存在/读取失败则返回None

    Raises:
        PermissionError: 当没有文件读取权限时抛出
        UnicodeDecodeError: 当文件不是UTF-8编码时抛出
    """
    # 空路径校验
    if not file_path:
        return None

    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"读取文件失败: 文件不存在 - {file_path}")
        return None

    # 检查路径是否为文件
    if not os.path.isfile(file_path):
        print(f"读取文件失败: 路径不是文件 - {file_path}")
        return None

    try:
        with open(file_path, "r", encoding="utf-8") as file_handler:
            file_content = file_handler.read()
        return file_content
    except PermissionError:
        print(f"读取文件失败: 没有读取权限 - {file_path}")
        return None
    except UnicodeDecodeError:
        print(f"读取文件失败: 文件不是UTF-8编码 - {file_path}")
        return None
    except IOError as e:
        print(f"读取文件失败: 输入输出错误 - {file_path}, 错误信息: {str(e)}")
        return None


def delete_file(file_path: Union[str, None]) -> None:
    """
    安全删除指定路径的文件

    包含前置校验和异常处理，确保删除操作不会导致程序崩溃，支持传入None值。

    Args:
        file_path: 要删除的文件路径（可为None）

    Returns:
        None
    """
    # 空路径直接返回
    if not file_path:
        return

    # 检查文件是否存在
    if not os.path.exists(file_path):
        return

    # 检查路径是否为文件（避免误删目录）
    if not os.path.isfile(file_path):
        print(f"删除失败: 路径不是文件 - {file_path}")
        return

    try:
        os.remove(file_path)
    except PermissionError:
        print(f"删除文件失败: 没有删除权限 - {file_path}")
    except IOError as e:
        print(f"删除文件失败: 输入输出错误 - {file_path}, 错误信息: {str(e)}")
