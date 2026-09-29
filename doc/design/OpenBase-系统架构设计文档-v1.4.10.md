# OpenBase 系统架构设计文档 - v1.4.10

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 文档版本 | v1.0.0 |
| 状态 | **[Review]（待设计评审）** |
| 版本号 | **v1.4.10**（承接型小版本：DPS 模板化能力对接深化） |
| 作者 | AA-OpenBase-Dev（架构）／FA-OpenBase-Dev（前端架构） |
| 创建日期 | 2026-09-29 |
| 上游依据 | 《OpenBase-需求设计追溯矩阵-v1.4.10》v1.0.0（DT 27）；《OpenBase-设计入场检查记录-v1.4.10》v1.0.0（四轨全激活）；《OpenBase-跨系统身份与多租户口径核对-v1.4.10》v1.1.0；DPS《API 接口设计文档-v2.11.0》**v1.2.0** |
| 存放 | `doc/design/` |

---

## 1. 架构总览

### 1.1 分层（现况 ＋ 本版改动面）

```text
┌──────────────────────────────────────────────────────────────┐
│ 接入层  openbase-ui（Vue：core/ ＋ modules/ ＋ pages/）        │
│  本版改动面 🎨：DPS 模块新增 8 类页面（P-01~P-08）            │
│  复用：core/api/http.ts（统一请求）｜core/api/error.ts（错误）│
│        core/router、core/stores（auth/moduleRegistry/ui）     │
└───────────────────────────┬──────────────────────────────────┘
                            │ HTTP（前端零密钥，身份由 cookie/会话承载）
┌───────────────────────────▼──────────────────────────────────┐
│ 应用层  openbase（Python 模块化单体，modules/ 下 24 模块）     │
│  ┌──────────────┬──────────────┬──────────────┬────────────┐ │
│  │ gateway      │ proxy（通用）│ dps_proxy ⚙️ │ llm_proxy  │ │
│  │              │              │ rag_proxy     │            │ │
│  │              │              │ memory_proxy  │            │ │
│  └──────────────┴──────────────┴──────────────┴────────────┘ │
│  支撑模块：identity｜tenant｜org｜protocol_headers｜auth       │
│           audit｜logs｜observability｜storage｜config｜dict   │
│  本版改动面 ⚙️：dps_proxy 路由扩展（+10 端点）                │
└───────────────────────────┬──────────────────────────────────┘
                            │ 四头注入 ＋ 4xx/5xx 语义透传
┌───────────────────────────▼──────────────────────────────────┐
│ 外部系统  DPS v2.11.x 🔗（10 端点 /api/v2/portrait/）          │
│           OpenLLM 🔗（AI 复核的 LLM 能力通道，经 llm_proxy）   │
└──────────────────────────────────────────────────────────────┘
```

### 1.2 技术栈（沿用，无本版演进）

| 层 | 技术 | 本版 |
|----|------|:----:|
| 前端 | Vue ＋ TypeScript ＋ Vite（`openbase-ui`） | 无演进 |
| 后端 | Python ＋ FastAPI（`openbase` 模块化单体） | 无演进 |
| 身份/租户 | 四头注入（`protocol_headers`）＋ 单键隔离（`tenant`） | **无新增隔离键** |
| 外部集成 | HTTP（`httpx`，经各 proxy 模块） | 新增 10 端点路由 |

---

## 2. 后端架构设计（⚙️ 轨道）

### 2.1 `dps_proxy` 模块扩展

| 项 | 设计 |
|----|------|
| 现有路由 | **实测 12 个**（`GET/POST /portraits`、`GET/PUT /portraits/{id}`、`POST /portraits/calculate`、`GET/POST /tags/categories`、`PUT/DELETE /tags/categories/{id}`、`GET /reports/overview`、`GET /batch/tasks/{id}`、`GET /audit/logs`、`GET /health`） |
| **本版新增** | **10 个**（DT-01）：`POST /template-packages/export`、`POST /template-packages/import`、`GET /templates/{code}/diff`、`POST /templates/{code}/rollback`、`GET /templates/{code}/preflight`、`GET /lineage/tags/{tag_code}`、`GET /lineage/impact`、`GET /measures/suggest`、`POST /annotation-adapters/{adapter_id}/generate`、`GET /scoring-types` |
| 转发机制 | 复用既有 `_forward(method, path, headers, request)`（`dps_proxy/__init__.py:253`），不新写 HTTP 客户端 |
| 身份注入 | 复用 `_build_identity_headers()`（`:96-113`）—— **唯一改动面是配置**（见 §5.2） |

> ⚠️ **口径校准（本版登记）**：规划与需求文档此前表述「**既有 8 端点**」，**实测为 12 个路由（11 业务 ＋ 1 health）**。推断「8」为 v1.4.5 首次交付口径，后续版本增至 11 业务端点。**本文档以实测为准**；相关表述将在设计评审中统一（属**文档校准，非功能变更**）。

### 2.2 路由注册顺序约束（DT-04，**强制**）

| 约束 | 理由 | 落点 |
|------|------|------|
| **静态路径必须先于动态路径** | DPS 契约 §5 明确「静态路由须先于 `/portrait/{person_id}` 注册」 | proxy 侧路由挂载顺序；Step 3 须加**路由映射断言测试**（对照契约矩阵） |
| **包端点用独立前缀 `template-packages`** | 避免 `export`／`import` 被解析为 `{code}` | 同上 |
| `/lineage`／`/measures`／`/scoring-types` 为静态段 | 同上 | 同上 |

### 2.3 依赖方向与分层纪律

```text
openbase-ui  →  openbase（应用层）
                 ├── modules/dps_proxy  →  protocol_headers（身份构造）
                 │                      →  proxy（通用转发件）
                 └── modules/llm_proxy  →  OpenLLM
```

**约束（沿用 `AGENTS.md` §1）**：路由层不写业务逻辑；`dps_proxy` 不直连数据库（透传）；身份构造**只经** `protocol_headers`（单一事实源）。

---

## 3. 前端架构设计（🎨 轨道）

### 3.1 目录与职责（沿用现况）

| 层 | 现状 | 本版增量 |
|----|------|----------|
| `core/api/` | `http.ts`／`error.ts`／`dps.ts`／`llm.ts`／`rag.ts`／… | **`dps.ts` 扩展 10 端点调用**（DT-01／DT-13） |
| `core/router/` | `index.ts`（＋ `legacyRedirects.ts`） | 新增 DPS 模块 8 页面路由 |
| `core/stores/` | `auth`／`moduleRegistry`／`ui` | 复用，不新增全局 store（页面级状态内聚） |
| `modules/`／`pages/` | 模块与页面 | **新增 DPS 模块 8 页面**（P-01~P-08）（DT-05~12） |

### 3.2 数据层设计（DT-13 mock 真实化）

| 项 | 设计 |
|----|------|
| 目标 | DPS 模块范围内页面 **100% 真实 API**，无 mock 常量 |
| 做法 | 页面 → `core/api/dps.ts` → `core/api/http.ts` → 后端 `/api/v1/proxy/dps/...`（**前端不直连 DPS**） |
| 边界 | **仅 DPS 模块**；其余子系统保持登记（BR-1410-09） |
| 验证 | 代码检索（无 mock 常量）＋ 联调实测（AC-13） |

### 3.3 错误呈现架构（DT-14，**含 A-1410-03 裁定**）

| 项 | 设计 |
|----|------|
| 统一错误模型 | 复用 `core/api/error.ts`：按 `code` 分支呈现（**400／401／403／404／409／422／503**） |
| **不静默降级** | 5xx／上游不可用 → 明确不可用提示 ＋ 重试入口（NFR-06） |
| 状态矩阵 | 8 态 × 8 页（见 UI 设计文档；P-08 的 409 已按 D-1410-01 移除） |
| **影响面 `basis` 呈现** | **采折叠/气泡**（A-1410-03 裁定）：默认收起，点「口径」图标展开原文；**审计导出时提供完整原文**，满足契约 §3.7「可复核、非隐式」 |

---

## 4. 第三方集成架构（🔗 轨道）

### 4.1 集成边界

| 项 | 设计 |
|----|------|
| 上游 | **DPS v2.11.x**（10 端点，契约 v1.2.0） |
| 通道 | 统一经 `dps_proxy`；**前端零直连** |
| 鉴权链 | `IdentityGate → TenantGate → PermissionGate`（**fail-closed**；缺标识 **401**） |
| 超时/降级 | 503 语义原样透传（**不阻塞人工路径**）；上游不可用不静默降级 |
| 契约缺口 | 本版**契约完备、无缺口**；若确需 DPS 配合改动 → **可直接实施**（D-1410-02） |

### 4.2 身份链路（**A-1410-02 落地**）

```text
前端会话 → openbase/identity → protocol_headers.build_outbound_headers()
   ├── X-User-ID   ← 有效主体
   ├── X-Tenant-ID ← tenant_code（＋ tenant_value_map）
   ├── X-Org-ID    ← org_value_map 命中值，否则回落 = X-Tenant-ID（OB-8 别名）
   └── X-User-Role ← 有效角色（dps 默认 "user"）
```

| 设计约束 | 内容 |
|----------|------|
| **① 单键隔离** | `tenant_code` 是唯一隔离维度，**本版不新增隔离键** |
| **② 别名语义** | `X-Org-ID` 为 tenant 的**可映射别名**（基准 B2） |
| **③ 映射必要** | DPS 要求 org 有效 ⇒ **须配 `dps_org_map`／`dps_code_map`** 传真 org（P1 联调前置） |
| **④ 强模式必须关闭** | **`enforce_org_alias` 须保持 `False`** —— 其 True 时**强制 org == tenant**（`inject.py:198-208`），与传真 org **互斥**；且 DPS 侧 org／tenant 本就是不同 code ⇒「org == tenant」不可行 |

---

## 5. 关键设计决策（ADR 摘要，详见 2.3 轨）

| # | 决策 | 备选 | 理由与后果 |
|:-:|------|------|------------|
| **AD-1** | **代理转发，不直连** | 前端直连 DPS | 复用既有四头注入与隔离口径；前端零密钥（BR-01／PS-02） |
| **AD-2** | **4xx/5xx 语义原样透传** | 统一转 500 | 契约 §4 语义丰富（400／403／404／409／422／503）；转 500 会丢失可判性（BR-03） |
| **AD-3** | **AI 复核走 OpenLLM 通道**（经 `llm_proxy`） | 让 DPS 补端点 | **A-1410-01 用户裁定**；不扩 DPS 范围、复用既有 LLM 网关能力 |
| **AD-4** | **org 映射传真，不用强模式** | 开 `enforce_org_alias` | 强模式要求 org == tenant，与 DPS 两级模型冲突（§4.2-④） |
| **AD-5** | **`basis` 折叠呈现** | 常显／不显 | **A-1410-03 用户裁定**：兼顾可复核（契约要求）与界面简洁 |
| **AD-6** | **不新增 DPS 端点、不改其内部模型** | 改造 DPS | 契约完备；改造破坏其 `organization→tenant` 外键（D-1410-02 边界） |

---

## 6. 兼容性设计（DT-21）

| 兼容项 | 要求 | 验证 |
|--------|------|------|
| 既有 **12 路由**（实测）行为 | **不变**（仅新增） | 既有用例回归（AC-02） |
| 既有画像 2 页 | 行为不变、不回归 | 前端用例 ＋ E2E |
| 身份头集 | **不新增头**（沿用四头 ＋ 控制头） | 代码检索 |
| 配置兼容 | 新增配置项**均可选**（缺省即现有行为） | 配置缺省回归 |

---

## 7. 部署拓扑（Dev 目标环境，详见部署架构草案）

```text
Dev 环境
├── openbase（应用服务）—— 本版落点（dps-proxy 扩展）
├── openbase-ui（静态构建产物 dist-v1.4.10）
├── DPS v2.11.x（本机可启动：cd DPS\src; python -m uvicorn main:app）  ← D3 已验证
└── 共享基础设施（.env.shared-infra：PostgreSQL／Redis）
```

| 项 | 设计 |
|----|------|
| 目标环境 | **Dev**（Test／Pro 另行排期，与 v1.4.8／v1.4.9 同口径） |
| 回滚 | **配置回滚为首选**（本版**无 DB 迁移**；后端与前端产物均可按版本回退） |
| 发布形态 | `main` ＋ tag `v1.4.10`，**三远程（origin＋backup＋github）** |

---

## 8. 架构风险

| # | 风险 | 级别 | 缓解 |
|:-:|------|:----:|------|
| 1 | **`dps_org_map` 未配** ⇒ DPS 401／归属校验失败 | **P1** | 联调前置（核对报告 §4-#1 已实证未配） |
| 2 | 误开 `enforce_org_alias` ⇒ org≠tenant 直接 403 | **P1** | **列为本版设计约束**（§4.2-④）；配置审查 |
| 3 | 路由顺序错误（`{code}` 吞掉 `export`） | P2 | 强制顺序约束（§2.2）＋ Step 3 断言测试 |
| 4 | `llm_proxy` 转发链路未验证（AI 复核） | P2 | 设计阶段核对 `llm_proxy` 现状（待办） |
| 5 | 既有端点口径「8 vs 12」文档漂移 | P3 | 已校准（§2.1）；评审中统一表述 |

---

## 9. 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|------|------|--------|----------|
| v1.0.0 | 2026-09-29 | AA-OpenBase-Dev | 初始创建（v1.4.10 Step 2 §2.2 产出）：**架构总览**（四层 ＋ 本版改动面标注）；**技术栈**（无演进）；**后端架构** —— `dps_proxy` 扩展（**实测既有 12 路由 ＋ 新增 10 端点**，含**「8 端点」口径校准**）／**路由注册顺序强制约束**／依赖方向纪律；**前端架构** —— 目录职责、数据层 mock 真实化（DT-13）、**错误呈现含 A-1410-03 折叠气泡裁定**；**第三方集成架构** —— 集成边界、**身份链路含 A-1410-02 四条设计约束**（含 `enforce_org_alias` 必须关闭）；**关键决策 AD-1~AD-6**；**兼容性设计 4 项**；**部署拓扑**（Dev ＋ 回滚）；**架构风险 5 项**。状态 [Review]。 |
