/**
 * 人工测试记录 API 客户端单测（DEF-FE-146-002：`src/core/api/testing.ts` v1.4.6 新增模块补测）
 *
 * 覆盖面（对齐后端 openbase/modules/testing 四端点与 _test-records 前端面板）：
 * - `testingApi.createRun`/`createRecord`/`updateRecord`/`runSummary`：HTTP 动词与 URL、
 *   `.then(r => r.data)` 返回**统一信封 `{code,message,data}`**（契约观察 DEF-FE-146-004：`testing.ts`
 *   返回 `ApiSuccess` 信封本身，与 `logs.ts`/`modules.ts` 解包返回业务对象不一致，调用方须自取 `result.data`）、
 *   `encodeURIComponent` 对 run_id 的转义防护；
 * - `resultTagType` / `resultLabel`：四种结果的分支映射全覆盖；
 * - 错误分支：异常原样上抛。
 *
 * 断言口径与 `api-logs.spec.ts` 一致：`toEqual` 严格全等 + `rejects.toBe` 身份全等。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
}))

vi.mock('@/core/api/http', () => ({
  http: { get: mocks.get, post: mocks.post, patch: mocks.patch },
}))

import {
  resultLabel,
  resultTagType,
  testingApi,
  type RunSummary,
  type TestCaseRecord,
} from '@/core/api/testing'

const envelope = (data: unknown) => ({ data: { code: 0, message: 'ok', data } })

interface HttpCall {
  url: string
  body?: unknown
}

function httpCall(mockFn: ReturnType<typeof vi.fn>, index: number): HttpCall {
  const call = mockFn.mock.calls[index] as [string, unknown?]
  return { url: call[0], body: call[1] }
}

const record: TestCaseRecord = {
  id: 1,
  run_id: 'run-146',
  case_id: 'C-146-001',
  step_id: 3,
  result: 'PASS',
  title: '登录冒烟',
  expected: '200',
  observed: '200',
  reason: '',
  request_id: 'req-test-001',
  duration_ms: 42,
  channel: '__manual__',
  operator: null,
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('DEF-FE-146-002: testingApi 四端点', () => {
  it('createRun：POST /test-runs，返回统一信封（业务对象取 result.data）', async () => {
    mocks.post.mockResolvedValueOnce(envelope({ run_id: 'run-146' }))

    const result = await testingApi.createRun({ title: 'v1.4.6 回归', scope: 'logs' })

    const call = httpCall(mocks.post, 0)
    expect(call.url).toBe('/test-runs')
    expect(call.body).toEqual({ title: 'v1.4.6 回归', scope: 'logs' })
    // 契约观察 DEF-FE-146-004：testingApi 返回统一信封本身，不解包
    expect(result).toEqual({ code: 0, message: 'ok', data: { run_id: 'run-146' } })
    expect(result.data).toEqual({ run_id: 'run-146' })
  })

  it('createRun：缺省 run_id 请求体不含未给定键', async () => {
    mocks.post.mockResolvedValueOnce(envelope({ run_id: 'run-x' }))

    await testingApi.createRun({})

    expect(httpCall(mocks.post, 0).url).toBe('/test-runs')
    expect(httpCall(mocks.post, 0).body).toEqual({})
  })

  it('createRecord：POST /test-records，step_id 0 值边界与 body 透传', async () => {
    mocks.post.mockResolvedValueOnce(envelope(record))

    const result = await testingApi.createRecord({
      run_id: 'run-146',
      case_id: 'C-146-001',
      step_id: 0,
      result: 'PASS',
      title: '登录冒烟',
    })

    const call = httpCall(mocks.post, 0)
    expect(call.url).toBe('/test-records')
    expect(call.body).toMatchObject({ run_id: 'run-146', case_id: 'C-146-001', step_id: 0, result: 'PASS' })
    expect(result.data).toEqual(record)
  })

  it('updateRecord：PATCH /test-records/{id}，result + 可选字段', async () => {
    mocks.patch.mockResolvedValueOnce(envelope({ ...record, result: 'BLOCKED', reason: '依赖缺失' }))

    const result = await testingApi.updateRecord(1, { result: 'BLOCKED', reason: '依赖缺失' })

    expect(httpCall(mocks.patch, 0).url).toBe('/test-records/1')
    expect(httpCall(mocks.patch, 0).body).toEqual({ result: 'BLOCKED', reason: '依赖缺失' })
    expect(result.data.result).toBe('BLOCKED')
    expect(result.data.reason).toBe('依赖缺失')
  })

  it('runSummary：GET /test-runs/{run_id}/summary（含 run_id 路径转义）', async () => {
    const summary: RunSummary = {
      run_id: 'run/146',
      total: 3,
      pass: 2,
      fail: 0,
      blocked: 0,
      skipped: 1,
      passed: true,
      cases: [
        { case_id: 'C-146-001', latest_result: 'PASS', steps: [] },
      ],
    }
    mocks.get.mockResolvedValueOnce(envelope(summary))

    const result = await testingApi.runSummary('run/146')

    // encodeURIComponent 将 `/` 编码为 %2F，避免破坏路径
    expect(httpCall(mocks.get, 0).url).toBe('/test-runs/run%2F146/summary')
    expect(result.data).toEqual(summary)
    expect(result.data.passed).toBe(true)
  })

  it('错误分支：异常原样上抛，不吞异常', async () => {
    const failure = new Error('summary boom')
    mocks.get.mockRejectedValueOnce(failure)

    await expect(testingApi.runSummary('run-146')).rejects.toBe(failure)
  })
})

describe('DEF-FE-146-002: resultTagType / resultLabel 分支映射', () => {
  it('resultTagType 四结果分支全覆盖', () => {
    expect(resultTagType('PASS')).toBe('success')
    expect(resultTagType('FAIL')).toBe('danger')
    expect(resultTagType('BLOCKED')).toBe('warning')
    expect(resultTagType('SKIPPED')).toBe('info')
  })

  it('resultLabel 四结果中文标签全覆盖', () => {
    expect(resultLabel('PASS')).toBe('通过')
    expect(resultLabel('FAIL')).toBe('失败')
    expect(resultLabel('BLOCKED')).toBe('阻塞')
    expect(resultLabel('SKIPPED')).toBe('跳过')
  })
})