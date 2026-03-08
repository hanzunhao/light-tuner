"""
实验管理模块
定义Experiment类，用于管理一次完整的模型超参数优化实验，
支持网格搜索/随机搜索两种模式，实现多进程并发测试控制。
"""
from typing import Dict, Literal, List
import multiprocessing

# 本地模块导入
from .param_generator import generate_grid_search_params, generate_random_search_params
from .test import Test
from light_tuner.utils.config import MAX_WORKERS
from light_tuner.utils.file_operations import read_file

# Windows系统多进程支持
multiprocessing.freeze_support()


class Experiment:
    """
    实验管理类，负责一次完整的模型超参数优化任务的生命周期管理

    核心功能：
    1. 根据指定的搜索模式生成超参数配置组合
    2. 创建对应的测试进程实例
    3. 控制并发进程数量，调度并运行所有测试
    4. 管理进程生命周期，确保资源正确回收

    Attributes:
        name: 实验名称，用于标识不同的优化任务
        hparams_space: 超参数搜索空间字典
        search_mode: 搜索模式，支持"grid"(网格搜索)和"random"(随机搜索)
        random_search_sample_num: 随机搜索时生成的超参数组合数量
        user_code_path: 用户训练代码文件路径
        user_params_dict_name: 用户代码中参数字典的变量名（用于动态替换）
        running_processes: 正在运行的测试进程列表，用于并发控制
        hparams_configs: 生成的所有超参数配置组合列表
        test_instances: 根据超参数配置创建的Test实例列表
    """

    def __init__(
            self,
            name: str,
            hparams_space: Dict,
            search_mode: Literal["grid", "random"],
            random_search_sample_num: int,
            user_code_path: str,
            user_params_dict_name: str
    ) -> None:
        """
        初始化实验实例

        Args:
            name: 实验名称
            hparams_space: 超参数搜索空间字典，格式参考param_generator模块
            search_mode: 搜索模式，仅支持"grid"或"random"
            random_search_sample_num: 随机搜索模式下生成的超参数组合数量
            user_code_path: 用户训练代码的文件路径（相对/绝对路径）
            user_params_dict_name: 用户代码中需要替换的参数字典变量名

        Raises:
            ValueError: 当传入不支持的搜索模式时抛出
            FileNotFoundError: 当用户代码文件路径不存在时抛出
        """
        # 基础实验配置
        self.name = name
        self.hparams_space = hparams_space
        self.search_mode = search_mode
        self.random_search_sample_num = random_search_sample_num
        self.user_code_path = user_code_path
        self.user_params_dict_name = user_params_dict_name

        # 进程管理相关属性
        self.running_processes: List[multiprocessing.Process] = []

        # 预生成超参数配置和测试实例
        self.hparams_configs = self._generate_hyperparameter_configs()
        self.test_instances = self._create_test_instances()

    def _generate_hyperparameter_configs(self) -> List[Dict]:
        """
        私有方法：根据搜索模式生成所有超参数配置组合

        Returns:
            List[Dict]: 超参数配置字典列表，每个字典对应一组超参数

        Raises:
            ValueError: 当指定的搜索模式不被支持时抛出
        """
        if self.search_mode == "grid":
            return generate_grid_search_params(self.hparams_space)
        elif self.search_mode == "random":
            return generate_random_search_params(
                hparams_space=self.hparams_space,
                num_samples=self.random_search_sample_num
            )
        else:
            raise ValueError(
                f"不支持的超参搜索模式: {self.search_mode}，仅支持'grid'或'random'"
            )

    def _create_test_instances(self) -> List[Test]:
        """
        私有方法：根据生成的超参数配置创建Test实例列表

        读取用户代码文件，为每组超参数配置创建对应的Test实例，
        用于后续多进程执行测试。

        Returns:
            List[Test]: Test类实例列表，每个实例对应一组超参数配置

        Raises:
            FileNotFoundError: 当用户代码文件路径不存在时抛出
            IOError: 当读取用户代码文件失败时抛出
        """
        # 读取用户训练代码
        try:
            user_code_content = read_file(self.user_code_path)
        except FileNotFoundError:
            raise FileNotFoundError(f"用户代码文件不存在: {self.user_code_path}")
        except IOError as e:
            raise IOError(f"读取用户代码文件失败: {self.user_code_path}, 错误信息: {str(e)}")

        # 为每组超参数配置创建Test实例
        test_instances = []
        for config_id, hparams_config in enumerate(self.hparams_configs):
            test_instance = Test(
                id=str(config_id + 1),  # 测试实例ID（从1开始）
                hparams=hparams_config,
                user_params_dict_name=self.user_params_dict_name,
                user_code=user_code_content
            )
            test_instances.append(test_instance)

        return test_instances

    def start_all_tests(self) -> None:
        """
        启动所有测试实例，控制并发进程数量不超过MAX_WORKERS

        核心逻辑：
        1. 循环启动测试进程，当运行中的进程数达到上限时等待
        2. 定期检查运行中的进程状态，回收已完成的进程资源
        3. 所有进程启动后，等待剩余进程全部完成
        """
        # 遍历所有测试实例，控制并发启动
        for test_instance in self.test_instances:
            # 等待直到运行中的进程数低于上限
            while len(self.running_processes) >= MAX_WORKERS:
                # 遍历检查运行中的进程，回收已完成的进程
                for running_test in list(self.running_processes):  # 使用list()避免遍历时修改列表
                    if not running_test.is_alive():
                        running_test.join()  # 回收进程资源
                        self.running_processes.remove(running_test)

            # 启动新的测试进程并加入运行列表
            test_instance.start()
            self.running_processes.append(test_instance)

        # 等待所有剩余的进程执行完成并回收资源
        for remaining_test in self.running_processes:
            if remaining_test.is_alive():
                remaining_test.join()
        # 清空运行列表
        self.running_processes.clear()