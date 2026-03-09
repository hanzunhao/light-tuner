import logging
from light_tuner.utils.config import LOG_LEVEL, LOG_FORMAT, DATE_FORMAT, COLOR_CODES

RESET_CODE = "\033[0m"  # 重置颜色


# ===================== 自定义彩色格式化器 =====================
class ColoredFormatter(logging.Formatter):
    def format(self, record):
        # 1. 获取当前日志级别对应的颜色编码
        color_code = COLOR_CODES.get(record.levelno, RESET_CODE)

        # 2. 先调用父类方法生成完整的日志字符串（包含时间、进程ID等所有内容）
        log_message = super().format(record)

        # 3. 为整条日志字符串添加颜色编码（开头加颜色，结尾重置）
        colored_log = f"{color_code}{log_message}{RESET_CODE}"

        return colored_log


def setup_logger(name: str = "hyperopt") -> logging.Logger:
    """
    初始化带彩色输出的全局统一logger实例
    :param name: logger名称（全局唯一）
    :return: 配置好的logger实例
    """
    # 获取全局唯一logger实例
    logger = logging.getLogger(name)

    # 转换日志级别（从配置文件读取）
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    logger.setLevel(level_map.get(LOG_LEVEL, logging.INFO))
    logger.propagate = False  # 禁用向上传播，避免重复输出

    # 仅在无handler时添加（防止多进程/多模块重复添加）
    if not logger.handlers:
        # 创建控制台handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logger.level)

        # 使用自定义彩色格式化器
        formatter = ColoredFormatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)
        console_handler.setFormatter(formatter)

        # 添加handler到logger
        logger.addHandler(console_handler)

    return logger


# 创建全局logger实例，所有模块直接导入使用
logger = setup_logger()
