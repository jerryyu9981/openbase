# OpenBase API 接口设计文档 - v1.4.8

| 项 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.8（会话编排前置与回写闭环） |
| 文档版本 | v1.0.0 |
| 状态 | [Approved]（2026-09-21 人工批准） |
| 作者 | DA-OpenBase-Dev |
| 创建日期 | 2026-09-21 |
| 更新日期 | 2026-09-21 |
| 存放 | doc/design/ |
| 上游依据 | 《开发需求文档-v1.4.8》§4.4/§9、《系统架构设计文档-v1.4.8》§4.4、《会话编排派单-OpenLLM-v1.2.0》§2.1、《api-contract-management》方法论 |
| 契约原则 | **API 契约为唯一事实源**；新增字段一律**可选**，缺省保持既有行为（缺省→按用户记账） |

---

## 1. 契约全景

| 接口 | 归属 | 变更类型 | 本仓是否实施 |
|------|------|----------|:------------:|
| `OpenLLMChatRequest` | OpenLLM 网关入口 | **新增可选字段** `session_id` | ❌（OpenLLM 仓） |
| `/chat`（同步）`/chat/stream`（流式） | OpenLLM 网关 | 共用步骤 + 回写补齐（行为变更，第零段不改输出） | ❌（OpenLLM 仓） |
| 回写回执查询 | OpenLLM WritebackStore | 新增可查接口（受理状态/序号/被丢弃项） | ❌（OpenLLM 仓） |
| 计量回执批量导出 | OpenLLM `routing_trace` | 新增批量导出契约 | ❌（OpenLLM 仓） |
| 前端发消息提交 | openbase-ui `llm.ts` | **新增** `session_id` 字段提交 | ❌（openbase-ui 仓，D2） |
| OpenBase 网关 `llm_chat` | 本仓 `llm_proxy` | **零改动**（原样透传请求体） | ✔（本仓验证） |

---

## 2. 请求契约变更：`OpenLLMChatRequest` 新增 `session_id`

### 2.1 变更说明

| 项 | 内容 |
|----|------|
| 变更对象 | `OpenLLMChatRequest`（`openllm_gateway.py:909-927` 定义） |
| 新增字段 | `session_id`：`str | None = None`（**可选**） |
| 语义 | 多轮对话的会话轴标识；标识同一会话的多条消息 |
| 缺省行为 | 未提交 → 退化为**按用户记账**（保持既有调用方行为不变） |
| 约束 | `session_id` **不携带凭据类信息**（脱敏；需求 §7）；长度/字符集由 OpenLLM 仓回填限制 |
| 追溯 | AC-148-04-2、DT-148-C2 |

```json
{
  "model": "auto",
  "messages": [ { "role": "user", "content": "..." } ],
  "session_id": "sess-0001"
}
```

### 2.2 兼容性

* 未传 `session_id`：请求体与 v1.4.7 完全一致 → 既有调用方零感知。
* OpenBase 网关 `llm_chat(payload)` 原样透传 → **新增字段直接透传，无网关改动**（`llm_proxy/__init__.py:355-366`）。

---

## 3. 响应契约

* `/chat` / `/chat/stream` 响应结构**不因本版本改变**（第零段不改变对话输出；AC-148-01-2）。
* 流式回写补齐后，SSE 事件语义与缓存命中在两路径一致（AC-148-03-1/3；SSE 事件契约沿用 `OpenLLM-SSE事件契约-v1.0.0`）。

---

## 4. 回写回执查询契约（DT-148-C2，第一批起必需）

| 项 | 内容 |
|----|------|
| 目的 | 三路回写 `accepted/duplicated/failed`、投递 `seq`、被丢弃项可查（AC-148-05-2） |
| 实现 | WritebackStore 提供查询能力（按 `session_id` / `request_id` 过滤） |
| 数据集 | 每回写项：`target`、`status`、`seq`、`dropped_items`、`created_at` |
| 保证 | 回写回执覆盖率 **100%**（每条回写均产生回执） |

---

## 5. 计量回执批量导出契约（DT-148-C1，第零段）

| 项 | 内容 |
|----|------|
| 目的 | 按 `request_id` + `session_id` 批量导出计量字段（AC-148-01-1） |
| 字段 | `routing_trace` 计量字段集（见数据库 §3.1） |
| 输出 | 可批量导出，供工装 7 汇总脚本计算指标 |

---

## 6. 跨仓契约（openbase-ui，D2 另行派单）

| 项 | 内容 | 依据 |
|----|------|------|
| 前端改动 | 发消息时提交 `{ model, messages, session_id? }`（`llm.ts:101/113`） | 需求 §8/§9 |
| 会话标识来源 | 由前端会话生命周期维护（新建会话生成、复用会话续传） | D2 |
| 缺省退化 | 前端缺省不提交 → OpenLLM 按用户记账 | 需求 §8 |
| 约束 | 历史已随 `messages` 提交，前端**无需**改造历史传输 | 需求 §9 |

> 前端仅为**接口层配合**（提交会话标识），**无界面交互改造**。

---

## 7. 错误码与异常

* 本版本 **不新增权限码**（需求 §7）；新增字段可选，缺省不引入新错误路径。
* 回写通道失败**不向调用方抛错**（异步 + 退避，不影响主链路；AC-148-05-3）。
* 组件不可用降级不报错（`ComponentUnavailableError` + degraded 标记）。
* 流式回写若不可行（R3 前置核实结论）→ **显式写入契约**，不得静默缺失（AC-148-03-3）。
* 错误响应统一格式 `{code, message, detail, request_id}`（AGENTS.md §2）。

---

## 8. 修订历史

| 版本 | 日期 | 修改人 | 修改摘要 |
|------|------|--------|----------|
| v1.0.0 | 2026-09-21 | DA-OpenBase-Dev | 初始创建。定义 v1.4.8 API 契约：`OpenLLMChatRequest` 新增可选 `session_id`、响应不变、回写回执查询、计量导出、openbase-ui 跨仓会话标识配合；OpenBase 网关零改动（原样透传）。状态 [Review] |