import sqlite3
from pathlib import Path
import os
from light_tuner.utils.logger import logger


class SQLiteManager:
    def __init__(self, path: str = "database.db"):
        self.path = Path(path)
        self._check_permission()
        self.conn = self._get_connection()
        self.cursor = self.conn.cursor()
        self.create_tables()

    # 检查写入权限
    def _check_permission(self):
        dir_path = self.path.parent

        # 尝试创建临时文件，判断目录是否可写
        try:
            # 创建临时文件并删除，验证写入权限
            temp_file = dir_path / ".temp_permission_check"
            temp_file.touch(exist_ok=True)
            temp_file.unlink()
            is_writable = True
        except (PermissionError, OSError):
            is_writable = False

        if not is_writable:
            logger.warning(f"目录 {dir_path} 无写入权限！")
            fallback_path = Path(os.path.expanduser("~")) / "light_tuner/database.db"
            fallback_path.parent.mkdir(parents=True, exist_ok=True)
            self.db_path = fallback_path
            logger.warning(f"已自动切换到用户目录：{self.db_path}")

    # 返回数据库连接
    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self.path,
            check_same_thread=False,
            timeout=10
        )
        # 启用WAL模式
        conn.execute("PRAGMA journal_mode=WAL")
        # 启用外键约束
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    # 创建表结构
    def create_tables(self) -> None:
        # 1. 实验表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Experiment (
                id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                name VARCHAR(100) UNIQUE NOT NULL,
                search_mode TEXT NOT NULL CHECK(search_mode IN ('grid', 'random')),
                random_search_sample_num INTEGER,
                user_code_path VARCHAR(255) NOT NULL,
                user_params_dict_name VARCHAR(100) NOT NULL,
                hparams_space TEXT NOT NULL,
                start_time DATETIME NOT NULL,
                end_time DATETIME,
                status TEXT NOT NULL CHECK(status IN ('running', 'finished', 'failed', 'paused')) DEFAULT 'running',
                CONSTRAINT chk_experiment_status CHECK(status IN ('running', 'finished', 'failed', 'paused')),
                CONSTRAINT chk_search_mode CHECK(search_mode IN ('grid', 'random'))
            );
        """)

        # 2. 测试表（单组参数执行记录）
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Test (
                id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                experiment_id INTEGER NOT NULL,
                hparams TEXT NOT NULL,
                start_time DATETIME NOT NULL,
                end_time DATETIME,
                status TEXT NOT NULL CHECK(status IN ('running', 'finished', 'failed', 'paused')) DEFAULT 'running',
                FOREIGN KEY (experiment_id) REFERENCES Experiment(id) 
                    ON DELETE CASCADE 
                    ON UPDATE CASCADE,
                CONSTRAINT chk_test_status CHECK(status IN ('running', 'finished', 'failed', 'paused'))
            );
        """)

        # 3. 指标表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Metric (
                id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                test_id INTEGER NOT NULL,
                metric_name VARCHAR(50) NOT NULL,
                metric_val FLOAT NOT NULL,
                epoch INTEGER NOT NULL DEFAULT 0,
                record_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (test_id) REFERENCES Test(id) 
                    ON DELETE CASCADE 
                    ON UPDATE CASCADE
            );
        """)

        # 提交事务
        self.conn.commit()

        logger.info("数据库表结构创建成功")

    # 关闭数据库连接
    def close(self) -> None:
        self.cursor.close()
        self.conn.close()
        logger.info("数据库连接已关闭")

    # todo 完善数据库增删改查操作函数


db_manager = SQLiteManager()
