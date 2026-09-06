import ReactECharts from 'echarts-for-react'
import { useMemo } from 'react'
import type { YieldPoint } from '../../api/types'

/** 股息率历史曲线 + 区间分位带(P25/P75/P90 参考线)。 */
export default function YieldZoneChart({
  yieldSeries,
  zone,
  height = 240,
}: {
  yieldSeries: YieldPoint[]
  zone: string
  height?: number
}) {
  const option = useMemo(() => {
    const points = yieldSeries.filter(p => p.div_yield != null)
    if (points.length < 2) return null
    const dates = points.map(p => p.date)
    const values = points.map(p => p.div_yield as number)
    const sorted = [...values].sort((a, b) => a - b)
    const pct = (q: number) => sorted[Math.min(sorted.length - 1, Math.floor((sorted.length - 1) * q / 100))]

    const markLines = [
      { yAxis: pct(75), name: 'P75 低估线', lineStyle: { color: '#ef4444', type: 'dashed' as const } },
      { yAxis: pct(50), name: 'P50 中枢', lineStyle: { color: '#f59e0b', type: 'dashed' as const } },
      { yAxis: pct(25), name: 'P25 高估线', lineStyle: { color: '#22c55e', type: 'dashed' as const } },
    ]

    return {
      backgroundColor: 'transparent',
      animation: false,
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(17,24,39,0.92)',
        borderColor: '#374151',
        textStyle: { color: '#e5e7eb', fontSize: 12 },
      },
      grid: { left: 50, right: 16, top: 28, bottom: 24 },
      xAxis: {
        type: 'category',
        data: dates,
        axisLine: { lineStyle: { color: '#374151' } },
        axisLabel: { color: '#6b7280' },
      },
      yAxis: {
        type: 'value',
        name: '股息率 %',
        nameTextStyle: { color: '#6b7280' },
        scale: true,
        splitLine: { lineStyle: { color: '#1f2937' } },
        axisLabel: { color: '#6b7280' },
      },
      series: [
        {
          name: 'TTM股息率',
          type: 'line',
          data: values,
          smooth: true,
          showSymbol: false,
          lineStyle: { color: '#f59e0b', width: 1.5 },
          areaStyle: { color: 'rgba(245,158,11,0.08)' },
          markLine: {
            symbol: 'none',
            label: { color: '#9ca3af', fontSize: 10, formatter: '{b}' },
            data: markLines,
          },
        },
      ],
    }
  }, [yieldSeries])

  if (!option) {
    return (
      <div className="flex items-center justify-center h-40 text-sm text-gray-500">
        暂无股息率历史(需分红数据)
      </div>
    )
  }
  return (
    <div>
      <div className="mb-1 flex items-center gap-2 text-xs text-gray-400">
        <span>TTM 股息率走势</span>
        <span className="text-gray-600">·</span>
        <span>当前区间: <span className="text-gray-200">{zone}</span></span>
      </div>
      <ReactECharts option={option} style={{ height }} notMerge />
    </div>
  )
}
