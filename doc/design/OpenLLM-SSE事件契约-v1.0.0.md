# OpenLLM-SSE事件契约-v1.1.0

| 属性 | 值 |
|------|-----|
| 文档编号 | OB-INTG-LLM-SSE-v1.1.0 |
| 版本 | v1.1.0 |
| 状态 | [Review] |
| 日期 | 2026-09-04 |
| 作者 | AD-OpenBase-Dev |
| 版本主题 | OpenLLM SSE 事件格式统一契约（M4）+ need_profile/profile_source 可选上报字段（need_* 统一编排 v0.4.0） |
| 适用范围 | OpenLLM 全 SSE 输出端（对话流/拉流）+ OpenBase llm-proxy 透传 + 前端 parseSseStream |

> 本契约是 OpenLLM SSE 流式输出的唯一格式依据（任务书 OpenBase-OpenLLM对接完善任务书 M4 实施产出）。对接方（OpenBase llm-proxy、前端、第三方客户端）按本契约消费，无需按端点特判。

## 修订历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|---------|
| v1.1.0 | 2026-09-04 | AD（跨项目分析） | routing 事件新增可选字段 need_profile/profile_source（仅上报，不改变旧客户端语义；画像组件化后 profile_source 反映真实来源 dps/skipped） |
| v1.0.0 | 2026-09-02 | AD-OpenBase-Dev | 初始版本：以网关 chat/stream 为基线，统一 chat-stream/*、local-models/pull 输出格式 |

---

## 1. 统一契约

### 1.1 事件序列

对话流事件序列（标准）：

```
event: routing   （1 次，首个事件）
event: chunk     （0~N 次，增量文本）
event: done      （1 次，终态）
```

error 事件可随时中断序列（替代 done 成为终态）：

```
event: routing → event: chunk ×N → event: error
```

usage 可独立事件（`event: usage`）或并入 done.data.usage；对话流默认并入 done。

### 1.2 事件与 data 字段结构

| 事件名 | data 字段 | 说明 |
|--------|-----------|------|
| `routing` | `components: {need_memory, need_rag, reason, rag_source?}`, `model: {selected, reason}`, `parallel: bool` | 路由决策（首事件） |
| `routing`（v1.1.0 扩展） | `components.need_profile?: bool`、`components.profile_source?: "dps"\|"skipped"` | **内存/进程内上报字段，仅追加可选键**：画像组件化后标记画像是否注入及真实来源（dps=注入成功；skipped=未启用/降级/空数据）；旧客户端忽略未知字段，语义零感知 |
| `chunk` | `delta: str` | 增量文本；可选扩展字段（id/model/index 等） |
| `done` | `usage: {prompt_tokens, completion_tokens}`, `request_id: str` | 流结束 + 用量；允许扩展字段 |
| `error` | `code: str/int`, `message: str` | 错误中断；code 见 §3 |
| `usage` | `prompt_tokens, completion_tokens, total_tokens?` | 独立用量事件（可选） |
| `function_call` / `metadata` | 业务扩展字段 | 工具调用/元数据（可选，不改变主序列） |

### 1.3 线格式

统一采用标准 SSE 线格式：

```
event: <event_name>
data: <json>

```

- `data` 为**裸 JSON 对象**（不含 event_type/data/trace_id/timestamp 包裹层）。
- 事件间以空行分隔；流式传输 `Content-Type: text/event-stream`。

## 2. 端点输出规格

| 端点 | 路径 | 输出 |
|------|------|------|
| 统一网关对话流 | `POST /openllm/v1/chat/stream` | routing → chunk×N → done（error 中断）；契约基线实现 |
| 流式聊天 V1 | `GET /api/v1/chat-stream/stream`、`POST /api/v1/chat-stream/stream` | chunk×N → done（无 routing，直连 Provider；error 中断） |
| 流式聊天 V2 | `POST /api/v1/chat-stream/stream/v2` | 同上（POST JSON 请求体） |
| 本地模型拉取 | `POST /api/v1/local-models/pull?stream=true` | chunk×N（进度 JSON 原文）→ done `{status:"done"}`；error 中断 |
| OpenAI 兼容补全 | `POST /api/v1/chat/completions`（stream=true） | **例外**：保持 OpenAI 标准 `data:` 格式（`data: {...}` / `data: [DONE]`），供标准 OpenAI SDK 客户端使用 |

> 说明：OpenAI 兼容端点（/chat/completions）为协议兼容例外，不改写为自定义 event 格式；统一契约由其余对话流端点提供。

## 3. 错误码（error 事件 code）

| code | 含义 |
|------|------|
| 1001 | 鉴权失败 |
| 2001 | 模型不可用/不存在 |
| 4005 | 参数/模式不支持 |
| 5001 | 内部错误（通用消息，防信息泄露） |
| `model_not_found` / `service_unavailable_error` / `insufficient_quota` / `stream_error` / `invalid_request_error` | 业务级错误（chat-stream 端点） |
| `pull_error` | 模型拉取失败（local-models/pull） |

## 4. 消费者兼容性

- **OpenBase llm-proxy**（`openbase/modules/llm_proxy/_forward_sse`）：逐事件透传，不解析 data 内容 → 无需修改。
- **OpenBase 前端**（`openbase-ui/src/core/api/llm.ts parseSseStream`）：按 `event:` 名分发，不解析 data 结构 → 无需修改；消费 routing/chunk/done/error 的页面逻辑沿用 data 字段。
- **第三方 OpenAI SDK 客户端**：使用 `/chat/completions`（保持 OpenAI 格式），不受影响。

## 5. 验证方法

| 检查 | 命令/操作 | 预期 |
|------|-----------|------|
| 契约单测 | `python -m pytest tests/unit/services/test_sse_adapter.py` | 14 用例通过（事件名/字段结构/OpenAI 兼容） |
| 网关事件序列 | `POST /openllm/v1/chat/stream` | routing→(chunk×N)→done 或 error 中断 |
| chat-stream error | `POST /api/v1/chat-stream/stream/v2?model=不存在` | `event: error` + `{code, message}` |
| pull 错误降级 | `POST /api/v1/local-models/pull`（Ollama 不可达） | `event: error` + `{code: "pull_error", message}` |
| OpenAI 兼容 | `POST /api/v1/chat/completions`（stream=true） | `data: {...}` / `data: [DONE]` 格式不变 |

## 6. 遗留事项

- `sse_adapter.to_openai_format` 为 OpenAI 兼容端点保留；`adapt()` 已统一产出 `chunk` 事件（TOKEN 旧枚举移除）。
- 网关 chat/stream 的事件构造仍为内联 f-string，字段结构与契约一致；后续可重构复用 `sse_adapter` 统一构造器（非必须）。
