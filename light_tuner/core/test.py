from typing import Dict
import threading
import runpy
from pathlib import Path
from light_tuner.utils.config import MAX_WORKERS

# 可同时运行的线程数
semaphore = threading.Semaphore(MAX_WORKERS)


# 优化任务中的各种超参组合的尝试，是一次模型训练代码的完整运行
class Test(threading.Thread):
    def __init__(self, id: str, config: Dict, path: str):
        super().__init__()
        # 测试唯一标识符
        self.id = id
        # 本次测试使用的超参数组合
        self.config = config
        # 训练模块路径
        self.path = path

    # 运行训练模块
    def run(self) -> None:
        semaphore.acquire()
        print(f"{self.id}号测试线程开始运行")
        runpy.run_path(path_name=self.path)
        print(f"{self.id}号测试线程运行完毕")
        semaphore.release()


if __name__ == '__main__':
    # 暂时使用固定路径
    current_file = Path(__file__)
    root_dir = current_file.parent.parent.parent
    target_file = str(root_dir / "examples/example.py")

    # 创建线程
    test_threads = []
    for i in range(10):
        test = Test(id=str(i + 1), config={}, path=target_file)
        test_threads.append(test)

    # 运行线程
    for test in test_threads:
        test.start()

    # 等待结束
    for test in test_threads:
        test.join()
