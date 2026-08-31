# OpenBase 代码逻辑审查记录 - v1.4.4

## 基本信息

- 项目：OpenBase（开放底座）
- 版本 / 迭代：v1.4.4（OpenRAG 对接，R-380）
- 审查对象：`openbase/modules/rag_proxy/__init__.py`、`openbase/settings.py`、`openbase/demo_app.py`、`tests/test_rag_proxy.py`、`openbase-ui/src/core/api/rag.ts`、`openbase-ui/src/modules/knowledge/pages/KnowledgeAdminView.vue`、`ChatView.vue`、`knowledge/index.ts`
- 关联需求：`doc/requirements/OpenBase-开发需求文档-v1.4.4.md`（FR-144-01~09 / AC-144-01~07）
- 关联设计：`doc/design/OpenBase-系统架构设计文档-v1.4.4.md`（ADR-144-01~04）、`doc/design/OpenBase-API接口设计文档-v1.4.4.md`
- 审查时间：2026-08-31
- 审查结论：**有条件通过**（P1 已修复；P2/P3 已记录）

## 审查范围

后端 rag_proxy 模块（12 端点：知识库族 4 + 文档族 4 + 查询族 3 + 健康 1）、settings 注册与配置、demo_app 挂载、22 个单测；前端 rag.ts API 层、知识库管理页/ RAG 对话页真实化、路由补齐。静态质量证据（ruff + 全量 pytest + 前端 build）与开发自测证据（L3 冒烟 22/22）齐备。

## 需求覆盖

| 需求项 | 实现位置 | 证据 | 结论 | 备注 |
|---|---|---|---|---|
| BL-144-01 OpenRAG 8010 部署 | OpenRAG 启动（OPENRAG_API_PORT=8010） | L3 冒烟 health 透传 + /docs 可用 | ✅ | SQLite 沙箱写限制 + Qdrant down 登记 |
| BL-144-02 认证边界 | rag_proxy 全端点 get_current_user | 单测 401×2 + 冒烟 401 | ✅ | 无上游认证注入 |
| BL-144-03 rag-proxy 转发 | 12 端点 + 统一响应 + {detail} 归一化 + SSE | 单测 22 + 冒烟 | ✅ | 见设计偏差 D1/D2 |
| BL-144-04 前端 2 页真实化 | rag.ts + 2 页面改造 + 路由 | 浏览器验证（真实数据/SSE 流式） | ✅ | fetch adapter（D3） |
| BL-144-05 双系统联调 | L3 冒烟真实链路 | 22/22 | ✅ | 知识库/文档/查询/SSE 真实闭环 |
| BL-144-06 对接完善任务书 | TD-144-11 | 待产出（本记录同步完成） | ⬜ | 本审查后立即产出 |
| BL-144-07 收尾还债 | 全量回归 + ruff + build | 全部通过 | ✅ | 覆盖率随 Step 4 |

## 设计一致性

| 设计项 | 实现情况 | 偏差 | 影响 | 处理建议 |
|---|---|---|---|---|
| ADR-144-01 独立 rag_proxy 模块 | ✅ 独立包 + `/api/v1/rag-proxy` 前缀 | 无 | - | - |
| ADR-144-02 OpenBase 唯一认证入口 | ✅ JWT 门禁 + 零上游注入 | 无 | - | - |
| ADR-144-03 错误归一化 + SSE | ✅ detail str/dict/list + 网关码 + SSE 逐事件 | 无 | - | - |
| ADR-144-04 前端改造 | ✅ 2 页真实化 + 统一 API 层 | 无 | - | - |
| 设计 11 端点清单 | 实现 12 端点（含文档详情） | D1：需求 §4.3 轮询契约端点遗漏于设计清单，按需求补足 | 无（新增向后兼容） | 已记录 TD-ID + DevLogReport |
| 查询请求体契约 | 增加 collection_ids 可选字段 | D2：OpenRAG 上游 query 契约要求 collection_ids | 无（可选字段） | 已记录 |
| SSE 浏览器消费 | rag.ts 使用 `adapter: 'fetch'` | D3：XHR 不支持 responseType stream，fetch adapter 返回真实 ReadableStream | 无（修复而非偏差） | 已记录 |

## 问题清单

| ID | 级别 | 类型 | 位置 | 问题 | 影响 | 建议 |
|---|---|---|---|---|---|---|
| L-144-01 | P1 | 状态流转 | KnowledgeAdminView.vue（uploadStatusText/pollDocumentStatus/docStatusType） | 上游文档状态返回小写（pending/processing/completed/failed），前端按大写比较，轮询无法识别完成态 | 文档上传轮询超时 60 次后误报"处理超时" | 已修复：状态统一 toUpperCase 比较 |
| L-144-02 | P2 | 可维护性 | `openbase-ui/src/core/api/llm.ts`（v1.4.3 既有） | sendChatStream 使用 responseType 'stream' + XHR adapter，浏览器端不返回 ReadableStream，SSE 走非流式兜底 | v1.4.3 对话页流式为假流式（本版本 rag 侧已用 fetch adapter 修复） | 登记技术债务，后续版本统一修复 llm 侧 |
| L-144-03 | P2 | 兼容性 | 路由挂载（main.ts/动态 addRoute） | console 存在 "Parent route not found" 路由 warn（模块路由动态注册模式） | 页面可正常访问，非阻塞 | 记录，不阻塞 |
| L-144-04 | P3 | 健壮性 | KnowledgeAdminView.vue loadHealth | health.components 值可为嵌套对象，已修复展示 status 字段 | 无（已修复） | - |

## 静态质量检查证据

| 检查项 | 命令或方式 | 结果 | 备注 |
|---|---|---|---|
| 语法 / Lint | `python -m ruff check openbase tests` | ✅ All checks passed | - |
| 后端测试 | `python -m pytest tests` | ✅ 全量通过（22 rag_proxy 用例） | - |
| 前端类型 / 构建 | `npm run build`（vue-tsc + vite） | ✅ built（0 error） | - |
| 一致性核对 | 设计文档 12 端点 ↔ 实现 ↔ rag.ts | ✅ 路径/方法/参数/响应对齐 | D1/D2 偏差已记录 |

## 自测证据

| 检查项 | 命令或方式 | 结果 | 备注 |
|---|---|---|---|
| 单元测试 | `python -m pytest tests/test_rag_proxy.py` | ✅ 22 passed | 401/列表/创建/{detail}/SSE/不可达/multipart |
| L1 构建 | ruff + vite build | ✅ | 前后端 |
| L2 启动 | OpenBase 8000 + OpenRAG 8010 + vite 5173 | ✅ | 健康检查通过 |
| L3 冒烟 | smoke_v144.py | ✅ 22 passed / 0 failed | 真实链路（登录→知识库→文档→查询→SSE） |
| 浏览器验证 | 知识库管理页/RAG 对话页走查 | ✅ | 真实数据 + SSE 流式回答渲染 |

## 修复与复审

| 问题 ID | 修复方式 | 复审结果 | 备注 |
|---|---|---|---|
| L-144-01 | 状态比较 toUpperCase（3 处） | ✅ 复审通过（重新 build 验证） | - |

## 剩余风险

1. L-144-02（P2）：llm.ts SSE 浏览器端兜底，登记技术债务（TD 待登记至技术债务总表），后续版本修复。
2. OpenRAG 上游环境：SQLite 沙箱写限制（当前临时库可写）、Qdrant down（向量库不可用，RAG 检索降级）→ 登记《OpenRAG 对接完善任务书》M 项 + Step 5 部署环境验证。
3. OpenRAG 文档状态小写、`{detail}` 数组错误格式、query 契约 collection_ids 必需 → 登记任务书（上游契约对齐）。

## 最终结论

P0/P1 已全部闭环（L-144-01 已修复复审通过）；P2/P3 已记录不阻塞。静态质量证据与自测证据齐备，设计偏差 D1/D2/D3 已记录。**允许进入开发审计**。
