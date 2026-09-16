/**
 * 模块注册表 API（对齐后端 /api/v1/modules 契约）
 *
 * 与 core/api/auth.ts 的 `modulesApi`（只读 list）不同，本文件提供 v1.4.6 新增的
 * 模块开关写路径（PATCH，ADR-146-07 / AC-146-15）与类型化响应，供 ModuleSwitchView 使用。
 *
 * 生效语义（ADR-146-07）：`effective=next_login` —— **不承诺热生效**；前端不自行刷新注册表。
 * 统一在页面展示该提示，避免误导用户。
 */
import { http, type ApiSuccess } from './http'

/** 模块开关响应（后端 PATCH 返回统一信封 `{code, message, data}`，`data` 为扁平字段） */
export interface ModuleSwitchResult {
  id: string
  status: 'enabled' | 'disabled'
  previous_status: 'enabled' | 'disabled'
  /** 固定 `next_login`（ADR-146-07：不承诺热生效） */
  effective: 'next_login'
  request_id: string
}

export interface ModuleDefinition {
  id: string
  name: string
  icon?: string
  route_prefix: string
  entry: string
  permission: string
  status: 'enabled' | 'disabled'
  sort_order: number
}

export const modulesWriteApi = {
  /**
   * 模块启用/停用（POST → PATCH）。返回生效语义与请求号。
   *
   * 解包口径与 `logs.ts` 一致：后端返回统一信封 `{code, message, data}`，
   * 此处**必须**取 `data.data`（业务对象），否则调用方按扁平字段读取会全部得到
   * `undefined`（DEF-FE-146-001）。类型声明同步为 `ApiSuccess<ModuleSwitchResult>`。
   *
   * @param moduleId 模块 ID（如 `openllm`）
   * @param status   目标状态
   */
  async switch(moduleId: string, status: 'enabled' | 'disabled'): Promise<ModuleSwitchResult> {
    const { data } = await http.patch<ApiSuccess<ModuleSwitchResult>>(`/modules/${moduleId}`, { status })
    return data.data
  },
}

/** 注册表只读（复用既有契约，供开关页展示字段补全） */
export async function listModuleDefinitions(): Promise<ModuleDefinition[]> {
  const { data } = await http.get<ApiSuccess<{ items: ModuleDefinition[]; total: number }>>('/modules')
  return data.data.items
}