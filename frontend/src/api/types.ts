/** 领域类型聚合出口: 后端 /api 响应结构。 */

export interface PoolStock {
  code: string
  name: string
  industry: string
  market?: string
  custom?: boolean
  price: number | null
  change_pct: number | null
  div_yield: number | null
  dps_ttm: number | null
  score: number | null
  grade: string
  zone: string
  odds: number | null
  target_price: number | null
  support_price: number | null
  snapshot_date: string | null
  realtime?: boolean
}

export interface PoolResponse {
  stocks: PoolStock[]
  count: number
}

export interface ZoneStatStock {
  code: string | null
  name: string | null
  market: string | null
  price: number | null
  change_pct: number | null
}

export interface ZoneStat {
  zone: string
  count: number
  up: number
  down: number
  flat: number
  valid: number
  win_rate: number | null
  avg_change: number | null
  stocks: ZoneStatStock[]
}

export interface ZoneStatsOverall {
  count: number
  up: number
  down: number
  flat: number
  valid: number
  win_rate: number | null
  equal_weight_return: number | null
}

export interface ZoneStatsResponse {
  zones: ZoneStat[]
  overall: ZoneStatsOverall
  updated_at: string
}

export interface KlineBar {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  amount: number | null
  change_pct: number | null
}

export interface DividendRecord {
  code: string
  year: number | null
  announce_date: string | null
  ex_date: string | null
  pay_date: string | null
  cash_per_share: number | null
  bonus_ratio: number | null
  special?: boolean
  note: string | null
}

export interface YieldPoint {
  date: string
  close: number
  dps_ttm: number
  div_yield: number | null
}

export interface FactorComponent {
  key: string
  score: number
  weight: number
}

export interface RangeAnchors {
  low: number | null
  central: number | null
  high: number | null
  optimistic: number | null
  pessimistic: number | null
}

export interface RangeInfo {
  zone: string
  qs: Record<string, number>
  anchors: RangeAnchors
  current_yield: number | null
}

export interface OddsInfo {
  current_price: number
  central_price: number | null
  optimistic_price: number | null
  pessimistic_price: number | null
  upside_pct: number | null
  downside_pct: number | null
  odds: number | null
  grade: string
  note: string
}

export interface StockDetail {
  code: string
  name: string
  industry: string
  market?: string
  custom?: boolean
  kline: KlineBar[]
  dividends: DividendRecord[]
  yield_series: YieldPoint[]
  factors: {
    total: number
    grade: string
    components: FactorComponent[]
  }
  inputs: {
    div_yield: number | null
    div_years: number | null
    div_growth: number | null
  }
  dps_ttm: number | null
  current_yield: number | null
  range: RangeInfo
  odds: OddsInfo | null
  snapshot: {
    date: string
    zone: string
    odds: number | null
    target_price: number | null
    support_price: number | null
  } | null
}

export interface DataStatusStock {
  code: string
  name: string
  industry: string
  custom?: boolean
  daily_count: number
  daily_first: string | null
  daily_last: string | null
  dividend_count: number
  dividend_last: string | null
  snapshot_date: string | null
}

export interface DataStatus {
  stocks: DataStatusStock[]
  db_size: number
  db_path: string
}

export interface RebuildResult {
  total: number
  ok: number
  failed: { code: string; name: string; error: string | null }[]
}

export interface RefreshResult {
  status: string
  code: string
  ok?: boolean
  error?: string | null
  retry_after_sec?: number
}

export interface CustomStock {
  code: string
  name: string
  industry: string | null
  market: string
  created_at: string
}

export interface PoolAddResult {
  status: string
  message: string
  refresh?: {
    code: string
    ok: boolean
    kline_count?: number
    dividend_count?: number
    error?: string | null
  }
}

export interface PoolRemoveResult {
  status: string
  message: string
}

export interface NewsItem {
  title: string
  time: string
  source: string
  content: string
  url: string
}

export interface StockNewsResponse {
  code: string
  name: string
  news: NewsItem[]
}

export interface AnalysisSettings {
  configured: boolean
  key_masked: string
  model: string
  base_url: string
}

export interface AnalysisJobStep {
  kind: string
  message: string
  time: string
  detail?: string | null
  duration?: number | null
}

export interface AnalysisJob {
  id: string
  code: string
  status: 'running' | 'done' | 'error'
  steps: AnalysisJobStep[]
  result: string | null
  error: string | null
  created_at: string
}

export interface LLMTestResult {
  ok: boolean
  reply?: string
  error?: string
}

export interface AnalysisReportItem {
  job_id: string
  code: string
  name: string | null
  status: string
  created_at: string
  finished_at: string
  report_len: number | null
}

export interface AnalysisReportDetail {
  job_id: string
  code: string
  name: string | null
  status: string
  report: string | null
  steps: AnalysisJobStep[]
  error: string | null
  created_at: string
  finished_at: string
}

export interface SessionMessage {
  role: 'user' | 'assistant'
  content: string
  usage?: Record<string, number>
  time: string
}

export interface SessionSummary {
  id: string
  code: string
  name: string | null
  created_at: string
  updated_at: string
  message_count: number
}

export interface SessionDetail {
  id: string
  code: string
  name: string | null
  messages: SessionMessage[]
  created_at: string
  updated_at: string
}
