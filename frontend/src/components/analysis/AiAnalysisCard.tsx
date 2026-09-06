import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import Markdown from '../common/Markdown'
import {
  useAnalysisSettings,
  useCreateSession,
  usePollAnalysisJob,
  useSendMessage,
  useSessionDetail,
  useSessions,
} from '../../hooks/useStocks'
import { useQueryClient } from '@tanstack/react-query'

const STEP_ICONS: Record<string, string> = {
  start: '🚀',
  round: '💭',
  tool: '🔧',
  usage: '💾',
  done: '✅',
  error: '❌',
}

/** 多轮会话 AI 分析: 会话切换 / 连续提问(补充提示词) / 实时执行过程 / 缓存统计。
 *  设计: system 提示词恒定 + 历史只追加问答 → 前缀命中 DeepSeek 磁盘缓存(输入 ~1/10 价)。 */
export default function AiAnalysisCard({ code }: { code: string }) {
  const qc = useQueryClient()
  const { data: settings } = useAnalysisSettings()
  const { data: sessionsData } = useSessions(code)
  const createSession = useCreateSession()
  const [sessionId, setSessionId] = useState<string | null>(null)
  const { data: session } = useSessionDetail(sessionId)
  const sendMsg = useSendMessage()
  const [jobId, setJobId] = useState<string | null>(null)
  const { data: job } = usePollAnalysisJob(jobId)
  const [input, setInput] = useState('')
  const [copied, setCopied] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const [expanded, setExpanded] = useState<Set<number>>(new Set())
  const [stepsOpen, setStepsOpen] = useState(true)
  const listRef = useRef<HTMLDivElement>(null)
  const stepsRef = useRef<HTMLDivElement>(null)

  const sessions = sessionsData?.sessions ?? []
  const messages = session?.messages ?? []
  const running = job?.status === 'running'
  const configured = settings?.configured ?? false

  // 默认选中最新会话
  useEffect(() => {
    if (!sessionId && sessions.length) setSessionId(sessions[0].id)
  }, [sessions, sessionId])

  // 任务结束: 刷新会话消息 + 10 分钟后允许重跑
  useEffect(() => {
    if (job?.status === 'done' || job?.status === 'error') {
      qc.invalidateQueries({ queryKey: ['session', sessionId] })
      qc.invalidateQueries({ queryKey: ['sessions', code] })
      const t = setTimeout(() => setJobId(null), 10 * 60_000)
      return () => clearTimeout(t)
    }
  }, [job?.status, sessionId, code, qc])

  // 运行计时
  useEffect(() => {
    if (!running) return
    const t = setInterval(() => setElapsed(e => e + 1), 1000)
    return () => clearInterval(t)
  }, [running])

  // 消息与步骤自动滚底
  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight
  }, [messages.length])
  useEffect(() => {
    if (stepsRef.current) stepsRef.current.scrollTop = stepsRef.current.scrollHeight
  }, [job?.steps.length])

  // 最新步骤默认展开
  useEffect(() => {
    const n = job?.steps.length ?? 0
    if (n) setExpanded(prev => new Set(prev).add(n - 1))
  }, [job?.steps.length])

  const send = (content: string, targetSessionId: string) => {
    const text = content.trim()
    if (!text || running || !targetSessionId) return
    setInput('')
    setElapsed(0)
    sendMsg.mutate(
      { sessionId: targetSessionId, content: text },
      {
        onSuccess: res => setJobId(res.job_id),
        onError: e => alert(`发送失败: ${e.message}`),
      },
    )
  }

  const startNew = async () => {
    const res = await createSession.mutateAsync(code)
    setSessionId(res.session_id)
    // 直接把新会话 id 传给 mutation(不用 state, 避免闭包过期)
    send(res.session_id ? `请对这只股票进行全面深度分析: 覆盖股息质量、估值区间、赔率与价值陷阱风险。` : '', res.session_id)
  }

  const copy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch { /* 忽略 */ }
  }

  const fmtElapsed = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
  const progressPct = running ? Math.min(100, Math.round(((job?.steps.length ?? 0) / 21) * 100)) : 100
  const toggle = (i: number) => {
    setExpanded(prev => {
      const next = new Set(prev)
      if (next.has(i)) next.delete(i)
      else next.add(i)
      return next
    })
  }

  return (
    <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
      <div className="flex items-center justify-between mb-2 gap-2 flex-wrap">
        <h3 className="text-sm font-medium text-gray-300">AI 深度分析（多轮会话）</h3>
        <div className="flex items-center gap-2">
          <span className="text-[11px] text-gray-600 hidden md:inline">
            DeepSeek 前缀缓存自动命中 · 历史对话持续优化分析
          </span>
          <button
            onClick={startNew}
            disabled={!configured || running || createSession.isPending}
            className="px-3 py-1 rounded text-xs bg-red-900/70 text-red-200 hover:bg-red-800/70 transition-colors disabled:opacity-40"
          >
            {createSession.isPending ? '创建中…' : '+ 新建会话'}
          </button>
        </div>
      </div>

      {!configured && (
        <div className="py-3 text-sm text-gray-500">
          尚未配置 DeepSeek API Key —— 请先到
          <Link to="/data" className="text-red-400 hover:underline mx-1">数据管理 → AI 分析设置</Link>
          填写后即可开启多轮分析会话。
        </div>
      )}

      {configured && sessions.length === 0 && !sessionId && (
        <div className="py-4 text-center text-sm text-gray-500">
          还没有分析会话 —— 点击右上角「新建会话」开始第一轮深度分析
        </div>
      )}

      {configured && (sessions.length > 0 || sessionId) && (
        <>
          {/* 会话切换 */}
          {sessions.length > 0 && (
            <div className="flex gap-1.5 overflow-x-auto pb-2 mb-2 border-b border-gray-800/60">
              {sessions.map(s => (
                <button
                  key={s.id}
                  onClick={() => { setSessionId(s.id); setJobId(null) }}
                  className={`shrink-0 px-2.5 py-1 rounded text-xs transition-colors ${
                    s.id === sessionId ? 'bg-gray-700 text-white' : 'bg-gray-800/60 text-gray-400 hover:text-gray-200'
                  }`}
                >
                  {s.message_count} 条 · {s.updated_at.slice(5, 16)}
                </button>
              ))}
            </div>
          )}

          {/* 消息区 */}
          <div ref={listRef} className="space-y-3 max-h-[30rem] overflow-y-auto pr-1 py-1">
            {messages.length === 0 && (
              <div className="py-8 text-center text-sm text-gray-500">
                会话已创建, 在下方输入你的第一个问题(或点「新建会话」自动发起全面分析)
              </div>
            )}
            {messages.map((m, i) =>
              m.role === 'user' ? (
                <div key={i} className="flex justify-end">
                  <div className="max-w-[85%] bg-red-950/50 border border-red-900/40 rounded-lg rounded-br-sm px-3 py-2 text-sm text-gray-200 whitespace-pre-wrap">
                    {m.content}
                    <div className="mt-1 text-[10px] text-gray-500 text-right">{m.time.slice(5, 16)}</div>
                  </div>
                </div>
              ) : (
                <div key={i} className="bg-gray-950/60 border border-gray-800 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[11px] text-gray-600">
                      AI 分析 · {m.time.slice(5, 16)}
                      {m.usage && (m.usage.cache_hit_tokens || m.usage.cache_miss_tokens) ? (
                        <span className="ml-2 text-emerald-500/80">
                          💾 输入 {(m.usage.prompt_tokens ?? 0).toLocaleString()} tokens
                          （缓存命中 {(m.usage.cache_hit_tokens ?? 0).toLocaleString()} / 未命中 {(m.usage.cache_miss_tokens ?? 0).toLocaleString()}）· 输出 {(m.usage.completion_tokens ?? 0).toLocaleString()}
                        </span>
                      ) : null}
                    </span>
                    <button onClick={() => copy(m.content)} className="text-[11px] text-gray-500 hover:text-gray-300">
                      {copied ? '已复制 ✓' : '复制'}
                    </button>
                  </div>
                  <Markdown text={m.content} />
                </div>
              ),
            )}

            {/* 运行中的执行过程 */}
            {running && job && (
              <div className="bg-orange-950/20 border border-orange-900/40 rounded-lg p-3">
                <button
                  onClick={() => setStepsOpen(o => !o)}
                  className="flex items-center gap-2 text-xs text-orange-300 w-full"
                >
                  <span className="inline-block w-2 h-2 rounded-full bg-orange-400 animate-pulse" />
                  <span>Agent 分析中…(第 {job.steps.length} 步)</span>
                  <span className="ml-auto font-mono">{fmtElapsed(elapsed)}</span>
                  <span className="text-gray-500">{stepsOpen ? '▾' : '▸'}</span>
                </button>
                {stepsOpen && (
                  <>
                    <div className="mt-2 h-1 rounded bg-gray-800 overflow-hidden">
                      <div className="h-full bg-orange-500 transition-all duration-700" style={{ width: `${progressPct}%` }} />
                    </div>
                    <div ref={stepsRef} className="mt-2 space-y-1 max-h-48 overflow-y-auto">
                      {(job.steps ?? []).map((s, i) => {
                        const isLast = i === job.steps.length - 1
                        const open = expanded.has(i) || isLast
                        return (
                          <div key={i} className="text-xs">
                            <div
                              className={`flex items-start gap-1.5 cursor-pointer rounded px-1.5 py-0.5 hover:bg-gray-800/50 ${isLast ? 'bg-gray-800/40' : ''}`}
                              onClick={() => toggle(i)}
                            >
                              <span>{STEP_ICONS[s.kind] ?? '·'}</span>
                              <span className={s.kind === 'tool' || s.kind === 'usage' ? 'text-gray-300' : 'text-gray-500'}>{s.message}</span>
                              <span className="ml-auto shrink-0 text-gray-600">{s.duration != null ? `${s.duration}s` : ''}</span>
                              {s.detail && <span className="shrink-0 text-gray-600">{open ? '▾' : '▸'}</span>}
                            </div>
                            {s.detail && open && (
                              <pre className="ml-5 mt-0.5 mb-1 p-2 rounded bg-gray-950 border border-gray-800 text-[11px] text-gray-400 whitespace-pre-wrap break-all max-h-32 overflow-y-auto">
                                {s.detail}
                              </pre>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  </>
                )}
              </div>
            )}

            {job?.status === 'error' && (
              <div className="text-sm text-red-400 bg-red-950/30 border border-red-900/40 rounded-lg p-3">
                分析失败: {job.error}
                <button onClick={() => setJobId(null)} className="ml-3 text-gray-400 hover:text-white underline text-xs">关闭</button>
              </div>
            )}
          </div>

          {/* 输入区 */}
          <div className="mt-3 flex items-center gap-2">
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(input, sessionId ?? '') } }}
              disabled={running || sendMsg.isPending}
              placeholder={running ? 'Agent 分析中, 请稍候…' : '继续提问 / 补充你的分析思路(如: 请重点分析分红可持续性, 并与中国神华对比)…'}
              className="flex-1 px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-200 text-sm placeholder-gray-600 disabled:opacity-50"
            />
            <button
              onClick={() => send(input, sessionId ?? '')}
              disabled={running || sendMsg.isPending || !input.trim() || !sessionId}
              className="px-4 py-2 rounded-lg text-sm bg-red-900/70 text-red-200 hover:bg-red-800/70 transition-colors disabled:opacity-40 shrink-0"
            >
              {running ? '分析中…' : '发送'}
            </button>
          </div>
          <p className="mt-1.5 text-[11px] text-gray-600">
            多轮会话: 每轮追加你的提问, AI 基于完整历史持续深化分析; 系统提示词恒定 + 历史前缀命中 DeepSeek 磁盘缓存(输入费用约 1/10)。
          </p>
        </>
      )}
    </div>
  )
}
