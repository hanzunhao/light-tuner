def helper():
    """
    Generates an Experiment entry file template for the console.
    """
    template = f'''from light_tuner import Experiment

if __name__ == '__main__':
    # 1. Specify the path to your training script
    # Ensure this script contains a global dictionary variable
    path = r"./your_training_script.py"

    # 2. Define the hyperparameter search space
    # Keys must match the keys in your training script's parameter dictionary.
    # - For discrete values, use a list: [val1, val2, ...]
    # - For continuous ranges, use a (min, max, step) tuple.
    hparams_space = {{
        "learning_rate": (0.001, 0.01, 0.001),
        "batch_size": [32, 64],
        "epochs": [50]
    }}

    # 3. Configure the Experiment
    experiment = Experiment(
        name="MyFirstExperiment",       # Unique name for the experiment
        hparams_space=hparams_space,    # Defined search space
        search_mode="random",           # Mode: "random" or "grid"
        user_code_path=path,            # Path to the training code
        random_search_sample_num=5,     # Number of samples (for random search only)
        user_params_dict_name="params"  # Name of the dict to inject into user code
    )

    # 4. Start batch parallel execution
    experiment.start_all_tests()
'''
    print(template)