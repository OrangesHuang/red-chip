"""base: 跨领域共用层(页面领域间下沉)。

严格单向依赖: base/fetch → base/analysis → base/store → base/api;
领域目录(dividend/)与 api/ 只依赖 base, base 不反向依赖领域。
"""

from base.config import DB_PATH
from base.pool import get_all_stocks, get_stock
from base.store.database import init_db

__all__ = ["DB_PATH", "init_db", "get_all_stocks", "get_stock"]
