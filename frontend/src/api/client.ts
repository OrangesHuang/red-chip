import type {
  AnalysisJob,
  AnalysisReportDetail,
  AnalysisReportItem,
  AnalysisSettings,
  CustomStock,
  DataStatus,
  LLMTestResult,
  PoolAddResult,
  PoolRemoveResult,
  PoolResponse,
  SessionDetail,
  SessionSummary,
  StockNewsResponse,
  RebuildResult,
  RefreshResult,
  StockDetail,
} from './types'

const BASE = `${__APP_BASE__}/api`

async function parseError(res: Response): Promise<Error> {
  let msg = `API error: ${res.status}`
  try {
    const body = await res.json()
    if (body && typeof body.detail === 'string') msg = body.detail
  } catch {
    /* 忽略非 JSON 响应 */
  }
  return new Error(msg)
}

// 请求超时兜底: 后端未就绪/接口慢时不让页面无限挂起, 由 React Query 重试恢复
const DEFAULT_TIMEOUT_MS = 20_000

async function request<T>(path: string, init?: RequestInit, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<T> {
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), timeoutMs)
  try {
    const res = await fetch(`${BASE}${path}`, { ...init, signal: ctrl.signal })
    if (!res.ok) throw await parseError(res)
    return res.json()
  } finally {
    clearTimeout(timer)
  }
}

async function get<T>(path: string, timeoutMs?: number): Promise<T> {
  return request<T>(path, undefined, timeoutMs)
}

async function post<T>(path: string, body?: unknown, timeoutMs?: number): Promise<T> {
  const hasBody = body !== undefined
  return request<T>(
    path,
    {
      method: 'POST',
      headers: hasBody ? { 'Content-Type': 'application/json' } : undefined,
      body: hasBody ? JSON.stringify(body) : undefined,
    },
    timeoutMs,
  )
}

export function fetchPool(): Promise<PoolResponse> {
  return get('/dividend/pool')
}

export function fetchStockDetail(code: string, days = 640): Promise<StockDetail> {
  return get(`/dividend/stock/${code}?days=${days}`)
}

export function refreshStock(code: string): Promise<RefreshResult> {
  return post(`/dividend/stock/${code}/refresh`, undefined, 120_000)
}

export function fetchDataStatus(): Promise<DataStatus> {
  return get('/data/status')
}

export function rebuildData(days = 300): Promise<RebuildResult> {
  return post(`/data/rebuild?days=${days}`, undefined, 300_000)
}

export function fetchHealth(): Promise<{ status: string }> {
  return get('/health')
}

export function fetchStockNews(code: string, limit = 20): Promise<StockNewsResponse> {
  return get(`/dividend/stock/${code}/news?limit=${limit}`)
}

export function fetchAnalysisSettings(): Promise<AnalysisSettings> {
  return get('/analysis/settings')
}

export function saveAnalysisSettings(body: { api_key?: string; model?: string; base_url?: string }): Promise<AnalysisSettings> {
  return request<AnalysisSettings>('/analysis/settings', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export function testLLM(body?: { api_key?: string; model?: string; base_url?: string }): Promise<LLMTestResult> {
  return post('/analysis/test', body ?? {})
}

export function startStockAnalysis(code: string): Promise<{ job_id: string; code: string }> {
  return post(`/analysis/stock/${code}`)
}

export function fetchAnalysisJob(jobId: string): Promise<AnalysisJob> {
  return get(`/analysis/jobs/${jobId}`)
}

export function fetchSessions(code?: string, limit = 20): Promise<{ sessions: SessionSummary[] }> {
  const q = new URLSearchParams({ limit: String(limit) })
  if (code) q.set('code', code)
  return get(`/analysis/sessions?${q}`)
}

export function createSession(code: string): Promise<{ session_id: string; code: string; name?: string }> {
  return post('/analysis/sessions', { code })
}

export function fetchSessionDetail(sessionId: string): Promise<SessionDetail> {
  return get(`/analysis/sessions/${sessionId}`)
}

export function sendMessage(sessionId: string, content: string): Promise<{ job_id: string; session_id: string }> {
  return post(`/analysis/sessions/${sessionId}/messages`, { content })
}

export function fetchAnalysisReports(code?: string, limit = 20): Promise<{ reports: AnalysisReportItem[] }> {
  const q = new URLSearchParams({ limit: String(limit) })
  if (code) q.set('code', code)
  return get(`/analysis/reports?${q}`)
}

export function fetchAnalysisReport(jobId: string): Promise<AnalysisReportDetail> {
  return get(`/analysis/reports/${jobId}`)
}

export function fetchCustomStocks(): Promise<{ stocks: CustomStock[] }> {
  return get('/dividend/pool/custom')
}

export function addStock(req: { code: string; name?: string; market?: string; industry?: string }): Promise<PoolAddResult> {
  return post('/dividend/pool', req, 300_000)
}

export function removeStock(code: string): Promise<PoolRemoveResult> {
  return request<PoolRemoveResult>(`/dividend/pool/${code}`, { method: 'DELETE' })
}
