import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import AddStockDialog from '../components/pool/AddStockDialog'
import {
  fmtPct,
  fmtPrice,
  oddsColor,
  scoreColor,
  SORT_DEFAULT_ASC,
  sortStocks,
  usePool,
  zoneColor,
} from '../hooks/useStocks'
import type { SortKey } from '../hooks/useStocks'
import type { PoolStock } from '../api/types'

function SortHeader({
  label,
  sortKey,
  activeKey,
  asc,
  onSort,
  align = 'left',
}: {
  label: string
  sortKey: SortKey
  activeKey: SortKey
  asc: boolean
  onSort: (key: SortKey) => void
  align?: 'left' | 'right' | 'center'
}) {
  const active = activeKey === sortKey
  return (
    <th
      onClick={() => onSort(sortKey)}
      title="点击排序"
      className={`py-2 pr-3 font-medium select-none cursor-pointer whitespace-nowrap transition-colors hover:text-gray-300 ${
        align === 'right' ? 'text-right' : align === 'center' ? 'text-center' : 'text-left'
      } ${active ? 'text-white' : ''}`}
    >
      {label}
      <span className="ml-0.5 text-[10px]">{active ? (asc ? '▲' : '▼') : ''}</span>
    </th>
  )
}

function PoolTable({ stocks }: { stocks: PoolStock[] }) {
  const navigate = useNavigate()
  const [sortKey, setSortKey] = useState<SortKey>('score')
  const [asc, setAsc] = useState(false)

  const sorted = useMemo(() => sortStocks(stocks, sortKey, asc), [stocks, sortKey, asc])

  const handleSort = (key: SortKey) => {
    if (key === sortKey) {
      setAsc(v => !v)
    } else {
      setSortKey(key)
      setAsc(SORT_DEFAULT_ASC[key])
    }
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-gray-500 border-b border-gray-800">
            <th className="py-2 pr-3 font-medium">代码 / 名称</th>
            <th className="py-2 pr-3 font-medium">行业</th>
            <SortHeader label="现价" sortKey="price" activeKey={sortKey} asc={asc} onSort={handleSort} align="right" />
            <SortHeader label="涨跌幅" sortKey="change_pct" activeKey={sortKey} asc={asc} onSort={handleSort} align="right" />
            <SortHeader label="股息率" sortKey="div_yield" activeKey={sortKey} asc={asc} onSort={handleSort} align="right" />
            <SortHeader label="因子分" sortKey="score" activeKey={sortKey} asc={asc} onSort={handleSort} align="right" />
            <th className="py-2 pr-3 text-center font-medium">等级</th>
            <SortHeader label="价格区间" sortKey="zone" activeKey={sortKey} asc={asc} onSort={handleSort} align="center" />
            <SortHeader label="赔率" sortKey="odds" activeKey={sortKey} asc={asc} onSort={handleSort} align="right" />
            <SortHeader label="目标价" sortKey="target_price" activeKey={sortKey} asc={asc} onSort={handleSort} align="right" />
            <th className="py-2 font-medium">支撑价</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map(s => (
            <tr
              key={s.code}
              onClick={() => navigate(`/stock/${s.code}`)}
              className="border-b border-gray-800/60 hover:bg-gray-800/40 cursor-pointer transition-colors"
            >
              <td className="py-2.5 pr-3">
                <span className="text-gray-400 font-mono text-xs mr-1.5">{s.code}</span>
                <span className={`inline-block w-4 text-center text-[10px] rounded mr-1 align-middle ${
                  s.market === 'hk' ? 'bg-purple-900/60 text-purple-300' : 'bg-blue-900/60 text-blue-300'
                }`}>{s.market === 'hk' ? 'H' : 'A'}</span>
                {s.custom && <span className="mr-1 text-[10px] text-emerald-400 align-middle">自定义</span>}
                <span className="text-gray-100 font-medium">{s.name}</span>
                {s.realtime && <span className="ml-1.5 text-[10px] text-emerald-400 align-middle">实时</span>}
              </td>
              <td className="py-2.5 pr-3 text-gray-400">{s.industry}</td>
              <td className="py-2.5 pr-3 text-right font-mono">{fmtPrice(s.price)}</td>
              <td className={`py-2.5 pr-3 text-right font-mono ${(s.change_pct ?? 0) >= 0 ? 'text-red-400' : 'text-green-400'}`}>
                {fmtPct(s.change_pct)}
              </td>
              <td className="py-2.5 pr-3 text-right font-mono text-orange-300">
                {s.div_yield != null ? `${s.div_yield.toFixed(2)}%` : '—'}
              </td>
              <td className={`py-2.5 pr-3 text-right font-mono ${scoreColor(s.score)}`}>
                {s.score != null ? s.score.toFixed(1) : '—'}
              </td>
              <td className="py-2.5 pr-3 text-center">
                <span
                  className={`px-2 py-0.5 rounded text-xs ${
                    s.grade === '优质' ? 'bg-red-900/60 text-red-300'
                    : s.grade === '良好' ? 'bg-orange-900/60 text-orange-300'
                    : s.grade === '一般' ? 'bg-yellow-900/60 text-yellow-300'
                    : 'bg-gray-800 text-gray-400'
                  }`}
                >
                  {s.grade}
                </span>
              </td>
              <td className="py-2.5 pr-3 text-center">
                <span className={`px-2 py-0.5 rounded text-xs ${zoneColor(s.zone)}`}>{s.zone}</span>
              </td>
              <td className={`py-2.5 pr-3 text-right font-mono ${oddsColor(s.odds)}`}>
                {s.odds != null ? s.odds.toFixed(2) : '—'}
              </td>
              <td className="py-2.5 pr-3 text-right font-mono text-gray-300">{fmtPrice(s.target_price)}</td>
              <td className="py-2.5 font-mono text-gray-400">{fmtPrice(s.support_price)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function Dashboard() {
  const { data, isLoading, isError, refetch, isFetching } = usePool()
  const [showAdd, setShowAdd] = useState(false)
  const stocks = data?.stocks ?? []

  const avgYield = (() => {
    const ys = stocks.map(s => s.div_yield).filter((v): v is number => v != null)
    return ys.length ? ys.reduce((a, b) => a + b, 0) / ys.length : null
  })()
  const goodCount = stocks.filter(s => (s.score ?? 0) >= 75).length
  const cheapCount = stocks.filter(s => ['低估', '深度低估'].includes(s.zone)).length
  const highOddsCount = stocks.filter(s => (s.odds ?? 0) >= 3).length

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">红筹高股息股票池</h2>
          <p className="mt-1 text-xs text-gray-500">
            高股息六因子打分 × 股息率锚定价格区间 × 赔率。点击行进入个股详情，点击表头排序（价格区间：深度低估在前）。
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowAdd(true)}
            className="px-3 py-1.5 rounded text-sm bg-emerald-900/70 text-emerald-200 hover:bg-emerald-800/70 transition-colors"
          >
            + 添加股票
          </button>
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="px-3 py-1.5 rounded text-sm bg-gray-800 text-gray-300 hover:bg-gray-700 transition-colors disabled:opacity-50"
          >
            {isFetching ? '刷新中…' : '刷新'}
          </button>
        </div>
      </div>

      {showAdd && <AddStockDialog onClose={() => setShowAdd(false)} />}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: '池内标的', value: String(stocks.length), cls: 'text-white' },
          { label: '平均股息率', value: avgYield != null ? `${avgYield.toFixed(2)}%` : '—', cls: 'text-orange-300' },
          { label: '优质股(≥75分)', value: String(goodCount), cls: 'text-red-400' },
          { label: '低估区', value: String(cheapCount), cls: 'text-red-300' },
          { label: '高赔率(≥3)', value: String(highOddsCount), cls: 'text-orange-400' },
        ].map(card => (
          <div key={card.label} className="bg-gray-900 rounded-lg p-3 border border-gray-800">
            <div className="text-xs text-gray-500">{card.label}</div>
            <div className={`mt-1 text-2xl font-bold font-mono ${card.cls}`}>{card.value}</div>
          </div>
        ))}
      </div>

      {isLoading && <div className="py-16 text-center text-sm text-gray-500">加载中…</div>}
      {isError && (
        <div className="py-16 text-center text-sm text-gray-500">
          后端不可用或尚未初始化, 请确认后端已启动(端口 8092)。
        </div>
      )}
      {!isLoading && !isError && stocks.length === 0 && (
        <div className="py-16 text-center text-sm text-gray-500">
          股票池暂无数据 —— 请先到「数据管理」页点击「一键重建」拉取 K 线与分红数据。
        </div>
      )}
      {!isLoading && !isError && stocks.length > 0 && <PoolTable stocks={stocks} />}
    </div>
  )
}
