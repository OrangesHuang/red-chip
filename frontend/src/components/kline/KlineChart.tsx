import ReactECharts from 'echarts-for-react'
import { useMemo } from 'react'
import type { KlineBar } from '../../api/types'

/** 日 K 蜡烛图 + MA5/20/60 + 成交量。数据为空时显示占位。 */
export default function KlineChart({ kline, height = 420 }: { kline: KlineBar[]; height?: number }) {
  const option = useMemo(() => {
    if (!kline.length) return null
    const dates = kline.map(k => k.date)
    const ohlc = kline.map(k => [k.open, k.close, k.low, k.high])
    const volumes = kline.map(k => k.volume)
    const closes = kline.map(k => k.close)

    const ma = (n: number) =>
      closes.map((_, i) => {
        if (i < n - 1) return null
        const window = closes.slice(i - n + 1, i + 1)
        return +(window.reduce((a, b) => a + b, 0) / n).toFixed(3)
      })

    return {
      backgroundColor: 'transparent',
      animation: false,
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
        backgroundColor: 'rgba(17,24,39,0.92)',
        borderColor: '#374151',
        textStyle: { color: '#e5e7eb', fontSize: 12 },
      },
      legend: {
        data: ['MA5', 'MA20', 'MA60'],
        textStyle: { color: '#9ca3af' },
        top: 0,
      },
      grid: [
        { left: 60, right: 16, top: 28, height: '62%' },
        { left: 60, right: 16, top: '78%', height: '14%' },
      ],
      xAxis: [
        { type: 'category', data: dates, boundaryGap: true, axisLine: { lineStyle: { color: '#374151' } }, axisLabel: { color: '#6b7280' } },
        { type: 'category', gridIndex: 1, data: dates, axisLabel: { show: false }, axisLine: { lineStyle: { color: '#374151' } } },
      ],
      yAxis: [
        { scale: true, splitLine: { lineStyle: { color: '#1f2937' } }, axisLabel: { color: '#6b7280' } },
        { gridIndex: 1, splitLine: { show: false }, axisLabel: { color: '#6b7280' } },
      ],
      dataZoom: [
        { type: 'inside', xAxisIndex: [0, 1], start: Math.max(0, 100 - (120 / dates.length) * 100), end: 100 },
      ],
      series: [
        {
          name: 'K线',
          type: 'candlestick',
          data: ohlc,
          itemStyle: {
            color: '#ef4444',
            color0: '#22c55e',
            borderColor: '#ef4444',
            borderColor0: '#22c55e',
          },
        },
        { name: 'MA5', type: 'line', data: ma(5), smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#f59e0b' } },
        { name: 'MA20', type: 'line', data: ma(20), smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#3b82f6' } },
        { name: 'MA60', type: 'line', data: ma(60), smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#a855f7' } },
        {
          name: '成交量',
          type: 'bar',
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: volumes,
          itemStyle: { color: '#4b5563' },
        },
      ],
    }
  }, [kline])

  if (!option) {
    return (
      <div className="flex items-center justify-center h-64 text-sm text-gray-500">
        暂无 K 线数据, 请先到「数据管理」页重建数据
      </div>
    )
  }
  return <ReactECharts option={option} style={{ height }} notMerge />
}
