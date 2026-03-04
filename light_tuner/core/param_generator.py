import random
from typing import Dict
from light_tuner.utils.exceptions import ParamGenerateError


# 网格搜索
def generate_grid(hparams_space: Dict):
    keys = list(hparams_space.keys())
    values = list(hparams_space.values())
    combinations = [[]]

    # 遍历所有组合
    for value in values:
        temp = []
        for combination in combinations:
            for item in value:
                temp.append(combination + [item])
        combinations = temp

    return [dict(zip(keys, combination)) for combination in combinations]


# 随机搜索
def generate_random(hparams_space: Dict, n: int):
    combinations = []

    for _ in range(n):

        combination = {}

        for key, value in hparams_space.items():
            # 若为离散型超参(list表示)，则随机选择一个侯选值
            if isinstance(value, list):
                combination[key] = random.choice(value)
            # 若为连续型超参(tuple表示)，则按(min, max, step)随机生成数值
            elif isinstance(value, tuple) and len(value) == 3:
                # 生成step步长的所有候选值
                min, max, step = value[0], value[1], value[2]
                candidates = []
                current = min
                while current <= max + 1e-8:  # 浮点精度容错
                    candidates.append(round(current, 6))  # 保留6位小数避免精度问题
                    current += step
                if not candidates:
                    raise ParamGenerateError(f"连续参数{key}无有效取值：min={min}, max={max}, step={step}")
                # 随机选择一个侯选值
                combination[key] = random.choice(candidates)
            else:
                raise ParamGenerateError(f"不支持的参数类型：{key}={value}")

        combinations.append(combination)

    return combinations


# 测试用例
if __name__ == '__main__':
    hparams_space = {
        # 离散整型：卷积层1的滤波器数量
        "conv1_filters": [16, 32],
        # 离散整型：卷积层2的滤波器数量
        "conv2_filters": [32, 64],
        # 离散整型：全连接层神经元数量
        "dense_units": [128, 256],
        # 连续浮点型：学习率
        "learning_rate": (0.005, 0.05, 0.005),
        # 连续浮点型：Dropout
        "dropout_rate": (0.1, 0.3, 0.05),
        # 离散分类型：优化器
        "optimizer": ["adam", "sgd"]
    }

    n = 6

    print("generate grid result:")
    combinations = generate_grid(hparams_space)
    for combination in combinations:
        print(combination)

    print("generate random result:")
    combinations = generate_random(hparams_space, n)
    for combination in combinations:
        print(combination)
