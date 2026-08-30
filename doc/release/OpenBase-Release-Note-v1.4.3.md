# OpenBase Release Note - v1.4.3

| 项 | 内容 |
|----|------|
| 版本 | v1.4.3 |
| 发布日期 | 2026-08-30 |
| 版本类型 | 功能版本（系统对接线第 1 站） |
| 标签 | git tag v1.4.3（origin + backup 双远程已推送） |

## 1. 版本主题

**OpenLLM 系统对接**（1.4.x 逐个系统对接线第 1 站，共 4 站）：OpenBase 经 llm-proxy 代理访问 OpenLLM v2.13.0（8001），实现模型列表/详情/对话（含 SSE 流式）真实闭环，前端模型管理/对话管理 2 页真实化。

## 2. 新增功能

| 功能 | 说明 |
|------|------|
| llm-proxy 模块 | 12 端点（models/models{id}/chat/chat-stream/health/conversations 族），OpenLLM API Key Bearer 注入，统一响应 {code,message,data,timestamp}，错误码透传（1001/1003/1004/2001/5001），SSE 逐事件透传 |
| 前端 2 页真实化 | 模型管理页（真实模型数据）、对话管理页（真实会话 + SSE 流式聊天） |
| 配置 | settings 新增 llm_api_key/llm_upstream_base/llm_upstream_timeout/llm_stream_timeout（.env 覆盖） |
| 对接完善任务书 | OpenLLM 侧 M1~M6 待完善项登记（会话 API Key 通道/模型写操作/身份头/SSE 统一/local_models 鉴权/openapi 开放） |

## 3. 变更摘要

| 类别 | 变更 |
|------|------|
| 后端 | 新增 openbase/modules/llm_proxy/（12 端点）；settings/demo_app 注册 llm_proxy；tests/test_llm_proxy.py（18 用例） |
| 前端 | 新增 src/core/api/llm.ts（9 方法 + parseSseStream）；改造 Models.vue/Conversations.vue；更新 module-pages.spec.ts |
| 文档 | Step 0~5 全流程文档（规划/需求/设计/开发/测试/运维 6 类 30+ 份） |

## 4. 质量指标

| 指标 | 值 |
|------|-----|
| 全量回归 | 250/250 = 100% |
| llm_proxy 覆盖率 | 84% |
| 前端测试 | 35/35 |
| 上线验证 | 8/8 |
| 静态质量 | ruff 0 错 / vue-tsc 0 错 / build 通过 |

## 5. 已知限制

| 项 | 说明 |
|----|------|
| 会话管理页 | OpenLLM 会话端点 JWT 通道（M1 待 OpenLLM 侧完善），当前 401 透传降级 |
| 模型写操作 | 需 OpenLLM 管理员 JWT（M2 待完善），当前只读 + 提示 |
| 对话真实回复 | 需 OpenLLM 侧可用模型（本地 Ollama 运行或云端 Key） |

## 6. 升级说明

- 配置：.env 新增 `OPENBASE_LLM_API_KEY` / `OPENBASE_LLM_UPSTREAM_BASE`（注意 OPENBASE_ 前缀）
- 依赖：OpenLLM v2.13.0 以 PORT=8001 启动
- 无数据库迁移（无新增表）
