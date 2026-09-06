"""SQLite 连接与建表(WAL 模式)。表结构集中管理, 变更通过迁移函数增量执行。"""

from __future__ import annotations

import sqlite3

from base.config import DB_PATH


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
        conn.executescript(
            """
            -- 个股日线(港股, 前复权)
            CREATE TABLE IF NOT EXISTS stock_daily (
                date        TEXT NOT NULL,
                code        TEXT NOT NULL,
                name        TEXT,
                open_price  REAL,
                high_price  REAL,
                low_price   REAL,
                close_price REAL,
                change_pct  REAL,
                volume      REAL,
                amount      REAL,
                created_at  TEXT DEFAULT (datetime('now','localtime')),
                updated_at  TEXT DEFAULT (datetime('now','localtime')),
                PRIMARY KEY (date, code)
            );
            CREATE INDEX IF NOT EXISTS idx_daily_code ON stock_daily(code);
            CREATE INDEX IF NOT EXISTS idx_daily_date ON stock_daily(date);

            -- 个股实时快照(盘中轮询)
            CREATE TABLE IF NOT EXISTS stock_realtime (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT NOT NULL,
                code        TEXT NOT NULL,
                price       REAL,
                change_pct  REAL,
                volume      REAL,
                amount      REAL,
                high        REAL,
                low         REAL,
                turnover    REAL,
                pe          REAL,
                pb          REAL,
                created_at  TEXT DEFAULT (datetime('now','localtime'))
            );
            CREATE INDEX IF NOT EXISTS idx_rt_code_ts ON stock_realtime(code, timestamp);

            -- 分红历史(每股现金已折算为港元等值/送转; 东财+同花顺口径)
            -- 无 UNIQUE 约束: replace 语义为「先删后插」, 入库前按 (ex_date, cash) 去重
            CREATE TABLE IF NOT EXISTS dividend (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                code            TEXT NOT NULL,
                year            INTEGER,
                announce_date   TEXT,
                ex_date         TEXT,
                pay_date        TEXT,
                cash_per_share  REAL,
                currency        TEXT,
                bonus_ratio     REAL,
                special         INTEGER NOT NULL DEFAULT 0,
                note            TEXT,
                created_at      TEXT DEFAULT (datetime('now','localtime'))
            );
            CREATE INDEX IF NOT EXISTS idx_div_code ON dividend(code);

            -- 因子快照(每股每日一版: 因子总分/区间/赔率)
            CREATE TABLE IF NOT EXISTS factor_snapshot (
                date            TEXT NOT NULL,
                code            TEXT NOT NULL,
                close_price     REAL,
                change_pct      REAL,
                dps_ttm         REAL,
                div_yield       REAL,
                score           REAL,
                grade           TEXT,
                zone            TEXT,
                odds            REAL,
                target_price    REAL,
                support_price   REAL,
                created_at      TEXT DEFAULT (datetime('now','localtime')),
                updated_at      TEXT DEFAULT (datetime('now','localtime')),
                PRIMARY KEY (date, code)
            );
            CREATE INDEX IF NOT EXISTS idx_snap_code ON factor_snapshot(code);

            -- 设置/状态
            CREATE TABLE IF NOT EXISTS settings (
                key        TEXT PRIMARY KEY,
                value      TEXT NOT NULL,
                updated_at TEXT DEFAULT (datetime('now','localtime'))
            );

            -- 用户自定义股票(页面自助添加; 内置池在 config.STOCKS)
            CREATE TABLE IF NOT EXISTS custom_stocks (
                code        TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                industry    TEXT,
                market      TEXT NOT NULL,
                created_at  TEXT DEFAULT (datetime('now','localtime'))
            );

            -- AI 分析报告(任务完成后持久化, 重启不丢)
            CREATE TABLE IF NOT EXISTS analysis_report (
                job_id      TEXT PRIMARY KEY,
                code        TEXT NOT NULL,
                name        TEXT,
                status      TEXT NOT NULL,
                report      TEXT,
                steps       TEXT,
                error       TEXT,
                created_at  TEXT,
                finished_at TEXT DEFAULT (datetime('now','localtime'))
            );
            CREATE INDEX IF NOT EXISTS idx_report_code ON analysis_report(code);
            CREATE INDEX IF NOT EXISTS idx_report_finished ON analysis_report(finished_at);

            -- AI 多轮会话(消息以 JSON 存储, 保持前缀紧凑利于缓存)
            CREATE TABLE IF NOT EXISTS analysis_session (
                id          TEXT PRIMARY KEY,
                code        TEXT NOT NULL,
                name        TEXT,
                messages    TEXT NOT NULL DEFAULT '[]',
                created_at  TEXT,
                updated_at  TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_session_code ON analysis_session(code);

            -- 交易日历(预留)
            CREATE TABLE IF NOT EXISTS trade_calendar (
                date TEXT PRIMARY KEY,
                created_at TEXT DEFAULT (datetime('now','localtime'))
            );
            """
        )
        _migrate_drop_dividend_unique(conn)
        _migrate_add_dividend_special(conn)
        conn.commit()
    finally:
        conn.close()


def _migrate_drop_dividend_unique(conn: sqlite3.Connection) -> None:
    """旧版 dividend 表带 UNIQUE(code, ex_date, cash_per_share) 约束,
    重复分红记录会撞约束; 重建为无约束表(replace 语义下约束无意义)。"""
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='dividend'"
    ).fetchone()
    if row and "UNIQUE" in (row[0] or ""):
        conn.executescript(
            """
            CREATE TABLE dividend_new (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                code            TEXT NOT NULL,
                year            INTEGER,
                announce_date   TEXT,
                ex_date         TEXT,
                pay_date        TEXT,
                cash_per_share  REAL,
                currency        TEXT,
                bonus_ratio     REAL,
                note            TEXT,
                created_at      TEXT DEFAULT (datetime('now','localtime'))
            );
            INSERT INTO dividend_new (code, year, announce_date, ex_date, pay_date,
                                      cash_per_share, currency, bonus_ratio, note, created_at)
                SELECT code, year, announce_date, ex_date, pay_date,
                       cash_per_share, currency, bonus_ratio, note, created_at FROM dividend;
            DROP TABLE dividend;
            ALTER TABLE dividend_new RENAME TO dividend;
            CREATE INDEX IF NOT EXISTS idx_div_code ON dividend(code);
            """
        )


def _migrate_add_dividend_special(conn: sqlite3.Connection) -> None:
    """旧版 dividend 表补 special 列。"""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(dividend)")}
    if "special" not in existing:
        conn.execute("ALTER TABLE dividend ADD COLUMN special INTEGER NOT NULL DEFAULT 0")
