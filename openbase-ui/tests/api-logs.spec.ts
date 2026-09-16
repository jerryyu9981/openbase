/**
 * 日志中心 API 客户端单测（DEF-FE-146-002：`src/core/api/logs.ts` v1.4.6 新增模块补测）
 *
 * 覆盖面（对齐《API接口设计文档-v1.4.6》§3.1/§3.2/§3.3）：
 * - `search`：统一信封解包、`module/operation/result/operator` **重复同名参数**序列化、
 *   可选键缺省不产生空参数、`step_id` 的 0 值边界、`page_size` 钳制 [1,100]；
 * - `facets`：信封解包 + 与 search 同一套筛选参数口径；
 * - `export`：CSV / JSON 两种 `format` + `responseType: 'blob'`，Blob 原样透传；
 * - 三者错误分支：异常**原样上抛**（不吞异常、不返回伪成功）。
 *
 * 断言口径：一律 `toEqual` 严格全等 + `rejects.toBe(error)` 身份全等，
 * 不使用 if-else 通过、不 try-except 吞异常、不使用超宽容断言。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({ get: vi.fn() }))

vi.mock('@/core/api/http', () => ({
  http: { get: mocks.get },
}))

import {
  LOG_SOURCE_LABELS,
  LOG_SOURCE_OPTIONS,
  logsApi,
  type LogEntry,
  type LogFacetsResponse,
  type LogSearchResponse,
} from '@/core/api/logs'

/** 统一响应信封（`{code, message, data}`），与后端 FastAPI 返回结构一致 */
const envelope = (data: unknown) => ({ data: { code: 0, message: 'ok', data } })

interface GetCall {
  url: string
  params: URLSearchParams
  responseType?: string
}

/** 取第 index 次 `http.get` 调用实参（强类型读出，避免裸 any 断言） */
function getCall(index: number): GetCall {
  const call = mocks.get.mock.calls[index] as [string, { params: URLSearchParams; responseType?: string }]
  return { url: call[0], params: call[1].params, responseType: call[1].responseType }
}

const sampleEntry: LogEntry = {
  ts: '2026-09-15T10:00:00Z',
  source: 'audit_db',
  module: 'identity',
  operation: 'auth_login',
  result: 'success',
  request_id: 'req-log-001',
  method: 'POST',
  path: '/api/v1/auth/login',
  status_code: 200,
  duration_ms: 42,
  operator_id: '1',
  tenant_id: 'tenant-a',
  ip_address: '10.0.0.1',
  case_id: 'C-146-001',
  step_id: 3,
  run_id: 'run-146',
  action: 'auth.login',
  summary: { channel: 'password' },
}

const emptySearch: LogSearchResponse = {
  items: [],
  total: 0,
  page: 1,
  page_size: 20,
  source: 'l1_file',
  truncated: false,
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('DEF-FE-146-002: logsApi.search', () => {
  it('解包统一信封并返回业务对象（items/total/page/page_size/source/truncated 全等）', async () => {
    const response: LogSearchResponse = {
      items: [sampleEntry],
      total: 1,
      page: 2,
      page_size: 50,
      source: 'audit_db',
      truncated: false,
    }
    mocks.get.mockResolvedValueOnce(envelope(response))

    const result = await logsApi.search({ source: 'audit_db' }, 2, 50)

    expect(mocks.get).toHaveBeenCalledTimes(1)
    expect(getCall(0).url).toBe('/logs/search')
    expect(result).toEqual(response)
    expect(result.items[0].request_id).not.toBeUndefined()
    expect(result.total).not.toBeUndefined()
  })

  it('多选筛选用重复同名参数传递（module/operation/result/operator 各 N 份）', async () => {
    mocks.get.mockResolvedValueOnce(envelope(emptySearch))

    await logsApi.search({
      source: 'audit_db',
      module: ['identity', 'memory'],
      operation: ['auth_login'],
      result: ['client_error', 'server_error'],
      operator: ['1', '2'],
      q: '登录失败',
      from: '2026-09-01T00:00:00Z',
      to: '2026-09-15T23:59:59Z',
      case_id: 'C-146-001',
      run_id: 'run-146',
      step_id: 3,
    })

    const { params } = getCall(0)
    expect(params.getAll('module')).toEqual(['identity', 'memory'])
    expect(params.getAll('operation')).toEqual(['auth_login'])
    expect(params.getAll('result')).toEqual(['client_error', 'server_error'])
    expect(params.getAll('operator')).toEqual(['1', '2'])
    expect(params.get('source')).toBe('audit_db')
    expect(params.get('q')).toBe('登录失败')
    expect(params.get('from')).toBe('2026-09-01T00:00:00Z')
    expect(params.get('to')).toBe('2026-09-15T23:59:59Z')
    expect(params.get('case_id')).toBe('C-146-001')
    expect(params.get('run_id')).toBe('run-146')
    expect(params.get('step_id')).toBe('3')
  })

  it('可选键缺省时不产生空参数；page/page_size 恒有值（默认 20）', async () => {
    mocks.get.mockResolvedValueOnce(envelope(emptySearch))

    await logsApi.search({ source: 'l1_file' })

    const { params } = getCall(0)
    expect([...params.keys()]).toEqual(['source', 'page', 'page_size'])
    expect(params.get('page')).toBe('1')
    expect(params.get('page_size')).toBe('20')
  })

  it('step_id 的 0 值边界：0 参与序列化，null 被剔除', async () => {
    mocks.get.mockResolvedValue(envelope(emptySearch))

    await logsApi.search({ source: 'test_record', step_id: 0 })
    expect(getCall(0).params.get('step_id')).toBe('0')

    await logsApi.search({ source: 'test_record', step_id: null })
    expect(getCall(1).params.has('step_id')).toBe(false)
  })

  it('page_size 钳制到 [1,100]（0/负数 → 1，超上限 → 100）', async () => {
    mocks.get.mockResolvedValue(envelope(emptySearch))

    await logsApi.search({ source: 'l1_file' }, 1, 0)
    expect(getCall(0).params.get('page_size')).toBe('1')

    await logsApi.search({ source: 'l1_file' }, 1, -5)
    expect(getCall(1).params.get('page_size')).toBe('1')

    await logsApi.search({ source: 'l1_file' }, 1, 500)
    expect(getCall(2).params.get('page_size')).toBe('100')

    await logsApi.search({ source: 'l1_file' }, 3, 100)
    expect(getCall(3).params.get('page_size')).toBe('100')
    expect(getCall(3).params.get('page')).toBe('3')
  })

  it('错误分支：异常原样上抛，不吞异常、不返回伪成功', async () => {
    const failure = Object.assign(new Error('Request failed with status code 503'), {
      response: {
        status: 503,
        data: {
          code: 'SYS_LOG_SOURCE_UNAVAILABLE',
          message: '日志源不可用',
          detail: null,
          request_id: 'req-log-503',
        },
      },
    })
    mocks.get.mockRejectedValueOnce(failure)

    await expect(logsApi.search({ source: 'repo_log' })).rejects.toBe(failure)
    expect(mocks.get).toHaveBeenCalledTimes(1)
  })
})

describe('DEF-FE-146-002: logsApi.facets', () => {
  it('解包统一信封并返回各维度计数', async () => {
    const response: LogFacetsResponse = {
      source: 'repo_log',
      module: { identity: 3, gateway: 1 },
      operation: { read: 2 },
      result: { success: 4, server_error: 2 },
      operator: { '1': 6 },
      truncated: true,
    }
    mocks.get.mockResolvedValueOnce(envelope(response))

    const result = await logsApi.facets({ source: 'repo_log', q: 'timeout' })

    expect(getCall(0).url).toBe('/logs/facets')
    expect(getCall(0).params.get('source')).toBe('repo_log')
    expect(getCall(0).params.get('q')).toBe('timeout')
    expect(result).toEqual(response)
    expect(result.truncated).toBe(true)
  })

  it('错误分支：异常原样上抛', async () => {
    const failure = new Error('facets boom')
    mocks.get.mockRejectedValueOnce(failure)

    await expect(logsApi.facets({ source: 'l1_file' })).rejects.toBe(failure)
    expect(mocks.get).toHaveBeenCalledTimes(1)
  })
})

describe('DEF-FE-146-002: logsApi.export（CSV / JSON）', () => {
  it('CSV 导出：blob 响应 + format=csv，Blob 原样透传', async () => {
    const csvBlob = new Blob(['ts,source,module\n2026-09-15T10:00:00Z,audit_db,identity\n'], {
      type: 'text/csv',
    })
    mocks.get.mockResolvedValueOnce({ data: csvBlob })

    const blob = await logsApi.export({ source: 'audit_db', module: ['identity'] }, 'csv')

    const call = getCall(0)
    expect(call.url).toBe('/logs/export')
    expect(call.responseType).toBe('blob')
    expect(call.params.get('format')).toBe('csv')
    expect(call.params.getAll('module')).toEqual(['identity'])
    expect(blob).toBe(csvBlob)
    expect(blob.type).toBe('text/csv')
    expect(blob.size).toBeGreaterThan(0)
  })

  it('JSON 导出：format=json，Blob 原样透传', async () => {
    const jsonBlob = new Blob(['{"items":[],"total":0}'], { type: 'application/json' })
    mocks.get.mockResolvedValueOnce({ data: jsonBlob })

    const blob = await logsApi.export({ source: 'l1_file', q: 'x' }, 'json')

    const call = getCall(0)
    expect(call.params.get('format')).toBe('json')
    expect(call.params.get('q')).toBe('x')
    expect(call.responseType).toBe('blob')
    expect(blob).toBe(jsonBlob)
    expect(blob.type).toBe('application/json')
    expect(blob.size).toBeGreaterThan(0)
  })

  it('错误分支：导出失败原样上抛（页面据此提示「导出失败」）', async () => {
    const failure = new Error('export boom')
    mocks.get.mockRejectedValueOnce(failure)

    await expect(logsApi.export({ source: 'audit_db' }, 'csv')).rejects.toBe(failure)
    expect(mocks.get).toHaveBeenCalledTimes(1)
  })
})

describe('DEF-FE-146-002: 日志源枚举与展示标签', () => {
  it('LOG_SOURCE_OPTIONS 与后端 4 数据源一致，LABELS 覆盖完整', () => {
    expect(LOG_SOURCE_OPTIONS).toEqual(['l1_file', 'audit_db', 'test_record', 'repo_log'])
    expect(Object.keys(LOG_SOURCE_LABELS)).toEqual([...LOG_SOURCE_OPTIONS])
    expect(LOG_SOURCE_LABELS.l1_file).toBe('L1 文件')
    expect(LOG_SOURCE_LABELS.audit_db).toBe('审计库')
    expect(LOG_SOURCE_LABELS.test_record).toBe('测试记录')
    expect(LOG_SOURCE_LABELS.repo_log).toBe('四仓日志')
  })
})
