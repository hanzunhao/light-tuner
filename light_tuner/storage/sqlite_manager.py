import sqlite3
from pathlib import Path
import os
from typing import List
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

        temp_file = None

        # 尝试创建临时文件，判断目录是否可写
        try:
            # 创建临时文件并删除，验证写入权限
            temp_file = dir_path / ".temp_permission_check"
            temp_file.touch(exist_ok=True)
            temp_file.unlink()
            is_writable = True
        except (PermissionError, OSError):
            is_writable = False
        finally:
            if temp_file and temp_file.exists():
                temp_file.unlink()

        if not is_writable:
            logger.warning(f"{dir_path} 无写入权限！")
            fallback_path = Path(os.path.expanduser("~")) / "light_tuner/database.db"
            fallback_path.parent.mkdir(parents=True, exist_ok=True)
            self.path = fallback_path
            logger.warning(f"已自动切换到：{self.path}")

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

    """
    EXPERIMENT操作
    """

    # 插入实验记录
    def insert_experiment(self, name, search_mode, random_search_sample_num, user_code_path, user_params_dict_name,
                          hparams_space, start_time, end_time, status) -> bool:
        sql = """
            INSERT INTO Experiment (
                name, search_mode, random_search_sample_num, user_code_path, 
                user_params_dict_name, hparams_space, start_time, end_time, status
            ) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        try:
            self.cursor.execute(
                sql,
                (
                    name, search_mode, random_search_sample_num, user_code_path,
                    user_params_dict_name, hparams_space, start_time, end_time, status
                )
            )
            self.conn.commit()
            return True
        except self.conn.Error as e:
            self.conn.rollback()
            logger.error(f"插入实验记录（{name}）时数据库操作错误：{str(e)}", exc_info=True)
            return False
        except Exception as e:
            self.conn.rollback()
            logger.error(f"插入实验记录（{name}）时发生未知错误：{str(e)}", exc_info=True)
            return False

    # 删除所有实验记录
    def delete_all_experiment(self) -> bool:
        sql = "DELETE FROM Experiment"
        try:
            self.cursor.execute(sql)
            self.conn.commit()
            logger.info("所有实验记录已删除")
            return True
        except self.conn.Error as e:
            self.conn.rollback()
            logger.error(f"删除实验记录时数据库错误：{str(e)}", exc_info=True)
            return False
        except Exception as e:
            self.conn.rollback()
            logger.error(f"删除实验记录时未知错误：{str(e)}", exc_info=True)
            return False

    # 按名称删除实验记录
    def delete_experiment_by_name(self, name) -> bool:
        sql = "DELETE FROM Experiment WHERE name = ?"
        try:
            self.cursor.execute(sql, (name,))
            if self.cursor.rowcount == 0:
                logger.warning(f"删除实验记录失败：未找到名称为{name}的实验")
                return False
            self.conn.commit()
            logger.info(f"实验记录（{name}）已删除")
            return True
        except self.conn.Error as e:
            self.conn.rollback()
            logger.error(f"删除实验记录（{name}）时数据库错误：{str(e)}", exc_info=True)
            return False
        except Exception as e:
            self.conn.rollback()
            logger.error(f"删除实验记录（{name}）时未知错误：{str(e)}", exc_info=True)
            return False

    # todo 实现动态sql
    # 查询所有实验记录
    def select_all_experiment(self) -> List:
        sql = "SELECT * FROM Experiment ORDER BY start_time DESC"
        try:
            self.cursor.execute(sql)
            columns = [desc[0] for desc in self.cursor.description]
            results = [dict(zip(columns, row)) for row in self.cursor.fetchall()]
            return results
        except self.conn.Error as e:
            logger.error(f"查询实验记录时数据库错误：{str(e)}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"查询实验记录时未知错误：{str(e)}", exc_info=True)
            return []

    # 按名称查询实验记录
    def select_experiment_by_name(self, name) -> List:
        sql = "SELECT * FROM Experiment WHERE name = ?"
        try:
            self.cursor.execute(sql, (name,))
            columns = [desc[0] for desc in self.cursor.description]
            result = self.cursor.fetchone()
            if not result:
                logger.info(f"未找到名称为{name}的实验记录")
                return []
            return [dict(zip(columns, result))]
        except self.conn.Error as e:
            logger.error(f"查询实验记录（{name}）时数据库错误：{str(e)}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"查询实验记录（{name}）时未知错误：{str(e)}", exc_info=True)
            return []

    # todo 实现动态sql
    # 按搜索模式查询实验记录
    def select_experiment_by_search_mode(self, search_mode) -> List:
        sql = "SELECT * FROM Experiment WHERE search_mode = ? ORDER BY start_time DESC"
        try:
            self.cursor.execute(sql, (search_mode,))
            columns = [desc[0] for desc in self.cursor.description]
            results = [dict(zip(columns, row)) for row in self.cursor.fetchall()]
            return results
        except self.conn.Error as e:
            logger.error(f"查询{search_mode}模式实验记录时数据库错误：{str(e)}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"查询{search_mode}模式实验记录时未知错误：{str(e)}", exc_info=True)
            return []

    # todo 实现动态sql
    # 按状态查询实验记录
    def select_experiment_by_status(self, status) -> List:
        sql = "SELECT * FROM Experiment WHERE status = ? ORDER BY start_time DESC"
        try:
            self.cursor.execute(sql, (status,))
            columns = [desc[0] for desc in self.cursor.description]
            results = [dict(zip(columns, row)) for row in self.cursor.fetchall()]
            return results
        except self.conn.Error as e:
            logger.error(f"查询{status}状态实验记录时数据库错误：{str(e)}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"查询{status}状态实验记录时未知错误：{str(e)}", exc_info=True)
            return []

    # 按名称查找并修改实验记录
    def update_experiment_by_name(self, name, **kwargs) -> bool:
        if not kwargs:
            logger.warning("更新实验记录失败：未指定更新字段")
            return False

        valid_fields = ['search_mode', 'random_search_sample_num', 'user_code_path',
                        'user_params_dict_name', 'hparams_space', 'start_time',
                        'end_time', 'status']

        update_fields = []
        update_values = []
        for key, value in kwargs.items():
            if key not in valid_fields:
                logger.warning(f"忽略无效字段：{key}")
                continue
            update_fields.append(f"{key} = ?")
            update_values.append(value)

        if not update_fields:
            logger.warning("更新实验记录失败：无有效更新字段")
            return False

        sql = f"UPDATE Experiment SET {', '.join(update_fields)} WHERE name = ?"
        update_values.append(name)

        try:
            self.cursor.execute(sql, tuple(update_values))
            if self.cursor.rowcount == 0:
                logger.warning(f"更新实验记录失败：未找到名称为{name}的实验")
                return False
            self.conn.commit()
            logger.info(f"实验记录（{name}）已更新")
            return True
        except self.conn.Error as e:
            self.conn.rollback()
            logger.error(f"更新实验记录（{name}）时数据库错误：{str(e)}", exc_info=True)
            return False
        except Exception as e:
            self.conn.rollback()
            logger.error(f"更新实验记录（{name}）时未知错误：{str(e)}", exc_info=True)
            return False

    # 重命名实验
    def rename_experiment(self, old_name, new_name) -> bool:
        if not new_name:
            logger.warning("重命名失败：新名称不能为空")
            return False
        if self.select_experiment_by_name(new_name):
            logger.warning(f"重命名失败：新名称「{new_name}」已存在")
            return False

        sql = "UPDATE Experiment SET name = ? WHERE name = ?"
        try:
            self.cursor.execute(sql, (new_name, old_name))
            if self.cursor.rowcount == 0:
                logger.warning(f"重命名失败：未找到原名称「{old_name}」的实验")
                return False
            self.conn.commit()
            logger.info(f"实验名称从「{old_name}」改为「{new_name}」")
            return True
        except self.conn.Error as e:
            self.conn.rollback()
            logger.error(f"重命名实验失败：{str(e)}", exc_info=True)
            return False

    """
    TEST操作
    """

    # 新增测试记录
    def insert_test(self, experiment_id, hparams, start_time, end_time, status) -> bool:
        sql = """
            INSERT INTO Test (
                experiment_id, hparams, start_time, end_time, status
            ) 
            VALUES (?, ?, ?, ?, ?)
        """

        try:
            self.cursor.execute(
                sql,
                (
                    experiment_id, hparams, start_time, end_time, status
                )
            )
            self.conn.commit()
            return True
        except self.conn.Error as e:
            self.conn.rollback()
            logger.error(
                f"插入测试记录（关联实验ID：{experiment_id}）时数据库操作错误：{str(e)}",
                exc_info=True
            )
            return False
        except Exception as e:
            self.conn.rollback()
            logger.error(
                f"插入测试记录（关联实验ID：{experiment_id}）时发生未知错误：{str(e)}",
                exc_info=True
            )
            return False

    # 按id删除测试记录
    def delete_test_by_id(self, id) -> bool:
        sql = "DELETE FROM Test WHERE id = ?"
        try:
            self.cursor.execute(sql, (id,))
            if self.cursor.rowcount == 0:
                logger.warning(f"删除测试记录失败：未找到ID为{id}的测试")
                return False
            self.conn.commit()
            logger.info(f"测试记录（ID：{id}）已删除")
            return True
        except self.conn.Error as e:
            self.conn.rollback()
            logger.error(f"删除测试记录（ID：{id}）时数据库错误：{str(e)}", exc_info=True)
            return False
        except Exception as e:
            self.conn.rollback()
            logger.error(f"删除测试记录（ID：{id}）时未知错误：{str(e)}", exc_info=True)
            return False

    # todo 动态sql
    # 按实验id查询测试记录
    def select_test_by_experiment_id(self, experiment_id) -> List:
        sql = "SELECT * FROM Test WHERE experiment_id = ? ORDER BY start_time DESC"
        try:
            self.cursor.execute(sql, (experiment_id,))
            columns = [desc[0] for desc in self.cursor.description]
            results = [dict(zip(columns, row)) for row in self.cursor.fetchall()]
            return results
        except self.conn.Error as e:
            logger.error(f"查询实验ID{experiment_id}的测试记录时数据库错误：{str(e)}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"查询实验ID{experiment_id}的测试记录时未知错误：{str(e)}", exc_info=True)
            return []

    # 按id查询测试记录
    def select_test_by_id(self, id) -> List:
        sql = "SELECT * FROM Test WHERE id = ?"
        try:
            self.cursor.execute(sql, (id,))
            columns = [desc[0] for desc in self.cursor.description]
            result = self.cursor.fetchone()
            if not result:
                logger.info(f"未找到ID为{id}的测试记录")
                return []
            return [dict(zip(columns, result))]
        except self.conn.Error as e:
            logger.error(f"查询测试记录（ID：{id}）时数据库错误：{str(e)}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"查询测试记录（ID：{id}）时未知错误：{str(e)}", exc_info=True)
            return []

    # 按id查询并修改测试记录
    def update_test_by_id(self, id, **kwargs) -> bool:
        if not kwargs:
            logger.warning("更新测试记录失败：未指定更新字段")
            return False

        valid_fields = ['experiment_id', 'hparams', 'start_time', 'end_time', 'status']

        update_fields = []
        update_values = []
        for key, value in kwargs.items():
            if key not in valid_fields:
                logger.warning(f"忽略无效字段：{key}")
                continue
            update_fields.append(f"{key} = ?")
            update_values.append(value)

        if not update_fields:
            logger.warning("更新测试记录失败：无有效更新字段")
            return False

        sql = f"UPDATE Test SET {', '.join(update_fields)} WHERE id = ?"
        update_values.append(id)

        try:
            self.cursor.execute(sql, tuple(update_values))
            if self.cursor.rowcount == 0:
                logger.warning(f"更新测试记录失败：未找到ID为{id}的测试")
                return False
            self.conn.commit()
            logger.info(f"测试记录（ID：{id}）已更新")
            return True
        except self.conn.Error as e:
            self.conn.rollback()
            logger.error(f"更新测试记录（ID：{id}）时数据库错误：{str(e)}", exc_info=True)
            return False
        except Exception as e:
            self.conn.rollback()
            logger.error(f"更新测试记录（ID：{id}）时未知错误：{str(e)}", exc_info=True)
            return False

    """
    METRIC操作
    """

    # 新增指标记录
    def insert_metric(self, test_id, metric_name, metric_value, record_time) -> bool:
        sql = """
            INSERT INTO Metric (
                test_id, metric_name, metric_val, record_time
            ) 
            VALUES (?, ?, ?, ?)
        """

        try:
            self.cursor.execute(
                sql,
                (
                    test_id, metric_name, metric_value, record_time
                )
            )
            self.conn.commit()
            return True
        except self.conn.Error as e:
            self.conn.rollback()
            logger.error(
                f"插入指标记录（测试ID：{test_id}，指标名：{metric_name}）时数据库错误：{str(e)}",
                exc_info=True
            )
            return False
        except Exception as e:
            self.conn.rollback()
            logger.error(
                f"插入指标记录（测试ID：{test_id}，指标名：{metric_name}）时未知错误：{str(e)}",
                exc_info=True
            )
            return False

    # 按测试id和指标名称查询所有指标记录
    def select_metric_by_test_id_and_metric_name(self, test_id, metric_name) -> List:
        sql = """
            SELECT * FROM Metric 
            WHERE test_id = ? AND metric_name = ?
            ORDER BY epoch ASC, record_time ASC
        """

        try:
            self.cursor.execute(sql, (test_id, metric_name))
            # 先判断是否有结果，再处理列元数据
            results = self.cursor.fetchall()
            if not results:
                logger.info(f"测试ID {test_id} 未查询到「{metric_name}」指标记录")
                return []

            # 提取列名，转为字典列表
            columns = [desc[0] for desc in self.cursor.description]
            metric_list = [dict(zip(columns, row)) for row in results]

            logger.info(f"测试ID {test_id} 共查询到「{metric_name}」指标记录 {len(metric_list)} 条")
            return metric_list

        except self.conn.Error as e:
            logger.error(
                f"查询测试ID {test_id} 的「{metric_name}」指标记录时数据库错误：{str(e)}",
                exc_info=True
            )
            return []
        except Exception as e:
            logger.error(
                f"查询测试ID {test_id} 的「{metric_name}」指标记录时未知错误：{str(e)}",
                exc_info=True
            )
            return []


db_manager = SQLiteManager()
