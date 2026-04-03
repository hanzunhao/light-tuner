import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Any
from light_tuner.utils.logger import logger


class SQLiteManager:
    def __init__(self,path=None):
        try:
            # --- 方案 A：跟随入口文件 (脚本模式) ---
            # sys.argv[0] 获取当前启动的脚本绝对路径（例如：D:/project/train.py）
            # .parent 获取该脚本所在的文件夹
            # 优点：数据库永远生成在用户的代码目录下，方便用户直接查看和拷贝
            run_dir = Path(os.path.abspath(sys.argv[0])).parent
            self.path = run_dir / "light_tuner.db"
        except ImportError:
            # --- 方案 B：跟随当前工作目录 (交互式/异常兜底) ---
            # 当在 Jupyter Notebook、嵌入式环境或 sys.argv 失效时触发
            # os.getcwd() 获取用户当前终端所在的目录
            # 优点：保证程序在任何环境下都能找到一个合法的路径创建数据库
            self.path = Path(os.getcwd()) / "light_tuner.db"

        # # 获取包路径并拼接数据库文件名称
        # try:
        #     package_root = importlib_files("light_tuner")
        #     self.path = Path(package_root) / "light_tuner.db"
        # except ImportError:
        #     from pkg_resources import resource_filename
        #     package_root = resource_filename("light_tuner", "")
        #     self.path = Path(package_root) / "light_tuner.db"

        self.conn = self._get_connection()
        self.create_tables()

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
        cursor = self.conn.cursor()

        try:
            # 1. 实验表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Experiment (
                    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                    name VARCHAR(50) UNIQUE NOT NULL,
                    search_mode VARCHAR(20) NOT NULL CHECK(search_mode IN ('grid', 'random')),
                    random_search_sample_num INTEGER,
                    user_code_path VARCHAR(255) NOT NULL,
                    user_params_dict_name VARCHAR(100) NOT NULL,
                    hparams_space TEXT NOT NULL,
                    start_time DATETIME,
                    end_time DATETIME,
                    status VARCHAR(10) NOT NULL CHECK(status IN ('running', 'finished', 'failed', 'paused')) DEFAULT 'running'
                );
            """)

            # 2. 测试表（单组参数执行记录）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Test (
                    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                    experiment_id INTEGER NOT NULL,
                    hparams TEXT NOT NULL,
                    start_time DATETIME,
                    end_time DATETIME,
                    status VARCHAR(10) NOT NULL CHECK(status IN ('running', 'finished', 'failed', 'paused')) DEFAULT 'running',
                    FOREIGN KEY (experiment_id) REFERENCES Experiment(id)  ON DELETE CASCADE  ON UPDATE CASCADE
                );
            """)

            # 3. 指标表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Metric (
                    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                    epoch INTEGER NOT NULL,
                    step INTEGER DEFAULT 0,
                    test_id INTEGER NOT NULL,
                    metric_name VARCHAR(50) NOT NULL,
                    metric_val TEXT NOT NULL,
                    data_type VARCHAR(10) NOT NULL CHECK(data_type IN ('scalar', 'array', 'matrix', 'json')),
                    tag VARCHAR(10) DEFAULT 'default',
                    record_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (test_id) REFERENCES Test(id) ON DELETE CASCADE ON UPDATE CASCADE
                );
            """)
            # 4.创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_metric_test_name ON Metric (test_id, metric_name);")
            # 提交事务
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            logger.error(f"初始化数据库表结构失败: {e}", exc_info=True)
        finally:
            cursor.close()

    # 关闭数据库连接
    def close(self) -> None:
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
        cursor = self.conn.cursor()
        try:
            cursor.execute(
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
        finally:
            cursor.close()

    # 按名称、搜索模式、状态查询实验记录（支持动态条件 + 升降序控制）
    def select_experiments(
            self,
            name: Optional[str] = None,
            status: Optional[str] = None,
            search_mode: Optional[str] = None,
            sort_by: str = "name",  # 排序字段，默认按start_time
            sort_order: str = "DESC"  # 排序方向，默认降序（DESC），可选 ASC（升序）
    ) -> List:
        # 1. 初始化条件列表和参数列表
        conditions = []
        params = []

        # 2. 非空检查：只有参数不为空时，才添加对应的查询条件
        if name:
            conditions.append("name LIKE ?")
            params.append(f"%{name}%")
        if status:
            conditions.append("status = ?")
            params.append(status)
        if search_mode:
            conditions.append("search_mode = ?")
            params.append(search_mode)

        # 3. 校验排序方向（防止传入非法值导致SQL错误）
        valid_sort_orders = ["ASC", "DESC"]
        # 统一转为大写，兼容小写输入（如 "asc" "desc"）
        sort_order = sort_order.strip().upper()
        if sort_order not in valid_sort_orders:
            logger.warning(f"无效的排序方向：{sort_order}，已自动转为默认值 DESC")
            sort_order = "DESC"

        # 4. 校验排序字段（限制可选字段，防止SQL注入/非法字段）
        valid_sort_fields = ["start_time", "name"]
        if sort_by not in valid_sort_fields:
            logger.warning(f"无效的排序字段：{sort_by}，已自动转为默认值 name")
            sort_by = "start_time"

        # 5. 拼接SQL语句
        if conditions:
            sql = f"""
                SELECT * FROM Experiment 
                WHERE {' AND '.join(conditions)} 
                ORDER BY {sort_by} {sort_order}
            """
        else:
            sql = f"""
                SELECT * FROM Experiment 
                ORDER BY {sort_by} {sort_order}
            """
        cursor = self.conn.cursor()

        try:
            cursor.execute(sql, tuple(params))
            columns = [desc[0] for desc in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return results
        except self.conn.Error as e:
            logger.error(f"查询实验记录时数据库错误：{str(e)}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"查询实验记录时未知错误：{str(e)}", exc_info=True)
            return []
        finally:
            cursor.close()

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

        cursor = self.conn.cursor()

        try:
            cursor.execute(sql, tuple(update_values))
            if cursor.rowcount == 0:
                logger.warning(f"更新实验记录失败：未找到名称为{name}的实验")
                return False
            self.conn.commit()
            return True
        except self.conn.Error as e:
            self.conn.rollback()
            logger.error(f"更新实验记录（{name}）时数据库错误：{str(e)}", exc_info=True)
            return False
        except Exception as e:
            self.conn.rollback()
            logger.error(f"更新实验记录（{name}）时未知错误：{str(e)}", exc_info=True)
            return False
        finally:
            cursor.close()

    """
    TEST操作
    """

    # 新增测试记录
    def insert_test(self, experiment_id, hparams, start_time, end_time, status) -> Optional[int]:
        sql = """
            INSERT INTO Test (
                experiment_id, hparams, start_time, end_time, status
            ) 
            VALUES (?, ?, ?, ?, ?)
        """

        cursor = self.conn.cursor()

        try:
            cursor.execute(
                sql,
                (
                    experiment_id, hparams, start_time, end_time, status
                )
            )
            self.conn.commit()
            return cursor.lastrowid
        except self.conn.Error as e:
            self.conn.rollback()
            logger.error(
                f"插入测试记录（关联实验ID：{experiment_id}）时数据库操作错误：{str(e)}",
                exc_info=True
            )
            return None
        except Exception as e:
            self.conn.rollback()
            logger.error(
                f"插入测试记录（关联实验ID：{experiment_id}）时发生未知错误：{str(e)}",
                exc_info=True
            )
            return None
        finally:
            cursor.close()

    # 按实验id查询测试记录
    def select_test_by_experiment_id(self, experiment_id) -> List:
        sql = "SELECT * FROM Test WHERE experiment_id = ? ORDER BY start_time DESC"
        cursor = self.conn.cursor()
        try:
            cursor.execute(sql, (experiment_id,))
            columns = [desc[0] for desc in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return results
        except self.conn.Error as e:
            logger.error(f"查询实验ID{experiment_id}的测试记录时数据库错误：{str(e)}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"查询实验ID{experiment_id}的测试记录时未知错误：{str(e)}", exc_info=True)
            return []
        finally:
            cursor.close()

    # 按id查询测试记录
    def select_test_by_id(self, id) -> List:
        sql = "SELECT * FROM Test WHERE id = ?"
        cursor = self.conn.cursor()
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
        finally:
            cursor.close()

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
        cursor = self.conn.cursor()
        try:
            cursor.execute(sql, tuple(update_values))
            if cursor.rowcount == 0:
                logger.warning(f"更新测试记录失败：未找到ID为{id}的测试")
                return False
            self.conn.commit()
            return True
        except self.conn.Error as e:
            self.conn.rollback()
            logger.error(f"更新测试记录（ID：{id}）时数据库错误：{str(e)}", exc_info=True)
            return False
        except Exception as e:
            self.conn.rollback()
            logger.error(f"更新测试记录（ID：{id}）时未知错误：{str(e)}", exc_info=True)
            return False
        finally:
            cursor.close()

    """
    METRIC操作
    """

    # 新增指标记录
    def insert_metric(
            self,
            test_id: int,
            metric_name: str,
            metric_val: Any,
            epoch: int,
            step: int = 0,
            data_type: str = 'scalar',
            tag: str = 'train',
            record_time: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ) -> bool:
        """
        匹配优化后的表结构，支持多维度指标存储
        :param test_id: 测试任务ID
        :param metric_name: 指标名称 (如 'loss', 'confusion_matrix')
        :param metric_val: 指标值 (支持数字、列表、字典)
        :param epoch: 当前轮次
        :param step: 当前步数 (默认为0)
        :param data_type: 数据类型 ('scalar', 'array', 'matrix', 'json')
        :param tag: 阶段标记 ('train', 'val', 'test')
        :param record_time: 记录时间
        """
        # --- 1. 数据预处理 ---
        # 如果 metric_val 是列表或字典，自动转换为 JSON 字符串存入 TEXT 字段
        processed_val = metric_val
        if isinstance(metric_val, (list, dict)):
            try:
                processed_val = json.dumps(metric_val)
            except Exception as e:
                logger.error(f"序列化指标 {metric_name} 失败: {e}")
                return False
        else:
            # 确保标量也转为字符串存储，匹配 TEXT 类型
            processed_val = str(metric_val)

        # --- 2. SQL 执行 ---
        sql = """
                INSERT INTO Metric (
                    test_id, epoch, step, metric_name, metric_val, data_type, tag, record_time
                ) 
                VALUES (?, ?, ?, ?, ?, ?, ? ,?)
            """
        cursor = self.conn.cursor()
        try:
            cursor.execute(sql, (test_id, epoch, step, metric_name, processed_val, data_type, tag, record_time))
            self.conn.commit()
            return True
        except self.conn.Error as e:
            self.conn.rollback()
            logger.error(
                f"插入指标记录失败（测试ID：{test_id}，指标名：{metric_name}）数据库错误：{str(e)}"
            )
            return False
        except Exception as e:
            self.conn.rollback()
            logger.error(
                f"插入指标记录失败（测试ID：{test_id}，指标名：{metric_name}）未知错误：{str(e)}",
                exc_info=True
            )
            return False
        finally:
            cursor.close()

    def select_metrics(
            self,
            test_id_list: List[int],
            metric_name: Optional[str] = None,
            tag: Optional[str] = None,
            data_type: Optional[str] = None
    ) -> List[dict]:
        """
        根据多个测试ID批量查询指标记录
        :param test_id_list: 测试ID列表 (必填)
        :param metric_name: 指标名称
        :param tag: 阶段
        :param data_type: 类型
        """
        if not test_id_list:
            return []

        # 1. 动态生成 IN 子句的占位符
        placeholders = ', '.join(['?'] * len(test_id_list))

        # 2. 构建基础 SQL，使用 IN 语法
        sql = f"SELECT * FROM Metric WHERE test_id IN ({placeholders})"
        params = list(test_id_list)

        # 3. 动态拼接其他过滤条件
        if metric_name:
            sql += " AND metric_name = ?"
            params.append(metric_name)
        if tag:
            sql += " AND tag = ?"
            params.append(tag)
        if data_type:
            sql += " AND data_type = ?"
            params.append(data_type)
        cursor = self.conn.cursor()

        try:
            # 4. 执行查询
            cursor.execute(sql, tuple(params))
            results = cursor.fetchall()

            # 转换为字典列表
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in results]
        except Exception as e:
            logger.error(f"批量查询指标失败 [TestIDs: {test_id_list}]: {e}")
            return []
        finally:
            cursor.close()


db_manager = SQLiteManager()
