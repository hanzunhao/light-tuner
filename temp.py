from tqdm import trange
from random import random, randint
import time

with trange(10) as t:
    for i in t:
        # 设置进度条左边显示的信息
        t.set_description("GEN %i" % i)
        # 设置进度条右边显示的信息
        t.set_postfix(loss=random(), gen=randint(1, 999), str="h", lst=[1, 2])
        time.sleep(0.1)
