def helper():
    """
    控制台生成 Experiment 入口文件模板。
    """
    template = f'''from light_tuner import Experiment

if __name__ == '__main__':
    # 1. 指定你的训练脚本路径
    # 确保该脚本中有一个全局字典变量（默认名为 params）
    path = r"./your/code/path"

    # 2. 定义超参数搜索空间（示例）
    # 键:与你的训练脚本中的字典一致
    # 离散值用 list: [val1, val2, ...]
    # 连续值用 tuple: (min, max, step)
    hparams_space = {{
        "learning_rate": (0.001, 0.01, 0.001),
        "batch_size": [32, 64],
        "epochs": [50]
    }}

    # 3. 配置实验
    experiment = Experiment(
        name="ExperimentName",      # 实验名称
        hparams_space=hparams_space,  # 搜索空间
        search_mode="random",         # 搜索模式: "random" 或 "grid"
        user_code_path=path,          # 训练脚本路径
        random_search_sample_num=5,   # 如果是随机搜索，采样多少组
        user_params_dict_name="params" # 训练脚本中对应的字典名
    )

    # 4. 启动批量并行训练
    experiment.start_all_tests()
'''
    print(template)
