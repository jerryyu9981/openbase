# OpenBase 字典与 Agent 前端删除闭环 DevLogReport - v1.0.1

## 文档元信息

| 项目 | 内容 |
| --- | --- |
| 文档编号 | OB-DEVLOG-FE-DICT-AGENT-001 |
| 文档版本 | v1.0.1 |
| 文档状态 | [Review]（待人工批准） |
| 编制日期 | 2026-11-07 |
| 适用环境 | 本机 Dev（openbase-ui + OpenBase 8000） |
| 上游依据 | 《OpenBase-基础设施子系统全生命周期走查报告-v2.0.0》§7 GAP-05／GAP-06；《OpenBase-字典与Agent前端删除闭环-实施计划-v1.0.0》 |
| 变更范围 | 仅前端：两页新增、路由与菜单接入、8 项 vitest 用例、路由权限契约扩展；后端零改动 |

### 修订历史

| 版本 | 日期 | 修订内容 | 修订人 |
| --- | --- | --- | --- |
| v1.0.1 | 2026-11-07 | 同步上游走查报告定稿：上游依据与交付清单引用由 v1.5.0 更新为 v2.0.0（[Final]），本文档结论与验证证据不变 | FA-OpenBase-Dev |
| v1.0.0 | 2026-11-07 | 首版：字典与 Agent 前端删除闭环的开发记录与验证证据 | FA-OpenBase-Dev |

---

## 1. 背景与目标

用户问询「前端字典／配置／agent 页面的删除按钮交互等是否已经和后端匹配？」。核查结论：

| 模块 | 前端页面 | 前端 API 模块 | 后端删除端点 | 结论 |
| --- | --- | --- | --- | --- |
| 配置 | `ConfigManageView.vue`（有删除按钮） | `core/api/configs.ts::remove` | `DELETE /api/v1/configs/{key}` | 已匹配，无需改动 |
| 字典 | **不存在** | **不存在** | `DELETE /api/v1/dicts/{type_code}`、`/dicts/items/{item_id}` | 前端缺失 |
| Agent | **不存在** | **不存在** | `DELETE /api/v1/identity/agents/{agent_id}` | 前端缺失 |

核查方法：在 `openbase-ui/src` 全量检索 `dict`／`字典`／`agent` 均无页面或 API 命中；`pages/platform` 40+ 视图与 `core/api` 20 个模块均无对应文件；兄弟目录无第二个 OpenBase 前端工程。

目标：补齐两页最小可用生命周期，使删除交互以后端契约为准，并纳入路由权限与回归测试。

---

## 2. 变更清单

| 编号 | 文件 | 类型 | 内容 |
| --- | --- | --- | --- |
| C-1 | `openbase-ui/src/core/api/dicts.ts` | 新增 | 类型/字典项列表、新建、删除共 6 个方法；类型与字典项删除路径分别 `DELETE /dicts/{code}`、`/dicts/items/{id}` |
| C-2 | `openbase-ui/src/core/api/agents.ts` | 新增 | 列表、新建、删除、密钥列表/签发/吊销；删除返回 `{code, agent_id, status, revoked_keys}` |
| C-3 | `openbase-ui/src/pages/platform/config/DictManageView.vue` | 新增 | 左类型右字典项布局；新建类型/字典项；删除二次确认；409/404 错误条 |
| C-4 | `openbase-ui/src/pages/platform/identity/AgentsView.vue` | 新增 | 列表、新建（raw_key 仅显示一次）、软删、密钥抽屉（签发/吊销）；写操作按 `identity:manage` 控制 |
| C-5 | `openbase-ui/src/pages/platform/routes.ts` | 修改 | 新增 `platform/config/dicts`（无 permission）与 `platform/identity/agents`（`identity:view`） |
| C-6 | `openbase-ui/src/core/layouts/AppLayout.vue` | 修改 | `PLATFORM_LEAVES` 两个域各加一条，图标复用已导入的 `Collection`／`Cpu` |
| C-7 | `openbase-ui/tests/r2-dicts-agents.spec.ts` | 新增 | 8 项接线用例：加载、删除确认/取消、409 呈现、raw_key 展示 |
| C-8 | `openbase-ui/tests/platform-ia.spec.ts` | 修改 | F3 门禁清单增 Agent 页；「仅登录可见」清单增字典页 |

后端无任何代码、配置或数据变更，故不涉及迁移与回滚脚本。

---

## 3. 前后端契约对齐

| 前端动作 | 请求 | 成功响应 | 失败语义与 UI 处置 |
| --- | --- | --- | --- |
| 删除字典项 | `DELETE /api/v1/dicts/items/{id}` | `{deleted}` | 404 → 错误条显示后端 message |
| 删除字典类型 | `DELETE /api/v1/dicts/{code}` | `{code, deleted}` | 409（仍有字典项）→ 错误条显示「存在字典项，禁止删除」；404 → 错误条并刷新 |
| 删除 Agent | `DELETE /api/v1/identity/agents/{id}` | `{code:0, agent_id, status:0, revoked_keys}` | 403 → 错误条显示后端权限提示；成功提示「已删除，吊销密钥 N 条」并刷新 |
| 吊销密钥 | `DELETE /api/v1/identity/agents/{id}/keys/{keyId}` | `{revoked, agent_id, key_id}` | 403／404 同理由错误条呈现 |
| 新建 Agent | `POST /api/v1/identity/agents` | 含 `api_key.raw_key` | 明文仅展示一次，弹窗提示立即保存 |

对齐要点：

1. 删除均使用 `ElMessageBox.confirm` 二次确认；取消为 reject，页面独立 `try/catch` 后 `return`，不落入错误提示。
2. 错误文案优先取 `error.response.data.message`（后端统一信封），无响应体时回落 `Error.message`。
3. 后端 `status=0` 的 Agent 删除按钮置灰，但保留密钥查看；重复删除仍幂等（后端保证）。
4. 字典页不声明 permission：后端 dict 路由无独立权限码，仅由全局 `AuthMiddleware` 要求登录；若误加权限码会导致页面被隐藏。

---

## 4. 验证证据

| 检查 | 命令（`openbase-ui` 目录） | 结果 |
| --- | --- | --- |
| 新增/契约定向单测 | `node_modules\.bin\vitest.cmd run tests/r2-dicts-agents.spec.ts tests/platform-ia.spec.ts` | **2 files / 30 tests passed**（新增 8 + 路由契约 22） |
| ESLint | `node_modules\.bin\eslint.cmd src --ext .ts,.vue` | **0 error**（28 warning 均为存量文件，新增文件 0 warning） |
| 类型检查 | `node_modules\.bin\vue-tsc.cmd --noEmit` | **0 error** |
| 全量前端单测 | `node_modules\.bin\vitest.cmd run` | **40 files / 382 tests passed**（存量 374 + 新增 8；新增前基线 39 files / 374 tests） |

### 4.1 全量回归

```
Test Files  40 passed (40)
     Tests  382 passed (382)
  Duration  952.90s
```

与存量基线相比：测试文件 +1（`tests/r2-dicts-agents.spec.ts`），用例 +8，既有用例 0 失败。控制台中的 Vue Router「No match found」与 jsdom `AggregateError` 为既有无害噪声，改动前后一致。

---

## 5. 影响与回滚

- 影响面：新增两个只读/可写页面与两个侧栏入口；不影响既有页面与后端。
- 回滚方式：`git revert` 本提交即可；无数据迁移、无配置变更。
- 兼容性：`configs.ts` 与配置中心页面未改动，原有删除链路保持 v1.2.0 行为。

---

## 6. 交付清单

| 交付物 | 路径 |
| --- | --- |
| 字典 API 模块 | `openbase-ui/src/core/api/dicts.ts` |
| Agent API 模块 | `openbase-ui/src/core/api/agents.ts` |
| 字典管理页 | `openbase-ui/src/pages/platform/config/DictManageView.vue` |
| Agent 管理页 | `openbase-ui/src/pages/platform/identity/AgentsView.vue` |
| 接线回归用例 | `openbase-ui/tests/r2-dicts-agents.spec.ts` |
| 走查报告回填 | `doc/test/OpenBase-基础设施子系统全生命周期走查报告-v2.0.0.md` §1.3／§6／§7 |
