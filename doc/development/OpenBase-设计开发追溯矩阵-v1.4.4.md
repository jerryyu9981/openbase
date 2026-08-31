# OpenBase 设计开发追溯矩阵 TD-ID - v1.4.4

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.4 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | AD-OpenBase-Dev |
| 创建日期 | 2026-08-31 |
| 存放 | doc/development/ |

---

## 1. 追溯矩阵（DT → TD → 文件）

| DT-ID（设计项） | TD-ID（开发项） | BL-ID | 涉及文件 | 状态 |
|----------------|-----------------|-------|----------|:----:|
| DT-144-01 OpenRAG 服务部署 | TD-144-01 OpenRAG 8010 启动 + 健康检查 + 端口治理 | BL-144-01 | OpenRAG 项目（OPENRAG_API_PORT=8010 + 临时库）；启动验证 | ✅ 完成（8010 启动，health 透传，database up / vector_store down 登记 M6） |
| DT-144-02 认证边界（OpenBase 唯一认证入口） | TD-144-02 settings rag_* 配置 + AVAILABLE_MODULES 注册 + JWT 门禁 | BL-144-02/03 | `openbase/settings.py`（rag_upstream_base/timeout/stream_timeout + "rag_proxy" 注册）；`openbase/demo_app.py`（enable_module） | ✅ 完成（401 门禁冒烟验证） |
| DT-144-03 rag-proxy 转发适配（知识库族） | TD-144-03 rag_proxy 模块：collections 4 端点 | BL-144-03 | `openbase/modules/rag_proxy/__init__.py`（新建）；`tests/test_rag_proxy.py`（新建） | ✅ 完成（列表/创建/详情/删除 + 22 单测） |
| DT-144-03 rag-proxy 转发适配（文档族） | TD-144-04 rag_proxy 模块：documents 4 端点（multipart/列表/详情/删除） | BL-144-03 | `openbase/modules/rag_proxy/__init__.py`（_forward_multipart + 文档详情） | ✅ 完成（详情端点按需求 §4.3 补足，偏差 D1） |
| DT-144-03 rag-proxy 转发适配（查询族 + SSE） | TD-144-05 rag_proxy 模块：query 3 端点（查询/SSE/检索） | BL-144-03 | `openbase/modules/rag_proxy/__init__.py`（_forward_sse start/token/done + collection_ids 透传） | ✅ 完成（真实 SSE 流式验证，偏差 D2） |
| DT-144-03 错误归一化 + 健康 | TD-144-06 rag_proxy 模块：health + {detail} 归一化 + 统一响应 | BL-144-03 | `openbase/modules/rag_proxy/__init__.py`（_adapt_response：detail str/dict/list） | ✅ 完成（冒烟 409/422/404 归一化验证） |
| DT-144-04 前端 2 页真实化（API 层） | TD-144-07 rag.ts API 客户端（13 方法 + SSE fetch adapter） | BL-144-04 | `openbase-ui/src/core/api/rag.ts`（新建） | ✅ 完成（queryStream fetch adapter，偏差 D3） |
| DT-144-04 前端 2 页真实化（知识库管理页） | TD-144-08 KnowledgeAdminView 真实化（列表/新建/详情/删除/文档上传轮询） | BL-144-04 | `openbase-ui/src/modules/knowledge/pages/KnowledgeAdminView.vue`（改造） | ✅ 完成（真实数据 + 状态大小写容错 L-144-01） |
| DT-144-04 前端 2 页真实化（RAG 对话页） | TD-144-09 ChatView 真实化（知识库选择/SSE 流式/来源引用/中止） | BL-144-04 | `openbase-ui/src/modules/knowledge/pages/ChatView.vue`（改造）+ `index.ts`（路由补齐） | ✅ 完成（SSE 流式真实渲染） |
| DT-144-05 双系统联调 | TD-144-10 联调闭环（登录→知识库→文档→RAG 查询/SSE） | BL-144-05 | 联调验证（L3 冒烟 22/22 + 浏览器走查） | ✅ 完成（真实链路闭环；Qdrant 依赖登记 M6） |
| DT-144-06 对接完善任务书 | TD-144-11 OpenRAG 对接完善任务书 | BL-144-06 | `doc/design/OpenBase-OpenRAG对接完善任务书-v1.0.0.md`（新建） | ✅ 完成（M1~M6 登记） |
| DT-144-07 收尾还债 | TD-144-12 回归/覆盖率/发布准备 | BL-144-07 | 全量 pytest + ruff + build + 债务归集 | ✅ 完成（回归 ✅；覆盖率随 Step 4） |

## 2. Subtask CheckList（子任务状态表）

| 子任务 | 设计规划文件操作 | 实际状态 | 偏差 |
|--------|------------------|:--------:|------|
| TD-144-02 配置 | settings.py 新增 rag_* 3 项 + AVAILABLE_MODULES 注册 | ✅ 完成 | 无 |
| TD-144-02 挂载 | demo_app.py enable_module 追加 "rag_proxy" | ✅ 完成 | 无 |
| TD-144-03~06 模块 | 新建 openbase/modules/rag_proxy/__init__.py（12 端点） | ✅ 完成 | 比设计清单多 1 端点（文档详情，需求 §4.3，D1） |
| TD-144-03~06 测试 | 新建 tests/test_rag_proxy.py（22 用例） | ✅ 完成 | 无 |
| TD-144-07 API 层 | 新建 openbase-ui/src/core/api/rag.ts | ✅ 完成 | queryStream 用 fetch adapter（D3） |
| TD-144-08 页面 | KnowledgeAdminView.vue 改造 | ✅ 完成 | 状态大小写容错（L-144-01 已修复） |
| TD-144-09 页面 | ChatView.vue 改造 + index.ts 路由 | ✅ 完成 | 补齐 admin/console 路由（导航缺口） |
| TD-144-11 任务书 | 新建 doc/design/OpenBase-OpenRAG对接完善任务书-v1.0.0.md | ✅ 完成 | 无 |

## 3. 版本控制记录（分支策略 + commit 约定）

| 项 | 内容 |
|----|------|
| 分支策略 | git-flow（沿用项目既有约定）：本次开发在 `feature/v1.4.4-openrag` 分支，完成后合并 develop |
| commit 格式 | `type(scope): subject`，footer 引用 TD-ID（如 `refs TD-144-03`） |
| TDD 合规 | feat/fix 提交必须包含对应测试文件变更；测试先于生产代码提交 |
| 备份 | 提交前 .devflow hooks（post-push）自动备份；重要节点打标 |

## 4. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-31 | AD-OpenBase-Dev | 初始创建：DT→TD 追溯矩阵（12 项）、Subtask CheckList、版本控制记录 |
| v1.0.1 | 2026-08-31 | AD-OpenBase-Dev | Step 3 完成状态更新：TD-144-01~12 全部 ✅（联调闭环 + 任务书 + 债务归集）；记录偏差 D1（文档详情端点）/D2（collection_ids）/D3（fetch adapter） |
