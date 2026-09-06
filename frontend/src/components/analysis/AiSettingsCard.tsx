import { useState } from 'react'
import { useAnalysisSettings, useSaveAnalysisSettings, useTestLLM } from '../../hooks/useStocks'

/** AI 分析设置: API Key(本地存储) / 模型 / 端点 + 连通性测试。 */
export default function AiSettingsCard() {
  const { data: settings, isLoading } = useAnalysisSettings()
  const save = useSaveAnalysisSettings()
  const test = useTestLLM()
  const [apiKey, setApiKey] = useState('')
  const [model, setModel] = useState('')
  const [baseUrl, setBaseUrl] = useState('')

  // 首次加载后用当前配置填充表单(模型/端点)
  if (settings && !model && !apiKey && !baseUrl) {
    setModel(settings.model)
    setBaseUrl(settings.base_url)
  }

  const doSave = () => {
    save.mutate(
      { api_key: apiKey.trim() || undefined, model: model.trim() || undefined, base_url: baseUrl.trim() || undefined },
      { onSuccess: () => setApiKey('') },
    )
  }

  const doTest = () => {
    test.mutate({ api_key: apiKey.trim() || undefined, model: model.trim() || undefined, base_url: baseUrl.trim() || undefined })
  }

  return (
    <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
      <h3 className="text-sm font-medium text-gray-300 mb-3">AI 分析设置（DeepSeek）</h3>

      {isLoading ? (
        <p className="text-xs text-gray-500">加载中…</p>
      ) : (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <label className="text-xs text-gray-500 w-24 shrink-0">API Key</label>
            <input
              type="password"
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
              placeholder={settings?.configured ? `已配置 ${settings.key_masked}(留空不修改)` : 'sk-...'}
              className="flex-1 min-w-52 px-2 py-1.5 rounded bg-gray-800 border border-gray-700 text-gray-200 text-sm placeholder-gray-600"
            />
            <span className="text-[11px] text-gray-600">仅存本地 SQLite</span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <label className="text-xs text-gray-500 w-24 shrink-0">模型</label>
            <input
              value={model}
              onChange={e => setModel(e.target.value)}
              placeholder="deepseek-chat"
              className="w-48 px-2 py-1.5 rounded bg-gray-800 border border-gray-700 text-gray-200 text-sm placeholder-gray-600"
            />
            <label className="text-xs text-gray-500 w-24 shrink-0 ml-2">API 端点</label>
            <input
              value={baseUrl}
              onChange={e => setBaseUrl(e.target.value)}
              placeholder="https://api.deepseek.com"
              className="flex-1 min-w-52 px-2 py-1.5 rounded bg-gray-800 border border-gray-700 text-gray-200 text-sm placeholder-gray-600"
            />
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={doSave}
              disabled={save.isPending}
              className="px-4 py-1.5 rounded text-sm bg-emerald-900/70 text-emerald-200 hover:bg-emerald-800/70 transition-colors disabled:opacity-50"
            >
              {save.isPending ? '保存中…' : '保存设置'}
            </button>
            <button
              onClick={doTest}
              disabled={test.isPending}
              className="px-4 py-1.5 rounded text-sm bg-gray-800 text-gray-300 hover:bg-gray-700 transition-colors disabled:opacity-50"
            >
              {test.isPending ? '测试中…' : '测试连接'}
            </button>
            {save.isSuccess && <span className="text-xs text-emerald-400">已保存 ✓</span>}
          </div>
          {test.data && (
            <div className={`text-xs ${test.data.ok ? 'text-emerald-400' : 'text-red-400'}`}>
              {test.data.ok ? `连接正常: ${test.data.reply}` : `连接失败: ${test.data.error}`}
            </div>
          )}
          <p className="text-[11px] text-gray-600 leading-relaxed">
            功能说明: 个股详情页「AI 深度分析」会启动一个 ReAct Agent(DeepSeek 模型),
            自动调用 行情/因子/分红/资讯/全池对比/bash 等工具多轮推理后输出中文分析报告。
            报告仅供参考, 不构成投资建议。
          </p>
        </div>
      )}
    </div>
  )
}
