import json
import sqlite3
from datetime import datetime
from typing import List, Optional, Any
from light_tuner.utils.logger import logger


class SQLiteManager:
    def __init__(self, path):
        self.path = path
        self.conn = self._get_connection()
        self.create_tables()

    # Returns the database connection
    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self.path,
            check_same_thread=False,
            timeout=10
        )
        # Enable WAL mode for concurrent access
        conn.execute("PRAGMA journal_mode=WAL")
        # Enable foreign key constraints
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    # Creates table structures
    def create_tables(self) -> None:
        cursor = self.conn.cursor()

        try:
            # 1. Experiment table
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

            # 2. Test table (execution records for a single set of parameters)
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

            # 3. Metric table
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
            # 4. Create index
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_metric_test_name ON Metric (test_id, metric_name);")
            # Commit transaction
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to initialize database tables: {e}", exc_info=True)
        finally:
            cursor.close()

    # Closes the database connection
    def close(self) -> None:
        self.conn.close()
        logger.info("Database connection closed")

    """
    EXPERIMENT Operations
    """

    # Inserts an experiment record
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
            logger.error(f"Database error while inserting experiment record ({name}): {str(e)}", exc_info=True)
            return False
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Unexpected error while inserting experiment record ({name}): {str(e)}", exc_info=True)
            return False
        finally:
            cursor.close()

    # Query experiments by name, mode, and status (supports dynamic conditions + sorting)
    def select_experiments(
            self,
            name: Optional[str] = None,
            status: Optional[str] = None,
            search_mode: Optional[str] = None,
            sort_by: str = "name",  # Default sorting field
            sort_order: str = "DESC"  # Default sorting order (DESC), optional: ASC
    ) -> List:
        # 1. Initialize condition and parameter lists
        conditions = []
        params = []

        # 2. Null check: Add conditions only if parameters are provided
        if name:
            conditions.append("name LIKE ?")
            params.append(f"%{name}%")
        if status:
            conditions.append("status = ?")
            params.append(status)
        if search_mode:
            conditions.append("search_mode = ?")
            params.append(search_mode)

        # 3. Validate sort order to prevent SQL injection
        valid_sort_orders = ["ASC", "DESC"]
        sort_order = sort_order.strip().upper()
        if sort_order not in valid_sort_orders:
            logger.warning(f"Invalid sort order: {sort_order}, defaulting to DESC")
            sort_order = "DESC"

        # 4. Validate sort field to prevent SQL injection
        valid_sort_fields = ["start_time", "name"]
        if sort_by not in valid_sort_fields:
            logger.warning(f"Invalid sort field: {sort_by}, defaulting to start_time")
            sort_by = "start_time"

        # 5. Join SQL statement
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
            logger.error(f"Database error while querying experiments: {str(e)}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"Unexpected error while querying experiments: {str(e)}", exc_info=True)
            return []
        finally:
            cursor.close()

    # Find and update an experiment record by name
    def update_experiment_by_name(self, name, **kwargs) -> bool:
        if not kwargs:
            logger.warning("Failed to update experiment: No fields specified")
            return False

        valid_fields = ['search_mode', 'random_search_sample_num', 'user_code_path',
                        'user_params_dict_name', 'hparams_space', 'start_time',
                        'end_time', 'status']

        update_fields = []
        update_values = []
        for key, value in kwargs.items():
            if key not in valid_fields:
                logger.warning(f"Ignoring invalid field: {key}")
                continue
            update_fields.append(f"{key} = ?")
            update_values.append(value)

        if not update_fields:
            logger.warning("Failed to update experiment: No valid fields found")
            return False

        sql = f"UPDATE Experiment SET {', '.join(update_fields)} WHERE name = ?"
        update_values.append(name)

        cursor = self.conn.cursor()

        try:
            cursor.execute(sql, tuple(update_values))
            if cursor.rowcount == 0:
                logger.warning(f"Failed to update experiment: Experiment with name '{name}' not found")
                return False
            self.conn.commit()
            return True
        except self.conn.Error as e:
            self.conn.rollback()
            logger.error(f"Database error while updating experiment ({name}): {str(e)}", exc_info=True)
            return False
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Unexpected error while updating experiment ({name}): {str(e)}", exc_info=True)
            return False
        finally:
            cursor.close()

    """
    TEST Operations
    """

    # Add a new test record
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
                f"Database error while inserting test record (Exp ID: {experiment_id}): {str(e)}",
                exc_info=True
            )
            return None
        except Exception as e:
            self.conn.rollback()
            logger.error(
                f"Unexpected error while inserting test record (Exp ID: {experiment_id}): {str(e)}",
                exc_info=True
            )
            return None
        finally:
            cursor.close()

    # Query test records by experiment id
    def select_test_by_experiment_id(self, experiment_id) -> List:
        sql = "SELECT * FROM Test WHERE experiment_id = ? ORDER BY start_time DESC"
        cursor = self.conn.cursor()
        try:
            cursor.execute(sql, (experiment_id,))
            columns = [desc[0] for desc in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return results
        except self.conn.Error as e:
            logger.error(f"Database error while querying tests for Exp ID {experiment_id}: {str(e)}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"Unexpected error while querying tests for Exp ID {experiment_id}: {str(e)}", exc_info=True)
            return []
        finally:
            cursor.close()

    # Query test record by id
    def select_test_by_id(self, id) -> List:
        sql = "SELECT * FROM Test WHERE id = ?"
        cursor = self.conn.cursor()
        try:
            cursor.execute(sql, (id,))
            columns = [desc[0] for desc in cursor.description]
            result = cursor.fetchone()
            if not result:
                logger.info(f"Test record with ID {id} not found")
                return []
            return [dict(zip(columns, result))]
        except self.conn.Error as e:
            logger.error(f"Database error while querying test record (ID: {id}): {str(e)}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"Unexpected error while querying test record (ID: {id}): {str(e)}", exc_info=True)
            return []
        finally:
            cursor.close()

    # Find and update a test record by id
    def update_test_by_id(self, id, **kwargs) -> bool:
        if not kwargs:
            logger.warning("Failed to update test record: No fields specified")
            return False

        valid_fields = ['experiment_id', 'hparams', 'start_time', 'end_time', 'status']

        update_fields = []
        update_values = []
        for key, value in kwargs.items():
            if key not in valid_fields:
                logger.warning(f"Ignoring invalid field: {key}")
                continue
            update_fields.append(f"{key} = ?")
            update_values.append(value)

        if not update_fields:
            logger.warning("Failed to update test record: No valid fields found")
            return False

        sql = f"UPDATE Test SET {', '.join(update_fields)} WHERE id = ?"
        update_values.append(id)
        cursor = self.conn.cursor()
        try:
            cursor.execute(sql, tuple(update_values))
            if cursor.rowcount == 0:
                logger.warning(f"Failed to update test record: Test with ID {id} not found")
                return False
            self.conn.commit()
            return True
        except self.conn.Error as e:
            self.conn.rollback()
            logger.error(f"Database error while updating test record (ID: {id}): {str(e)}", exc_info=True)
            return False
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Unexpected error while updating test record (ID: {id}): {str(e)}", exc_info=True)
            return False
        finally:
            cursor.close()

    """
    METRIC Operations
    """

    # Add a new metric record
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
        Supports multi-dimensional metric storage matching the optimized table structure.
        :param test_id: Test task ID
        :param metric_name: Name of the metric (e.g., 'loss', 'confusion_matrix')
        :param metric_val: Value (supports number, list, dict)
        :param epoch: Current epoch
        :param step: Current step (default: 0)
        :param data_type: Data type ('scalar', 'array', 'matrix', 'json')
        :param tag: Stage tag ('train', 'val', 'test')
        :param record_time: Time of recording
        """
        # --- 1. Data Pre-processing ---
        # Convert lists/dicts to JSON strings for TEXT field storage
        processed_val = metric_val
        if isinstance(metric_val, (list, dict)):
            try:
                processed_val = json.dumps(metric_val)
            except Exception as e:
                logger.error(f"Failed to serialize metric {metric_name}: {e}")
                return False
        else:
            # Ensure scalar is stored as string to match TEXT type
            processed_val = str(metric_val)

        # --- 2. SQL Execution ---
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
                f"Database error while inserting metric (Test ID: {test_id}, Name: {metric_name}): {str(e)}"
            )
            return False
        except Exception as e:
            self.conn.rollback()
            logger.error(
                f"Unexpected error while inserting metric (Test ID: {test_id}, Name: {metric_name}): {str(e)}",
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
        Batch query metrics based on multiple test IDs.
        :param test_id_list: List of Test IDs (Required)
        :param metric_name: Metric name filter
        :param tag: Stage filter
        :param data_type: Type filter
        """
        if not test_id_list:
            return []

        # 1. Dynamically generate placeholders for IN clause
        placeholders = ', '.join(['?'] * len(test_id_list))

        # 2. Build base SQL using IN syntax
        sql = f"SELECT * FROM Metric WHERE test_id IN ({placeholders})"
        params = list(test_id_list)

        # 3. Dynamically append other filtering conditions
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
            # 4. Execute query
            cursor.execute(sql, tuple(params))
            results = cursor.fetchall()

            # Convert to list of dictionaries
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in results]
        except Exception as e:
            logger.error(f"Failed to batch query metrics [TestIDs: {test_id_list}]: {e}")
            return []
        finally:
            cursor.close()