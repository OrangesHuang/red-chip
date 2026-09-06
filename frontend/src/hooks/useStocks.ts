import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  addStock,
  createSession,
  fetchAnalysisJob,
  fetchAnalysisReport,
  fetchAnalysisReports,
  fetchAnalysisSettings,
  fetchSessionDetail,
  fetchSessions,
  sendMessage,
  fetchCustomStocks,
  fetchDataStatus,
  fetchPool,
  fetchStockDetail,
  fetchStockNews,
  rebuildData,
  refreshStock,
  removeStock,
  saveAnalysisSettings,
  startStockAnalysis,
  testLLM,
} from '../api/client'
import type { PoolStock } from '../api/types'

export function usePool() {
  return useQuery({
    queryKey: ['pool'],
    queryFn: fetchPool,
    refetchInterval: 60_000, // 盘中每分钟刷新实时行情
  })
}

export function useStockDetail(code: string) {
  return useQuery({
    queryKey: ['stock', code],
    queryFn: () => fetchStockDetail(code),
    enabled: !!code,
  })
}

export function useStockNews(code: string) {
  return useQuery({
    queryKey: ['stock-news', code],
    queryFn: () => fetchStockNews(code),
    enabled: !!code,
    staleTime: 60_000, // 资讯 2 分钟内不重复拉取(后端也有 TTL 缓存)
  })
}

export function useAnalysisSettings() {
  return useQuery({
    queryKey: ['analysis-settings'],
    queryFn: fetchAnalysisSettings,
  })
}

export function useSaveAnalysisSettings() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { api_key?: string; model?: string; base_url?: string }) => saveAnalysisSettings(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['analysis-settings'] }),
  })
}

export function useTestLLM() {
  return useMutation({
    mutationFn: (body?: { api_key?: string; model?: string; base_url?: string }) => testLLM(body),
  })
}

export function useStartAnalysis(code: string) {
  return useMutation({
    mutationFn: () => startStockAnalysis(code),
  })
}

/** 轮询任务直到结束(在组件内用 setInterval 驱动)。 */
export function usePollAnalysisJob(jobId: string | null, onSettled?: () => void) {
  return useQuery({
    queryKey: ['analysis-job', jobId],
    queryFn: () => fetchAnalysisJob(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (status === 'done' || status === 'error') {
        onSettled?.()
        return false
      }
      return 1500
    },
  })
}

export function useAnalysisReports(code: string) {
  return useQuery({
    queryKey: ['analysis-reports', code],
    queryFn: () => fetchAnalysisReports(code),
    enabled: !!code,
  })
}

export function useAnalysisReportDetail(jobId: string | null) {
  return useQuery({
    queryKey: ['analysis-report-detail', jobId],
    queryFn: () => fetchAnalysisReport(jobId!),
    enabled: !!jobId,
  })
}

export function useSessions(code: string) {
  return useQuery({
    queryKey: ['sessions', code],
    queryFn: () => fetchSessions(code),
    enabled: !!code,
  })
}

export function useCreateSession() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (code: string) => createSession(code),
    onSuccess: res => qc.invalidateQueries({ queryKey: ['sessions', res.code] }),
  })
}

export function useSessionDetail(sessionId: string | null) {
  return useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => fetchSessionDetail(sessionId!),
    enabled: !!sessionId,
  })
}

export function useSendMessage() {
  return useMutation({
    // sessionId 在 mutate 时传入, 避免闭包捕获过期状态(新建会话后立即发送会拿到旧 id)
    mutationFn: ({ sessionId, content }: { sessionId: string; content: string }) =>
      sendMessage(sessionId, content),
  })
}

export function useCustomStocks() {
  return useQuery({
    queryKey: ['custom-stocks'],
    queryFn: fetchCustomStocks,
  })
}

export function useAddStock() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (req: { code: string; name?: string; market?: string; industry?: string }) => addStock(req),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['pool'] })
      qc.invalidateQueries({ queryKey: ['custom-stocks'] })
      qc.invalidateQueries({ queryKey: ['data-status'] })
    },
  })
}

export function useRemoveStock() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (code: string) => removeStock(code),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['pool'] })
      qc.invalidateQueries({ queryKey: ['custom-stocks'] })
      qc.invalidateQueries({ queryKey: ['data-status'] })
    },
  })
}

export function useDataStatus() {
  return useQuery({
    queryKey: ['data-status'],
    queryFn: fetchDataStatus,
    refetchInterval: 30_000,
  })
}

export function useRefreshStock(code: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => refreshStock(code),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['stock', code] })
      qc.invalidateQueries({ queryKey: ['pool'] })
      qc.invalidateQueries({ queryKey: ['data-status'] })
    },
  })
}

export function useRebuildData() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (days?: number) => rebuildData(days),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['pool'] })
      qc.invalidateQueries({ queryKey: ['data-status'] })
    },
  })
}

/** 因子分 → 颜色(红=优, 黄=中, 灰=差; 与 A 股习惯一致: 红涨绿跌) */
export function scoreColor(score: number | null | undefined): string {
  if (score == null) return 'text-gray-500'
  if (score >= 75) return 'text-red-400'
  if (score >= 60) return 'text-orange-400'
  if (score >= 45) return 'text-yellow-400'
  return 'text-gray-400'
}

export function zoneColor(zone: string | null | undefined): string {
  switch (zone) {
    case '深度低估':
      return 'bg-red-900/60 text-red-300'
    case '低估':
      return 'bg-red-950/60 text-red-400'
    case '高估':
      return 'bg-green-900/60 text-green-300'
    case '深度高估':
      return 'bg-green-950/60 text-green-400'
    default:
      return 'bg-gray-800 text-gray-300'
  }
}

export function oddsColor(odds: number | null | undefined): string {
  if (odds == null) return 'text-gray-500'
  if (odds >= 3) return 'text-red-400'
  if (odds >= 1.5) return 'text-orange-400'
  return 'text-gray-300'
}

export function fmtPrice(v: number | null | undefined): string {
  return v == null ? '—' : v.toFixed(2)
}

export function fmtPct(v: number | null | undefined): string {
  if (v == null) return '—'
  const s = v > 0 ? '+' : ''
  return `${s}${v.toFixed(2)}%`
}

export function sortByScore(a: PoolStock, b: PoolStock): number {
  return (b.score ?? -1) - (a.score ?? -1)
}
