"""红筹高股息因子分析 — 全局配置。

全部可调常量集中于此: 股票池/阈值/窗口/限流。
数据目录默认 = 仓库根/data(项目内, gitignored), 可用环境变量 RED_CHIP_HOME 覆盖。
"""

from __future__ import annotations

import os
from pathlib import Path

# backend/base/config.py → parents[2] = 仓库根
PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = Path(os.environ.get("RED_CHIP_HOME", str(PROJECT_ROOT / "data"))).expanduser()
DB_PATH = WORKSPACE / "red_chip.db"

# ─── 高股息股票池 ──────────────────────────────────────────────────
# market: hk=港股(红筹/中资), sh=上交所A股, sz=深交所A股。
# 红筹股: 注册在境外/香港、香港上市、中资(国有/央企背景为主)控股;
# A 股标的为高股息主线(银行/煤炭/公用/能源), 与红筹池互补。
# 如需增删标的, 直接编辑本表即可(代码为 6 位证券代码)。
STOCKS: dict[str, dict] = {
    # ── 红筹股(港股) ──
    "00941": {"name": "中国移动", "industry": "电信运营", "market": "hk"},
    "00762": {"name": "中国联通", "industry": "电信运营", "market": "hk"},
    "00883": {"name": "中国海洋石油", "industry": "石油天然气", "market": "hk"},
    "00836": {"name": "华润电力", "industry": "电力", "market": "hk"},
    "01193": {"name": "华润燃气", "industry": "燃气公用", "market": "hk"},
    "00135": {"name": "昆仑能源", "industry": "燃气公用", "market": "hk"},
    "00267": {"name": "中信股份", "industry": "综合金融", "market": "hk"},
    "02388": {"name": "中银香港", "industry": "银行", "market": "hk"},
    "00688": {"name": "中国海外发展", "industry": "房地产", "market": "hk"},
    "01109": {"name": "华润置地", "industry": "房地产", "market": "hk"},
    "00992": {"name": "联想集团", "industry": "科技硬件", "market": "hk"},
    "01093": {"name": "石药集团", "industry": "医药", "market": "hk"},
    # ── A 股高股息(上交所) ──
    "600941": {"name": "中国移动", "industry": "电信运营", "market": "sh"},
    "601088": {"name": "中国神华", "industry": "煤炭", "market": "sh"},
    "601857": {"name": "中国石油", "industry": "石油天然气", "market": "sh"},
    "600028": {"name": "中国石化", "industry": "石油天然气", "market": "sh"},
    "600900": {"name": "长江电力", "industry": "电力", "market": "sh"},
    "601398": {"name": "工商银行", "industry": "银行", "market": "sh"},
    "601939": {"name": "建设银行", "industry": "银行", "market": "sh"},
    "601288": {"name": "农业银行", "industry": "银行", "market": "sh"},
    "601328": {"name": "交通银行", "industry": "银行", "market": "sh"},
    "600036": {"name": "招商银行", "industry": "银行", "market": "sh"},
    "601166": {"name": "兴业银行", "industry": "银行", "market": "sh"},
    "601225": {"name": "陕西煤业", "industry": "煤炭", "market": "sh"},
    "601006": {"name": "大秦铁路", "industry": "铁路运输", "market": "sh"},
    "600019": {"name": "宝钢股份", "industry": "钢铁", "market": "sh"},
    "600585": {"name": "海螺水泥", "industry": "建材", "market": "sh"},
    "600350": {"name": "山东高速", "industry": "高速公路", "market": "sh"},
    "600519": {"name": "贵州茅台", "industry": "白酒", "market": "sh"},
    "601318": {"name": "中国平安", "industry": "保险", "market": "sh"},
    "601601": {"name": "中国太保", "industry": "保险", "market": "sh"},
    "600030": {"name": "中信证券", "industry": "证券", "market": "sh"},
    "601688": {"name": "华泰证券", "industry": "证券", "market": "sh"},
    "601668": {"name": "中国建筑", "industry": "建筑", "market": "sh"},
    "601988": {"name": "中国银行", "industry": "银行", "market": "sh"},
    "601658": {"name": "邮储银行", "industry": "银行", "market": "sh"},
    "600887": {"name": "伊利股份", "industry": "食品饮料", "market": "sh"},
    "000895": {"name": "双汇发展", "industry": "食品饮料", "market": "sz"},
    # ── A 股高股息(深交所) ──
    "000858": {"name": "五粮液", "industry": "白酒", "market": "sz"},
    "000651": {"name": "格力电器", "industry": "家电", "market": "sz"},
    "000333": {"name": "美的集团", "industry": "家电", "market": "sz"},
}

DEFAULT_STOCK_CODE = "00941"

# ─── 行情拉取 ─────────────────────────────────────────────────────
KLINE_LIMIT = 300  # 常规 K 线拉取根数(约 1.2 年交易日)
KLINE_RANGE_LIMIT = 650  # 区间接口单块 limit(腾讯接口单次响应上限约 640~700 根)
RANGE_CHUNK_NATURAL_DAYS = 850  # 区间分块: 每块自然日跨度(≈600 交易日)
KLINE_CACHE_TTL_SEC = 60
KLINE_FAIL_COOLDOWN_SEC = 30
HTTP_TIMEOUT = 15
FETCH_SLEEP_SEC = 0.3  # 相邻股票拉取间隔(秒, 防封)
MAX_RETRY = 2

KLINE_URL = "https://ifzq.gtimg.cn/appstock/app/fqkline/get?param={symbol},day,,,{limit},qfq"
KLINE_URL_RANGE = "https://ifzq.gtimg.cn/appstock/app/fqkline/get?param={symbol},day,{start},{end},{limit},qfq"
KLINE_URL_ALT = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={symbol},day,,,{limit},qfq"
KLINE_URL_RANGE_ALT = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={symbol},day,{start},{end},{limit},qfq"
SINA_HK_KLINE_URL = (
    "https://quotes.sina.cn/hk/api/json_v2.php/"
    "HK_MarketDataService.getKLineData?symbol={code}&scale=240&ma=no&datalen={limit}"
)
REALTIME_URL = "https://qt.gtimg.cn/q={symbols}"

# ─── 分红数据(akshare: 东财港股分红派息, 同花顺降级) ───────────────
AKSHARE_TIMEOUT = 60
DIVIDEND_HISTORY_YEARS = 8  # 分红历史覆盖年数(区间回填用)
# 港股以港币计价, 外币分红折算率(近似值, 随汇率更新; 方案含「相当于港币」时优先用其给出的金额)
FX_RMB_HKD = 1.10
FX_USD_HKD = 7.80
# 特别股息(东财「特别分配」)为一次性事件, 计入 TTM 会扭曲股息率锚点/赔率,
# 默认从 TTM 与成长性计算中剔除(历史表仍保留展示, 打标「特别」)
EXCLUDE_SPECIAL_DIVIDENDS = True
# A 股分红为「每10股派X元(含税)」口径, 每股 = X/10 元(人民币, 无需折算)。
# 红利税按持股时长(≤1月20% / 1月~1年10% / >1年 0%)由券商代扣, 个人实际到手
# 与含税口径不同; v1 按含税口径(gross)计算, 与行情软件「股息率(含税)」一致。
A_SHARE_TAX_POLICY = "gross"

# ─── 因子模型(高股息六因子) ────────────────────────────────────────
# 各因子得分 0~100, 按权重加权; 缺失因子权重按剩余权重重新归一化(优雅降级)。
FACTOR_WEIGHTS = {
    "div_yield": 0.35,  # 股息率(滚动 TTM)
    "div_years": 0.20,  # 连续分红年数
    "div_growth": 0.15,  # 近 3 年每股股息复合增速
    "payout": 0.15,  # 派息率(健康区间 30~70%)
    "debt": 0.10,  # 资产负债率(越低越好)
    "volatility": 0.05,  # 年化波动率(越低越稳)
}
SCORE_GOOD = 75.0  # ≥ 此分 → 优质
SCORE_FINE = 60.0  # ≥ 此分 → 良好
SCORE_FAIR = 45.0  # ≥ 此分 → 一般; 否则回避

# 股息率打分锚点: (股息率%, 得分)
DIV_YIELD_CURVE = [(2.0, 10), (3.0, 30), (4.0, 50), (5.0, 65), (6.0, 80), (8.0, 100)]
DIV_YEARS_CURVE = [(0, 0), (1, 20), (3, 40), (5, 60), (8, 85), (10, 100)]
DIV_GROWTH_CURVE = [(-10.0, 10), (-5.0, 30), (0.0, 60), (5.0, 100)]
PAYOUT_CURVE = [(0.0, 40), (20.0, 80), (35.0, 100), (55.0, 100), (70.0, 90), (90.0, 50), (120.0, 20)]
DEBT_CURVE = [(0.0, 100), (30.0, 100), (50.0, 70), (70.0, 40), (85.0, 10)]
VOLATILITY_CURVE = [(0.0, 100), (25.0, 100), (40.0, 60), (60.0, 20)]

# ─── 价格区间与赔率(股息率锚定) ────────────────────────────────────
YIELD_HISTORY_DAYS = 1250  # 股息率历史序列回看窗口(≈5 年交易日)
ZONE_Q_LOW = 25.0  # 股息率 ≤ 此分位 → 高估区
ZONE_Q_HIGH = 75.0  # 股息率 ≥ 此分位 → 低估区
ZONE_Q_DEEP_LOW = 90.0  # ≥ 此分位 → 深度低估
ZONE_Q_DEEP_HIGH = 10.0  # ≤ 此分位 → 深度高估
ODDS_Q_CENTRAL = 50.0  # 赔率中枢目标: 股息率回到历史中位对应的价格
ODDS_Q_OPTIMISTIC = 25.0  # 乐观目标: 股息率回到 P25(较贵端)对应的价格
ODDS_Q_PESSIMISTIC = 95.0  # 悲观支撑: 股息率走到 P95(最便宜端)对应的价格
ODDS_HIGH = 3.0  # ≥ 此赔率 → 高赔率
ODDS_MID = 1.5  # ≥ 此赔率 → 中等赔率; 否则低赔率
ODDS_FLOOR_CAP = 99.0  # 下行空间 ≤ 0 时赔率的封顶值

# ─── 调度与限流 ───────────────────────────────────────────────────
MARKET_CLOSE_HOUR, MARKET_CLOSE_MIN = 16, 35  # 港股收盘 16:00, 16:35 拉日线
DIVIDEND_FETCH_DOW = "sun"  # 每周日刷新分红数据
DIVIDEND_FETCH_HOUR = 10
REFRESH_MIN_INTERVAL_SEC = 120  # 手动刷新接口最小间隔(秒)
DEFAULT_BACKFILL_DAYS = 1250  # 一键重建: 每只股票回填交易日数(≈5年, 支撑股息率分位/赔率锚定)
JOB_SLEEP_SEC = 0.15  # 重建/回填循环内间隔(秒)

# 涨跌幅口径: 港股 K 线无涨跌幅, 由昨收计算; 区间判定窗口
POSITION_WINDOW = 60  # 价格位置回看窗口(交易日)

# ─── LLM 分析(DeepSeek ReAct agent) ───────────────────────────────
DEFAULT_LLM_BASE_URL = "https://api.deepseek.com"  # OpenAI 兼容端点
DEFAULT_LLM_MODEL = "deepseek-chat"
LLM_TIMEOUT = 90  # 单次补全请求超时(秒)
LLM_MAX_STEPS = 10  # agent 最大工具轮数
LLM_MAX_TOKENS = 4096
LLM_TEMPERATURE = 0.3
LLM_BASH_TIMEOUT = 30  # bash 工具超时(秒)
LLM_BASH_MAX_OUTPUT = 3000  # bash 输出截断(字符)
