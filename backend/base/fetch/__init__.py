"""base/fetch: 数据源请求与解析(A/H 日 K/实时/分红/资讯/日历)。

约定: 只做请求与解析, 不做业务判断; 网络失败一律返回空/None, 不抛异常。
"""

from base.fetch.calendar import fetch_trade_days
from base.fetch.dividend import fetch_dividend_history
from base.fetch.kline import fetch_kline
from base.fetch.news import fetch_stock_news
from base.fetch.realtime import fetch_realtime

__all__ = [
    "fetch_kline",
    "fetch_realtime",
    "fetch_dividend_history",
    "fetch_stock_news",
    "fetch_trade_days",
]
