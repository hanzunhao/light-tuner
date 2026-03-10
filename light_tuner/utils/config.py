"""
项目配置常量模块
存储系统核心配置参数，统一管理便于维护和环境切换
"""
import logging

MAX_WORKERS = 2

BACKEND_URL = "http://localhost:8080/api"

LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s | %(process)d | %(module)s | %(levelname)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
COLOR_CODES = {
    logging.DEBUG: "\033[0;37m",  # 灰色 (DEBUG)
    logging.INFO: "\033[0;32m",  # 绿色 (INFO)
    logging.WARNING: "\033[0;33m",  # 黄色 (WARNING)
    logging.ERROR: "\033[0;31m",  # 红色 (ERROR)
    logging.CRITICAL: "\033[1;31m"  # 亮红色 (CRITICAL)
}

AUTOLOG_ENABLED = False

