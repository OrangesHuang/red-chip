import ReactECharts from 'echarts-for-react'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { fmtPct, fmtPrice, useZoneStats, zoneColor } from '../hooks/useStocks'
import type { ZoneStat, ZoneStatStock } from '../api/types'

function ZoneChart({ zones }: { zones: ZoneStat[] }) {
  const option = useMemo(() => {
    return {
      backgroundColor: 'transparent',
      animation: false,
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        backgroundColor: 'rgba(17,24,39,0.92)',
        borderColor: '#374151',
        textStyle: { color: '#e5e7eb', fontSize: 12 },
      },
      legend: {
        data: ['上涨', '下跌', '持平', '胜率'],
        textStyle: { color: '#9ca3af', fontSize: 11 },
        top: 0,
      },
      grid: { left: 44, right: 52, top: 40, bottom: 28 },
      xAxis: {
        type: 'category',
        data: zones.map(z => z.zone),
        axisLine: { lineStyle: { color: '#374151' } },
        axisLabel: { color: '#9ca3af' },
      },
      yAxis: [
        {
          type: 'value',
          name: '家数',
          minInterval: 1,
          nameTextStyle: { color: '#6b7280' },
          splitLine: { lineStyle: { color: '#1f2937' } },
          axisLabel: { color: '#6b7280' },
        },
        {
          type: 'value',
          name: '胜率 %',
          min: 0,
          max: 100,
          nameTextStyle: { color: '#6b7280' },
          splitLine: { show: false },
          axisLabel: { color: '#6b7280', formatter: '{value}%' },
        },
      ],
      series: [
        { name: '上涨', type: 'bar', stack: 'chg', data: zones.map(z => z.up), itemStyle: { color: '#ef4444' } },
        { name: '下跌', type: 'bar', stack: 'chg', data: zones.map(z => z.down), itemStyle: { color: '#22c55e' } },
        { name: '持平', type: 'bar', stack: 'chg', data: zones.map(z => z.flat), itemStyle: { color: '#6b7280' } },
        {
          name: '胜率',
          type: 'line',
          yAxisIndex: 1,
          data: zones.map(z => z.win_rate),
          connectNulls: false,
          symbolSize: 7,
          lineStyle: { color: '#f59e0b', width: 2 },
          itemStyle: { color: '#f59e0b' },
        },
      ],
    }
  }, [zones])

  return <ReactECharts option={option} style={{ height: 320 }} notMerge />
}

function ZoneTable({ zones, onSelectZone }: { zones: ZoneStat[]; onSelectZone: (z: ZoneStat) => void }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-gray-500 border-b border-gray-800">
            <th className="py-2 pr-3 font-medium">价格区间</th>
            <th className="py-2 pr-3 text-right font-medium">数量</th>
            <th className="py-2 pr-3 text-right font-medium">上涨</th>
            <th className="py-2 pr-3 text-right font-medium">下跌</th>
            <th className="py-2 pr-3 text-right font-medium">持平</th>
            <th className="py-2 pr-3 text-right font-medium">胜率</th>
            <th className="py-2 text-right font-medium">平均涨跌</th>
          </tr>
        </thead>
        <tbody>
          {zones.map(z => (
            <tr key={z.zone} className="border-b border-gray-800/60">
              <td className="py-2.5 pr-3">
                <span className={`px-2 py-0.5 rounded text-xs ${zoneColor(z.zone)}`}>{z.zone}</span>
              </td>
              <td
                onClick={() => z.count > 0 && onSelectZone(z)}
                title={z.count > 0 ? '点击查看该区间的标的' : undefined}
                className={`py-2.5 pr-3 text-right font-mono transition-colors ${
                  z.count > 0
                    ? 'text-sky-400 underline decoration-dotted underline-offset-2 cursor-pointer hover:text-sky-300'
                    : 'text-gray-600'
                }`}
              >
                {z.count}
              </td>
              <td className="py-2.5 pr-3 text-right font-mono text-red-400">{z.up}</td>
              <td className="py-2.5 pr-3 text-right font-mono text-green-400">{z.down}</td>
              <td className="py-2.5 pr-3 text-right font-mono text-gray-400">{z.flat}</td>
              <td className="py-2.5 pr-3 text-right font-mono text-orange-300">
                {z.win_rate != null ? `${z.win_rate.toFixed(1)}%` : '—'}
              </td>
              <td className={`py-2.5 text-right font-mono ${(z.avg_change ?? 0) >= 0 ? 'text-red-400' : 'text-green-400'}`}>
                {fmtPct(z.avg_change)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function StockLine({ stock, onPick }: { stock: ZoneStatStock; onPick: (code: string) => void }) {
  const up = (stock.change_pct ?? 0) >= 0
  return (
    <button
      type="button"
      onClick={() => stock.code && onPick(stock.code)}
      className="w-full flex items-center gap-2 rounded px-2 py-2 text-left text-sm hover:bg-gray-800/70 transition-colors"
    >
      <span className="text-gray-400 font-mono text-xs">{stock.code}</span>
      <span
        className={`inline-block w-4 text-center text-[10px] rounded ${
          stock.market === 'hk' ? 'bg-purple-900/60 text-purple-300' : 'bg-blue-900/60 text-blue-300'
        }`}
      >
        {stock.market === 'hk' ? 'H' : 'A'}
      </span>
      <span className="flex-1 text-gray-100 truncate">{stock.name}</span>
      <span className="font-mono text-gray-300">{fmtPrice(stock.price)}</span>
      <span className={`w-16 text-right font-mono ${up ? 'text-red-400' : 'text-green-400'}`}>
        {fmtPct(stock.change_pct)}
      </span>
    </button>
  )
}

function ZoneStocksModal({ zone, onClose }: { zone: ZoneStat; onClose: () => void }) {
  const navigate = useNavigate()
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/60" />
      <div
        onClick={e => e.stopPropagation()}
        className="relative z-10 w-full max-w-md max-h-[80vh] flex flex-col rounded-lg border border-gray-700 bg-gray-900 shadow-xl"
      >
        <div className="flex items-center justify-between border-b border-gray-800 px-4 py-3">
          <div className="flex items-center gap-2">
            <span className={`px-2 py-0.5 rounded text-xs ${zoneColor(zone.zone)}`}>{zone.zone}</span>
            <span className="text-xs text-gray-400">共 {zone.count} 只 · 上涨 {zone.up} / 下跌 {zone.down}</span>
          </div>
          <button
            onClick={onClose}
            className="rounded px-2 text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
            aria-label="关闭"
          >
            ✕
          </button>
        </div>
        <div className="overflow-y-auto p-2">
          {zone.stocks.length === 0 ? (
            <div className="py-10 text-center text-sm text-gray-500">该区间暂无标的</div>
          ) : (
            zone.stocks.map((s, i) => (
              <StockLine
                key={`${s.code ?? s.name ?? 'stock'}-${i}`}
                stock={s}
                onPick={code => {
                  onClose()
                  navigate(`/stock/${code}`)
                }}
              />
            ))
          )}
        </div>
      </div>
    </div>
  )
}

export default function ZoneBoard() {
  const { data, isLoading, isError } = useZoneStats()
  const zones = data?.zones ?? []
  const overall = data?.overall
  const [activeZone, setActiveZone] = useState<ZoneStat | null>(null)

  const cards = [
    { label: '池内标的', value: String(overall?.count ?? 0), cls: 'text-white' },
    { label: '当日上涨', value: String(overall?.up ?? 0), cls: 'text-red-400' },
    { label: '当日下跌', value: String(overall?.down ?? 0), cls: 'text-green-400' },
    { label: '综合胜率', value: overall?.win_rate != null ? `${overall.win_rate.toFixed(1)}%` : '—', cls: 'text-orange-300' },
    {
      label: '等权综合涨跌',
      value: fmtPct(overall?.equal_weight_return),
      cls: (overall?.equal_weight_return ?? 0) >= 0 ? 'text-red-400' : 'text-green-400',
    },
  ]

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold text-white">价格区间看板</h2>
        <p className="mt-1 text-xs text-gray-500">
          按股息率锚定的价格区间统计数量与当日涨跌。等权综合涨跌 = 资金平均分配到池内每只标的，
          组合当日涨跌即各标的涨跌幅的算术平均。数据时间: {data?.updated_at || '—'}
        </p>
      </div>

      {isLoading && <div className="py-16 text-center text-sm text-gray-500">加载中…</div>}
      {isError && (
        <div className="py-16 text-center text-sm text-gray-500">
          后端不可用或尚未初始化, 请确认后端已启动(端口 8092)。
        </div>
      )}

      {!isLoading && !isError && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {cards.map(card => (
              <div key={card.label} className="bg-gray-900 rounded-lg p-3 border border-gray-800">
                <div className="text-xs text-gray-500">{card.label}</div>
                <div className={`mt-1 text-2xl font-bold font-mono ${card.cls}`}>{card.value}</div>
              </div>
            ))}
          </div>

          <div className="bg-gray-900 rounded-lg p-3 border border-gray-800">
            <div className="mb-2 text-xs text-gray-400">各区间涨跌分布与胜率</div>
            <ZoneChart zones={zones} />
          </div>

          <div className="bg-gray-900 rounded-lg p-3 border border-gray-800">
            <div className="mb-2 text-xs text-gray-400">区间明细（点击蓝色「数量」查看该区间标的）</div>
            <ZoneTable zones={zones} onSelectZone={setActiveZone} />
          </div>

          {activeZone && <ZoneStocksModal zone={activeZone} onClose={() => setActiveZone(null)} />}
        </>
      )}
    </div>
  )
}
