from typing import Dict, Literal
from param_generator import generate_random, generate_grid


# 管理各Test的类，代表一次完整的模型优化任务
class Experiment:
    def __init__(self, name: str, hparams_space: Dict, search_mode: Literal["grid", "random"], n: int, path: str):
        # 实验名称
        self.name = name
        # 本次实验的超参数据空间
        self.hparams_space = hparams_space
        # 超参数搜索算法
        self.search_mode = search_mode
        # 随机搜索算法的n
        self.n = n

    # 生成各test所需的超参数配置
    def __generate_tests_configs(self) -> Dict:
        if self.search_mode == "grid":
            return generate_grid(self.hparams_space)
        elif self.search_mode == "random":
            return generate_random(self.hparams_space, self.n)
        else:
            raise ValueError(f"不支持的超参搜索模式: {self.search_mode}"f"")
