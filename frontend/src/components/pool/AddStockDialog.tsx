import { useState } from 'react'
import { useAddStock } from '../../hooks/useStocks'

/** 添加股票弹窗: 代码(5位港股/6位A股) → 市场自动识别 + 名称自动补全 → 拉取5年数据。
 *  成功添加后自动失效股票池查询, 页面即出新股分析。 */
export default function AddStockDialog({ onClose }: { onClose: () => void }) {
  const add = useAddStock()
  const [code, setCode] = useState('')
  const [name, setName] = useState('')
  const [market, setMarket] = useState('')
  const [error, setError] = useState('')
  const [done, setDone] = useState<string | null>(null)

  const submit = () => {
    setError('')
    setDone(null)
    add.mutate(
      { code: code.trim(), name: name.trim() || undefined, market: market || undefined },
      {
        onError: e => setError(e.message),
        onSuccess: res => {
          if (res.status !== 'ok') setError(res.message)
          else {
            setDone(res.message)
            setTimeout(onClose, 600) // 短暂提示后关闭
          }
        },
      },
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={() => !add.isPending && onClose()} />
      <div className="relative w-[26rem] max-w-[92vw] bg-gray-900 border border-gray-700 rounded-xl p-5 shadow-2xl">
        <h3 className="text-base font-bold text-white mb-1">添加自选股票</h3>
        <p className="text-xs text-gray-500 mb-4">
          支持任意 A 股 / 港股(5位港股代码、6位A股代码)。市场自动识别, 名称自动补全;
          添加后自动拉取约 5 年 K 线 + 分红并生成因子分析。
        </p>
        <div className="space-y-3">
          <input
            value={code}
            onChange={e => setCode(e.target.value)}
            placeholder="股票代码, 如 601899 / 000858 / 00941"
            autoFocus
            className="w-full px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-200 text-sm placeholder-gray-600"
          />
          <div className="flex gap-2">
            <input
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="名称(留空自动补全)"
              className="flex-1 px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-200 text-sm placeholder-gray-600"
            />
            <select
              value={market}
              onChange={e => setMarket(e.target.value)}
              className="px-2 py-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-300 text-sm"
            >
              <option value="">市场自动</option>
              <option value="hk">港股 H</option>
              <option value="sh">沪市 A</option>
              <option value="sz">深市 A</option>
            </select>
          </div>
        </div>
        {add.data?.message && !error && !done && (
          <p className="mt-2 text-xs text-emerald-300">{add.data.message}</p>
        )}
        {done && <p className="mt-2 text-xs text-emerald-300">{done} ✓</p>}
        {error && <p className="mt-2 text-xs text-red-400">{error}</p>}
        <div className="mt-4 flex justify-end gap-2">
          <button
            onClick={onClose}
            disabled={add.isPending}
            className="px-4 py-2 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-gray-800 transition-colors disabled:opacity-40"
          >
            取消
          </button>
          <button
            onClick={submit}
            disabled={add.isPending || !code.trim()}
            className="px-4 py-2 rounded-lg text-sm bg-red-900/70 text-red-200 hover:bg-red-800/70 transition-colors disabled:opacity-40"
          >
            {add.isPending ? '添加并拉取数据中(约10~30秒)…' : '添加股票'}
          </button>
        </div>
      </div>
    </div>
  )
}
