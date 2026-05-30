"""结构化记忆数据存储 — 支持 MySQL（生产）与 SQLite（本地开发）

连接优先级: 构造参数 > 环境变量 > 默认值
  环境变量: DB_TYPE, DB_HOST, DB_PORT, DB_USER, DB_PASSWORD,
            DB_DATABASE, DB_TABLE_PREFIX

生产推荐: pip install pymysql  → 自动使用 MySQL
开发模式: 默认 SQLite，零依赖
"""

import json
import os
from datetime import datetime
from typing import Optional

from ..base import MemoryItem


# ── 尝试导入 pymysql（决定使用 MySQL 还是 SQLite）─────────────
try:
    import pymysql

    PYMYSQL_AVAILABLE = True
except ImportError:
    PYMYSQL_AVAILABLE = False


def _load_env_str(key: str, default: str) -> str:
    return os.getenv(key, default)


def _load_env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except (ValueError, TypeError):
        return default


class DocumentStore:
    """
    文档存储。

    自动选择后端：
      - MySQL（生产）：pip install pymysql，设置 DB_HOST 等环境变量
      - SQLite（本地兜底）：零配置

    相同接口，无缝切换。
    """

    def __init__(
        self,
        db_path: str = "memory.db",              #? 数据库文件路径（默认 memory.db）
        db_type: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
        table_prefix: str = "", 
    ):
        self.table_prefix = table_prefix            #? 表前缀
        self._table = f"{table_prefix}memories"     #? 文档记忆表名

        # 读取环境变量
        env_type = _load_env_str("DB_TYPE", "mysql")   #? 数据库类型（默认 MySQL，无 pymysql 时自动降级 SQLite）
        self.db_type = db_type or env_type

        # ── MySQL 模式 ────────────────────────────────────────
        if self._use_mysql():
            if not PYMYSQL_AVAILABLE:
                # 未显式指定 MySQL 时自动降级到 SQLite
                if db_type is None and _load_env_str("DB_TYPE", "mysql") == "mysql":
                    self.db_type = "sqlite"
                    import sqlite3
                    self._sqlite3 = sqlite3
                    self.db_path = db_path
                    self._init_db()
                    return
                raise ImportError(
                    "MySQL 模式需要 pymysql: pip install pymysql"
                )
            self._host = host or _load_env_str("MYSQL_HOST", "localhost")
            self._port = port or _load_env_int("MYSQL_PORT", 3306)
            self._user = user or _load_env_str("MYSQL_USER", "root")
            self._password = password or _load_env_str("MYSQL_PASSWORD", "")
            self._database = database or _load_env_str("MYSQL_DATABASE", "hello_agents")
            self._create_database_if_not_exists()
            self._init_db()

        # ── SQLite 模式 ──────────────────────────────────────
        else:
            import sqlite3

            self._sqlite3 = sqlite3
            self.db_path = db_path
            self._init_db()

    # ── 后端检测 ──────────────────────────────────────────────

    def _use_mysql(self) -> bool:
        return self.db_type.lower() == "mysql"

    # ── 建表 ──────────────────────────────────────────────────

    def _create_database_if_not_exists(self):
        """MySQL: 确保数据库存在"""
        conn = pymysql.connect(
            host=self._host,
            port=self._port,
            user=self._user,
            password=self._password,
            charset="utf8mb4",
        )
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{self._database}` "
                    f"DEFAULT CHARACTER SET utf8mb4"
                )
            conn.commit()
        finally:
            conn.close()

    def _init_db(self):
        if self._use_mysql():
            self._init_mysql()
        else:
            self._init_sqlite()

    def _table_sql(self) -> str:
        return (
            f"CREATE TABLE IF NOT EXISTS `{self._table}` ("
            f"  id VARCHAR(32) PRIMARY KEY,"
            f"  content TEXT NOT NULL,"
            f"  memory_type VARCHAR(32) NOT NULL DEFAULT 'working',"
            f"  user_id VARCHAR(128) DEFAULT '',"
            f"  session_id VARCHAR(128) DEFAULT '',"
            f"  importance FLOAT DEFAULT 0.5,"
            f"  timestamp VARCHAR(32) NOT NULL,"
            f"  metadata TEXT"
            f")"
        )

    def _init_mysql(self):
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(self._table_sql())
                # MySQL 不支持 CREATE INDEX IF NOT EXISTS，用 try-except 容错
                for col in ("memory_type", "session_id"):
                    try:
                        cur.execute(
                            f"CREATE INDEX idx_{self._table}_{col} "
                            f"ON `{self._table}`({col})"
                        )
                    except Exception:
                        pass  # 索引已存在，忽略
            conn.commit()
        finally:
            conn.close()

    def _init_sqlite(self):
        conn = self._sqlite3.connect(self.db_path)
        try:
            conn.execute(self._table_sql())
            conn.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{self._table}_type "
                f"ON `{self._table}`(memory_type)"
            )
            conn.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{self._table}_session "
                f"ON `{self._table}`(session_id)"
            )
            conn.commit()
        finally:
            conn.close()

    # ── 连接管理 ──────────────────────────────────────────────

    def _connect(self):
        if self._use_mysql():
            return pymysql.connect(
                host=self._host,
                port=self._port,
                user=self._user,
                password=self._password,
                database=self._database,
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
            )
        return self._sqlite3.connect(self.db_path)

    # ── CRUD ──────────────────────────────────────────────────

    def insert(self, item: MemoryItem) -> str:
        conn = self._connect()
        try:
            self._execute(
                conn,
                f"INSERT INTO `{self._table}` "
                f"(id, content, memory_type, user_id, session_id, "
                f" importance, timestamp, metadata) "
                f"VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    item.id,
                    item.content,
                    item.memory_type,
                    item.user_id,
                    item.session_id,
                    item.importance,
                    item.timestamp.isoformat(),
                    json.dumps(item.metadata, ensure_ascii=False),
                ),
            )
            return item.id
        finally:
            conn.close()

    def fetch(self, memory_id: str) -> Optional[MemoryItem]:
        conn = self._connect()
        try:
            row = self._fetch_one(
                conn,
                f"SELECT * FROM `{self._table}` WHERE id = %s",
                (memory_id,),
            )
            return self._row_to_item(row) if row else None
        finally:
            conn.close()

    def search(
        self,
        memory_type: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[MemoryItem]:
        conn = self._connect()
        try:
            clauses = []
            params = []

            if memory_type:
                clauses.append("memory_type = %s")
                params.append(memory_type)
            if user_id:
                clauses.append("user_id = %s")
                params.append(user_id)
            if session_id:
                clauses.append("session_id = %s")
                params.append(session_id)

            where = " AND ".join(clauses) if clauses else "1=1"
            sql = (
                f"SELECT * FROM `{self._table}` WHERE {where} "
                f"ORDER BY timestamp DESC LIMIT %s OFFSET %s"
            )
            rows = self._fetch_all(conn, sql, (*params, limit, offset))
            return [self._row_to_item(r) for r in rows if r]
        finally:
            conn.close()

    def update(self, memory_id: str, **fields) -> bool:
        allowed = {"content", "importance", "metadata"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return False

        if "metadata" in updates and isinstance(updates["metadata"], dict):
            updates["metadata"] = json.dumps(updates["metadata"], ensure_ascii=False)

        conn = self._connect()
        try:
            set_clause = ", ".join(f"`{k}` = %s" for k in updates)
            values = list(updates.values()) + [memory_id]
            affected = self._execute(
                conn,
                f"UPDATE `{self._table}` SET {set_clause} WHERE id = %s",
                values,
            )
            return affected > 0
        finally:
            conn.close()

    def delete(self, memory_id: str) -> bool:
        conn = self._connect()
        try:
            affected = self._execute(
                conn,
                f"DELETE FROM `{self._table}` WHERE id = %s",
                (memory_id,),
            )
            return affected > 0
        finally:
            conn.close()

    def clear(self, memory_type: Optional[str] = None) -> int:
        conn = self._connect()
        try:
            if memory_type:
                affected = self._execute(
                    conn,
                    f"DELETE FROM `{self._table}` WHERE memory_type = %s",
                    (memory_type,),
                )
            else:
                affected = self._execute(conn, f"DELETE FROM `{self._table}`")
            return affected
        finally:
            conn.close()

    def count(self, memory_type: Optional[str] = None) -> int:
        conn = self._connect()
        try:
            if memory_type:
                row = self._fetch_one(
                    conn,
                    f"SELECT COUNT(*) AS cnt FROM `{self._table}` WHERE memory_type = %s",
                    (memory_type,),
                )
            else:
                row = self._fetch_one(
                    conn, f"SELECT COUNT(*) AS cnt FROM `{self._table}`"
                )
            return row["cnt"] if row else 0
        finally:
            conn.close()

    def fetch_all(self, memory_type: Optional[str] = None) -> list[MemoryItem]:
        conn = self._connect()
        try:
            if memory_type:
                rows = self._fetch_all(
                    conn,
                    f"SELECT * FROM `{self._table}` WHERE memory_type = %s "
                    f"ORDER BY timestamp DESC",
                    (memory_type,),
                )
            else:
                rows = self._fetch_all(
                    conn,
                    f"SELECT * FROM `{self._table}` ORDER BY timestamp DESC",
                )
            return [self._row_to_item(r) for r in rows if r]
        finally:
            conn.close()

    # ── 新增: EpisodicMemory 需要的方法 ───────────────────────

    def fetch_recent(self, memory_type: str, since: str, limit: int = 100) -> list[MemoryItem]:
        """获取指定类型中某个时间戳之后的记忆"""
        conn = self._connect()
        try:
            rows = self._fetch_all(
                conn,
                f"SELECT * FROM `{self._table}` "
                f"WHERE memory_type = %s AND timestamp >= %s "
                f"ORDER BY timestamp DESC LIMIT %s",
                (memory_type, since, limit),
            )
            return [self._row_to_item(r) for r in rows if r]
        finally:
            conn.close()

    def delete_before(self, memory_type: str, before: str) -> int:
        """删除指定类型中某个时间戳之前的记忆"""
        conn = self._connect()
        try:
            affected = self._execute(
                conn,
                f"DELETE FROM `{self._table}` "
                f"WHERE memory_type = %s AND timestamp < %s",
                (memory_type, before),
            )
            return affected
        finally:
            conn.close()

    def delete_by_importance(self, memory_type: str, threshold: float) -> int:
        """删除指定类型中重要性低于阈值的记忆"""
        conn = self._connect()
        try:
            affected = self._execute(
                conn,
                f"DELETE FROM `{self._table}` "
                f"WHERE memory_type = %s AND importance < %s",
                (memory_type, threshold),
            )
            return affected
        finally:
            conn.close()

    # ── 底层执行（统一 MySQL %s 与 SQLite ? 占位符）──────────

    def _adapt_sql(self, sql: str) -> str:
        """将 MySQL 风格 %s 占位符转为 SQLite 的 ? 占位符"""
        if self._use_mysql():
            return sql
        return sql.replace("%s", "?")

    def _execute(self, conn, sql: str, params=None) -> int:
        sql = self._adapt_sql(sql)
        if self._use_mysql():
            with conn.cursor() as cur:
                affected = cur.execute(sql, params or ())
            conn.commit()
            return affected
        else:
            cur = conn.execute(sql, params or ())
            conn.commit()
            return cur.rowcount

    def _fetch_one(self, conn, sql: str, params=None):
        sql = self._adapt_sql(sql)
        if self._use_mysql():
            with conn.cursor() as cur:
                cur.execute(sql, params or ())
                return cur.fetchone()
        else:
            cur = conn.execute(sql, params or ())
            row = cur.fetchone()
            if row is None:
                return None
            # sqlite3 返回的是 sqlite3.Row，转为 dict
            return dict(row) if hasattr(row, "keys") else {
                "id": row[0],
                "content": row[1],
                "memory_type": row[2],
                "user_id": row[3],
                "session_id": row[4],
                "importance": row[5],
                "timestamp": row[6],
                "metadata": row[7],
            }

    def _fetch_all(self, conn, sql: str, params=None) -> list[dict]:
        sql = self._adapt_sql(sql)
        if self._use_mysql():
            with conn.cursor() as cur:
                cur.execute(sql, params or ())
                return list(cur.fetchall())
        else:
            cur = conn.execute(sql, params or ())
            rows = cur.fetchall()
            return [
                dict(r) if hasattr(r, "keys") else {
                    "id": r[0],
                    "content": r[1],
                    "memory_type": r[2],
                    "user_id": r[3],
                    "session_id": r[4],
                    "importance": r[5],
                    "timestamp": r[6],
                    "metadata": r[7],
                }
                for r in rows
            ]

    # ── 结果解析 ──────────────────────────────────────────────

    @staticmethod
    def _row_to_item(row: dict) -> Optional[MemoryItem]:
        if row is None:
            return None
        return MemoryItem(
            id=row["id"],
            content=row["content"],
            memory_type=row["memory_type"],
            user_id=row.get("user_id", "") or "",
            session_id=row.get("session_id", "") or "",
            importance=row["importance"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            metadata=json.loads(row["metadata"]) if row.get("metadata") else {},
        )
