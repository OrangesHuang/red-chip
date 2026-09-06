"""base/store: SQLite 访问层(database + 各表 repo)。

约定: 所有 SQL 参数化; 连接走 get_connection(); 表结构变更走 database.py
的 CREATE TABLE IF NOT EXISTS + _migrate_* 迁移函数。
"""

from base.store.database import get_connection, init_db

__all__ = ["get_connection", "init_db"]
