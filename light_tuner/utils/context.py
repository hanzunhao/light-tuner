import multiprocessing
from typing import Optional

# 进程内线程锁
_lock = multiprocessing.Lock()
# 每个测试进程的SQLite数据库Test表的主键id,用于给指标记录函数log_metric传参
_test_id = None


def set_test_id(test_id: int) -> None:
    with _lock:
        global _test_id
        _test_id = test_id


def get_test_id() -> Optional[int]:
    with _lock:
        if _test_id:
            return _test_id


def clear_test_id() -> None:
    with _lock:
        global _test_id
        _test_id = None
