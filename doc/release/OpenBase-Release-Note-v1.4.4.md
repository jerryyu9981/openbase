# OpenBase Release Note - v1.4.4

| 项 | 内容 |
|----|------|
| 版本 | v1.4.4 |
| 发布日期 | 2026-08-31 |
| 版本类型 | 功能版本（系统对接线第 2 站） |
| 标签 | git tag v1.4.4（commit 2dde2c6，origin + backup 双远程已推送） |

## 1. 版本主题

**OpenRAG 系统对接**（1.4.x 逐个系统对接线第 2 站，共 4 站）：OpenBase 经 rag-proxy 代理访问 OpenRAG v1.8.0（8010），实现知识库管理、文档上传（异步轮询）、RAG 查询（检索 + 生成 + SSE 流式）真实闭环，前端知识库管理/RAG 对话 2 页真实化。

## 2. 新增功能

| 功能 | 说明 |
|------|------|
| rag-proxy 模块 | 12 端点（collections 4 + documents 4 + query 3 + health 1），OpenBase JWT 唯一认证入口（未认证 401），无上游认证注入（OpenRAG 无认证），统一响应 {code,message,data,timestamp}，{detail} 归一化（str/dict/list 全形态），SSE start/token/done 逐事件透传，multipart 文档上传原始体透传 |
| 前端 2 页真实化 | 知识库管理页（真实列表/新建/详情/删除/文档上传 PENDING→轮询）、RAG 对话页（知识库选择/SSE 流式回答/来源引用/流式中止） |
| 配置 | settings 新增 rag_upstream_base（http://127.0.0.1:8010）/rag_upstream_timeout/rag_stream_timeout；无 rag_api_key（OpenRAG 无认证） |
| 对接完善任务书 | OpenRAG 侧 M1~M6 待完善项登记（认证体系/错误格式/状态枚举/双前缀/查询契约/部署依赖） |

## 3. 变更摘要

| 类别 | 变更 |
|------|------|
| 后端 | 新增 openbase/modules/rag_proxy/（12 端点 + Pydantic schema）；settings/demo_app 注册 rag_proxy；tests/test_rag_proxy.py（22 用例） |
| 前端 | 新增 src/core/api/rag.ts（13 方法 + fetch adapter SSE）；改造 KnowledgeAdminView.vue/ChatView.vue；补齐 admin/console 路由 |
| 文档 | Step 0~5 全流程文档（规划/需求/设计/开发/测试/运维）+ OpenRAG 对接完善任务书 v1.0.0 |

## 4. 质量指标

| 指标 | 值 |
|------|-----|
| 全量回归 | 100%（无失败，4 跳过有说明） |
| rag_proxy 覆盖率 | 94% |
| API 测试 | 22/22（pytest）+ 22/22（真实链路三要素） |
| L3 冒烟 | 22/22 |
| 上线验证 | 6/6 |
| 静态质量 | ruff 0 错 / vite build 通过 |

## 5. 已知限制

| 项 | 说明 |
|----|------|
| RAG 真实检索命中 | Qdrant 向量库未启动（vector_store down），检索降级返回（如"未找到相关信息"），任务书 M6 |
| 创建知识库 | Qdrant down 时上游 500（DB 落库 + Qdrant 建集失败）→ proxy 归一化透传；同名 409 |
| 文档上传终态 | 依赖 embedding 模型 + Qdrant（M6），当前返回 pending/error（sha256 去重） |
| OpenLLM 对话页 SSE | v1.4.3 既有缺陷（TD-新增-011，浏览器端 XHR 假流式），后续版本修复 |

## 6. 升级说明

| 项 | 内容 |
|----|------|
| 升级路径 | 自 v1.4.3 平滑升级（新增模块 + 配置，无破坏性变更、无数据库变更） |
| 配置要求 | `.env` 新增 OPENBASE_RAG_UPSTREAM_BASE（默认 http://127.0.0.1:8010）；OpenRAG 以 OPENRAG_API_PORT=8010 启动 |
| 兼容性 | 既有 llm-proxy/memory-proxy/gateway 无回归（全量测试通过） |
| 回滚 | git tag v1.4.3 一键回滚（代码）；无数据库迁移，无数据回滚需求 |

## 7. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-31 | DO-OpenBase-Dev | 初始创建：v1.4.4 OpenRAG 对接发布说明（rag-proxy 12 端点 + 前端 2 页真实化） |
