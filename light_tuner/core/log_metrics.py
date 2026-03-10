from datetime import datetime
from typing import Dict


# todo:补充向后端传入指标的函数

# 记录一轮训练中的多个指标并打印在控制台上
def log_metrics(
        metrics: Dict,
        epoch: int,
        console_print: bool = True
) -> None:
    metrics_with_meta = metrics.copy()
    metrics_with_meta["epoch"] = epoch
    metrics_with_meta["datetime"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if console_print:
        # 标题行
        print(f"\n{'=' * 50} Epoch {epoch + 1} Metrics {'=' * 50}")
        # 遍历指标
        for k, v in metrics.items():
            # 指标值格式化：数值保留6位小数，学习率用科学计数法
            if "lr" in k.lower():
                val_str = f"{v:.6e}"
            else:
                val_str = f"{v:.6f}"
            # 对齐排版（左对齐键名，右对齐值）
            print(f"🔹 {k:<15}: {val_str:>12}")
