from datetime import datetime
from typing import Dict, Any, Optional
from light_tuner.storage.sqlite_manager import db_manager
from light_tuner.utils.context import get_test_id, get_console_test_id
from light_tuner.utils.config import CONSOLE_PRINT_METRICS


def log_metrics(
        metrics: Dict[str, Any],
        epoch: int,
        step: int = 0,
        tag: Optional[str] = None,
        data_type: Optional[str] = None
) -> None:
    """
    记录训练指标，支持自动识别标量与复杂数据结构

    :param metrics: 指标字典，如 {"loss": 0.1, "cm": [[1,0],[0,1]]}
    :param epoch: 当前轮次
    :param step: 当前迭代步数
    :param tag: 阶段标记 ('train', 'val', 'test')
    :param data_type: 强制指定类型，不传则由函数自动推断
    """
    console_test_id = get_console_test_id()
    test_id = get_test_id()
    record_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. 控制台打印逻辑
    if CONSOLE_PRINT_METRICS:
        print(f"\n{'=' * 30} Test {console_test_id} | {tag.upper()} | Epoch {epoch} | Step {step} {'=' * 30}")

        for k, v in metrics.items():
            # 针对不同数据类型的打印优化
            if isinstance(v, (list, dict)):
                val_display = f"[Complex Data: {type(v).__name__}]"
            elif isinstance(v, float) or isinstance(v, int):
                if "lr" in k.lower():
                    val_display = f"{v:.6e}"
                else:
                    val_display = f"{v:.6f}"
            else:
                val_display = str(v)

            print(f"🔹 {k:<20}: {val_display:>15}")

    # 2. 数据库写入逻辑
    for k, v in metrics.items():
        # --- 自动推断 data_type ---
        current_type = data_type
        if not current_type:
            if isinstance(v, (int, float)):
                current_type = 'scalar'
            elif isinstance(v, list):
                # 简单判断是否为嵌套列表（矩阵）
                current_type = 'matrix' if (len(v) > 0 and isinstance(v[0], list)) else 'array'
            elif isinstance(v, dict):
                current_type = 'json'
            else:
                current_type = 'scalar'

        db_manager.insert_metric(
            test_id=test_id,
            epoch=epoch,
            step=step,
            metric_name=k,
            metric_val=v,
            data_type=current_type,
            tag=tag,
            record_time=record_time
        )
