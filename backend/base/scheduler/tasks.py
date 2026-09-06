"""定时任务: 每日收盘后自动刷新全池数据。

- 港股收盘 16:00, 16:35 拉当日日线 + 分红 + 因子快照(周一至周五)
- 周末/节假日拉取失败自动优雅降级(空数据不落库), 无需日历支持
"""

from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from base.config import MARKET_CLOSE_HOUR, MARKET_CLOSE_MIN
from dividend.service import refresh_all_stocks

_scheduler: BackgroundScheduler | None = None


def _job_refresh_all() -> None:
    try:
        result = refresh_all_stocks()
        print(f"[SCHED] daily refresh done: {result}")
    except Exception as e:  # noqa: BLE001
        print(f"[SCHED] daily refresh failed: {e}")


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    _scheduler.add_job(
        _job_refresh_all,
        CronTrigger(day_of_week="mon-fri", hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MIN),
        id="daily_refresh",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    _scheduler.start()
    print(f"[SCHED] scheduler started (daily {MARKET_CLOSE_HOUR}:{MARKET_CLOSE_MIN:02d})")


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
