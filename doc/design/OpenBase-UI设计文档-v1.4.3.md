# OpenBase UI 设计文档 - v1.4.3

| 项目 | 内容 |
|------|------|
| 项目名称 | OpenBase（开放底座） |
| 版本号 | v1.4.3 |
| 文档版本 | v1.0.0 |
| 状态 | [Review] |
| 作者 | UI-OpenBase-Dev |
| 创建日期 | 2026-08-30 |
| 存放 | doc/design/ |

---

## 1. 设计范围

| 项 | 内容 |
|----|------|
| 页面 | 模型管理页（`Models.vue`）、对话管理页（`Conversations.vue`）——OpenLLM 模块 2 页 mock 真实化 |
| 设计基线 | 统一前端 Design Token（tokens.css）+ Element Plus 组件库 + v1.4.2 记忆管理页交互模式 |
| 不涉及 | 其他 OpenLLM 页面（保持现状 mock/占位）；全局布局/主题不变 |

## 2. 原型设计说明

### 2.1 模型管理页（/openllm/models）

| 区域 | 现状（mock） | 改造后（真实） | 交互状态 |
|------|-------------|---------------|---------|
| 工具栏 | 搜索框 + 状态筛选 + 新增按钮 | 保留；新增按钮按 OpenLLM 能力适配（写操作评估，缺口登记任务书） | 加载态：搜索防抖 |
| 表格 | 本地 mock 数据 | GET /api/v1/llm-proxy/models 真实数据（名称/Provider/类型/能力/定价/状态/更新时间） | 加载态：表格 loading；空态：无模型提示；错误态：请求失败提示 + 重试 |
| 行操作 | 详情/编辑/删除（本地） | 详情（GET models/{id}）；编辑/删除按能力适配或禁用 | 表单提交态：对话框确认中禁用 |
| 对话框 | 新增/编辑表单 | 保留骨架，提交行为按端点能力适配 | 成功态：保存成功提示 |

### 2.2 对话管理页（/openllm/conversations）

| 区域 | 现状（mock） | 改造后（真实） | 交互状态 |
|------|-------------|---------------|---------|
| 工具栏 | 搜索 + 模型筛选 + 新建 + 导出 + 批量删除 | 保留搜索/模型筛选/新建；导出/批量删除按会话端点能力适配 | 加载态 |
| 表格 | 本地 mock | GET /api/v1/llm-proxy/conversations 真实数据（标题/模型/消息数/开始时间/Token） | 加载态/空态/错误态 |
| 行操作 | 聊天/归档/删除（本地） | 聊天（进入对话视图，SSE 流式）；归档（POST archive）；删除（DELETE） | 表单提交态/成功态 |
| 聊天视图 | 无（现状仅表格） | 会话内聊天：POST /llm-proxy/chat/stream SSE 流式展示（增量渲染） | 加载态：流式连接中；错误态：流中断提示 + 重试 |

### 2.3 交互状态清单（供 Step 4 断言）

| 状态 | 说明 | 断言用途 |
|:-----|:-----|:---------|
| 空态 | 模型/会话无数据展示（el-empty「暂无数据」） | E2E 空列表断言 |
| 错误态 | 请求失败展示（el-message 错误提示 + 页面重试按钮） | E2E 错误提示断言 |
| 加载态 | 数据加载中（表格 loading + 按钮禁用） | E2E 加载指示断言 |
| 成功态 | 新建/归档/删除成功（el-message success 提示） | E2E 成功提示断言 |
| 表单提交态 | 提交中禁用（按钮 loading） | E2E 提交状态断言 |
| 流式态 | SSE 对话中（输入禁用 + 增量渲染 + 停止按钮） | E2E 流式渲染断言 |

## 3. 设计系统说明

| 项 | 规范 |
|----|------|
| 颜色 | 沿用 tokens.css Design Token（primary #409EFF 系 / 语义色 success/warning/danger）；模型状态标签（在线=success、离线=info、部署中=warning、异常=danger） |
| 字体 | 沿用统一前端字体栈（Noto Sans CJK SC 回退） |
| 组件 | Element Plus：el-table/el-tag/el-dialog/el-input/el-select/el-button/el-popconfirm/el-empty/el-message |
| 间距/布局 | 沿用 ob-table-scroll 容器 + page-toolbar 工具栏模式（与 v1.4.2 记忆管理页一致） |
| 交互模式 | 列表页工具行 + 表格 + 行操作（link 按钮）+ 二次确认（popconfirm）+ 反馈（message） |

## 4. 前端实现要点（移交 Step 3）

| # | 要点 | 说明 |
|---|------|------|
| 1 | API 层封装 | 新增 `src/core/api/llm.ts`：`fetchModels` / `fetchModelDetail` / `sendChat`（含 SSE 流式 fetch）/ `listConversations` / `createConversation` / `archiveConversation` / `deleteConversation` / `listMessages` / `getLlmHealth`，统一走 http.ts（OpenBase JWT 自动附加） |
| 2 | SSE 解析 | 新增 `parseSSEStream` 工具：基于 fetch ReadableStream 解析 `event:`/`data:`，按 routing/chunk/done 分发回调；chunk 增量追加渲染；done 收尾（usage 展示） |
| 3 | Models.vue 改造 | data 源替换为 `fetchModels()`；detail 走 `fetchModelDetail()`；新增/编辑/删除按钮按能力开关（`llmWriteEnabled` 配置，默认 false→禁用并提示登记任务书） |
| 4 | Conversations.vue 改造 | data 源替换为 `listConversations()`；新建 → `createConversation()`；归档/删除 → 对应端点；聊天 → 对话抽屉/视图内嵌 `sendChat(stream:true)` |
| 5 | 密钥隔离 | 前端代码零 OpenLLM 密钥/零上游地址（全部经 llm-proxy）；新增代码无 sk-openllm- 字样 |

## 5. 原型（prototype/index.html）

| 项 | 内容 |
|----|------|
| 产出 | `doc/design/prototype/index.html` 设计总览首页（file:// 直接打开） |
| 内容 | 页面导航卡片：模型管理页 / 对话管理页 / 交互状态说明 / API 契约索引 |
| 链接 | 相对路径，指向本 UI 文档 + 原型状态清单 |

## 6. 修订历史

| 版本 | 日期 | 修改人 | 摘要 |
|------|------|--------|------|
| v1.0.0 | 2026-08-30 | UI-OpenBase-Dev | 初始创建：模型管理/对话管理 2 页真实化设计（原型说明/交互状态清单/设计系统/前端实现要点 + SSE 解析） |
