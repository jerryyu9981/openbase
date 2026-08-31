# OpenBase 单版本规划文档 - v1.4.4

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.4 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | PM-OpenBase-Dev |
| 创建日期 | 2026-08-30 |
| 更新日期 | 2026-08-30 |
| 存放 | doc/version/releases/v1.4.4/ |

---

## 1. 版本概述

### 1.1 版本定位

| 项 | 内容 |
|----|------|
| 版本主题 | OpenRAG 系统对接（1.4.x 逐个系统对接线第 2 站，共 4 站） |
| 版本类型 | 系统对接增量版本 |
| 基线 | v1.4.3（Step 5 已部署发布，全流程闭环） |
| 周期 | 2 周（Phase 1 OpenRAG 服务接入 + Phase 2 认证边界/proxy 转发 + Phase 3 前端真实化 + Phase 4 联调收尾） |

### 1.2 背景与问题

| # | 问题 |
|---|------|
| ① | VC-011 对接线第 2 站：v1.4.4 OpenRAG（v1.4.3 OpenLLM → v1.4.4 OpenRAG → v1.4.5 DPS → v1.5 统一集成测试 + 平台治理） |
| ② | v1.4.3 已沉淀 OpenLLM 对接模式（服务端口规划 + proxy 转发 + 统一响应 + SSE 透传 + 前端真实化 + 联调），v1.4.4 OpenRAG 对标复用 |
| ③ | **关键差异**：OpenRAG v1.8.0 HTTP API 无认证（设计文档《OpenRAG-API接口设计文档-v2.1.2》声称 API Key 认证但代码未实现）→ OpenBase 代理层为唯一认证入口（JWT 门禁），无需注入上游认证 |
| ④ | OpenRAG 以 `OPENRAG_API_PORT=8010` 启动（默认 8000，与 OpenBase 错开）；健康检查 `/api/v1/system/health`（PG+Qdrant）；OpenAPI 文档无条件开放（优于 OpenLLM DEBUG 限制） |
| ⑤ | 响应格式两种并存（{code,message,data,timestamp} 成功 + {detail} 错误）→ proxy 需归一化；文档上传为异步（PENDING → 轮询状态） |

### 1.3 版本目标

| 目标 ID | 目标 | 验收指标 |
|---------|------|---------|
| G1 | OpenRAG 服务就绪 | OpenRAG 以 8010 启动，`/api/v1/system/health` 健康检查通过（PG/Qdrant 依赖可用），与 OpenBase 8000 并存 |
| G2 | 认证边界打通 | OpenBase 统一 JWT 门禁（rag-proxy 未认证 401）；OpenRAG 侧认证补强需求登记任务书 |
| G3 | rag-proxy 转发适配 | OpenRAG 核心端点经 OpenBase 代理 ≥6 个（知识库列表/详情/创建/删除、文档上传/列表/删除、RAG 查询/检索），统一响应 {code,message,data,timestamp} 适配 + {detail} 错误归一化透传 |
| G4 | 前端真实化 | OpenRAG 相关页 mock/占位替换真实 API（走 rag-proxy），核心页：知识库管理/RAG 对话 |
| G5 | 双系统联调闭环 | OpenBase 统一认证 → OpenRAG 知识库→文档→RAG 查询真实闭环；集成测试 + UAT 走查 |

### 1.4 不包含范围

| # | 内容 | 说明 |
|---|------|------|
| ① | DPS 对接 | v1.4.5 完成 |
| ② | 四系统统一集成测试 | 集中 v1.5（VC-011） |
| ③ | R-376 团队管理 / R-377 智能体管理 | 顺延 v1.5 |
| ④ | OpenRAG 前端功能补全（R-313~R-317 历史条目） | 本版本仅接入核心可走查页（知识库管理/RAG 对话 2 页） |
| ⑤ | OpenRAG 侧认证体系落地（代码实现） | 登记任务书，本版本 OpenBase 侧 JWT 门禁兜底 |
| ⑥ | OpenLLM M1/M2 遗留 | 随任务书实施（不阻塞本版本） |

## 2. 需求来源

| 来源 | 说明 |
|------|------|
| VC-011（2026-08-30 用户决策） | 对接线第 2 站 v1.4.4 OpenRAG |
| v1.4.3 对接模式复用（R-379 沉淀） | 端口规划 + proxy 转发 + 统一响应 + SSE 透传 + 前端真实化 + 联调 |
| 候选需求池 §1.10（R-380，本版本登记） | OpenRAG 系统对接（v1.4.4，P1） |
| 候选需求池 §1.3（R-313~R-317） | OpenRAG 前端功能历史条目（v1.3.0 目标），本版本仅取核心子集 |

## 3. 范围

### 3.1 包含范围（四 Phase）

**Phase 1：OpenRAG 服务接入（0.5 周）** —— `OPENRAG_API_PORT=8010` 启动 OpenRAG v1.8.0，健康检查（/api/v1/system/health）、依赖可用性（PG/Qdrant）、端口治理

**Phase 2：认证边界 + rag-proxy 转发（0.5 周）** —— OpenBase JWT 门禁（rag-proxy 未认证 401）；rag-proxy 转发（知识库列表/详情/创建/删除、文档上传/列表/删除、RAG 查询核心端点；统一响应适配 + {detail} 归一化 + SSE 流式透传 start/token/done）

**Phase 3：前端真实化（0.5 周）** —— 知识库管理/ RAG 对话 2 页 mock/占位替换真实 API（走 rag-proxy）

**Phase 4：联调收尾（0.5 周）** —— 双系统联调（知识库→文档上传→RAG 查询闭环）、集成测试、UAT 走查、回归 + 覆盖率、Step 4/5 文档、发布

### 3.2 关键差异（vs v1.4.3 OpenLLM 对接）

| 维度 | OpenLLM（v1.4.3） | OpenRAG（v1.4.4） |
|------|-------------------|-------------------|
| 上游认证 | API Key Bearer 注入 | 无认证（OpenBase 唯一认证入口） |
| 端口 | PORT=8001 | OPENRAG_API_PORT=8010 |
| 错误格式 | 网关数值码（1001 等） | {code,message,data} + {detail} 并存（归一化） |
| SSE 事件 | routing/chunk/done | start/token/done |
| OpenAPI | DEBUG 限制 | 无条件开放 |

## 4. 版本成功指标

| 指标 | 目标 |
|------|------|
| OpenRAG 服务 | 8010 健康检查通过（/api/v1/system/health），PG/Qdrant 依赖可用 |
| proxy 端点 | 核心业务端点经 OpenBase 代理 ≥6 个，统一响应 + {detail} 归一化正确 |
| 前端真实化 | 知识库管理/ RAG 对话 2 页 mock/占位替换真实 API（走 proxy，无上游直连） |
| 联调闭环 | OpenBase 统一认证 → 知识库→文档→RAG 查询真实闭环 |
| 质量门槛 | 全量回归通过率 ≥95%；覆盖率 ≥80%；无新增 P0/P1 缺陷；Step 4/5 文档齐备 |

## 5. 关键依赖与风险

### 5.1 依赖清单

| 依赖 | 说明 | 状态 |
|------|------|------|
| v1.4.3（基线） | 已发布，提供对接模式沉淀（R-379） | ✅ 已满足 |
| OpenRAG 后端 | v1.8.0，`OPENRAG_API_PORT=8010` 启动，健康检查可用 | 待验证 |
| OpenRAG 基础设施 | PG（本机 SQLite 可切换）+ Qdrant | 待验证 |
| OpenBase 网关服务发现 | rag 服务循环探测骨架已具备 | ✅ 已具备 |

### 5.2 风险清单

| 风险 | 级别 | 缓解计划 |
|------|:---:|----------|
| OpenRAG 无认证（设计文档与代码不一致） | P1 | OpenBase JWT 唯一认证入口；OpenRAG 侧认证补强登记任务书（M 级） |
| 8010 启动失败/依赖重（PG/Qdrant） | P2 | 健康检查先行；本机 SQLite 降级；端口冲突检测 |
| 错误格式不统一（{detail}） | P2 | proxy 归一化（body.code > body.detail > HTTP 状态码） |
| v1.3 双前缀路由（/api/v1/api/v1/*） | P2 | 避免使用 v1.3 端点，仅用 /api/v1 标准路由 |
| 文档上传异步（PENDING） | P2 | 前端轮询文档状态；proxy 透传 status |
| SSE 事件格式（start/token/done） | P2 | 联调专项验证逐事件透传 |

## 6. 规划评审结论

| 项 | 结论 |
|----|------|
| 目标可衡量 | ✅ G1~G5 均有量化验收指标 |
| 范围边界 | ✅ 包含 4 Phase + 不包含 6 项均已定义 |
| P0/P1 覆盖 | ✅ 本版本无 P0；P1 项均有 Backlog 条目（BL-144-01~07） |
| 还债容量 | BL-144-07（收尾与还债）占 1/7 ≈ 14%，与 Step 4 测试阶段合并执行（实际 ≥15%），PM 已批准 |
| 评审结论 | 待批准（[Review] → [Approved]） |

## 7. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-30 | PM-OpenBase-Dev | 初始创建：v1.4.4 OpenRAG 对接规划（4 Phase、G1~G5、关键差异 vs v1.4.3、风险 6 项） |
