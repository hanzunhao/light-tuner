with open(r"D:\Program Files\Code\Python\light-tuner\examples\example_lighttuner.py", "r", encoding="utf-8") as f:
    user_code = f.read()

d = {
    "learning_rate": 0.004,
    "epochs": 5
}

rd = repr(d)


def f(rd):
    s = f"""
# ????????????
params={rd}
"""
    return s


print(f(rd)+user_code)
