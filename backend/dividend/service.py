"""高股息分析领域服务: 编排 fetch/store/analysis, 含 I/O。

刷新流程(每股):
    1. 拉 K 线(最近 backfill_days 交易日) → upsert stock_daily
    2. 拉分红历史 → replace dividend
    3. 计算 TTM DPS / 因子 / 区间 / 赔率 → upsert factor_snapshot

任何一步失败不影响其余; 单股失败记入 failed 列表, 不中断全池。
"""

from __future__ import annotations

import time
from datetime import datetime

from base.config import DEFAULT_BACKFILL_DAYS, JOB_SLEEP_SEC, YIELD_HISTORY_DAYS
from base.pool import get_all_stocks, get_stock
from base.fetch.dividend import fetch_dividend_history
from base.fetch.kline import fetch_kline
from base.fetch.realtime import fetch_realtime
from base.analysis.position import annualized_volatility
from base.store import dividend_repo, factor_repo, stock_repo
from dividend.analysis import (
    DividendInputs,
    anchor_prices,
    build_daily_yield_series,
    factor_scores,
    odds,
    trailing_dps,
)

_REFRESH_LOCK = __import__("threading").Lock()


# ─── 因子输入组装 ──────────────────────────────────────────────────


def _yearly_dps(dividends: list[dict]) -> dict[int, float]:
    """按除净日年份汇总每股现金股息(港元), 剔除一次性特别股息。"""
    result: dict[int, float] = {}
    for r in dividends:
        if r.get("special"):
            continue
        year = r.get("year")
        cash = r.get("cash_per_share")
        if year and cash:
            result[year] = result.get(year, 0.0) + float(cash)
    return result


def _div_years(dividends: list[dict]) -> int:
    """近 5 个日历年内有现金分红的年数(含当年)。"""
    now_year = datetime.now().year
    years = {
        r["year"] for r in dividends
        if r.get("year") and r.get("cash_per_share") and not r.get("special")
    }
    return len([y for y in years if now_year - 5 < y <= now_year])


def _last_close_change_pct(kline: list[dict]) -> float | None:
    """最新一根 K 线相对前收的涨跌幅 %(与 stock_repo.upsert_daily 同口径)。

    fetch_kline 返回的 bar 不含 change_pct, 必须在此按相邻收盘价计算, 否则
    快照 change_pct 会恒为 None(realtime 拉取失败时前端拿不到当日涨跌)。
    """
    if len(kline) < 2:
        return None
    prev = kline[-2].get("close")
    last = kline[-1].get("close")
    if not prev or prev <= 0 or last is None:
        return None
    return round((last / prev - 1.0) * 100.0, 4)


def _div_growth(dividends: list[dict]) -> float | None:
    """近 3 年每股股息 CAGR %。

    用「最新已完成财政年度」作为增速终点(当年可能只派了中期, 拉低增速):
    某财政年度所有分红的派息日(缺省用除净日)都 ≤ 今天 → 视为已完成。
    数据不足返回 None。
    """
    from datetime import date

    today = date.today()
    yearly = _yearly_dps(dividends)
    if not yearly:
        return None
    by_year: dict[int, list[dict]] = {}
    for r in dividends:
        if r.get("year"):
            by_year.setdefault(r["year"], []).append(r)

    def _complete(y: int) -> bool:
        rows = by_year.get(y, [])
        if not rows:
            return False
        for r in rows:
            anchor = r.get("pay_date") or r.get("ex_date")
            if not anchor:
                return False
            try:
                if date.fromisoformat(str(anchor)[:10]) > today:
                    return False
            except ValueError:
                return False
        return True

    complete_years = [y for y in yearly if _complete(y)]
    latest_year = max(complete_years) if complete_years else max(yearly)
    base_year = latest_year - 3
    if latest_year not in yearly or base_year not in yearly:
        return None
    latest, base = yearly[latest_year], yearly[base_year]
    if base <= 0 or latest <= 0:
        return None
    return round(((latest / base) ** (1.0 / 3.0) - 1.0) * 100.0, 2)


def compute_dividend_inputs(code: str, kline: list[dict], dividends: list[dict]) -> DividendInputs:
    """组装因子输入。财务类因子(payout/debt)未接入数据源 → None(权重自动归一化)。"""
    last_close = kline[-1]["close"] if kline else None
    dps = trailing_dps(dividends) if dividends else 0.0
    div_yield = round(dps / last_close * 100.0, 4) if dps > 0 and last_close else None
    closes = [bar["close"] for bar in kline]
    return DividendInputs(
        div_yield=div_yield,
        div_years=_div_years(dividends) if dividends else None,
        div_growth=_div_growth(dividends),
        payout=None,  # TODO: 接入港股财务数据源(akshare 财务指标)后填充
        debt=None,  # TODO: 同上
        volatility=annualized_volatility(closes),
    )


# ─── 刷新 ─────────────────────────────────────────────────────────


def refresh_one_stock(code: str, backfill_days: int = DEFAULT_BACKFILL_DAYS) -> dict:
    """刷新单只股票: K线 + 分红 + 因子快照。返回结果摘要, 不抛异常。"""
    info = get_stock(code)
    if info is None:
        return {"code": code, "name": code, "ok": False, "error": "未知代码"}
    result: dict = {"code": code, "name": info["name"], "ok": False, "error": None}

    if backfill_days > 600:
        # 腾讯无日期路径单次响应上限约 640~700 根, 长回填必须走日期区间
        # 分块拉取, 否则历史只有最近 ~640 根(约 2.5 年), 股息率分位缺深度。
        from datetime import date, timedelta

        span_days = int(backfill_days * 7 / 5) + 5  # 交易日 → 自然日(5/7 密度 + 缓冲)
        start = (date.today() - timedelta(days=span_days)).isoformat()
        kline = fetch_kline(code, limit=backfill_days, start_date=start, end_date=date.today().isoformat())
    else:
        kline = fetch_kline(code, limit=backfill_days)

    if kline:
        stock_repo.upsert_daily(code, info["name"], kline)
        result["kline_count"] = len(kline)
    else:
        result["kline_count"] = 0
        result["error"] = "K线拉取失败"

    dividends = fetch_dividend_history(code)
    if dividends:
        dividend_repo.replace_dividends(code, dividends)
        result["dividend_count"] = len(dividends)
    else:
        result["dividend_count"] = 0

    _compute_and_store_snapshot(code, kline, dividends)
    result["ok"] = bool(kline) or bool(dividends)
    return result


def _compute_and_store_snapshot(code: str, kline: list[dict], dividends: list[dict]) -> dict | None:
    """计算并落库当日因子快照。数据不足时返回 None 不落库。"""
    if not kline:
        return None
    last = kline[-1]
    dps = trailing_dps(dividends) if dividends else 0.0
    current_yield = round(dps / last["close"] * 100.0, 4) if dps > 0 and last["close"] > 0 else None

    scores = factor_scores(compute_dividend_inputs(code, kline, dividends))
    yield_series = build_daily_yield_series(kline, dividends, lookback=YIELD_HISTORY_DAYS)
    anchors = anchor_prices(dps, yield_series, current_yield)
    odds_result = odds(last["close"], dps, yield_series)

    snap = {
        "date": last["date"],
        "code": code,
        "close_price": last["close"],
        "change_pct": _last_close_change_pct(kline),
        "dps_ttm": dps if dps > 0 else None,
        "div_yield": current_yield,
        "score": scores.total,
        "grade": scores.grade,
        "zone": anchors["zone"],
        "odds": odds_result.odds,
        "target_price": odds_result.central_price or anchors["anchors"]["central"],
        "support_price": odds_result.pessimistic_price,
    }
    factor_repo.upsert_snapshot(snap)
    return snap


def refresh_all_stocks(backfill_days: int = DEFAULT_BACKFILL_DAYS) -> dict:
    """刷新全池(独占锁防重叠)。返回 {total, ok, failed:[{code,name,error}]}。"""
    with _REFRESH_LOCK:
        stocks = get_all_stocks()
        failed = []
        for i, (code, info) in enumerate(stocks.items()):
            result = refresh_one_stock(code, backfill_days=backfill_days)
            if not result["ok"]:
                failed.append({"code": code, "name": result["name"], "error": result["error"]})
            if i < len(stocks) - 1:
                time.sleep(JOB_SLEEP_SEC)
        return {"total": len(stocks), "ok": len(stocks) - len(failed), "failed": failed}


# ─── 读组装 ────────────────────────────────────────────────────────


def build_pool() -> list[dict]:
    """股票池: 最新因子快照 × 股票池配置, 按因子总分降序。"""
    snaps = {s["code"]: s for s in factor_repo.latest_snapshots()}
    rows = []
    for code, info in get_all_stocks().items():
        s = snaps.get(code)
        rows.append(
            {
                "code": code,
                "name": info["name"],
                "industry": info["industry"],
                "market": info.get("market", "hk"),
                "custom": bool(info.get("custom")),
                "price": s["close_price"] if s else None,
                "change_pct": s["change_pct"] if s else None,
                "div_yield": s["div_yield"] if s else None,
                "dps_ttm": s["dps_ttm"] if s else None,
                "score": s["score"] if s else None,
                "grade": s["grade"] if s else "无数据",
                "zone": s["zone"] if s else "无数据",
                "odds": s["odds"] if s else None,
                "target_price": s["target_price"] if s else None,
                "support_price": s["support_price"] if s else None,
                "snapshot_date": s["date"] if s else None,
            }
        )
    rows.sort(key=lambda r: (r["score"] is None, -(r["score"] or 0)))
    return rows


def build_pool_live() -> list[dict]:
    """股票池 + 实时行情叠加(实时失败降级用快照价)。pool / 区间统计共用。"""
    rows = build_pool()
    try:
        rt = {r["code"]: r for r in fetch_realtime([r["code"] for r in rows])}
    except Exception:  # noqa: BLE001
        rt = {}
    for r in rows:
        live = rt.get(r["code"])
        if live:
            r["price"] = live["price"]
            r["change_pct"] = live["change_pct"]
            r["realtime"] = True
    return rows


def build_stock_detail(code: str, kline_days: int = 640) -> dict:
    """个股详情: 信息 + K线 + 分红 + 因子明细 + 区间 + 赔率 + 股息率曲线。"""
    info = get_stock(code) or {"name": code, "industry": "自定义", "market": "hk"}
    daily = stock_repo.get_daily(code, kline_days)
    kline = [
        {
            "date": r["date"],
            "open": r["open_price"],
            "high": r["high_price"],
            "low": r["low_price"],
            "close": r["close_price"],
            "volume": r["volume"],
            "amount": r["amount"],
            "change_pct": r["change_pct"],
        }
        for r in daily
    ]
    dividends = dividend_repo.get_dividends(code)
    dps = trailing_dps(dividends)
    last_close = kline[-1]["close"] if kline else None
    current_yield = round(dps / last_close * 100.0, 4) if dps > 0 and last_close else None

    inputs = compute_dividend_inputs(code, kline, dividends)
    scores = factor_scores(inputs)
    yield_series = build_daily_yield_series(kline, dividends, lookback=YIELD_HISTORY_DAYS)
    anchors = anchor_prices(dps, yield_series, current_yield)
    odds_result = odds(last_close, dps, yield_series) if last_close else None

    latest_snap = None
    snaps = factor_repo.snapshot_dates(code, limit=1)
    if snaps:
        latest_snap = snaps[-1]

    return {
        "code": code,
        "name": info["name"],
        "industry": info["industry"],
        "market": info.get("market", "hk"),
        "custom": bool(info.get("custom")),
        "kline": kline,
        "dividends": dividends,
        "yield_series": yield_series,
        "factors": {
            "total": scores.total,
            "grade": scores.grade,
            "components": [
                {"key": k, "score": v, "weight": round(scores.weights.get(k, 0.0), 4)}
                for k, v in scores.raw.items()
            ],
        },
        "inputs": {
            "div_yield": inputs.div_yield,
            "div_years": inputs.div_years,
            "div_growth": inputs.div_growth,
        },
        "dps_ttm": dps if dps > 0 else None,
        "current_yield": current_yield,
        "range": anchors,
        "odds": odds_result.__dict__ if odds_result else None,
        "snapshot": latest_snap,
    }


def build_llm_context(code: str, news_limit: int = 8, kline_recent: int = 10) -> dict:
    """为 LLM 构建紧凑分析上下文(不包含全量 K 线, 控制 token 开销)。

    包含: 基本信息 / 最新快照 / 因子明细 / 股息率分位与锚定价 / 区间收益统计 /
    近 N 根 K 线 / 分红历史(最近10条) / 资讯摘要。
    """
    from base.fetch.news import fetch_stock_news

    info = get_stock(code) or {"name": code, "industry": "自定义", "market": "hk"}
    daily = stock_repo.get_daily(code, 300)
    kline = [
        {"date": r["date"], "close": r["close_price"], "volume": r["volume"], "change_pct": r["change_pct"]}
        for r in daily
    ]
    dividends = dividend_repo.get_dividends(code)
    dps = trailing_dps(dividends)
    last_close = kline[-1]["close"] if kline else None
    current_yield = round(dps / last_close * 100.0, 4) if dps > 0 and last_close else None

    inputs = compute_dividend_inputs(code, kline, dividends)
    scores = factor_scores(inputs)
    yield_series = build_daily_yield_series(kline, dividends, lookback=YIELD_HISTORY_DAYS)
    anchors = anchor_prices(dps, yield_series, current_yield)
    odds_result = odds(last_close, dps, yield_series) if last_close else None

    closes = [b["close"] for b in kline]
    price_stats: dict = {"position_60": None}
    if len(closes) >= 60:
        span = max(closes[-60:]) - min(closes[-60:])
        price_stats["position_60"] = round((closes[-1] - min(closes[-60:])) / span * 100, 1) if span > 0 else None
    for label, n in (("chg_1m", 21), ("chg_3m", 63), ("chg_6m", 126), ("chg_1y", 250)):
        if len(closes) > n and closes[-1 - n] > 0:
            price_stats[label] = round((closes[-1] / closes[-1 - n] - 1) * 100, 2)
        else:
            price_stats[label] = None
    if closes:
        price_stats.update(
            high_1y=round(max(closes[-250:]), 4) if len(closes) >= 1 else None,
            low_1y=round(min(closes[-250:]), 4) if len(closes) >= 1 else None,
        )

    news = fetch_stock_news(code, limit=news_limit)
    return {
        "stock": {"code": code, "name": info.get("name"), "industry": info.get("industry"), "market": info.get("market")},
        "snapshot": {
            "date": kline[-1]["date"] if kline else None,
            "price": last_close,
            "change_pct": kline[-1].get("change_pct") if kline else None,
            "dps_ttm": dps if dps > 0 else None,
            "div_yield": current_yield,
            "score": scores.total,
            "grade": scores.grade,
            "zone": anchors["zone"],
            "odds": odds_result.odds if odds_result else None,
            "upside_pct": odds_result.upside_pct if odds_result else None,
            "downside_pct": odds_result.downside_pct if odds_result else None,
            "target_price": odds_result.central_price if odds_result else None,
            "support_price": odds_result.pessimistic_price if odds_result else None,
        },
        "factors": {
            "total": scores.total,
            "grade": scores.grade,
            "components": {k: v for k, v in scores.raw.items()},
            "inputs": {
                "div_yield": inputs.div_yield,
                "div_years": inputs.div_years,
                "div_growth": inputs.div_growth,
            },
        },
        "yield_quantiles": {k: round(v, 4) for k, v in anchors["qs"].items()},
        "anchors": anchors["anchors"],
        "price_stats": price_stats,
        "recent_bars": kline[-kline_recent:],
        "dividends": [
            {
                "year": r["year"],
                "ex_date": r["ex_date"],
                "cash_per_share": r["cash_per_share"],
                "currency": r["currency"],
                "special": bool(r["special"]),
                "note": (r["note"] or "")[:60],
            }
            for r in dividends[:10]
        ],
        "news": [{"title": n["title"], "time": n["time"], "source": n["source"]} for n in news],
    }
