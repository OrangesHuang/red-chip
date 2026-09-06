#!/usr/bin/env python3
"""CLI: 单只/全部红筹股数据回填(薄壳, 等价于「数据管理」页的一键重建)。

用法:
    .venv/bin/python scripts/seed_daily.py                # 全池, 默认 1250 交易日
    .venv/bin/python scripts/seed_daily.py 600            # 指定回填深度
    .venv/bin/python scripts/seed_daily.py 600 00941      # 单只股票

数据目录: 项目内 data/(可用环境变量 RED_CHIP_HOME 覆盖)。
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from base.config import DEFAULT_BACKFILL_DAYS  # noqa: E402
from base.pool import get_all_stocks, get_stock  # noqa: E402
from dividend.service import refresh_all_stocks, refresh_one_stock  # noqa: E402


def main() -> None:
    args = sys.argv[1:]
    days = int(args[0]) if args and args[0].isdigit() else DEFAULT_BACKFILL_DAYS
    code = args[1] if len(args) > 1 else None

    if code:
        if get_stock(code) is None:
            print(f"未知代码: {code}, 可选: {list(get_all_stocks())}")
            sys.exit(1)
        result = refresh_one_stock(code, backfill_days=days)
        print(f"{result['name']}({code}): ok={result['ok']} "
              f"kline={result.get('kline_count', 0)} dividends={result.get('dividend_count', 0)}")
        return

    result = refresh_all_stocks(backfill_days=days)
    print(f"全池重建完成: 成功 {result['ok']}/{result['total']}")
    for f in result["failed"]:
        print(f"  失败: {f['name']}({f['code']}): {f['error']}")


if __name__ == "__main__":
    main()
