/**
 * 人工测试记录 API（C-10 后端 + C-12 面板）.
 *
 * 对齐后端 openbase/modules/testing：受权 test:record 四端点。
 * 统一信封 {code, message, data}，经 http 拦截器注入 JWT 与测试头。
 */
import { http, type ApiSuccess } from './http'

export type TestResult = 'PASS' | 'FAIL' | 'BLOCKED' | 'SKIPPED'

export interface TestCaseRecord {
  id: number
  run_id: string
  case_id: string
  step_id: number | string | null
  result: TestResult
  title: string
  expected: string
  observed: string
  reason: string
  request_id: string
  duration_ms: number | null
  channel: string
  operator: string | null
}

export interface StepSummary {
  id: number
  step_id: number | string | null
  result: TestResult
  reason: string | null
  request_id: string | null
  duration_ms: number | null
  title: string | null
}

export interface CaseSummary {
  case_id: string
  latest_result: TestResult
  steps: StepSummary[]
}

export interface RunSummary {
  run_id: string
  total: number
  pass: number
  fail: number
  blocked: number
  skipped: number
  passed: boolean
  cases: CaseSummary[]
}

/** 测试轮次列表项（v1.9.2） */
export interface TestRunItem {
  id: string
  title: string
  scope: string
  operator: string | null
  created_at: string | null
  record_count: number
}

/** 测试记录分页（v1.9.2） */
export interface TestRecordPage {
  items: TestCaseRecord[]
  total: number
  skip: number
  limit: number
}

export const testingApi = {
  createRun(body: { run_id?: string; title?: string; scope?: string }): Promise<ApiSuccess<{ run_id: string }>> {
    return http.post('/test-runs', body).then((r) => r.data)
  },
  /** 轮次列表（v1.9.2，按创建时间倒序，含记录数） */
  listRuns(params: { skip?: number; limit?: number } = {}): Promise<ApiSuccess<TestRecordPage & { items: TestRunItem[] }>> {
    return http.get('/test-runs', { params }).then((r) => r.data)
  },
  /** 记录列表（v1.9.2，支持轮次/用例/结论过滤） */
  listRecords(
    params: { run_id?: string; case_id?: string; result?: TestResult; skip?: number; limit?: number } = {},
  ): Promise<ApiSuccess<TestRecordPage>> {
    return http.get('/test-records', { params }).then((r) => r.data)
  },
  createRecord(body: {
    run_id: string
    case_id: string
    step_id?: number | string | null
    result: TestResult
    title?: string
    expected?: string
    observed?: string
    reason?: string
    request_id?: string
    duration_ms?: number
  }): Promise<ApiSuccess<TestCaseRecord>> {
    return http.post('/test-records', body).then((r) => r.data)
  },
  updateRecord(
    id: number,
    body: { result: TestResult; reason?: string; observed?: string },
  ): Promise<ApiSuccess<TestCaseRecord>> {
    return http.patch(`/test-records/${id}`, body).then((r) => r.data)
  },
  runSummary(runId: string): Promise<ApiSuccess<RunSummary>> {
    return http.get(`/test-runs/${encodeURIComponent(runId)}/summary`).then((r) => r.data)
  },
}

export function resultTagType(result: TestResult): 'success' | 'danger' | 'warning' | 'info' {
  switch (result) {
    case 'PASS':
      return 'success'
    case 'FAIL':
      return 'danger'
    case 'BLOCKED':
      return 'warning'
    default:
      return 'info'
  }
}

export function resultLabel(result: TestResult): string {
  switch (result) {
    case 'PASS':
      return '通过'
    case 'FAIL':
      return '失败'
    case 'BLOCKED':
      return '阻塞'
    default:
      return '跳过'
  }
}