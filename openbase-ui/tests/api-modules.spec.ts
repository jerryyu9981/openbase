/**
 * 模块开关 API 客户端单测（DEF-FE-146-002：`src/core/api/modules.ts` v1.4.6 新增模块补测）
 *
 * 覆盖面（对齐 ADR-146-07 / AC-146-15 / DEF-FE-146-001）：
 * - `modulesWriteApi.switch`：POST→PATCH 写路径、**统一信封双重解包**（`data.data` 业务对象，
 *   回归 DEF-FE-146-001 未解包导致字段全为 undefined 的缺陷）、`effective=next_login` 语义；
 * - `listModuleDefinitions`：注册表只读，信封内 `{items,total}` 解包；
 * - 错误分支：异常原样上抛，不吞异常。
 *
 * 断言口径与 `api-logs.spec.ts` 一致：`toEqual` 严格全等 + `rejects.toBe` 身份全等。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({ get: vi.fn(), patch: vi.fn() }))

vi.mock('@/core/api/http', () => ({
  http: { get: mocks.get, patch: mocks.patch },
}))

import {
  listModuleDefinitions,
  modulesWriteApi,
  type ModuleDefinition,
  type ModuleSwitchResult,
} from '@/core/api/modules'

const envelope = (data: unknown) => ({ data: { code: 0, message: 'ok', data } })

interface PatchCall {
  url: string
  body: Record<string, unknown>
}

function patchCall(index: number): PatchCall {
  const call = mocks.patch.mock.calls[index] as [string, { status: string }]
  return { url: call[0], body: call[1] }
}

interface GetCall {
  url: string
}

function getCall(index: number): GetCall {
  const call = mocks.get.mock.calls[index] as [string]
  return { url: call[0] }
}

const switchResult: ModuleSwitchResult = {
  id: 'openllm',
  status: 'disabled',
  previous_status: 'enabled',
  effective: 'next_login',
  request_id: 'req-mod-001',
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('DEF-FE-146-002: modulesWriteApi.switch', () => {
  it('PATCH 到 /modules/{id}，双重解包返回业务对象（回归 DEF-FE-146-001）', async () => {
    mocks.patch.mockResolvedValueOnce(envelope(switchResult))

    const result = await modulesWriteApi.switch('openllm', 'disabled')

    expect(mocks.patch).toHaveBeenCalledTimes(1)
    const call = patchCall(0)
    expect(call.url).toBe('/modules/openllm')
    expect(call.body).toEqual({ status: 'disabled' })
    // 关键断言：必须取 `data.data`（业务对象），否则字段全 undefined
    expect(result).toEqual(switchResult)
    expect(result.effective).toBe('next_login')
    expect(result.id).toBe('openllm')
    expect(result.status).toBe('disabled')
    expect(result.previous_status).toBe('enabled')
  })

  it('启用方向 status=enabled 正确透传', async () => {
    mocks.patch.mockResolvedValueOnce(
      envelope({ ...switchResult, status: 'enabled', previous_status: 'disabled' }),
    )

    const result = await modulesWriteApi.switch('gateway', 'enabled')

    expect(patchCall(0).body).toEqual({ status: 'enabled' })
    expect(result.status).toBe('enabled')
    expect(result.previous_status).toBe('disabled')
  })

  it('错误分支：异常原样上抛，不吞异常、不返回伪成功', async () => {
    const failure = Object.assign(new Error('Request failed with status code 403'), {
      response: { status: 403, data: { code: 'PERM_FORBIDDEN' } },
    })
    mocks.patch.mockRejectedValueOnce(failure)

    await expect(modulesWriteApi.switch('openllm', 'enabled')).rejects.toBe(failure)
    expect(mocks.patch).toHaveBeenCalledTimes(1)
  })
})

describe('DEF-FE-146-002: listModuleDefinitions（注册表只读）', () => {
  const definitions: ModuleDefinition[] = [
    {
      id: 'openllm',
      name: 'OpenLLM',
      route_prefix: '/openllm',
      entry: 'modules/openllm',
      permission: 'openllm:read',
      status: 'enabled',
      sort_order: 1,
    },
    {
      id: 'gateway',
      name: 'Gateway',
      route_prefix: '/gateway',
      entry: 'modules/gateway',
      permission: 'gateway:read',
      status: 'disabled',
      sort_order: 2,
    },
  ]

  it('GET /modules 并解包 {items,total}', async () => {
    mocks.get.mockResolvedValueOnce(envelope({ items: definitions, total: 2 }))

    const result = await listModuleDefinitions()

    expect(getCall(0).url).toBe('/modules')
    expect(result).toEqual(definitions)
    expect(result).toHaveLength(2)
    expect(result[1].status).toBe('disabled')
  })

  it('错误分支：异常原样上抛', async () => {
    const failure = new Error('list boom')
    mocks.get.mockRejectedValueOnce(failure)

    await expect(listModuleDefinitions()).rejects.toBe(failure)
    expect(mocks.get).toHaveBeenCalledTimes(1)
  })
})