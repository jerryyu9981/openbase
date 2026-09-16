/**
 * v1.4.6 新增 API 客户端单测（DEF-FE-146-001 / DEF-FE-146-002）
 *
 * 覆盖两个模块：
 * - `src/core/api/modules.ts`：模块开关写路径（PATCH）与注册表只读；
 * - `src/core/api/testing.ts`：人工测试记录 4 端点 + 结果文案映射。
 *
 * 断言口径（统一响应信封 `{code, message, data}`）：API 客户端**必须**解包 `data` 层后
 * 返回业务对象 —— 与 `src/core/api/logs.ts` 既有口径一致。任何「返回整包」或「字段全
 * undefined」都会在 `toEqual` 严格全等 / `not.toBeUndefined()` 下失败；
 * 错误分支一律 `rejects.toBe(error)` 身份全等（不吞异常、不返回伪成功）。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
}))

vi.mock('@/core/api/http', () => ({
  http: { get: mocks.get, post: mocks.post, patch: mocks.patch },
}))

import { listModuleDefinitions, modulesWriteApi, type ModuleDefinition } from '@/core/api/modules'
import {
  resultLabel,
  resultTagType,
  testingApi,
  type RunSummary,
  type TestCaseRecord,
} from '@/core/api/testing'
import ModuleSwitchView from '@/pages/platform/config/ModuleSwitchView.vue'

/** 统一响应信封（`{code, message, data}`），与后端 FastAPI 返回结构一致 */
const envelope = (data: unknown) => ({ data: { code: 0, message: 'ok', data } })

const openllmModule: ModuleDefinition = {
  id: 'openllm',
  name: 'OpenLLM',
  icon: 'cpu',
  route_prefix: '/openllm',
  entry: 'modules/openllm',
  permission: 'openllm:view',
  status: 'enabled',
  sort_order: 10,
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('DEF-FE-146-001: modulesWriteApi.switch 统一信封解包', () => {
  it('解包 data 层返回扁平业务对象（修复前 id/status/previous_status/effective/request_id 全 undefined）', async () => {
    const payload = {
      id: 'openllm',
      status: 'disabled' as const,
      previous_status: 'enabled' as const,
      effective: 'next_login' as const,
      request_id: 'req-146-0001',
    }
    mocks.patch.mockResolvedValueOnce(envelope(payload))

    const result = await modulesWriteApi.switch('openllm', 'disabled')

    expect(mocks.patch).toHaveBeenCalledTimes(1)
    expect(mocks.patch).toHaveBeenCalledWith('/modules/openllm', { status: 'disabled' })
    // 严格全等：返回整包（未解包）或字段缺失都会失败
    expect(result).toEqual(payload)
    expect(result.id).not.toBeUndefined()
    expect(result.status).not.toBeUndefined()
    expect(result.previous_status).not.toBeUndefined()
    expect(result.effective).not.toBeUndefined()
    expect(result.request_id).not.toBeUndefined()
    expect(result.status).toBe('disabled')
    expect(result.previous_status).toBe('enabled')
    expect(result.effective).toBe('next_login')
    expect(result.request_id).toBe('req-146-0001')
  })

  it('启用路径同样解包（previous_status=disabled），且模块 ID 参与 URL 编码位置', async () => {
    const payload = {
      id: 'knowledge',
      status: 'enabled' as const,
      previous_status: 'disabled' as const,
      effective: 'next_login' as const,
      request_id: 'req-146-0002',
    }
    mocks.patch.mockResolvedValueOnce(envelope(payload))

    const result = await modulesWriteApi.switch('knowledge', 'enabled')

    expect(mocks.patch).toHaveBeenCalledWith('/modules/knowledge', { status: 'enabled' })
    expect(result).toEqual(payload)
    expect(result.status).toBe('enabled')
    expect(result.previous_status).toBe('disabled')
  })

  it('幂等回读（previous_status === status）原样透传，不篡改服务端语义', async () => {
    const payload = {
      id: 'openllm',
      status: 'disabled' as const,
      previous_status: 'disabled' as const,
      effective: 'next_login' as const,
      request_id: 'req-146-0003',
    }
    mocks.patch.mockResolvedValueOnce(envelope(payload))

    expect(await modulesWriteApi.switch('openllm', 'disabled')).toEqual(payload)
  })

  it('错误分支：403 权限异常原样上抛（不吞异常、不返回伪成功对象）', async () => {
    const failure = Object.assign(new Error('Request failed with status code 403'), {
      response: {
        status: 403,
        data: { code: 'PERM_DENIED', message: '缺少 module:manage 权限', detail: null, request_id: 'req-146-403' },
      },
    })
    mocks.patch.mockRejectedValueOnce(failure)

    await expect(modulesWriteApi.switch('openllm', 'disabled')).rejects.toBe(failure)
    expect(mocks.patch).toHaveBeenCalledTimes(1)
  })

  it('错误分支：留痕不可用（503 BIZ）原样上抛，调用方按失败回滚', async () => {
    const failure = Object.assign(new Error('Request failed with status code 503'), {
      response: {
        status: 503,
        data: {
          code: 'BIZ_MODULE_SWITCH_AUDIT_UNAVAILABLE',
          message: 'module switch rejected: audit trail unavailable',
          detail: { module_id: 'openllm', reason: 'audit persist disabled' },
          request_id: 'req-146-503',
        },
      },
    })
    mocks.patch.mockRejectedValueOnce(failure)

    await expect(modulesWriteApi.switch('openllm', 'disabled')).rejects.toBe(failure)
    expect(mocks.patch).toHaveBeenCalledTimes(1)
  })
})

describe('DEF-FE-146-002: modules.ts 注册表只读', () => {
  it('listModuleDefinitions 解包信封并取 items（不返回整包）', async () => {
    const items: ModuleDefinition[] = [
      openllmModule,
      { ...openllmModule, id: 'memory', name: 'OpenMemory', route_prefix: '/memory', sort_order: 30 },
    ]
    mocks.get.mockResolvedValueOnce(envelope({ items, total: items.length }))

    const result = await listModuleDefinitions()

    expect(mocks.get).toHaveBeenCalledTimes(1)
    expect(mocks.get).toHaveBeenCalledWith('/modules')
    expect(result).toEqual(items)
    expect(result).toHaveLength(2)
    expect(result[0].route_prefix).toBe('/openllm')
  })

  it('空注册表边界：items 为空数组时返回 []，不抛错', async () => {
    mocks.get.mockResolvedValueOnce(envelope({ items: [], total: 0 }))

    expect(await listModuleDefinitions()).toEqual([])
  })

  it('错误分支：列表接口异常原样上抛（页面据此渲染加载失败提示）', async () => {
    const failure = new Error('modules list boom')
    mocks.get.mockRejectedValueOnce(failure)

    await expect(listModuleDefinitions()).rejects.toBe(failure)
  })
})

describe('DEF-FE-146-001: 模块开关页「修改详情」抽屉端到端回归', () => {
  it('切换成功后抽屉「模块/新状态/生效方式/请求号」四项均非空（修复前四项全空）', async () => {
    mocks.get.mockResolvedValueOnce(envelope({ items: [openllmModule], total: 1 }))
    mocks.patch.mockResolvedValueOnce(
      envelope({
        id: 'openllm',
        status: 'disabled',
        previous_status: 'enabled',
        effective: 'next_login',
        request_id: 'req-146-0001',
      }),
    )

    const wrapper = mount(ModuleSwitchView, { global: { plugins: [ElementPlus] } })
    await flushPromises()

    const switchControl = wrapper.find('[data-test="module-switch"]')
    expect(switchControl.exists()).toBe(true)
    expect(wrapper.findAll('[data-test="module-switch"]')).toHaveLength(1)

    // el-switch 受控（model-value=enabled）→ 点击语义为「停用」：change(false)
    await switchControl.trigger('click')
    await flushPromises()
    await flushPromises()

    expect(mocks.patch).toHaveBeenCalledWith('/modules/openllm', { status: 'disabled' })

    const drawerBody = wrapper.find('.el-drawer__body')
    expect(drawerBody.exists()).toBe(true)
    const detailText = drawerBody.text()
    expect(detailText.trim().length).toBeGreaterThan(0)
    expect(detailText).toContain('openllm')
    expect(detailText).toContain('disabled')
    expect(detailText).toContain('下次登录/刷新')
    expect(detailText).toContain('req-146-0001')
    expect(detailText).not.toContain('undefined')
    expect(wrapper.find('.el-drawer').exists()).toBe(true)
  })

  it('切换失败：抽屉不弹出、不改写表格状态；以服务端为准重载列表', async () => {
    const listItems: ModuleDefinition[] = [
      { ...openllmModule, id: 'openllm', status: 'enabled' },
      { ...openllmModule, id: 'memory', name: 'OpenMemory', route_prefix: '/memory', sort_order: 30 },
    ]
    mocks.get.mockResolvedValueOnce(envelope({ items: listItems, total: 2 }))
    mocks.get.mockResolvedValueOnce(envelope({ items: listItems, total: 2 }))
    mocks.patch.mockRejectedValueOnce(
      Object.assign(new Error('Request failed with status code 503'), {
        response: { status: 503, data: { code: 'BIZ_MODULE_SWITCH_AUDIT_UNAVAILABLE', message: '留痕不可用' } },
      }),
    )

    const wrapper = mount(ModuleSwitchView, { global: { plugins: [ElementPlus] } })
    await flushPromises()

    await wrapper.findAll('[data-test="module-switch"]')[0].trigger('click')
    await flushPromises()
    await flushPromises()

    // 失败 → 抽屉不弹出（无「修改详情」结果）；重载列表 = 第 2 次 GET
    expect(wrapper.find('.el-drawer__body').exists()).toBe(false)
    expect(mocks.get).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('OpenLLM')
  })
})

describe('DEF-FE-146-002: testingApi 人工测试记录 4 端点', () => {
  const record: TestCaseRecord = {
    id: 7,
    run_id: 'run-146',
    case_id: 'C-146-001',
    step_id: 2,
    result: 'PASS',
    title: '模块开关留痕',
    expected: '写入 audit_logs',
    observed: '已写入',
    reason: '',
    request_id: 'req-146-test',
    duration_ms: 120,
    channel: 'api',
    operator: '1',
  }

  it('createRun 返回统一信封（调用方按 res.data.run_id 读取）', async () => {
    mocks.post.mockResolvedValueOnce(envelope({ run_id: 'run-146' }))

    const result = await testingApi.createRun({ run_id: 'run-146', title: 'v1.4.6 回归', scope: 'modules' })

    expect(mocks.post).toHaveBeenCalledTimes(1)
    expect(mocks.post).toHaveBeenCalledWith('/test-runs', { run_id: 'run-146', title: 'v1.4.6 回归', scope: 'modules' })
    expect(result).toEqual({ code: 0, message: 'ok', data: { run_id: 'run-146' } })
    expect(result.data.run_id).toBe('run-146')
  })

  it('createRecord 透传用例字段并返回记录', async () => {
    mocks.post.mockResolvedValueOnce(envelope(record))

    const result = await testingApi.createRecord({
      run_id: 'run-146',
      case_id: 'C-146-001',
      step_id: 2,
      result: 'PASS',
      title: '模块开关留痕',
      request_id: 'req-146-test',
      duration_ms: 120,
    })

    expect(mocks.post).toHaveBeenCalledWith('/test-records', {
      run_id: 'run-146',
      case_id: 'C-146-001',
      step_id: 2,
      result: 'PASS',
      title: '模块开关留痕',
      request_id: 'req-146-test',
      duration_ms: 120,
    })
    expect(result.data).toEqual(record)
    expect(result.data.request_id).not.toBeUndefined()
  })

  it('updateRecord 走 PATCH 且 ID 落路径', async () => {
    mocks.patch.mockResolvedValueOnce(envelope({ ...record, result: 'FAIL', reason: '留痕缺失' }))

    const result = await testingApi.updateRecord(7, { result: 'FAIL', reason: '留痕缺失', observed: '无 audit 行' })

    expect(mocks.patch).toHaveBeenCalledWith('/test-records/7', {
      result: 'FAIL',
      reason: '留痕缺失',
      observed: '无 audit 行',
    })
    expect(result.data.result).toBe('FAIL')
    expect(result.data.reason).toBe('留痕缺失')
  })

  it('runSummary 对 run_id 做 URL 编码并返回轮次汇总', async () => {
    const summary: RunSummary = {
      run_id: 'run/146 a',
      total: 2,
      pass: 1,
      fail: 1,
      blocked: 0,
      skipped: 0,
      passed: false,
      cases: [
        {
          case_id: 'C-146-001',
          latest_result: 'PASS',
          steps: [
            {
              id: 1,
              step_id: 1,
              result: 'PASS',
              reason: null,
              request_id: 'req-1',
              duration_ms: 10,
              title: '步骤一',
            },
          ],
        },
      ],
    }
    mocks.get.mockResolvedValueOnce(envelope(summary))

    const result = await testingApi.runSummary('run/146 a')

    expect(mocks.get).toHaveBeenCalledWith('/test-runs/run%2F146%20a/summary')
    expect(result.data).toEqual(summary)
    expect(result.data.passed).toBe(false)
    expect(result.data.cases[0].steps[0].request_id).not.toBeUndefined()
  })

  it('错误分支：异常原样上抛（页面 catch 后不清空既有汇总）', async () => {
    const failure = new Error('test-runs boom')
    mocks.get.mockRejectedValueOnce(failure)
    await expect(testingApi.runSummary('run-146')).rejects.toBe(failure)

    const postFailure = new Error('createRun boom')
    mocks.post.mockRejectedValueOnce(postFailure)
    await expect(testingApi.createRun({})).rejects.toBe(postFailure)

    const patchFailure = new Error('updateRecord boom')
    mocks.patch.mockRejectedValueOnce(patchFailure)
    await expect(testingApi.updateRecord(1, { result: 'BLOCKED' })).rejects.toBe(patchFailure)
  })

  it('结果文案与标签色映射：PASS/FAIL/BLOCKED/SKIPPED 全覆盖', () => {
    expect(resultTagType('PASS')).toBe('success')
    expect(resultTagType('FAIL')).toBe('danger')
    expect(resultTagType('BLOCKED')).toBe('warning')
    expect(resultTagType('SKIPPED')).toBe('info')

    expect(resultLabel('PASS')).toBe('通过')
    expect(resultLabel('FAIL')).toBe('失败')
    expect(resultLabel('BLOCKED')).toBe('阻塞')
    expect(resultLabel('SKIPPED')).toBe('跳过')
  })
})
