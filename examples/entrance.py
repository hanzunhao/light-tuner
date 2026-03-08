from light_tuner import Experiment

if __name__ == '__main__':
    path = r"D:\Program Files\Code\Python\light-tuner\examples\example_lighttuner.py"

    hparams_space = {
        "learning_rate": [0.001, 0.002, 0.003, 0.004, 0.005],  # 调优学习率：0.001、0.002...0.01
        "epochs": [1, 2, 3, 4, 5],  # 调优训练轮数
    }

    experiment = Experiment(
        name="flower",
        hparams_space=hparams_space,
        search_mode="random",
        user_code_path=path,
        random_search_sample_num=5,
        user_params_dict_name="params"
    )

    experiment.start_all_tests()
