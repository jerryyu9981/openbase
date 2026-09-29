# OpenBase 权限 / 限流 / API 管理 / 监控 归属裁定与收口方案 - v1.4.10

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.10（承接型小版本：DPS 模板化能力对接深化） |
| 文档 | 权限 / 限流 / API 管理 / 监控 归属裁定与收口方案 |
| 文档版本 | v1.0.0 |
| 状态 | **[Review]**（待人工批准） |
| 适用环境 | Dev / Test / Pro |
| 作者 | AA-OpenBase-Dev（架构归属裁定）／FA-OpenBase-Dev（前端路由与页面归属） |
| 复核 | AU-OpenBase-Dev（口径一致性与证据复核） |
| 创建日期 | 2026-09-29 |
| 更新日期 | 2026-09-29 |
| 存放 | `doc/design/` |
| 性质 | **跨版本归属口径裁定 + 收口项登记**；本方案**不改四仓任何文件**（沿用 VC-014 边界），**不计入 v1.4.10 功能范围** |
| 上游依据 | 《开发需求文档-v1.4.6》§4.11／§4.12／§4.13／§10.6（BL-146-11／12／13）；《需求评审记录-v1.4.6》决议 7／9／10（2026-09-15）；《路径归属矩阵-v1.4.6》；《系统架构设计文档-v1.4.9》；《模块成熟度审计与来源决策-v1.0.0》；《编排归属与 DSL 边界定界-v1.4.8》；版本范围变更 VC-006 |
| 下游影响 | 《系统架构设计文档》《前端架构设计文档》《路径归属矩阵》《需求设计追溯矩阵》须按本方案登记口径与收口项 |

---

## 0. 裁定摘要

**结论：不是二选一。** 按 OpenBase 整体设计，四项能力的归属按 **「跨模块通用 vs 仅本模块业务语义」** 切分——**机制与平台通用治理面上收到 OpenBase 底座，只有服务单一模块业务语义的管理面留在 AI 基础设施模块侧（画像 DPS／记忆 OpenMemory／知识库 OpenRAG／模型 OpenLLM）**。

判定口径（契约化，沿用《开发需求文档-v1.4.6》BL-146-12）：

| 判定 | 口径 | 判据 |
|------|------|------|
| **上收（→ OpenBase）** | 该能力**跨模块通用**（治理／观测／配置／身份／密钥／用量） | 四系统同时需要；分散实现必然产生口径分叉 |
| **留模块（→ AI 模块侧）** | 该能力**仅**服务本模块业务语义 | 仅能在单一模块内解释；无跨模块复用价值 |

**硬门禁**：四模块**特色页零删减**——上收只变更**归属与入口**，不删除任何业务功能；迁移后模块内以链接／快捷入口指向平台管理域对应页。

逐项裁定：

| 能力 | OpenBase 侧（机制／通用治理） | AI 模块侧（业务语义） | 裁定 |
|------|------------------------------|------------------------|------|
| 权限 | `auth`（RBAC／ABAC + API 密钥）+ 平台「身份与权限」域 | 画像 `DpsPermissionView`（DPS 业务侧权限矩阵） | **通用上收 ／ 业务留模块** |
| 限流 | `tenant`（`QuotaChecker` 配额算法 + 配额接口） | 画像 `DpsRateLimitView`（画像配额与规则） | **机制在底座 ／ 业务面留模块** |
| API 管理 | `gateway`（服务发现／聚合编排）+ 平台「API 密钥」+ `protocol_headers` | 画像 `DpsApiManageView`（DPS 端点／版本／错误码目录） | **框架上收 ／ 业务目录留模块** |
| 监控 | `observability` + `audit` + `logs` + 平台「可观测与审计」域 | `DpsMonitorView` **已裁定上收**，模块侧仅保留业务指标入口 | **整体上收（保留业务指标入口）** |

**收口项 3 条**：COL-01（`DpsMonitorView` 迁移落地并与口径对齐）、COL-02（平台通用「限流与配额」管理页补建）、COL-03（上收后模块侧组件与目录残留清理）。详见 §6。

---

## 1. 背景与问题

### 1.1 问题提出

评估「权限／限流／API 管理／监控」应落位在 **OpenBase 底座侧**，还是 **AI 基础设施模块系统（画像、记忆、知识库、模型）侧**。

### 1.2 既有裁定链（本方案不改口径，只固化与收口）

| 时间 | 来源 | 裁定 |
|------|------|------|
| 2026-09-15 | 《需求评审记录-v1.4.6》决议 7 | 采纳「**上收系统性能力、模块只留特色**」；判定口径契约化（业务专有→留模块，跨模块通用→上收） |
| 2026-09-15 | 《需求评审记录-v1.4.6》决议 9 | 6 项争议页裁定：`DpsMonitorView`／`knowledge/Settings`／`knowledge/Users`／`gateway 模块` → **上收**；`ToolCallMonitorView`／`Routing` → **留模块** |
| 2026-09-15 | 《需求评审记录-v1.4.6》决议 10 | 模块开关管理页纳入 v1.4.6；**通用「限流与配额」页不纳入**（现仅 DPS 侧 `DpsRateLimitView` 属业务侧保留） |
| 2026-08-28 | 版本范围变更 **VC-006** | 归属确认：**统一网关与 API 服务框架均属 OpenBase**（多单体 + 统一网关，非微服务化） |
| — | 《模块成熟度审计与来源决策-v1.0.0》 | `auth`／`tenant`／`audit`／`observability` 四模块已从四系统抽取并落地到 `openbase/modules/` |
| 2026-09-21 | 《编排归属与 DSL 边界定界-v1.4.8》 | 网关 = 薄策略聚合层（BFF）；请求鉴权与身份透传归网关 |

### 1.3 现状实测（证据）

| 证据来源 | 实测内容 |
|----------|----------|
| `openbase/modules/` | 已具备 `auth`（`rbac.py`／`api_keys.py`／`oidc.py`）、`tenant`（`QuotaChecker` + 配额接口）、`gateway`（`discovery.py`／`aggregate.py`／`registry.py`／`probe.py`）、`observability`、`audit`、`logs`、`protocol_headers` 模块 |
| `openbase-ui/src/pages/platform/routes.ts` | 平台四域路由就位：身份与权限（7 页）、平台配置与密钥（3 页，含 API 密钥）、可观测与审计（13 页，含统一监控／日志中心／服务发现与编排）、开发者资源（3 页） |
| `openbase-ui/src/modules/portrait/index.ts` | 画像模块**仍持有** `permissions`／`monitor`／`api-manage`／`rate-limit` 四条业务路由（实测在册） |
| `openbase-ui/src/modules/memory/index.ts` | 记忆模块**已迁出** `admin`／`monitor`／`api-gateway`，旧路径经 `legacyRedirects.ts` 承接（禁 404） |
| `openbase-ui/src/core/router/legacyRedirects.ts` | 已登记 `/portrait/dps-monitor → /platform/observability/monitoring`；**未登记** `/portrait/monitor` 重定向 |

> **判定**：口径本身**无歧义**；问题不在「该不该分层」，而在**落地一致性**——偏差见 §5。

---

## 2. 判定口径与边界用例

### 2.1 两条口径（契约化）

1. **上收（→ OpenBase 底座）**：能力跨模块通用，落在治理／观测／配置／身份／密钥／用量六类语义内。判据是「**四系统同时需要**」，而不是「该能力听起来像平台能力」。
2. **留模块（→ AI 模块侧）**：能力仅在单一模块的业务语义下可解释，脱离该模块即失去意义。判据是「**是否需要在四模块之间对齐口径**」——需要则上收，不需要则留模块。

### 2.2 边界判定用例（消除残留歧义）

| 场景 | 归属 | 判据 |
|------|------|------|
| 统一用户／角色／组织／租户／工作空间管理 | **上收** → 平台「身份与权限」 | 跨模块通用身份治理；模块**不应有独立用户体系** |
| 画像模板／字段级权限矩阵 | 留模块（画像） | 仅对画像业务语义可解释 |
| 租户级配额算法、限流中间件 | **上收** → `tenant` 模块 | 四系统共用同一配额语义（算法已自 OpenMemory multitenancy 抽取） |
| 画像配额与限流规则配置 | 留模块（画像） | 业务侧规则面，无跨模块复用价值 |
| 统一网关、服务发现、聚合编排、API 密钥 | **上收** → `gateway`／平台「平台配置与密钥」 | VC-006 已定；基础设施能力，非业务模块 |
| DPS 端点／版本／错误码目录 | 留模块（画像） | DPS 自有 API 语义，经 `dps_proxy` 透传呈现 |
| 统一监控仪表盘、日志中心、链路追踪、成本／告警 | **上收** → `observability`／`logs`／平台「可观测与审计」 | 跨模块通用观测 |
| LLM 工具调用监控、模型路由与熔断 | 留模块（模型） | 属 LLM 能力**固有观测维度**与平台联动能力（决议 9） |
| 记忆衰减配置 | 留模块（记忆） | 记忆域特色能力 |

### 2.3 术语防歧义（强制分写）

- **「API 管理」须分写为两义**：**API 服务框架**（网关／服务发现／密钥 → OpenBase）与**业务 API 目录**（DPS 端点／版本／错误码 → 模块侧）。禁止混用单一词项表达两者。
- **「监控」须分写为两义**：**统一监控**（跨模块通用 → OpenBase）与**业务指标入口**（模块侧保留，指向统一监控）。**上收 ≠ 删除业务指标**。

---

## 3. 逐项裁定

### 3.1 权限（OWN-01）

| 项 | 内容 |
|----|------|
| 现状 | 底座 `auth` 已提供 RBAC／ABAC + API 密钥；平台「身份与权限」域 7 页就位；画像侧 `DpsPermissionView` 在册 |
| 裁定 | **通用身份与权限上收**（用户／角色／组织／租户／工作空间／认证扩展／API 密钥）；**DPS 业务侧权限矩阵留模块** |
| 依据 | 决议 7／9；《开发需求文档-v1.4.6》§10.6.2 ①：`DpsPermissionView` 判为留模块，理由「DPS **业务侧**权限，非平台通用治理」；`knowledge/Users`、`memory/Admin` 已按同口径上收 |
| 落点 | OpenBase：`openbase/modules/auth`、`openbase/modules/identity`、平台「身份与权限」域；模块侧：`modules/portrait/pages/DpsPermissionView.vue` |
| 不变式 | 模块**不得**自建用户体系；**权限码 ↔ 菜单可见性 ↔ 路由守卫三处一致** |

### 3.2 限流（OWN-02）

| 项 | 内容 |
|----|------|
| 现状 | 底座 `tenant` 模块已含 `QuotaChecker`（自 OpenMemory `multitenancy/quota_checker.py` 抽取）与配额接口（`POST／GET／PUT .../quota`）；平台「平台配置与密钥」域**尚无**「限流与配额」页 |
| 裁定 | **配额与限流机制上收 `tenant` 模块**；**画像业务侧配额与规则面留模块**（`DpsRateLimitView`）；平台通用「限流与配额」管理页**判定为待建**（非本次上收项） |
| 依据 | 决议 10：通用限流配额页**不纳入** v1.4.6，现仅 DPS 侧 `DpsRateLimitView` 属业务侧保留；《开发需求文档-v1.4.6》§10.6.2 ⑥ 已把「限流与配额（通用）」登记为**待建** |
| 落点 | OpenBase：`openbase/modules/tenant`；模块侧：`modules/portrait/pages/DpsRateLimitView.vue` |
| 不变式 | 限流**算法与配额存储口径**只允许在 `tenant` 模块内实现一处；模块侧不得各写一套限流器 |

### 3.3 API 管理（OWN-03）

| 项 | 内容 |
|----|------|
| 现状 | 底座 `gateway` 模块（服务发现／聚合编排／注册表／探针）与 `protocol_headers`（四维身份注入）已就位；平台「可观测与审计」域含「服务发现与编排」「聚合网关测试」，「平台配置与密钥」域含「API 密钥」 |
| 裁定 | **API 服务框架上收 OpenBase**（网关／服务发现／聚合编排／API 密钥／协议头）；**DPS 业务 API 目录留模块**（`DpsApiManageView`，经 `dps_proxy` 透传） |
| 依据 | **VC-006**：统一网关与 API 服务框架均属 OpenBase；决议 9：`gateway` 模块**整体**从「业务模块」区迁入平台「可观测与审计」域（基础设施能力，非业务模块）；《开发需求文档-v1.4.6》§10.6.2 ①：`DpsApiManageView` 判为留模块，理由「DPS **业务侧**接口管理」 |
| 落点 | OpenBase：`openbase/modules/gateway`、`openbase/modules/protocol_headers`、平台「平台配置与密钥」的 API 密钥页；模块侧：`modules/portrait/pages/DpsApiManageView.vue` |
| 不变式 | `gateway` **不得**回流为业务模块；模块侧**不得**自建网关／服务发现 |

### 3.4 监控（OWN-04）

| 项 | 内容 |
|----|------|
| 现状 | 底座 `observability`／`audit`／`logs` 模块与平台「可观测与审计」域 13 页均已就位（含统一监控 `/platform/observability/monitoring`）；但 `DpsMonitorView` **仍以 `/portrait/monitor` 在册** |
| 裁定 | **统一监控整体上收**（监控仪表盘／日志中心／链路追踪／成本／预算／告警／用量／GPU／计费）；`DpsMonitorView` **上收**，DPS 侧**仅保留业务指标入口**（链接指向统一监控） |
| 依据 | 决议 9（2026-09-15）明确 `DpsMonitorView` → 上收；《开发需求文档-v1.4.6》§10.6.2 ①、「10.6.3 上收汇总」均含 `DpsMonitorView`；`ToolCallMonitorView`／`Routing` 因属 LLM 固有观测与联动能力而留模块 |
| 落点 | OpenBase：`openbase/modules/observability`、`openbase/modules/logs`、`openbase/modules/audit`、平台「可观测与审计」域；模块侧：仅业务指标入口（`DpsMonitorView` **不再**作为独立业务监控页承载通用监控职责） |
| 不变式 | 监控**不得**出现第二套仪表盘实现；业务指标**必须**保留可见入口（零删减门禁） |

---

## 4. 归属矩阵（全量）

| 能力 | 侧 | 承载物 | 路径／模块 | 现状 |
|------|:--:|--------|-----------|:----:|
| 权限 | OpenBase | `auth` 模块（RBAC／ABAC／API 密钥） | `openbase/modules/auth` | 已就位 |
| 权限 | OpenBase | 身份与权限域（租户／角色／组织／工作空间／认证扩展／用户／记忆席位） | `/platform/identity/**` | 已就位 |
| 权限 | 模块侧 | DPS 业务侧权限矩阵 | `/portrait/permissions` | 在册（留模块，符合口径） |
| 限流 | OpenBase | `tenant` 模块（`QuotaChecker` + 配额接口） | `openbase/modules/tenant` | 已就位 |
| 限流 | OpenBase | 通用「限流与配额」管理页 | 平台「平台配置与密钥」域 | **缺位（待建）** |
| 限流 | 模块侧 | 画像配额与规则 | `/portrait/rate-limit` | 在册（留模块，符合口径） |
| API 管理 | OpenBase | `gateway` 模块（服务发现／聚合编排） | `openbase/modules/gateway` | 已就位 |
| API 管理 | OpenBase | API 密钥 + 服务发现与编排 + 聚合网关测试 | `/platform/config/api-keys`、`/platform/observability/service-discovery`、`/platform/observability/gateway-test` | 已就位 |
| API 管理 | OpenBase | 四维身份协议头注入 | `openbase/modules/protocol_headers` | 已就位 |
| API 管理 | 模块侧 | DPS 端点／版本／错误码目录 | `/portrait/api-manage` | 在册（留模块，符合口径） |
| 监控 | OpenBase | `observability`／`logs`／`audit` 模块 | `openbase/modules/observability`、`logs`、`audit` | 已就位 |
| 监控 | OpenBase | 统一监控／日志中心／链路追踪／成本／告警／用量／GPU／计费／预算／应用调用记录 | `/platform/observability/**` | 已就位 |
| 监控 | 模块侧 | `DpsMonitorView` | `/portrait/monitor` | **在册（应上收，未迁移 → DEV-01）** |
| 监控 | 模块侧 | 业务指标入口 | 指向 `/platform/observability/monitoring` | **待建（随 COL-01）** |

---

## 5. 偏差登记（Decision ↔ Implementation 一致性）

| 编号 | 偏差 | 证据 | 影响 | 级别 |
|:----:|------|------|------|:----:|
| **DEV-01** | `DpsMonitorView` 已裁定**上收**，但前端仍以 `/portrait/monitor` 作为画像模块业务路由在册，未迁移、未重定向 | `openbase-ui/src/modules/portrait/index.ts`（`monitor` 在册）；`openbase-ui/src/core/router/legacyRedirects.ts`（**未登记** `/portrait/monitor`）；《路径归属矩阵-v1.4.6》仍将 `/portrait/monitor` 登记为「业务模块本色，不迁移」 | 平台「统一监控」与画像「系统监控」**双入口并存**，口径与决议 9 不一致；用户对「监控到底归谁」产生歧义 | P1 |
| **DEV-02** | 平台通用「限流与配额」管理页**缺位**：机制已在底座（`tenant`），管理面无平台落点 | `openbase-ui/src/pages/platform/routes.ts` 的 `configRoutes` 仅含全局配置／模块开关／API 密钥 | 「平台配置与密钥」域对限流配额**不可见、不可配**；诉求只能落在 DPS 业务页，加剧「限流到底归谁」的歧义 | P2 |
| **DEV-03** | 上收后组件与目录**残留**：`MemoryMonitorView.vue`、`ApiGateway.vue` 仍位于 `modules/memory/pages/`，但**已无任何引用**（路由已迁出） | `openbase-ui/src/modules/memory/index.ts`（不含 monitor／api-gateway）；全仓检索 `MemoryMonitorView`／`ApiGateway` **0 命中引用** | 模块目录不纯（违反 BL-146-13「模块目录只含本模块特色」）；可能被误读为「记忆侧仍在承载监控/网关」 | P2 |

> **一致性结论**：§0 裁定口径**无需变更**；上述三项均为**落地偏差**，按 §6 收口。

---

## 6. 收口计划

| 编号 | 收口项 | 动作 | 责任角色 | 验收标准 |
|:----:|--------|------|----------|----------|
| **COL-01** | `DpsMonitorView` 迁移落地与口径对齐 | ① 画像模块内**下线** `/portrait/monitor` 业务监控页承载职责，改为**业务指标入口**（链接／快捷入口指向 `/platform/observability/monitoring`）；② `legacyRedirects.ts` 登记旧路径承接（**禁 404**，兼容书签与既有 E2E）；③ **同步更新**《路径归属矩阵》与《前端架构设计文档》，消除「本色不迁移」残留登记 | FA-OpenBase-Dev | AC-OWN-01／02／03 |
| **COL-02** | 平台通用「限流与配额」管理页补建 | 以「平台配置与密钥」域为落点新增管理页，数据面挂接 `tenant` 模块配额接口（`GET／PUT .../quota`）；若判定不建，须**显式登记「不建 + 理由」**，不得静默缺位 | AA-OpenBase-Dev + FA-OpenBase-Dev | AC-OWN-04／05 |
| **COL-03** | 上收后残留清理 | 清理 `modules/memory/pages/MemoryMonitorView.vue`、`modules/memory/pages/ApiGateway.vue` 等**零引用**残留组件（**先列出清单并取得批准，禁止擅自删除**）；清理后模块目录只含本模块特色页 | FA-OpenBase-Dev | AC-OWN-06 |

**排期建议**：COL-01／COL-03 属前端归属治理，**可并入下一承接型小版本**（与既有 IA 治理同类，零后端依赖）；COL-02 需 `tenant` 配额接口对齐与页面新增，**建议单独立项评估**。

---

## 7. 不变式与硬门禁

| 编号 | 不变式 | 说明 |
|:----:|--------|------|
| INV-01 | **特色页零删减** | 上收只变更归属与入口；四模块业务功能一律不删 |
| INV-02 | **单一实现源** | 身份／配额算法／网关／统一监控在 `openbase/modules` 内**各自只有一处实现**，模块侧不得各写一套 |
| INV-03 | **模块无独立用户体系** | 模块侧不得自建用户／角色体系，与统一身份／租户体系冲突 |
| INV-04 | **旧路径禁 404** | 任何归属迁移必须由 `legacyRedirects.ts` 承接旧路径 |
| INV-05 | **三处一致** | 权限码 ↔ 菜单可见性 ↔ 路由守卫三处一致 |
| INV-06 | **四仓零改动** | 本方案及收口项**不改** OpenLLM／OpenRAG／OpenMemory／DPS 任一仓文件（沿用 VC-014） |
| INV-07 | **视觉不改** | 本轮只做归属与入口治理，不改视觉规范与设计系统 |

---

## 8. 风险、假设与约束

| 类型 | 内容 | 应对 |
|------|------|------|
| 风险 | COL-01 迁移触发画像侧入口消失，用户感知为「功能被删」 | 保留业务指标入口并先行登记；旧路径重定向 + 短信/文档告知；E2E 断言菜单与深链 |
| 风险 | 「DPS 业务侧权限／限流」与平台「通用权限／配额」的**业务语义边界**被反复争议 | 以 §2.2 判定用例为准；边界争议**由用户裁决**，不自行武断（沿用 §4.11 要求 ③） |
| 风险 | DEV-02 长期不补建，导致限流诉求持续沉淀在 DPS 业务页 | 本方案显式登记为收口项；不建亦须显式登记理由 |
| 假设 | 平台四域路由与 `openbase/modules` 能力在本方案有效期内**不再发生结构性变更** | 若变更，须升版本方案并同步下游文档 |
| 约束 | 本方案不引入新服务、不改四仓、不改模块注册表语义（`id`／`route_prefix`／`permission` 不变） | 收口项验收按 §7 不变式核对 |
| 约束 | `DpsPermissionView`／`DpsRateLimitView`／`DpsApiManageView` 的**业务语义边界**以 DPS 契约为唯一事实源 | 与 DPS 契约冲突时以契约为准并回写本方案 |

---

## 9. 验收标准

| 编号 | 验收标准 | 验证方式 |
|:----:|----------|----------|
| AC-OWN-01 | `/portrait/monitor` 不再作为独立业务监控页承载通用监控职责；画像侧存在指向 `/platform/observability/monitoring` 的业务指标入口 | 前端路由表核对 + 手工走查截图 |
| AC-OWN-02 | `/portrait/monitor` 旧路径**可访问且不 404**（经 `legacyRedirects.ts` 承接） | 深链直访 E2E 断言 |
| AC-OWN-03 | 《路径归属矩阵》与《前端架构设计文档》中 `DpsMonitorView` 的登记与决议 9 一致（差异 0） | 文档比对 |
| AC-OWN-04 | 平台「限流与配额」管理页可读列表并经 `tenant` 配额接口读写；**或**已显式登记「不建 + 理由」 | 页面走查 + 接口联调 / 文档核对 |
| AC-OWN-05 | 限流算法与配额存储口径在仓库内**仅 `tenant` 模块一处**实现 | 代码检索（0 处重复实现） |
| AC-OWN-06 | `modules/memory/pages/` 下零引用残留组件已清理（清理清单经批准），模块目录只含本模块特色页 | 目录核对 + 引用检索 0 命中 |
| AC-OWN-07 | 全量入口检查：菜单可见性（有／无权限两角色）、深链直访、旧路径重定向、`console.warn = 0` | E2E |
| AC-OWN-08 | 四仓（OpenLLM／OpenRAG／OpenMemory／DPS）**零文件改动** | `git status` 跨仓核查 |

---

## 10. 附录：证据索引

| 编号 | 证据 | 位置 |
|:----:|------|------|
| E-01 | 上收判定口径契约化 | 《开发需求文档-v1.4.6》§4.12（BL-146-12） |
| E-02 | 全量功能归属矩阵与逐页理由 | 《开发需求文档-v1.4.6》§10.6.2 |
| E-03 | 上收/迁移汇总（决策 9 全裁定） | 《开发需求文档-v1.4.6》§10.6.3 |
| E-04 | 模块目录边界治理要求 | 《开发需求文档-v1.4.6》§4.13（BL-146-13） |
| E-05 | 决议 7／9／10 | 《需求评审记录-v1.4.6》 |
| E-06 | 网关与 API 服务框架归属 | 版本范围变更 **VC-006**（2026-08-28） |
| E-07 | 四模块来源决策与抽取执行记录 | 《模块成熟度审计与来源决策-v1.0.0》 |
| E-08 | 网关薄策略层与鉴权透传边界 | 《编排归属与 DSL 边界定界-v1.4.8》 |
| E-09 | 路径归属基线 | 《路径归属矩阵-v1.4.6》 |
| E-10 | 平台四域路由实现 | `openbase-ui/src/pages/platform/routes.ts` |
| E-11 | 画像模块路由（四条业务页在册） | `openbase-ui/src/modules/portrait/index.ts` |
| E-12 | 记忆模块路由（已迁出） | `openbase-ui/src/modules/memory/index.ts` |
| E-13 | 旧路径重定向承接表 | `openbase-ui/src/core/router/legacyRedirects.ts` |
| E-14 | `tenant` 配额机制 | `openbase/modules/tenant/__init__.py` |

---

## 11. 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|------|------|--------|----------|
| v1.0.0 | 2026-09-29 | AA-OpenBase-Dev | 初始创建。固化「权限／限流／API 管理／监控」归属口径（上收 vs 留模块两条判据 + 9 条边界用例 + 术语强制分写），输出四项能力逐项裁定（OWN-01~04）与全量归属矩阵；登记三项落地偏差（DEV-01 `DpsMonitorView` 未迁移／DEV-02 平台通用限流与配额页缺位／DEV-03 上收后组件残留）与三项收口计划（COL-01~03）；定义 7 条不变式与 8 条验收标准。状态 [Review] |
