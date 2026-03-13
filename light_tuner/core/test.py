"""
测试执行模块
定义Test类（继承自multiprocessing.Process），负责单组超参数配置的模型训练代码执行，
核心流程：参数注入 → 创建临时文件 → 运行代码 → 清理临时文件
"""
import multiprocessing
import runpy
import traceback
from typing import Dict, Optional
from light_tuner.utils.code_injector import replace_parameter_dict_in_code
from light_tuner.utils.file_operations import delete_file, create_temp_py_file
from light_tuner.utils.logger import logger
from light_tuner.utils.context import set_test_id, clear_test_id


class Test(multiprocessing.Process):
    """
    单组超参数测试执行进程类

    继承自multiprocessing.Process，用于在独立进程中执行一组超参数配置的模型训练代码，
    自动完成参数注入、临时文件创建、代码运行和资源清理，确保进程安全执行。

    Attributes:
        console_id: 测试实例唯一标识符，用于区分不同的超参数组合测试
        hparams: 本次测试使用的超参数配置字典
        user_params_dict_name: 用户代码中需要替换的参数字典变量名
        user_code: 用户原始训练代码文本内容
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
        初始化测试进程实例

        Args:
            id:唯一测试标识符,与数据库主键相同
            console_id: 测试标识符,仅用于一次实验运行时的控制台打印
            hparams: 本次测试使用的超参数组合字典
            user_params_dict_name: 用户训练代码中需要替换的参数字典变量名
            user_code: 用户训练代码的文本内容
        """
        super().__init__()

        # 基础配置属性
        self.id = id
        self.console_id = console_id
        self.hparams = hparams
        self.user_params_dict_name = user_params_dict_name
        self.user_code = user_code
        # 初始化日志 - 测试实例创建
        logger.info(f"[测试实例-{self.console_id}] 初始化完成 | 超参数: {self.hparams}")

    def run(self) -> None:
        """
        进程核心执行逻辑（自动调用）

        执行流程：
        1. 将超参数注入到用户代码中
        2. 创建临时Python文件保存注入后的代码
        3. 运行临时文件中的训练代码
        4. 无论执行成功/失败，最终清理临时文件
        """
        temp_file_path: Optional[str] = None
        logger.info(f"[测试实例-{self.console_id}] 开始执行 | PID: {self.pid}")

        try:
            set_test_id(self.id)
            # 步骤1：超参数注入到用户代码
            injected_code = replace_parameter_dict_in_code(
                code_content=self.user_code,
                target_dict_name=self.user_params_dict_name,
                new_parameter_dict=self.hparams
            )

            # 步骤2：创建临时Python文件
            temp_file_path = create_temp_py_file(injected_code)
            if not temp_file_path:
                raise RuntimeError(f"测试[{self.console_id}]：创建临时文件失败")
            logger.info(f"[测试实例-{self.console_id}] 临时文件创建成功 | 路径: {temp_file_path}")

            # 步骤3：运行注入后的用户代码
            logger.info(f"[测试实例-{self.console_id}] 开始执行训练代码 ✨")
            runpy.run_path(path_name=temp_file_path, run_name="__main__")
            logger.info(f"[测试实例-{self.console_id}] 训练代码执行完成 ✅")

        except Exception as e:
            error_detail = traceback.format_exc()
            logger.error(f"[测试实例-{self.console_id}] 执行失败 ❌ | 错误: {str(e)}")
            logger.debug(f"[测试实例-{self.console_id}] 错误堆栈:\n{error_detail}")

        finally:
            clear_test_id()
            # 步骤4：确保临时文件被清理，避免文件残留
            if temp_file_path:
                delete_file(temp_file_path)
                logger.info(f"[测试实例-{self.console_id}] 临时文件已清理 | 路径: {temp_file_path}")
