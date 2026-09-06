import { useState } from 'react'
import AiSettingsCard from '../components/analysis/AiSettingsCard'
import {
  useAddStock,
  useCustomStocks,
  useDataStatus,
  useRebuildData,
  useRemoveStock,
} from '../hooks/useStocks'

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(2)} MB`
}

/** 股票池管理: 添加自定义股票 + 删除 */
function PoolManager() {
  const { data: customData, refetch } = useCustomStocks()
  const add = useAddStock()
  const remove = useRemoveStock()
  const [code, setCode] = useState('')
  const [name, setName] = useState('')
  const [market, setMarket] = useState('')
  const [error, setError] = useState('')

  const custom = customData?.stocks ?? []

  const submit = () => {
    setError('')
    add.mutate(
      {
        code: code.trim(),
        name: name.trim() || undefined,
        market: market || undefined,
      },
      {
        onError: e => setError(e.message),
        onSuccess: res => {
          if (res.status !== 'ok') setError(res.message)
          else {
            setCode('')
            setName('')
            setMarket('')
            refetch()
          }
        },
      },
    )
  }

  return (
    <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
      <h3 className="text-sm font-medium text-gray-300 mb-3">股票池管理</h3>
      <div className="flex flex-wrap items-center gap-2">
        <input
          value={code}
          onChange={e => setCode(e.target.value)}
          placeholder="股票代码(5位港股/6位A股)"
          className="w-44 px-2 py-1.5 rounded bg-gray-800 border border-gray-700 text-gray-200 text-sm placeholder-gray-600"
        />
        <input
          value={name}
          onChange={e => setName(e.target.value)}
          placeholder="名称(可留空自动补全)"
          className="w-40 px-2 py-1.5 rounded bg-gray-800 border border-gray-700 text-gray-200 text-sm placeholder-gray-600"
        />
        <select
          value={market}
          onChange={e => setMarket(e.target.value)}
          className="px-2 py-1.5 rounded bg-gray-800 border border-gray-700 text-gray-300 text-sm"
        >
          <option value="">市场(自动)</option>
          <option value="hk">港股 H</option>
          <option value="sh">沪市 A</option>
          <option value="sz">深市 A</option>
        </select>
        <button
          onClick={submit}
          disabled={add.isPending || !code.trim()}
          className="px-4 py-1.5 rounded text-sm bg-emerald-900/70 text-emerald-200 hover:bg-emerald-800/70 transition-colors disabled:opacity-50"
        >
          {add.isPending ? '添加并拉取数据中…' : '添加股票'}
        </button>
      </div>
      {add.data?.message && !error && (
        <p className="mt-2 text-xs text-emerald-300">{add.data.message}</p>
      )}
      {error && <p className="mt-2 text-xs text-red-400">{error}</p>}
      <p className="mt-2 text-xs text-gray-500">
        添加后自动拉取约 5 年 K 线 + 分红并计算因子快照(约 10~30 秒)。
        代码格式: 5 位为港股, 6 位按开头自动识别沪深(北交所暂不支持)。
      </p>

      {custom.length > 0 && (
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-gray-500 border-b border-gray-800">
                <th className="py-1.5 pr-3 font-medium">代码</th>
                <th className="py-1.5 pr-3 font-medium">名称</th>
                <th className="py-1.5 pr-3 font-medium">市场</th>
                <th className="py-1.5 pr-3 font-medium">行业</th>
                <th className="py-1.5 pr-3 font-medium">添加时间</th>
                <th className="py-1.5 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {custom.map(s => (
                <tr key={s.code} className="border-b border-gray-800/60">
                  <td className="py-1.5 pr-3 font-mono text-gray-300 text-xs">{s.code}</td>
                  <td className="py-1.5 pr-3 text-gray-200">{s.name}</td>
                  <td className="py-1.5 pr-3 text-xs text-gray-500">
                    {s.market === 'hk' ? '港股 H' : s.market === 'sh' ? '沪市 A' : '深市 A'}
                  </td>
                  <td className="py-1.5 pr-3 text-gray-500">{s.industry ?? '—'}</td>
                  <td className="py-1.5 pr-3 font-mono text-xs text-gray-500">{s.created_at}</td>
                  <td className="py-1.5 text-right">
                    <button
                      onClick={() => {
                        if (window.confirm(`移除 ${s.name}(${s.code})? 其数据也会被清理。`)) remove.mutate(s.code)
                      }}
                      disabled={remove.isPending}
                      className="text-xs text-red-400 hover:text-red-300 disabled:opacity-50"
                    >
                      移除
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {custom.length === 0 && (
        <p className="mt-3 text-xs text-gray-500">暂无自定义股票。内置池中的股票不可在此删除(编辑 config.STOCKS 可调整)。</p>
      )}
    </div>
  )
}

export default function DataManage() {
  const { data, isLoading } = useDataStatus()
  const rebuild = useRebuildData()
  const [days, setDays] = useState(1250)

  const stocks = data?.stocks ?? []
  const hasAnyData = stocks.some(s => s.daily_count > 0 || s.dividend_count > 0)
  const failed = rebuild.data?.failed ?? []

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold text-white">数据管理</h2>
        <p className="mt-1 text-xs text-gray-500">
          数据源: 腾讯行情(A/H 日 K / 实时) + akshare 东财(分红)。全部数据本地落库(SQLite)。
        </p>
      </div>

      <PoolManager />

      <AiSettingsCard />

      {/* 一键重建 */}
      <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
        <h3 className="text-sm font-medium text-gray-300 mb-3">一键重建</h3>
        <div className="flex flex-wrap items-center gap-3">
          <label className="text-xs text-gray-500">
            回填深度(交易日, 默认≈5年)
            <input
              type="number"
              value={days}
              min={60}
              max={2000}
              onChange={e => setDays(Number(e.target.value))}
              className="ml-2 w-24 px-2 py-1 rounded bg-gray-800 border border-gray-700 text-gray-200 text-sm"
            />
          </label>
          <button
            onClick={() => rebuild.mutate(days)}
            disabled={rebuild.isPending}
            className="px-4 py-2 rounded text-sm bg-red-900/70 text-red-200 hover:bg-red-800/70 transition-colors disabled:opacity-50"
          >
            {rebuild.isPending ? '重建中…(约 1~2 分钟)' : '全量重建'}
          </button>
          <span className="text-xs text-gray-500">
            为全部 {stocks.length || 41} 只股票拉取 K 线 + 分红 + 因子快照
          </span>
        </div>
        {rebuild.isPending && (
          <p className="mt-3 text-xs text-orange-300">正在拉取数据, 请勿关闭页面 …</p>
        )}
        {rebuild.data && (
          <div className="mt-3 text-xs">
            <span className="text-gray-300">
              完成: 成功 {rebuild.data.ok} / 共 {rebuild.data.total}
            </span>
            {failed.length > 0 && (
              <ul className="mt-1 text-red-400">
                {failed.map(f => (
                  <li key={f.code}>
                    {f.name}({f.code}): {f.error ?? '未知错误'}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
        {!isLoading && !rebuild.data && !hasAnyData && (
          <p className="mt-3 text-xs text-gray-500">
            首次使用: 点击「全量重建」即可 bootstrap 全部数据, 无需任何脚本。
          </p>
        )}
      </div>

      {/* 数据状态表 */}
      <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
        <h3 className="text-sm font-medium text-gray-300 mb-3">
          数据覆盖状态
          {data && <span className="ml-2 text-xs text-gray-500">数据库 {formatBytes(data.db_size)}</span>}
        </h3>
        {isLoading ? (
          <p className="py-8 text-center text-sm text-gray-500">加载中…</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 border-b border-gray-800">
                  <th className="py-2 pr-3 font-medium">代码</th>
                  <th className="py-2 pr-3 font-medium">名称</th>
                  <th className="py-2 pr-3 text-right font-medium">K线数</th>
                  <th className="py-2 pr-3 font-medium">K线区间</th>
                  <th className="py-2 pr-3 text-right font-medium">分红记录</th>
                  <th className="py-2 pr-3 font-medium">最近除净</th>
                  <th className="py-2 font-medium">快照日期</th>
                </tr>
              </thead>
              <tbody>
                {stocks.map(s => (
                  <tr key={s.code} className="border-b border-gray-800/60">
                    <td className="py-2 pr-3 font-mono text-gray-400 text-xs">{s.code}</td>
                    <td className="py-2 pr-3 text-gray-200">{s.name}</td>
                    <td className="py-2 pr-3 text-right font-mono text-gray-300">{s.daily_count}</td>
                    <td className="py-2 pr-3 font-mono text-xs text-gray-500">
                      {s.daily_first ? `${s.daily_first} ~ ${s.daily_last ?? '?'}` : '—'}
                    </td>
                    <td className="py-2 pr-3 text-right font-mono text-gray-300">{s.dividend_count}</td>
                    <td className="py-2 pr-3 font-mono text-xs text-gray-500">{s.dividend_last ?? '—'}</td>
                    <td className="py-2 font-mono text-xs text-gray-500">{s.snapshot_date ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
