import { Link, useParams } from 'react-router-dom'
import AiAnalysisCard from '../components/analysis/AiAnalysisCard'
import KlineChart from '../components/kline/KlineChart'
import YieldZoneChart from '../components/kline/YieldZoneChart'
import { fmtPct, fmtPrice, oddsColor, scoreColor, useRefreshStock, useStockDetail, useStockNews, zoneColor } from '../hooks/useStocks'

/** 个股资讯卡片: A股来源东财, 港股来源腾讯新闻; 点击标题新窗口打开原文。 */
function NewsCard({ code }: { code: string }) {
  const { data, isLoading } = useStockNews(code)
  const news = data?.news ?? []
  return (
    <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-medium text-gray-300">个股资讯</h3>
        <span className="text-xs text-gray-600">
          {news.length > 0 ? `最近 ${news.length} 条` : 'A股=东财 · 港股=腾讯新闻'}
        </span>
      </div>
      {isLoading && <p className="py-6 text-center text-sm text-gray-500">加载中…</p>}
      {!isLoading && news.length === 0 && (
        <p className="py-6 text-center text-sm text-gray-500">暂无相关资讯</p>
      )}
      {!isLoading && news.length > 0 && (
        <ul className="divide-y divide-gray-800/60">
          {news.map((n, i) => (
            <li key={i} className="py-2">
              <a
                href={n.url}
                target="_blank"
                rel="noreferrer"
                className="text-sm text-gray-200 hover:text-red-300 transition-colors line-clamp-2"
              >
                {n.title}
              </a>
              {n.content && <p className="mt-0.5 text-xs text-gray-500 line-clamp-2">{n.content}</p>}
              <div className="mt-1 flex items-center gap-2 text-[11px] text-gray-600">
                <span>{n.time}</span>
                <span>·</span>
                <span>{n.source}</span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

const FACTOR_LABELS: Record<string, string> = {
  div_yield: '股息率',
  div_years: '分红持续性',
  div_growth: '分红成长性',
  payout: '派息率',
  debt: '负债率',
  volatility: '低波动',
}

function FactorBar({ label, score, weight }: { label: string; score: number; weight: number }) {
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-gray-400">{label}</span>
        <span className="text-gray-300 font-mono">
          {score.toFixed(0)}<span className="text-gray-600"> · 权重 {(weight * 100).toFixed(0)}%</span>
        </span>
      </div>
      <div className="h-1.5 rounded bg-gray-800 overflow-hidden">
        <div
          className={`h-full rounded ${score >= 75 ? 'bg-red-500' : score >= 45 ? 'bg-yellow-500' : 'bg-gray-500'}`}
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  )
}

export default function StockDetail() {
  const { code = '' } = useParams()
  const { data, isLoading, isError } = useStockDetail(code)
  const refresh = useRefreshStock(code)

  if (isLoading) return <div className="py-16 text-center text-sm text-gray-500">加载中…</div>
  if (isError || !data) {
    return (
      <div className="py-16 text-center text-sm text-gray-500">
        个股数据不可用 —— <Link to="/pool" className="text-red-400 hover:underline">返回股票池</Link>
      </div>
    )
  }

  const { range, odds: oddsInfo } = data
  const anchors = range.anchors
  const kline = data.kline

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-baseline gap-3">
            <h2 className="text-xl font-bold text-white">{data.name}</h2>
            <span className={`text-[10px] rounded px-1 py-0.5 ${
              data.market === 'hk' ? 'bg-purple-900/60 text-purple-300' : 'bg-blue-900/60 text-blue-300'
            }`}>{data.market === 'hk' ? 'H' : 'A'}</span>
            <span className="font-mono text-sm text-gray-500">{data.code}</span>
            <span className="text-xs text-gray-500">{data.industry}</span>
          </div>
          <p className="mt-1 text-xs text-gray-500">
            最近交易日 {kline.length ? kline[kline.length - 1].date : '—'} · 数据快照 {data.snapshot?.date ?? '—'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => refresh.mutate()}
            disabled={refresh.isPending}
            className="px-3 py-1.5 rounded text-sm bg-gray-800 text-gray-300 hover:bg-gray-700 transition-colors disabled:opacity-50"
          >
            {refresh.isPending ? '刷新中…' : refresh.data?.status === 'skipped' ? `冷却中(${refresh.data.retry_after_sec}s)` : '刷新数据'}
          </button>
          <Link to="/pool" className="px-3 py-1.5 rounded text-sm bg-gray-800 text-gray-300 hover:bg-gray-700 transition-colors">
            返回
          </Link>
        </div>
      </div>

      {/* 概览卡片 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-gray-900 rounded-lg p-3 border border-gray-800">
          <div className="text-xs text-gray-500">现价</div>
          <div className="mt-1 text-2xl font-bold font-mono text-white">
            {fmtPrice(kline.length ? kline[kline.length - 1].close : null)}
          </div>
          <div className={`text-xs font-mono ${(kline[kline.length - 1]?.change_pct ?? 0) >= 0 ? 'text-red-400' : 'text-green-400'}`}>
            {fmtPct(kline[kline.length - 1]?.change_pct)}
          </div>
        </div>
        <div className="bg-gray-900 rounded-lg p-3 border border-gray-800">
          <div className="text-xs text-gray-500">TTM 股息率</div>
          <div className="mt-1 text-2xl font-bold font-mono text-orange-300">
            {data.current_yield != null ? `${data.current_yield.toFixed(2)}%` : '—'}
          </div>
          <div className="text-xs text-gray-500">每股股息 {data.dps_ttm != null ? `HK$ ${data.dps_ttm.toFixed(4)}` : '—'}</div>
        </div>
        <div className="bg-gray-900 rounded-lg p-3 border border-gray-800">
          <div className="text-xs text-gray-500">因子总分</div>
          <div className={`mt-1 text-2xl font-bold font-mono ${scoreColor(data.factors.total)}`}>
            {data.factors.total.toFixed(1)}
          </div>
          <div className="text-xs text-gray-500">
            等级
            <span className={`ml-1 px-1.5 py-0.5 rounded text-xs ${
              data.factors.grade === '优质' ? 'bg-red-900/60 text-red-300'
              : data.factors.grade === '良好' ? 'bg-orange-900/60 text-orange-300'
              : data.factors.grade === '一般' ? 'bg-yellow-900/60 text-yellow-300'
              : 'bg-gray-800 text-gray-400'
            }`}>{data.factors.grade}</span>
          </div>
        </div>
        <div className="bg-gray-900 rounded-lg p-3 border border-gray-800">
          <div className="text-xs text-gray-500">赔率(上行/下行)</div>
          <div className={`mt-1 text-2xl font-bold font-mono ${oddsColor(oddsInfo?.odds)}`}>
            {oddsInfo?.odds != null ? oddsInfo.odds.toFixed(2) : '—'}
          </div>
          <div className="text-xs text-gray-500">
            区间
            <span className={`ml-1 px-1.5 py-0.5 rounded text-xs ${zoneColor(range.zone)}`}>{range.zone}</span>
          </div>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-4">
        {/* 左: 图表区 */}
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
            <h3 className="text-sm font-medium text-gray-300 mb-2">日 K 线(前复权)</h3>
            <KlineChart kline={kline} />
          </div>
          <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
            <YieldZoneChart yieldSeries={data.yield_series} zone={range.zone} />
          </div>
        </div>

        {/* 右: 分析区 */}
        <div className="space-y-4">
          <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
            <h3 className="text-sm font-medium text-gray-300 mb-3">高股息因子明细</h3>
            <div className="space-y-3">
              {data.factors.components.length === 0 && (
                <p className="text-xs text-gray-500">暂无因子数据(需先重建数据)</p>
              )}
              {data.factors.components.map(c => (
                <FactorBar
                  key={c.key}
                  label={FACTOR_LABELS[c.key] ?? c.key}
                  score={c.score}
                  weight={c.weight}
                />
              ))}
            </div>
            {data.inputs.div_years != null && (
              <p className="mt-3 text-xs text-gray-500">
                近 5 年分红年数 {data.inputs.div_years} 年
                {data.inputs.div_growth != null && ` · 近 3 年股息增速 ${data.inputs.div_growth.toFixed(1)}%`}
              </p>
            )}
          </div>

          <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
            <h3 className="text-sm font-medium text-gray-300 mb-3">价格区间与赔率</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">区间判定</span>
                <span className={`px-2 py-0.5 rounded text-xs ${zoneColor(range.zone)}`}>{range.zone}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">中枢价(P50)</span>
                <span className="font-mono text-gray-200">{fmtPrice(anchors.central)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">低估阈值价(P75)</span>
                <span className="font-mono text-red-300">{fmtPrice(anchors.low)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">高估阈值价(P25)</span>
                <span className="font-mono text-green-300">{fmtPrice(anchors.high)}</span>
              </div>
              <div className="border-t border-gray-800 pt-2 flex justify-between">
                <span className="text-gray-500">乐观价(P25 股息率)</span>
                <span className="font-mono text-gray-200">{fmtPrice(anchors.optimistic)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">悲观支撑价(P95)</span>
                <span className="font-mono text-gray-400">{fmtPrice(anchors.pessimistic)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">上行空间</span>
                <span className="font-mono text-red-300">{oddsInfo?.upside_pct != null ? `${oddsInfo.upside_pct.toFixed(1)}%` : '—'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">下行空间</span>
                <span className="font-mono text-green-300">{oddsInfo?.downside_pct != null ? `${oddsInfo.downside_pct.toFixed(1)}%` : '—'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">赔率</span>
                <span className={`font-mono ${oddsColor(oddsInfo?.odds)}`}>
                  {oddsInfo?.odds != null ? oddsInfo.odds.toFixed(2) : '—'}
                  <span className="ml-1.5 text-xs text-gray-500">{oddsInfo?.grade}</span>
                </span>
              </div>
              {oddsInfo?.note && <p className="text-xs text-gray-500 pt-1">{oddsInfo.note}</p>}
            </div>
          </div>

          <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
            <h3 className="text-sm font-medium text-gray-300 mb-3">分红历史</h3>
            {data.dividends.length === 0 ? (
              <p className="text-xs text-gray-500">暂无分红数据</p>
            ) : (
              <div className="max-h-64 overflow-y-auto">
                <table className="w-full text-xs">
                  <thead className="text-gray-500 sticky top-0 bg-gray-900">
                    <tr>
                      <th className="text-left py-1 pr-2 font-medium">年度</th>
                      <th className="text-left py-1 pr-2 font-medium">除净日</th>
                      <th className="text-right py-1 pr-2 font-medium">每股派息</th>
                      <th className="text-left py-1 font-medium">备注</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.dividends.slice(0, 30).map((d, i) => (
                      <tr key={i} className="border-t border-gray-800/60">
                        <td className="py-1.5 pr-2 text-gray-300">{d.year ?? '—'}</td>
                        <td className="py-1.5 pr-2 font-mono text-gray-400">{d.ex_date ?? '—'}</td>
                        <td className="py-1.5 pr-2 text-right font-mono text-orange-300">
                          {d.cash_per_share != null ? d.cash_per_share.toFixed(4) : '—'}
                        </td>
                        <td className="py-1.5 text-gray-500 truncate max-w-[9rem]">{d.note ?? ''}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 个股资讯 */}
      <NewsCard code={code} />

      {/* AI 深度分析 */}
      <AiAnalysisCard code={code} />
    </div>
  )
}
