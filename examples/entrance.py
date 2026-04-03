from light_tuner import Experiment

if __name__ == '__main__':
    path = r"example_lighttuner.py"

    hparams_space = {
        "learning_rate": [0.001, 0.002, 0.003, 0.004, 0.005],
        "batch_size": [32, 64, 128],
        "epochs": [3, 4, 5, 6, 7, 8, 9, 10]
    }

    experiment = Experiment(
        name="第一次实验",
        hparams_space=hparams_space,
        search_mode="random",
        user_code_path=path,
        random_search_sample_num=5,
        max_workers=2,
        user_params_dict_name="params"
    )

    experiment.start_all_tests()
