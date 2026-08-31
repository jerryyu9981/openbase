# OpenBase 单版本规划文档 - v1.4.5

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.5 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | PM-OpenBase-Dev |
| 创建日期 | 2026-08-31 |
| 更新日期 | 2026-08-31 |
| 存放 | doc/version/releases/v1.4.5/ |

---

## 1. 版本概述

### 1.1 版本定位

| 项 | 内容 |
|----|------|
| 版本主题 | DPS 系统对接（1.4.x 逐个系统对接线第 3 站，共 4 站） |
| 版本类型 | 系统对接增量版本 |
| 基线 | v1.4.4（Step 5 已部署发布，全流程闭环） |
| 周期 | 2 周（Phase 1 DPS 服务接入 + Phase 2 认证边界/身份头注入/proxy 转发 + Phase 3 前端真实化 + Phase 4 联调收尾） |

### 1.2 背景与问题

| # | 问题 |
|---|------|
| ① | VC-011 对接线第 3 站：v1.4.5 DPS（v1.4.3 OpenLLM → v1.4.4 OpenRAG → v1.4.5 DPS → v1.5 统一集成测试 + 平台治理） |
| ② | v1.4.4 已沉淀 OpenRAG 对接模式（服务端口规划 + proxy 转发 + 统一响应 + {detail} 归一化 + 前端真实化 + 联调），v1.4.5 DPS 对标复用 |
| ③ | **关键差异 A（认证形态）**：DPS v2.7.1 HTTP API 采用「Header 身份直传 + RBAC 中间件」认证——请求必带 `X-Org-ID` + `X-Tenant-ID` + `X-User-ID`（+X-User-Role），组织/租户须预存在库（platform.organization/tenant active）；`/api/v2/auth/login` 端点未实际实现（仅中间件白名单）→ OpenBase 统一 JWT 门禁 + **身份头注入**（从 OpenBase JWT/用户上下文构造三头） |
| ④ | **关键差异 B（端口变量）**：DPS 端口环境变量为 `API_PORT`（默认 8000，无 PORT/DPS_API_PORT）→ 启动时 `API_PORT=8030` 与 OpenBase 8000 错开；入口 `src/rest_api/app.py`（PYTHONPATH=src） |
| ⑤ | **关键差异 C（无 SSE）**：DPS 无 HTTP SSE/流式端点（stream_engine 为后台任务管理，非 SSE）→ dps-proxy 无需 SSE 透传逻辑（简化） |
| ⑥ | 响应格式：成功 `{code:200, message:"success", data}`；404 例外 FastAPI `{detail}` → proxy 需归一化；健康检查 `/health/liveness`、`/health/readiness`（白名单免鉴权） |

### 1.3 版本目标

| 目标 ID | 目标 | 验收指标 |
|---------|------|---------|
| G1 | DPS 服务就绪 | DPS 以 API_PORT=8030 启动，`/health/liveness` 健康检查通过，与 OpenBase 8000 并存 |
| G2 | 认证边界打通 | OpenBase 统一 JWT 门禁（dps-proxy 未认证 401）；身份头注入验证（X-Org-ID/X-Tenant-ID/X-User-ID 由 OpenBase 侧构造，DPS 组织/租户存在性校验通过）；DPS 侧认证体系补强登记任务书 |
| G3 | dps-proxy 转发适配 | DPS 核心端点经 OpenBase 代理 ≥6 个（画像计算/画像查询/标签分类/报表统计/批量状态/审计日志），统一响应 {code,message,data,timestamp} 适配 + {detail} 错误归一化透传 |
| G4 | 前端真实化 | DPS 画像模块核心页 mock 替换真实 API（走 dps-proxy），核心页：画像列表/画像详情 |
| G5 | 双系统联调闭环 | OpenBase 统一认证 + 身份头注入 → DPS 画像→标签→报表真实闭环；集成测试 + UAT 走查 |

### 1.4 不包含范围

| # | 内容 | 说明 |
|---|------|------|
| ① | 四系统统一集成测试 | 集中 v1.5（VC-011） |
| ② | R-376 团队管理 / R-377 智能体管理 | 顺延 v1.5 |
| ③ | DPS 前端功能补全（R-322~R-326/R-331/R-359 历史条目） | 本版本仅接入核心可走查页（画像列表/画像详情 2 页） |
| ④ | DPS 侧认证体系落地（代码实现） | 登记任务书，本版本 OpenBase 侧 JWT 门禁 + 身份头注入兜底 |
| ⑤ | 四维身份专项（已挂起） | 本版本身份头注入采用 OpenBase 既有 JWT org_id + 用户上下文构造，四维统一方案专项处理 |
| ⑥ | OpenLLM/OpenRAG M 项遗留 | 随任务书实施（不阻塞本版本） |

## 2. 需求来源

| 来源 | 说明 |
|------|------|
| VC-011（2026-08-31 登记） | 对接线第 3 站：DPS 系统对接（R-381，P1） |
| 候选需求池 §1.11 | R-381 DPS 对接（复用 R-380 OpenRAG 对接模式，差异：Header 身份认证 + 无 SSE） |
| 历史条目 | R-322~R-326/R-331/R-359 保持原排期（不纳入本版本） |

## 3. 技术债务清单（0.0a 跨版本债务审查）

| 债务 ID | 级别 | 状态 | 本版本计划 |
|---------|:---:|:---:|-----------|
| TD-新增-011 | P2 | 待偿还 | **纳入本版本偿还**：llm.ts SSE 与 rag.ts 对齐 fetch adapter（低成本高价值，前端 SSE 统一） |
| TD-新增-012 | P1 | 待偿还 | 不纳入：OpenRAG 侧 M1~M6 需 OpenRAG 独立会话实施（任务书跟踪） |
| TD-001/002/004 | P1/P2 | 待偿还/挂起 | 不纳入：回灌/模块版本/AI 规则，随 v1.5 统一治理评估 |
| TD-新增-009/010 | P2/P1 | 待偿还 | 不纳入：pytest 环境问题 / OpenLLM JWT 用户映射（任务书跟踪） |

**还债容量检查**：本版本还债 1 项（TD-新增-011）/ 总需求约 6 项（BL-145-01~06）= 16.7% ≥ 15% ✅

## 4. 版本成功指标

| 指标 | 目标值 | 度量方式 |
|------|:------:|----------|
| dps-proxy 端点数量 | ≥6 | Step 2 API 契约核对 |
| 未认证 401 门禁 | 100% 端点 | Step 4 API 测试 |
| 身份头注入正确率 | 100%（联调通过） | Step 4 集成测试 |
| 前端真实化页数 | 2 页 | UAT 走查 |
| 全量回归通过率 | ≥95% | Step 4 回归 |
| rag_proxy 覆盖率（新代码） | ≥80% | pytest --cov |

## 5. 版本发布策略草案

| 项 | 内容 |
|----|------|
| 发布方式 | Dev 直接部署（源码更新 + 服务重启），与 v1.4.4 一致 |
| 发布窗口 | 2026-08-31 起 2 周内 |
| 回滚策略 | git tag v1.4.4 一键回滚（无 DB 变更） |
| 兼容策略 | 无破坏性变更；DPS 数据为上游系统，不落 OpenBase 库 |

## 6. 版本依赖清单

| 依赖 | 类型 | 状态 |
|------|------|:---:|
| DPS 项目（D:\Trae CN\myproject\Dev\DPS，v2.7.1） | 外部系统 | ✅ 已存在（调研完成） |
| DPS 数据库（PostgreSQL 或 SQLite 降级） | 外部依赖 | ✅ SQLITE_FALLBACK 可用 |
| DPS 组织/租户种子数据 | 数据依赖 | ⚠️ 需联调确认（X-Org-ID/X-Tenant-ID 对应组织/租户须存在） |
| OpenBase JWT org_id 字段 | 内部依赖 | ✅ 已签发（auth login extra） |

## 7. 版本风险清单

| 风险 | 级别 | 缓解 |
|------|:---:|------|
| DPS 身份头注入映射不成立（OpenBase JWT 仅 org_id，缺 tenant/user 维度） | P1 | Step 1/2 预研：X-Org-ID=org_id、X-Tenant-ID=org_id 或配置映射、X-User-ID=当前用户 ID；预研结论固化到 API 契约 |
| DPS 组织/租户须预存在库（无则 401/403） | P1 | 联调前种子组织/租户数据；OpenBase 侧可配置默认组织 |
| DPS 无统一认证（login 未实现） | P1 | OpenBase 统一 JWT 门禁 + 身份头注入兜底；DPS 侧认证登记任务书 |
| DPS 响应格式混合（{code,message,data} + {detail}） | P2 | proxy {detail} 归一化（复用 rag_proxy 模式） |
| DPS 端口变量 API_PORT 与 OpenBase 8000 冲突 | P2 | API_PORT=8030 启动 + 端口检测 |

## 8. 范围变更记录（本版本）

| 版本 | 变更 | 说明 |
|------|------|------|
| v1.0.0 | 初始规划 | 无变更（R-381 单需求拆解 Backlog） |

## 9. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-31 | PM-OpenBase-Dev | 初始创建：DPS 对接规划（R-381，目标 G1~G5、范围/排除、债务清单、成功指标、发布策略、依赖、风险） |
