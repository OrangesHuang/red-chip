"""分红/派息数据拉取, A股与港股通用。

港股主源: akshare 东方财富港股分红派息 `stock_hk_dividend_payout_em`(稳定, 含
除净日/发放日/分红方案文本); 降级源同花顺 `stock_hk_fhpx_detail_ths`。
A股主源: akshare 东方财富分红送配 `stock_fhps_detail_em`(结构化列: 每10股派息
比例/送转比例/除权除息日; 每股 = 比例/10, 人民币含税口径, 见 config.A_SHARE_TAX_POLICY)。

港股分红货币处理: 港股价格以港币计价, 每股股息统一折算为「港币等值」存储:
    - 方案含「相当于港币/港元X元」→ 直接取该金额(HKD)
    - 方案含「港币/港元X元」→ 取 X(HKD)
    - 人民币 → 按 config.FX_RMB_HKD 折算(近似, 可调)
    - 美元 → 按 config.FX_USD_HKD 折算(近似, 可调)

规范化结构:
    {year, announce_date, ex_date, pay_date, cash_per_share(港元等值/人民币),
     currency(原始币种), bonus_ratio, special(特别股息标记), note}
"""

from __future__ import annotations

import re

from base.config import FX_RMB_HKD, FX_USD_HKD
from base.pool import get_stock

# 币种关键词 → 折算率(相对港币)
_CURRENCY_RULES: list[tuple[list[str], str, float | None]] = [
    (["相当于港币", "相当于港元"], "HKD", 1.0),
    (["港币", "港元"], "HKD", 1.0),
    (["人民币", "RMB"], "RMB", FX_RMB_HKD),
    (["美元", "USD", "美金"], "USD", FX_USD_HKD),
]


def _parse_plan(text: str) -> tuple[float | None, str | None, float | None]:
    """解析分红方案文本 → (每股派息(港元等值), 原始币种, 送转比例)。

    「10派3.2」按每股折算; 送转匹配「每10股送X股/转增X股」。
    """
    if not text:
        return None, None, None
    currency: str | None = None
    rate: float | None = None
    cash_raw: float | None = None
    for keywords, cur, r in _CURRENCY_RULES:
        for kw in keywords:
            if kw in text:
                currency, rate = cur, r
                break
        if currency:
            break

    # 港币等值优先: 「相当于港币2.9003元」→ 取该数
    m = re.search(r"相当于\s*(?:港币|港元)\s*([\d.]+)", text)
    if m:
        cash_raw = float(m.group(1))
        return round(cash_raw, 4), currency, None

    m = re.search(r"(?:每股|每10股)?\s*派(?:现金)?\s*(?:港币|港元|人民币|美元|美金)?\s*([\d.]+)", text)
    if not m:
        m = re.search(r"派\s*(?:港币|港元|人民币|美元|美金)?\s*([\d.]+)", text)
    if not m:
        # 「10派3.2」或「10派人民币3.2元」
        m = re.search(r"10\s*派(?:现金)?\s*(?:港币|港元|人民币|美元|美金)?\s*([\d.]+)", text)
        if m:
            cash_raw = float(m.group(1)) / 10.0
    if m and cash_raw is None:
        cash_raw = float(m.group(1))
        if "10派" in text or "每10股" in text:
            cash_raw = cash_raw / 10.0

    bonus: float | None = None
    bm = re.search(r"(?:每10股)?\s*(?:送|转增|转)\s*([\d.]+)\s*股", text)
    if bm:
        bonus = float(bm.group(1))

    if cash_raw is None:
        return None, currency, bonus
    if rate and rate != 1.0:
        cash_raw = cash_raw * rate
    return round(cash_raw, 4), currency, bonus


def _normalize_em(df) -> list[dict]:
    """东财港股分红 DataFrame → 规范化记录。"""
    if df is None or getattr(df, "empty", True):
        return []
    rows: list[dict] = []
    for _, row in df.iterrows():
        plan = str(row.get("分红方案") or "")
        cash, currency, bonus = _parse_plan(plan)
        dist_type = str(row.get("分配类型") or "")
        special = any(k in dist_type for k in ("特别", "特殊"))
        year = row.get("财政年度")
        ex_date = str(row.get("除净日") or "")[:10] or None
        pay_date = str(row.get("发放日") or "")[:10] or None
        announce = str(row.get("最新公告日期") or "")[:10] or None
        if year is not None:
            try:
                year = int(str(year)[:4])
            except ValueError:
                year = None
        if not ex_date and not pay_date:
            continue
        if cash is None and bonus is None:
            continue
        rows.append(
            {
                "year": year,
                "announce_date": announce,
                "ex_date": ex_date,
                "pay_date": pay_date,
                "cash_per_share": cash,
                "currency": currency,
                "bonus_ratio": bonus,
                "special": special,
                "note": f"{plan} ({dist_type})".strip()[:200],
            }
        )
    rows.sort(key=lambda r: (r["ex_date"] or r["pay_date"] or r["announce_date"] or ""), reverse=True)
    return rows


def _normalize_ths(df) -> list[dict]:
    """同花顺港股分红 DataFrame → 规范化记录(降级源, 列名容错)。"""
    if df is None or getattr(df, "empty", True):
        return []
    cols = [str(c) for c in df.columns]
    plan_col = next((c for c in cols if "方案" in c), None)
    ex_col = next((c for c in cols if "除净" in c or "除权" in c), None)
    pay_col = next((c for c in cols if "派息" in c or "发放" in c), None)
    ann_col = next((c for c in cols if "公告" in c), None)
    year_col = next((c for c in cols if "年度" in c or "年份" in c), None)

    rows: list[dict] = []
    for _, row in df.iterrows():
        plan = str(row[plan_col]) if plan_col else ""
        cash, currency, bonus = _parse_plan(plan)
        special = any(k in plan for k in ("特别", "特殊"))
        ex_date = str(row[ex_col])[:10] if ex_col and row[ex_col] is not None else None
        pay_date = str(row[pay_col])[:10] if pay_col and row[pay_col] is not None else None
        announce = str(row[ann_col])[:10] if ann_col and row[ann_col] is not None else None
        year = row[year_col] if year_col and row[year_col] is not None else None
        if year is not None:
            try:
                year = int(str(year)[:4])
            except ValueError:
                year = None
        if not ex_date and not pay_date:
            continue
        if cash is None and bonus is None:
            continue
        rows.append(
            {
                "year": year,
                "announce_date": announce,
                "ex_date": ex_date,
                "pay_date": pay_date,
                "cash_per_share": cash,
                "currency": currency,
                "bonus_ratio": bonus,
                "special": special,
                "note": plan[:200],
            }
        )
    rows.sort(key=lambda r: (r["ex_date"] or r["pay_date"] or r["announce_date"] or ""), reverse=True)
    return rows


def _normalize_a_share(df) -> list[dict]:
    """东财 A 股分红送配 DataFrame → 规范化记录(每股人民币, 含税口径)。

    结构化列直接取数: 现金分红比例 = 每10股派息元数 → 每股 = /10;
    送转总比例 = 每10股送转股数 → 每股 = /10。只保留已实施的记录(有除权除息日)。
    """
    if df is None or getattr(df, "empty", True):
        return []
    rows: list[dict] = []
    for _, row in df.iterrows():
        ex_date = str(row.get("除权除息日") or "")[:10] or None
        if not ex_date:  # 预案/未实施的行无除权除息日, 不参与股息率
            continue
        pay_date = None  # A股接口无派息日列, TTM 锚点用除权除息日
        announce = str(row.get("最新公告日期") or "")[:10] or None

        cash_raw = row.get("现金分红-现金分红比例")
        cash = round(float(cash_raw) / 10.0, 4) if cash_raw is not None and str(cash_raw) != "nan" else None
        bonus_raw = row.get("送转股份-送转总比例")
        bonus = round(float(bonus_raw) / 10.0, 4) if bonus_raw is not None and str(bonus_raw) != "nan" else None
        if cash is None and bonus is None:
            continue

        report = str(row.get("报告期") or "")[:10]
        year = int(report[:4]) if report[:4].isdigit() else None

        desc = str(row.get("现金分红-现金分红比例描述") or "")
        special = any(k in desc for k in ("特别", "特殊"))
        progress = str(row.get("方案进度") or "")
        rows.append(
            {
                "year": year,
                "announce_date": announce,
                "ex_date": ex_date,
                "pay_date": pay_date,
                "cash_per_share": cash,
                "currency": "CNY",  # A股人民币计价, 无需折算
                "bonus_ratio": bonus,
                "special": special,
                "note": f"{desc} ({progress})".strip()[:200],
            }
        )
    rows.sort(key=lambda r: r["ex_date"] or "", reverse=True)
    return rows


def fetch_dividend_history(code: str) -> list[dict]:
    """拉取分红历史(A股/港股自动分发)。全部失败返回空列表, 不抛异常。"""
    try:
        import akshare as ak
    except ImportError:
        print("[FETCH] akshare 未安装, 分红数据不可用")
        return []

    market = (get_stock(code) or {}).get("market", "hk")
    if market != "hk":
        fn = getattr(ak, "stock_fhps_detail_em", None)
        if fn is None:
            print("[FETCH] akshare 无 stock_fhps_detail_em 接口, A股分红不可用")
            return []
        try:
            df = fn(symbol=code)
            rows = _normalize_a_share(df)
            if rows:
                return rows
            print(f"[FETCH] dividend {code} A股返回空")
        except Exception as e:  # noqa: BLE001
            print(f"[FETCH] dividend {code} A股 failed: {e}")
        return []

    em_fn = getattr(ak, "stock_hk_dividend_payout_em", None)
    if em_fn is not None:
        try:
            df = em_fn(symbol=code)
            rows = _normalize_em(df)
            if rows:
                return rows
            print(f"[FETCH] dividend {code} eastmoney 返回空, 尝试降级源")
        except Exception as e:  # noqa: BLE001
            print(f"[FETCH] dividend {code} eastmoney failed: {e}")

    ths_fn = getattr(ak, "stock_hk_fhpx_detail_ths", None)
    if ths_fn is not None:
        try:
            df = ths_fn(symbol=code)
            return _normalize_ths(df)
        except Exception as e:  # noqa: BLE001
            print(f"[FETCH] dividend {code} ths failed: {e}")
    return []
